use crate::dsp::{Landmark, HOP, RATE};
use anyhow::{bail, Result};
use rusqlite::{params, Connection, OpenFlags, OptionalExtension};
use serde::Serialize;
use std::{
    collections::HashMap,
    path::{Path, PathBuf},
    time::Duration,
};

const SCHEMA:&str="
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS songs(id INTEGER PRIMARY KEY AUTOINCREMENT,filepath TEXT NOT NULL UNIQUE,
filename TEXT NOT NULL,duration REAL,file_hash TEXT,status TEXT DEFAULT 'indexed');
CREATE TABLE IF NOT EXISTS fingerprints(hash INTEGER NOT NULL,song_id INTEGER NOT NULL,offset INTEGER NOT NULL,
PRIMARY KEY(song_id,hash,offset),FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
";
pub const ENGINE: &str = "rust-landmarks-v1";
pub struct Store {
    pub conn: Connection,
    path: PathBuf,
}
#[derive(Debug, Serialize)]
pub struct Stats {
    pub songs: i64,
    pub fingerprints: i64,
    pub bytes: u64,
}
#[derive(Debug, Serialize)]
pub struct Match {
    pub song_id: i64,
    pub filename: String,
    pub filepath: String,
    pub aligned_hashes: u64,
    pub total_query_hashes: usize,
    pub confidence: f64,
    pub offset_seconds: f64,
}
impl Store {
    pub fn open(path: &Path, write: bool) -> Result<Self> {
        let mut conn = if write {
            Connection::open(path)?
        } else {
            Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)?
        };
        conn.busy_timeout(Duration::from_secs(30))?;
        if write {
            let has_songs: bool = conn.query_row(
                "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE name='songs')",
                [],
                |r| r.get(0),
            )?;
            if has_songs {
                let has_meta: bool = conn.query_row(
                    "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE name='metadata')",
                    [],
                    |r| r.get(0),
                )?;
                let engine: Option<String> = if has_meta {
                    conn.query_row("SELECT value FROM metadata WHERE key='engine'", [], |r| {
                        r.get(0)
                    })
                    .optional()?
                } else {
                    None
                };
                if engine.as_deref() != Some(ENGINE) {
                    bail!("This is a legacy or incompatible index. Keep it intact and index into a new --db file with Rust.");
                }
            }
            conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON; PRAGMA cache_size=-65536;")?;
            let tx = conn.transaction()?;
            tx.execute_batch(SCHEMA)?;
            tx.execute(
                "INSERT OR IGNORE INTO metadata VALUES('engine',?1)",
                [ENGINE],
            )?;
            tx.commit()?;
        }
        Ok(Self {
            conn,
            path: path.to_owned(),
        })
    }
    pub fn identities(&self) -> Result<HashMap<String, String>> {
        let mut stmt = self
            .conn
            .prepare("SELECT filepath,file_hash FROM songs WHERE status='indexed'")?;
        let rows = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?;
        Ok(rows.collect::<rusqlite::Result<_>>()?)
    }
    pub fn insert(
        &mut self,
        path: &Path,
        identity: &str,
        duration: f64,
        hashes: &mut [Landmark],
    ) -> Result<()> {
        hashes.sort_unstable_by_key(|h| (h.hash, h.offset));
        let path = path.to_string_lossy();
        let filename = Path::new(path.as_ref())
            .file_name()
            .unwrap_or_default()
            .to_string_lossy();
        let tx = self.conn.transaction()?;
        tx.execute("INSERT INTO songs(filepath,filename,duration,file_hash) VALUES(?1,?2,?3,?4)
            ON CONFLICT(filepath) DO UPDATE SET filename=excluded.filename,duration=excluded.duration,file_hash=excluded.file_hash,status='indexed'",
            params![path,filename,duration,identity])?;
        let id: i64 = tx.query_row("SELECT id FROM songs WHERE filepath=?1", [&path], |r| {
            r.get(0)
        })?;
        tx.execute("DELETE FROM fingerprints WHERE song_id=?1", [id])?;
        {
            let mut stmt = tx
                .prepare_cached("INSERT INTO fingerprints(hash,song_id,offset) VALUES(?1,?2,?3)")?;
            for h in hashes {
                stmt.execute(params![h.hash, id, i64::try_from(h.offset)?])?;
            }
        }
        tx.commit()?;
        Ok(())
    }
    pub fn matches(&self, hashes: &[Landmark], top: usize) -> Result<Vec<Match>> {
        if hashes.is_empty() {
            return Ok(vec![]);
        }
        let mut query: HashMap<u32, Vec<u64>> = HashMap::new();
        for h in hashes {
            query.entry(h.hash).or_default().push(h.offset);
        }
        let mut votes: HashMap<(i64, i64), u64> = HashMap::new();
        // One indexed prepared lookup per unique hash; rows are scored as read.
        let mut stmt = self
            .conn
            .prepare_cached("SELECT song_id,offset FROM fingerprints WHERE hash=?1")?;
        for (hash, offsets) in query {
            let mut rows = stmt.query([hash])?;
            while let Some(row) = rows.next()? {
                let song: i64 = row.get(0)?;
                let offset: i64 = row.get(1)?;
                for &q in &offsets {
                    *votes.entry((song, offset - q as i64)).or_default() += 1;
                }
            }
        }
        let mut best: HashMap<i64, (u64, i64)> = HashMap::new();
        for ((song, delta), count) in votes {
            let slot = best.entry(song).or_insert((0, delta));
            if count > slot.0 || (count == slot.0 && delta < slot.1) {
                *slot = (count, delta);
            }
        }
        let mut candidates: Vec<_> = best
            .into_iter()
            .filter(|(_, (count, _))| *count >= 5)
            .collect();
        candidates.sort_unstable_by(|a, b| b.1 .0.cmp(&a.1 .0).then(a.0.cmp(&b.0)));
        let mut output = vec![];
        for (song, (count, delta)) in candidates.into_iter().take(top) {
            let (filename, filepath) = self.conn.query_row(
                "SELECT filename,filepath FROM songs WHERE id=?1",
                [song],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )?;
            output.push(Match {
                song_id: song,
                filename,
                filepath,
                aligned_hashes: count,
                total_query_hashes: hashes.len(),
                confidence: count as f64 / hashes.len() as f64,
                offset_seconds: delta as f64 * HOP as f64 / RATE as f64,
            });
        }
        Ok(output)
    }
    pub fn stats(&self) -> Result<Stats> {
        let songs = self
            .conn
            .query_row("SELECT COUNT(*) FROM songs", [], |r| r.get(0))?;
        let fingerprints = self
            .conn
            .query_row("SELECT COUNT(*) FROM fingerprints", [], |r| r.get(0))?;
        let mut wal = self.path.as_os_str().to_owned();
        wal.push("-wal");
        let bytes = [self.path.clone(), PathBuf::from(wal)]
            .iter()
            .filter_map(|p| p.metadata().ok())
            .map(|m| m.len())
            .sum();
        Ok(Stats {
            songs,
            fingerprints,
            bytes,
        })
    }
    pub fn compact(&self) -> Result<()> {
        self.conn.execute_batch(
            "PRAGMA wal_checkpoint(TRUNCATE); VACUUM; PRAGMA wal_checkpoint(TRUNCATE);",
        )?;
        Ok(())
    }
    pub fn remove(&mut self, path: &Path) -> Result<usize> {
        let path = path.to_string_lossy();
        let prefix = format!(
            "{}{}",
            path.trim_end_matches(std::path::is_separator),
            std::path::MAIN_SEPARATOR
        );
        let tx = self.conn.transaction()?;
        let count = tx.execute(
            "DELETE FROM songs WHERE filepath=?1 OR substr(filepath,1,length(?2))=?2",
            params![path, prefix],
        )?;
        tx.commit()?;
        Ok(count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn replacement_rollback_match_and_remove() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("test.db");
        let mut db = Store::open(&path, true).unwrap();
        let song = tmp.path().join("song.wav");
        let hashes: Vec<_> = (0..10)
            .map(|i| Landmark {
                hash: i,
                offset: 5000 + i as u64,
            })
            .collect();
        db.insert(&song, "first", 240.0, &mut hashes.clone())
            .unwrap();
        let mut bad = vec![hashes[0], hashes[0]];
        assert!(db.insert(&song, "bad", 240.0, &mut bad).is_err());
        assert_eq!(db.stats().unwrap().fingerprints, 10);
        let query: Vec<_> = (0..10)
            .map(|i| Landmark {
                hash: i,
                offset: i as u64,
            })
            .collect();
        assert_eq!(db.matches(&query, 10).unwrap()[0].aligned_hashes, 10);
        assert_eq!(db.remove(&song).unwrap(), 1);
        assert_eq!(db.stats().unwrap().fingerprints, 0);
    }
}
