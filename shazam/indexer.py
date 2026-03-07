"""Parallel fingerprinting orchestrator using ProcessPoolExecutor."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from shazam.audio import decode_audio
from shazam.fingerprint import fingerprint
from shazam.scanner import file_identity_hash, scan_directory
from shazam.database import Database
from shazam.config import FAN_VALUE, FAN_VALUE_COMPACT, SAMPLE_RATE
from tqdm import tqdm


def _process_file(filepath: str, fan_value: int) -> tuple[str, str, str, float | None, list[tuple[int, int]]]:
    """Worker function: decode + fingerprint a single file.

    Returns (filepath, filename, file_hash, duration, hashes).
    Runs in a subprocess.
    """
    from pathlib import Path
    file_hash = file_identity_hash(filepath)
    filename = Path(filepath).name
    try:
        samples = decode_audio(filepath)
        duration = len(samples) / SAMPLE_RATE
        hashes = fingerprint(samples, fan_value=fan_value)
    except Exception as e:
        # Return empty hashes on decode failure — we'll skip it
        return (filepath, filename, file_hash, None, [])
    return (filepath, filename, file_hash, duration, hashes)


def bootstrap_directory(directories: list[str], db: Database, workers: int = 4,
                        compact: bool = False, show_progress: bool = True) -> dict:
    """Index all audio files in directories.

    Returns stats dict with counts of processed/skipped/failed files.
    """
    fan_value = FAN_VALUE_COMPACT if compact else FAN_VALUE

    # Collect all files
    all_files = []
    for d in directories:
        all_files.extend(scan_directory(d))

    if not all_files:
        return {"total": 0, "indexed": 0, "skipped": 0, "failed": 0}

    # Get already-indexed file hashes for incremental indexing
    existing_hashes = db.get_all_file_hashes()

    # Pre-filter: compute file hashes and skip already-indexed
    files_to_process = []
    skipped = 0
    for f in all_files:
        fh = file_identity_hash(f)
        if fh in existing_hashes:
            skipped += 1
        else:
            files_to_process.append(f)

    if not files_to_process:
        return {"total": len(all_files), "indexed": 0, "skipped": skipped, "failed": 0}

    indexed = 0
    failed = 0

    progress = tqdm(total=len(files_to_process), desc="Fingerprinting",
                    disable=not show_progress, unit="file")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_file, fp, fan_value): fp
            for fp in files_to_process
        }

        for future in as_completed(futures):
            filepath = futures[future]
            try:
                fp, filename, file_hash, duration, hashes = future.result()
                if not hashes:
                    failed += 1
                    progress.update(1)
                    continue

                song_id = db.insert_song(fp, filename, duration, file_hash)
                db.insert_fingerprints(song_id, hashes)
                indexed += 1
            except Exception:
                failed += 1
            progress.update(1)

    progress.close()

    return {
        "total": len(all_files),
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
    }
