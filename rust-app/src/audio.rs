use crate::dsp::{Landmark, Stream};
use anyhow::{bail, Context, Result};
use crossbeam_channel::bounded;
use std::{
    ffi::OsStr,
    io::{Read, Seek, SeekFrom},
    path::Path,
    process::{Child, Command, Stdio},
    thread,
    time::{Duration, Instant},
};

pub fn command(program: impl AsRef<OsStr>) -> Command {
    let mut cmd = Command::new(program);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // No extra console window for each song.
    }
    cmd
}
struct ChildGuard(Child);
impl Drop for ChildGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

pub fn fingerprint(path: &Path, fan: usize) -> Result<(Vec<Landmark>, f64)> {
    let mut errors = tempfile::tempfile()?;
    let mut child = ChildGuard(
        command("ffmpeg")
            .args([
                "-nostdin",
                "-hide_banner",
                "-v",
                "error",
                "-threads",
                "1",
                "-i",
            ])
            .arg(path)
            .args([
                "-map",
                "0:a:0",
                "-vn",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "11025",
                "-ac",
                "1",
                "pipe:1",
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(errors.try_clone()?)
            .spawn()
            .context("Cannot start FFmpeg. Install ffmpeg and add it to PATH")?,
    );
    let mut stdout = child.0.stdout.take().unwrap();
    let (tx, rx) = bounded(2);
    let reader = thread::spawn(move || {
        let mut buffer = vec![0u8; 32768];
        loop {
            let item = match stdout.read(&mut buffer) {
                Ok(0) => break,
                Ok(n) => Ok(buffer[..n].to_vec()),
                Err(e) => {
                    let _ = tx.send(Err(e));
                    break;
                }
            };
            if tx.send(item).is_err() {
                break;
            }
        }
    });
    let result = (|| -> Result<_> {
        let mut stream = Stream::new(fan)?;
        let mut pending = None;
        loop {
            match rx.recv_timeout(Duration::from_secs(60)) {
                Ok(data) => {
                    let mut data = data?;
                    if let Some(byte) = pending.take() {
                        data.insert(0, byte);
                    }
                    if data.len() % 2 != 0 {
                        pending = data.pop();
                    }
                    let pcm: Vec<_> = data
                        .as_chunks::<2>()
                        .0
                        .iter()
                        .map(|b| i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0)
                        .collect();
                    stream.push(&pcm);
                }
                Err(crossbeam_channel::RecvTimeoutError::Disconnected) => break,
                Err(_) => bail!("FFmpeg produced no data for 60 seconds: {}", path.display()),
            }
        }
        if pending.is_some() {
            bail!("Incomplete PCM sample: {}", path.display());
        }
        let deadline = Instant::now() + Duration::from_secs(60);
        let status = loop {
            if let Some(status) = child.0.try_wait()? {
                break status;
            }
            if Instant::now() > deadline {
                bail!("FFmpeg failed to exit: {}", path.display());
            }
            thread::sleep(Duration::from_millis(10));
        };
        if !status.success() || stream.sample_count == 0 {
            errors.seek(SeekFrom::Start(0))?;
            let mut detail = String::new();
            errors.take(4096).read_to_string(&mut detail)?;
            bail!("FFmpeg failed on {}: {}", path.display(), detail.trim());
        }
        Ok(stream.finish())
    })();
    drop(rx);
    drop(child); // Unblock a reader before joining it on errors.
    let _ = reader.join();
    result
}

pub fn has_audio(path: &Path) -> Result<bool> {
    let mut output = tempfile::tempfile()?;
    let mut child = ChildGuard(
        command("ffprobe")
            .args([
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
            ])
            .arg(path)
            .stdin(Stdio::null())
            .stdout(output.try_clone()?)
            .stderr(Stdio::null())
            .spawn()
            .context("FFprobe is needed to identify unfamiliar file extensions")?,
    );
    let deadline = Instant::now() + Duration::from_secs(10);
    loop {
        if let Some(status) = child.0.try_wait()? {
            output.seek(SeekFrom::Start(0))?;
            let mut text = String::new();
            output.take(4096).read_to_string(&mut text)?;
            return Ok(status.success() && text.contains("audio"));
        }
        if Instant::now() > deadline {
            bail!("FFprobe timed out: {}", path.display());
        }
        thread::sleep(Duration::from_millis(10));
    }
}
