"""Decode any audio file to mono PCM samples via ffmpeg subprocess."""

import subprocess
import numpy as np
from shazam.config import SAMPLE_RATE


def decode_audio(filepath: str) -> np.ndarray:
    """Decode audio file to mono float32 numpy array at SAMPLE_RATE Hz.

    Uses ffmpeg to handle every format — pipes raw PCM to stdout (no temp files).
    """
    cmd = [
        "ffmpeg",
        "-i", filepath,
        "-f", "s16le",       # raw signed 16-bit little-endian PCM
        "-acodec", "pcm_s16le",
        "-ar", str(SAMPLE_RATE),
        "-ac", "1",          # mono
        "-v", "quiet",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed on {filepath}: {proc.stderr.decode(errors='replace')[:200]}"
        )
    if len(proc.stdout) == 0:
        raise RuntimeError(f"ffmpeg produced no output for {filepath}")

    samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32)
    # Normalize to [-1, 1]
    samples /= 32768.0
    return samples
