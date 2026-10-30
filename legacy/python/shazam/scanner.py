"""Directory crawling and file identity hashing for incremental indexing."""

import hashlib
from pathlib import Path
from shazam.config import AUDIO_EXTENSIONS, FILE_HASH_BYTES


def file_identity_hash(filepath: str) -> str:
    """SHA-256 of first 8KB + file size — fast identity check without reading entire file."""
    p = Path(filepath)
    size = p.stat().st_size
    with open(filepath, "rb") as f:
        head = f.read(FILE_HASH_BYTES)
    h = hashlib.sha256(head + size.to_bytes(8, "little")).hexdigest()
    return h


def scan_directory(directory: str) -> list[str]:
    """Recursively find all audio files in directory by extension."""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(str(p.resolve()))
    files.sort()
    return files
