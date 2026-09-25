"""SQLite database for fingerprint storage and lookup."""

import sqlite3
from pathlib import Path
from shazam.config import BATCH_INSERT_SIZE

DEFAULT_DB = "shazam.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    duration REAL,
    file_hash TEXT,
    status TEXT DEFAULT 'indexed'
);

CREATE TABLE IF NOT EXISTS fingerprints (
    hash INTEGER NOT NULL,
    song_id INTEGER NOT NULL,
    offset INTEGER NOT NULL,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
CREATE INDEX IF NOT EXISTS idx_fp_song ON fingerprints(song_id);
"""


class Database:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-65536")  # 64MB
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def insert_song(self, filepath: str, filename: str, duration: float | None,
                    file_hash: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO songs (filepath, filename, duration, file_hash) VALUES (?, ?, ?, ?)",
            (filepath, filename, duration, file_hash),
        )
        self.conn.commit()
        return cur.lastrowid

    def insert_fingerprints(self, song_id: int, hashes: list[tuple[int, int]]):
        """Batch insert fingerprints. hashes = list of (hash_value, offset)."""
        rows = [(h, song_id, off) for h, off in hashes]
        for i in range(0, len(rows), BATCH_INSERT_SIZE):
            batch = rows[i:i + BATCH_INSERT_SIZE]
            self.conn.executemany(
                "INSERT INTO fingerprints (hash, song_id, offset) VALUES (?, ?, ?)",
                batch,
            )
        self.conn.commit()

    def insert_chunk(self, songs_data: list[dict]) -> int:
        """Bulk insert a chunk of songs + their fingerprints in a single transaction.

        songs_data: list of dicts with keys: filepath, filename, duration, file_hash, hashes
        Returns number of songs successfully inserted.
        """
        inserted = 0
        self.conn.execute("BEGIN")
        try:
            for song in songs_data:
                existing = self.conn.execute(
                    "SELECT id FROM songs WHERE filepath = ?", (song["filepath"],)
                ).fetchone()
                if existing:
                    song_id = existing[0]
                    self.conn.execute("DELETE FROM fingerprints WHERE song_id = ?", (song_id,))
                    self.conn.execute(
                        "UPDATE songs SET filename = ?, duration = ?, file_hash = ?, status = 'indexed' WHERE id = ?",
                        (song["filename"], song["duration"], song["file_hash"], song_id),
                    )
                else:
                    cur = self.conn.execute(
                        "INSERT INTO songs (filepath, filename, duration, file_hash) VALUES (?, ?, ?, ?)",
                        (song["filepath"], song["filename"], song["duration"], song["file_hash"]),
                    )
                    song_id = cur.lastrowid
                hashes = song["hashes"]
                if hashes:
                    rows = [(h, song_id, off) for h, off in hashes]
                    for i in range(0, len(rows), BATCH_INSERT_SIZE):
                        batch = rows[i:i + BATCH_INSERT_SIZE]
                        self.conn.executemany(
                            "INSERT INTO fingerprints (hash, song_id, offset) VALUES (?, ?, ?)",
                            batch,
                        )
                inserted += 1
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return inserted

    def query_hashes(self, hashes: list[int]) -> list[tuple[int, int, int]]:
        """Look up hashes. Returns list of (hash, song_id, offset)."""
        if not hashes:
            return []
        results = []
        batch_size = 900
        for i in range(0, len(hashes), batch_size):
            batch = hashes[i:i + batch_size]
            placeholders = ",".join("?" * len(batch))
            cur = self.conn.execute(
                f"SELECT hash, song_id, offset FROM fingerprints WHERE hash IN ({placeholders})",
                batch,
            )
            results.extend(cur.fetchall())
        return results

    def get_song(self, song_id: int) -> dict | None:
        cur = self.conn.execute(
            "SELECT id, filepath, filename, duration, file_hash, status FROM songs WHERE id = ?",
            (song_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(("id", "filepath", "filename", "duration", "file_hash", "status"), row))

    def get_all_file_hashes(self) -> set[str]:
        """Return set of all file_hash values in the database."""
        cur = self.conn.execute("SELECT file_hash FROM songs")
        return {row[0] for row in cur.fetchall()}

    def get_song_by_filepath(self, filepath: str) -> dict | None:
        cur = self.conn.execute(
            "SELECT id, filepath, filename, duration, file_hash, status FROM songs WHERE filepath = ?",
            (filepath,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(("id", "filepath", "filename", "duration", "file_hash", "status"), row))

    def remove_song(self, song_id: int):
        self.conn.execute("DELETE FROM fingerprints WHERE song_id = ?", (song_id,))
        self.conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        self.conn.commit()

    def remove_songs_by_path_prefix(self, prefix: str) -> int:
        """Remove songs under a directory, without matching sibling path prefixes."""
        from os import sep

        directory = prefix.rstrip("/\\") + sep
        escaped = directory.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cur = self.conn.execute(
            "DELETE FROM songs WHERE filepath LIKE ? ESCAPE '\\'", (escaped + "%",)
        )
        self.conn.commit()
        return cur.rowcount

    def get_stats(self) -> dict:
        song_count = self.conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        fp_count = self.conn.execute("SELECT COUNT(*) FROM fingerprints").fetchone()[0]
        db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
        return {
            "songs": song_count,
            "fingerprints": fp_count,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
        }
