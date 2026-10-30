//! Non-audio regression tests: temporary metadata only, no decoders or runtime processes.
use local_shazam::{
    dsp::Landmark,
    index,
    store::{Store, ENGINE},
};
use rusqlite::Connection;
use std::fs;

#[test]
fn legacy_and_incompatible_sqlite_indexes_are_preserved() {
    for engine in [None, Some("python-landmarks"), Some("future-rust-version")] {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("legacy.db");
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch("CREATE TABLE songs(id INTEGER PRIMARY KEY);")
            .unwrap();
        if let Some(engine) = engine {
            conn.execute_batch("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);")
                .unwrap();
            conn.execute("INSERT INTO metadata VALUES ('engine', ?1)", [engine])
                .unwrap();
        }
        drop(conn);
        let before = fs::read(&path).unwrap();
        let error = Store::open(&path, true).err().unwrap().to_string();
        assert!(error.contains("legacy or incompatible"));
        assert_eq!(fs::read(&path).unwrap(), before);
    }
}

#[test]
fn fresh_rust_database_keeps_original_engine_identifier() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("comparison.db");
    let store = Store::open(&path, true).unwrap();
    let engine: String = store
        .conn
        .query_row("SELECT value FROM metadata WHERE key='engine'", [], |r| {
            r.get(0)
        })
        .unwrap();
    assert_eq!(engine, ENGINE);
    assert_eq!(engine, "rust-landmarks-v1");
    drop(store);
    assert!(Store::open(&path, false).is_ok());
}

#[test]
fn rust_worker_bounds_fail_before_scanning_or_decoding() {
    let dir = tempfile::tempdir().unwrap();
    let mut store = Store::open(&dir.path().join("comparison.db"), true).unwrap();
    for workers in [0, 65, usize::MAX] {
        let error = index::bootstrap(
            &[dir.path().join("missing")],
            &mut store,
            workers,
            5,
            false,
            false,
        )
        .unwrap_err()
        .to_string();
        assert!(error.contains("workers must be between 1 and 64"));
    }
    assert_eq!(store.stats().unwrap().songs, 0);
}

#[test]
fn directory_removal_does_not_match_sibling_prefixes() {
    let dir = tempfile::tempdir().unwrap();
    let mut store = Store::open(&dir.path().join("comparison.db"), true).unwrap();
    for album in ["album", "album-sibling"] {
        store
            .insert(
                &dir.path().join(album).join("song.wav"),
                "fixture",
                1.0,
                &mut [Landmark { hash: 1, offset: 1 }],
            )
            .unwrap();
    }
    assert_eq!(store.remove(&dir.path().join("album")).unwrap(), 1);
    assert_eq!(store.stats().unwrap().songs, 1);
}

#[cfg(unix)]
#[test]
fn unix_backslashes_are_filename_characters_not_separators() {
    let dir = tempfile::tempdir().unwrap();
    let mut store = Store::open(&dir.path().join("comparison.db"), true).unwrap();
    let album = dir.path().join("album\\");
    store
        .insert(
            &album.join("song.wav"),
            "fixture",
            1.0,
            &mut [Landmark { hash: 1, offset: 1 }],
        )
        .unwrap();
    assert_eq!(store.remove(&album).unwrap(), 1);
}

#[cfg(windows)]
#[test]
fn unpaired_surrogates_are_rejected_instead_of_lossily_aliased() {
    use std::{ffi::OsString, os::windows::ffi::OsStringExt};
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join(OsString::from_wide(&[0xD800]));
    assert!(index::normalize(&path).is_err());
}
