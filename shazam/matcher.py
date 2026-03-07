"""Hash lookup and time-alignment scoring for audio matching."""

from collections import defaultdict
from shazam.audio import decode_audio
from shazam.fingerprint import fingerprint
from shazam.database import Database
from shazam.config import MIN_ALIGNED_HASHES, FAN_VALUE


def match_snippet(snippet_path: str, db: Database, top_n: int = 10,
                  fan_value: int = FAN_VALUE) -> list[dict]:
    """Fingerprint a snippet and find matching songs.

    Returns ranked list of matches with confidence scores.
    """
    samples = decode_audio(snippet_path)
    hashes = fingerprint(samples, fan_value=fan_value)

    if not hashes:
        return []

    total_query_hashes = len(hashes)

    # Build lookup: hash -> list of query offsets
    query_map: dict[int, list[int]] = defaultdict(list)
    for h, offset in hashes:
        query_map[h].append(offset)

    # Query database
    unique_hashes = list(query_map.keys())
    db_results = db.query_hashes(unique_hashes)

    # Time-alignment scoring:
    # For each (song_id, delta) where delta = db_offset - query_offset,
    # count how many hashes align at that same delta.
    alignment: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for db_hash, song_id, db_offset in db_results:
        for query_offset in query_map[db_hash]:
            delta = db_offset - query_offset
            alignment[song_id][delta] += 1

    # Find best delta for each song, rank by count
    candidates = []
    for song_id, deltas in alignment.items():
        best_delta = max(deltas, key=deltas.get)
        count = deltas[best_delta]
        if count >= MIN_ALIGNED_HASHES:
            confidence = count / total_query_hashes
            candidates.append({
                "song_id": song_id,
                "aligned_hashes": count,
                "total_query_hashes": total_query_hashes,
                "confidence": confidence,
                "offset_delta": best_delta,
            })

    candidates.sort(key=lambda c: c["aligned_hashes"], reverse=True)
    candidates = candidates[:top_n]

    # Enrich with song info
    for c in candidates:
        song = db.get_song(c["song_id"])
        if song:
            c["filepath"] = song["filepath"]
            c["filename"] = song["filename"]
        else:
            c["filepath"] = "???"
            c["filename"] = "???"

    return candidates


def confidence_label(confidence: float) -> str:
    if confidence >= 0.20:
        return "HIGH"
    elif confidence >= 0.10:
        return "PROBABLE"
    elif confidence >= 0.05:
        return "POSSIBLE"
    else:
        return "LOW"
