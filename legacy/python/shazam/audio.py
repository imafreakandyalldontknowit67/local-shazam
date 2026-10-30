"""Decode any audio file to mono PCM samples via ffmpeg subprocess."""

import subprocess
import numpy as np
from shazam.config import SAMPLE_RATE


def decode_audio(filepath: str, max_duration: int = 120, timeout: int = 30) -> np.ndarray:
    """Decode audio file to mono float32 numpy array at SAMPLE_RATE Hz.

    Uses ffmpeg to handle every format — pipes raw PCM to stdout (no temp files).
    Only decodes the first *max_duration* seconds to cap memory usage.
    Kills ffmpeg if it doesn't finish within *timeout* seconds.
    """
    cmd = [
        "ffmpeg",
        "-i", filepath,
        "-t", str(max_duration),
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ar", str(SAMPLE_RATE),
        "-ac", "1",
        "-v", "quiet",
        "pipe:1",
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"ffmpeg timed out after {timeout}s on {filepath}") from e

    if result.returncode != 0 or len(result.stdout) == 0:
        stderr_out = result.stderr.decode(errors="replace")[:200]
        raise RuntimeError(f"ffmpeg failed on {filepath}: {stderr_out}")

    samples = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)
    samples /= 32768.0
    return samples
