"""Parallel fingerprinting orchestrator using ProcessPoolExecutor."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from shazam.audio import decode_audio
from shazam.fingerprint import fingerprint
from shazam.scanner import file_identity_hash, scan_directory
from shazam.database import Database
from shazam.config import FAN_VALUE, FAN_VALUE_COMPACT, SAMPLE_RATE
from tqdm import tqdm

CHUNK_SIZE = 50       # files per batch — bounds memory usage


def _process_file(filepath: str, file_hash: str, fan_value: int) -> tuple[str, str, str, float | None, list[tuple[int, int]]]:
    """Worker function: decode + fingerprint a single file.

    Returns (filepath, filename, file_hash, duration, hashes).
    Runs in a subprocess.
    """
    from pathlib import Path
    filename = Path(filepath).name
    try:
        samples = decode_audio(filepath)
        duration = len(samples) / SAMPLE_RATE
        hashes = fingerprint(samples, fan_value=fan_value)
    except Exception:
        return (filepath, filename, file_hash, None, [])
    return (filepath, filename, file_hash, duration, hashes)


def bootstrap_directory(directories: list[str], db: Database, workers: int = 4,
                        compact: bool = False, show_progress: bool = True) -> dict:
    """Index all audio files in directories.

    Processes files in chunks to bound memory usage and avoid executor queue backup.
    Returns stats dict with counts of processed/skipped/failed files.
    """
    fan_value = FAN_VALUE_COMPACT if compact else FAN_VALUE

    # Collect all files
    all_files = []
    for d in directories:
        all_files.extend(scan_directory(d))
    all_files = sorted(set(all_files))

    if not all_files:
        return {"total": 0, "indexed": 0, "skipped": 0, "failed": 0}

    # Pre-filter: compute file hashes and skip already-indexed
    existing_hashes = db.get_all_file_hashes()
    files_to_process = []  # list of (filepath, file_hash)
    skipped = 0
    failed = 0
    for f in all_files:
        try:
            fh = file_identity_hash(f)
        except OSError:
            failed += 1
            continue
        if fh in existing_hashes:
            skipped += 1
        else:
            files_to_process.append((f, fh))

    if not files_to_process:
        return {"total": len(all_files), "indexed": 0, "skipped": skipped, "failed": failed}

    indexed = 0

    progress = tqdm(total=len(files_to_process), desc="Fingerprinting",
                    disable=not show_progress, unit="file")

    # Keep one pool alive across chunks; ffmpeg has its own per-file timeout.
    with ProcessPoolExecutor(max_workers=max(1, workers)) as executor:
        for chunk_start in range(0, len(files_to_process), CHUNK_SIZE):
            chunk = files_to_process[chunk_start:chunk_start + CHUNK_SIZE]
            chunk_results = []
            futures = {
                executor.submit(_process_file, fp, fh, fan_value): fp
                for fp, fh in chunk
            }

            for future in as_completed(futures):
                try:
                    fp, filename, file_hash, duration, hashes = future.result()
                    if not hashes:
                        failed += 1
                    else:
                        chunk_results.append({
                            "filepath": fp,
                            "filename": filename,
                            "file_hash": file_hash,
                            "duration": duration,
                            "hashes": hashes,
                        })
                except Exception:
                    failed += 1
                progress.update(1)

            # Bulk insert, then retry individually without leaving half-indexed songs.
            if chunk_results:
                try:
                    indexed += db.insert_chunk(chunk_results)
                except Exception:
                    for song in chunk_results:
                        try:
                            indexed += db.insert_chunk([song])
                        except Exception:
                            failed += 1

    progress.close()

    return {
        "total": len(all_files),
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
    }
