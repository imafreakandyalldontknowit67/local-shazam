use anyhow::{bail, Result};
use rustfft::{num_complex::Complex, Fft, FftPlanner};
use serde::Serialize;
use std::{collections::VecDeque, sync::Arc};

pub const RATE: usize = 11025;
pub const FFT: usize = 1024;
pub const HOP: usize = 512;
const BINS: usize = 513;
const RADIUS: usize = 10;
const TARGET: usize = 100;
const BLOCK: usize = 2048;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Landmark {
    pub hash: u32,
    pub offset: u64,
}

pub struct Extractor {
    fft: Arc<dyn Fft<f64>>,
    window: Vec<f64>,
    scale: f64,
    scratch: Vec<Complex<f64>>,
    frame: Vec<Complex<f64>>,
}

// Reflection at an endpoint repeats that endpoint, as scipy.ndimage does.
fn reflect(mut i: isize, n: usize) -> usize {
    let n = n as isize;
    while i < 0 || i >= n {
        i = if i < 0 { -i - 1 } else { 2 * n - i - 1 };
    }
    i as usize
}

fn extrema(input: &[f32], maximum: bool) -> Vec<f32> {
    if input.is_empty() {
        return vec![];
    }
    let mut queue: VecDeque<(usize, f32)> = VecDeque::new();
    let mut output = Vec::with_capacity(input.len());
    for i in 0..input.len() + 2 * RADIUS {
        let value = input[reflect(i as isize - RADIUS as isize, input.len())];
        while let Some(&(_, back)) = queue.back() {
            if (maximum && back <= value) || (!maximum && back >= value) {
                queue.pop_back();
            } else {
                break;
            }
        }
        queue.push_back((i, value));
        while queue.front().is_some_and(|&(j, _)| j + 2 * RADIUS < i) {
            queue.pop_front();
        }
        if i >= 2 * RADIUS {
            output.push(queue.front().unwrap().1);
        }
    }
    output
}

impl Default for Extractor {
    fn default() -> Self {
        Self::new()
    }
}
impl Extractor {
    pub fn new() -> Self {
        let fft = FftPlanner::<f64>::new().plan_fft_forward(FFT);
        let window: Vec<_> = (0..FFT)
            .map(|i| 0.5 - 0.5 * (std::f64::consts::TAU * i as f64 / FFT as f64).cos())
            .collect();
        let scale = 1.0 / (RATE as f64 * window.iter().map(|v| v * v).sum::<f64>());
        let scratch = vec![Complex::default(); fft.get_inplace_scratch_len()];
        Self {
            fft,
            window,
            scale,
            scratch,
            frame: vec![Complex::default(); FFT],
        }
    }
    pub fn fingerprint(&mut self, samples: &[f32], fan: usize) -> Vec<Landmark> {
        if samples.len() < FFT {
            return vec![];
        }
        let frames = 1 + (samples.len() - FFT) / HOP;
        let mut spectrum = vec![0f32; frames * BINS];
        for t in 0..frames {
            let samples = &samples[t * HOP..t * HOP + FFT];
            let mean = samples.iter().map(|&x| x as f64).sum::<f64>() / FFT as f64;
            for (i, &x) in samples.iter().enumerate() {
                self.frame[i] = Complex::new((x as f64 - mean) * self.window[i], 0.0);
            }
            self.fft
                .process_with_scratch(&mut self.frame, &mut self.scratch);
            for f in 0..BINS {
                let power = self.frame[f].norm_sqr()
                    * self.scale
                    * if f == 0 || f == BINS - 1 { 1.0 } else { 2.0 };
                spectrum[t * BINS + f] = (10.0 * power.max(1e-10).log10()) as f32;
            }
        }
        let mut maxima = Vec::with_capacity(spectrum.len());
        let mut minima = Vec::with_capacity(spectrum.len());
        for row in spectrum.as_chunks::<BINS>().0 {
            maxima.extend(extrema(row, true));
            minima.extend(extrema(row, false));
        }
        let mut peaks = Vec::new();
        for f in 0..BINS {
            let column: Vec<_> = (0..frames).map(|t| maxima[t * BINS + f]).collect();
            let max = extrema(&column, true);
            let column: Vec<_> = (0..frames).map(|t| minima[t * BINS + f]).collect();
            let min = extrema(&column, false);
            for t in 0..frames {
                let value = spectrum[t * BINS + f];
                if value == max[t] && value - min[t] > 10.0 {
                    peaks.push((t, f));
                }
            }
        }
        peaks.sort_unstable();
        let mut hashes = Vec::with_capacity(peaks.len() * fan);
        for (i, &(t1, f1)) in peaks.iter().enumerate() {
            let mut targets = 0;
            for &(t2, f2) in &peaks[i + 1..] {
                let dt = t2 - t1;
                if dt == 0 {
                    continue;
                }
                if dt > TARGET {
                    break;
                }
                if f1.abs_diff(f2) > 200 {
                    continue;
                }
                hashes.push(Landmark {
                    hash: ((f1 as u32) << 22) | ((f2 as u32) << 12) | dt as u32,
                    offset: t1 as u64,
                });
                targets += 1;
                if targets >= fan {
                    break;
                }
            }
        }
        hashes
    }
}

pub struct Stream {
    extractor: Extractor,
    pcm: Vec<f32>,
    base: u64,
    start: u64,
    pub sample_count: u64,
    fan: usize,
    pub hashes: Vec<Landmark>,
}
impl Stream {
    pub fn new(fan: usize) -> Result<Self> {
        if !(1..=128).contains(&fan) {
            bail!("fan must be between 1 and 128");
        }
        Ok(Self {
            extractor: Extractor::new(),
            pcm: vec![],
            base: 0,
            start: 0,
            sample_count: 0,
            fan,
            hashes: vec![],
        })
    }
    fn emit(&mut self, count: usize, stop: u64) {
        for mut h in self.extractor.fingerprint(&self.pcm[..count], self.fan) {
            h.offset += self.base;
            if h.offset >= self.start && h.offset < stop {
                self.hashes.push(h);
            }
        }
    }
    pub fn push(&mut self, pcm: &[f32]) {
        self.sample_count += pcm.len() as u64;
        self.pcm.extend_from_slice(pcm);
        loop {
            let stop = self.start + BLOCK as u64;
            let needed = (stop + (TARGET + RADIUS) as u64 - self.base) as usize * HOP + FFT;
            if self.pcm.len() < needed {
                break;
            }
            self.emit(needed, stop);
            self.start = stop;
            let next_base = self.start.saturating_sub(RADIUS as u64);
            self.pcm.drain(..(next_base - self.base) as usize * HOP);
            self.base = next_base;
        }
    }
    pub fn finish(mut self) -> (Vec<Landmark>, f64) {
        self.emit(self.pcm.len(), u64::MAX);
        (self.hashes, self.sample_count as f64 / RATE as f64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn extrema_matches_naive() {
        for n in [1, 2, 7, 21, 57] {
            let v: Vec<_> = (0..n).map(|i| ((i * 17) % 13) as f32).collect();
            for maximum in [true, false] {
                let expected: Vec<_> = (0..n)
                    .map(|i| {
                        (-10..=10)
                            .map(|d| v[reflect(i as isize + d, n)])
                            .reduce(|a, b| if maximum { a.max(b) } else { a.min(b) })
                            .unwrap()
                    })
                    .collect();
                assert_eq!(extrema(&v, maximum), expected);
            }
        }
    }
    #[test]
    fn streaming_matches_whole_file() {
        let pcm: Vec<_> = (0..RATE * 110)
            .map(|i| ((i as f64 * 0.137).sin() * (i as f64 * 0.0017).sin()) as f32)
            .collect();
        let expected = Extractor::new().fingerprint(&pcm, 5);
        let mut stream = Stream::new(5).unwrap();
        for block in pcm.chunks(16001) {
            stream.push(block);
        }
        assert_eq!(stream.finish().0, expected);
    }
}
