"""Regression tests for incremental indexing and database transactions."""

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from shazam.database import Database
from shazam.indexer import bootstrap_directory


def song(path, file_hash, hashes):
    return {
        "filepath": str(path),
        "filename": Path(path).name,
        "duration": 1.0,
        "file_hash": file_hash,
        "hashes": hashes,
    }


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(str(Path(self.tmp.name) / "test.db"))
        self.addCleanup(self.db.close)

    def test_reindex_replaces_fingerprints_without_duplicate_song(self):
        path = Path(self.tmp.name) / "track.mp3"
        self.db.insert_chunk([song(path, "old", [(11, 1), (12, 2)])])
        self.db.insert_chunk([song(path, "new", [(13, 3)])])
        self.assertEqual(self.db.get_stats()["songs"], 1)
        self.assertEqual(self.db.get_stats()["fingerprints"], 1)
        self.assertEqual(self.db.get_song_by_filepath(str(path))["file_hash"], "new")
        self.assertEqual(self.db.query_hashes([11, 12, 13])[0][0], 13)

    def test_failed_reindex_rolls_back_old_fingerprints(self):
        path = Path(self.tmp.name) / "track.mp3"
        self.db.insert_chunk([song(path, "old", [(11, 1)])])
        with self.assertRaises(Exception):
            self.db.insert_chunk([song(path, "new", [(None, 1)])])
        self.assertEqual(self.db.get_song_by_filepath(str(path))["file_hash"], "old")
        self.assertEqual(len(self.db.query_hashes([11])), 1)

    def test_remove_directory_does_not_match_siblings_or_like_wildcards(self):
        root = Path(self.tmp.name)
        target = root / "mix_1"
        paths = [target / "one.mp3", root / "mix_12" / "two.mp3",
                 root / "mixX1" / "three.mp3"]
        self.db.insert_chunk([song(path, str(i), [(i, 0)]) for i, path in enumerate(paths)])
        self.assertEqual(self.db.remove_songs_by_path_prefix(str(target)), 1)
        self.assertEqual(self.db.get_stats()["songs"], 2)
        self.assertEqual(self.db.get_stats()["fingerprints"], 2)

    def test_remove_large_directory(self):
        root = Path(self.tmp.name) / "collection"
        self.db.insert_chunk([song(root / f"{i}.mp3", str(i), [(i, 0)])
                              for i in range(1001)])
        self.assertEqual(self.db.remove_songs_by_path_prefix(str(root)), 1001)
        self.assertEqual(self.db.get_stats()["fingerprints"], 0)


class IndexerTests(unittest.TestCase):
    def test_modified_file_is_reindexed_and_duplicate_directory_deduped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "track.mp3"
            path.write_bytes(b"first")
            db = Database(str(Path(tmp) / "test.db"))
            try:
                def fake_process(filepath, file_hash, fan_value):
                    return filepath, Path(filepath).name, file_hash, 1.0, [(len(path.read_bytes()), 0)]

                with patch("shazam.indexer.ProcessPoolExecutor", ThreadPoolExecutor), \
                     patch("shazam.indexer._process_file", fake_process):
                    first = bootstrap_directory([tmp, tmp], db, show_progress=False)
                    self.assertEqual(first["total"], 1)
                    self.assertEqual(first["indexed"], 1)
                    path.write_bytes(b"second version")
                    second = bootstrap_directory([tmp], db, show_progress=False)

                self.assertEqual(second["indexed"], 1)
                self.assertEqual(db.get_stats()["songs"], 1)
                self.assertEqual(db.get_stats()["fingerprints"], 1)
                self.assertEqual(len(db.query_hashes([len(b"second version")])), 1)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
