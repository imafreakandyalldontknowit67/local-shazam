"""Spectrogram generation, peak finding, and constellation hash pair creation."""

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter, minimum_filter
from shazam.config import (
    SAMPLE_RATE, FFT_WINDOW, HOP_SIZE,
    PEAK_NEIGHBORHOOD, MIN_PEAK_AMPLITUDE,
    FAN_VALUE, TARGET_T_MIN, TARGET_T_MAX, TARGET_F_RANGE,
)


def _spectrogram(samples: np.ndarray) -> np.ndarray:
    """Generate log-power spectrogram."""
    _, _, Sxx = signal.spectrogram(
        samples,
        fs=SAMPLE_RATE,
        window="hann",
        nperseg=FFT_WINDOW,
        noverlap=FFT_WINDOW - HOP_SIZE,
        nfft=FFT_WINDOW,
    )
    Sxx = 10 * np.log10(np.maximum(Sxx, 1e-10))
    return Sxx


def _find_peaks(Sxx: np.ndarray) -> list[tuple[int, int]]:
    """Find local maxima in the spectrogram. Returns (freq_bin, time_bin) pairs."""
    size = PEAK_NEIGHBORHOOD * 2 + 1
    local_max = maximum_filter(Sxx, size=size)
    local_min = minimum_filter(Sxx, size=size)
    detected = (Sxx == local_max) & ((Sxx - local_min) > MIN_PEAK_AMPLITUDE)
    freq_idx, time_idx = np.where(detected)
    return list(zip(freq_idx.tolist(), time_idx.tolist()))


def _hash_pair(f1: int, f2: int, dt: int) -> int:
    """Create a 32-bit hash from an anchor-target peak pair.

    Layout: freq1 (10 bits) | freq2 (10 bits) | delta_t (12 bits)
    """
    return ((f1 & 0x3FF) << 22) | ((f2 & 0x3FF) << 12) | (dt & 0xFFF)


def fingerprint(samples: np.ndarray, fan_value: int = FAN_VALUE) -> list[tuple[int, int]]:
    """Generate fingerprint hashes from audio samples.

    Returns list of (hash_value, time_offset) tuples.
    """
    if len(samples) < FFT_WINDOW:
        return []

    Sxx = _spectrogram(samples)
    peaks = _find_peaks(Sxx)

    if len(peaks) < 2:
        return []

    peaks.sort(key=lambda p: (p[1], p[0]))

    hashes = []
    for i, (f1, t1) in enumerate(peaks):
        targets_found = 0
        for j in range(i + 1, len(peaks)):
            f2, t2 = peaks[j]
            dt = t2 - t1

            if dt < TARGET_T_MIN:
                continue
            if dt > TARGET_T_MAX:
                break
            if abs(f2 - f1) > TARGET_F_RANGE:
                continue

            hashes.append((_hash_pair(f1, f2, dt), t1))
            targets_found += 1
            if targets_found >= fan_value:
                break

    return hashes
