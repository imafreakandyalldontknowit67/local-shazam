# Native application guide

Local Shazam recognizes snippets against **your own indexed files**, not the
Shazam service or a global catalog. The native source version is `0.2.2-beta.1`; Python
`1.0.x` tags describe the older reference implementation.

The executable is written in Rust and does not embed or invoke Python. **Olaf
retrieval with local Rust candidate-window verification is the experimental
default.** `--backend rust` selects the retained Rust-only comparison engine.

## Prepare and launch

Install FFmpeg and FFprobe separately and make both available on `PATH`.
Decodable formats depend on that build's codecs. SQLite is bundled for the
Rust backend; Python is not a native runtime dependency.

The package places `local-shazam.exe` beside `olaf-runtime/olaf.exe`
on Windows, or `local-shazam` beside `olaf-runtime/olaf` on Unix-like targets.
Keep package notices and matching runtime source materials. Use
[Building](../docs/BUILDING.md) for source prerequisites and
[Releasing](../docs/RELEASING.md) for packaging. The current private v0.2.1
release includes Windows x64 and x86 packages. x64 passed native gates; x86
passed under WOW64 on x64 Windows, not on a native 32-bit PC. See the root README
for downloads and [release status](../docs/PREVIEW_STATUS.md) for exact build
identities. Clean-host installation and minimum Windows versions remain unverified.
The Python reference is archived under `legacy/python/` and is not required.

Run the prepared executable without arguments for the menu:

```powershell
.\local-shazam.exe
```

1. **Add a music folder:** select a folder, then choose 1–64 workers, Enter for
   the default, or `q` to cancel.
2. **Identify audio clips:** select one or more existing audio files.
3. **View library stats:** view the selected backend's index information.
4. **Exit**.

No indexing starts merely by opening the app. The default is available parallelism
capped at six, or four if detection fails. More workers increase concurrent
resource demands and may not improve throughput. Start with a small folder and
low concurrency on a stable machine; do not resume work after unresolved crashes.

## CLI examples

These PowerShell examples use generic, user-chosen paths. Replace them and keep
indexes separate from source music. Commands are examples, not a validation log.
On a prepared Linux/macOS target, use `./local-shazam` and your own POSIX paths.

### Default Olaf workflow

```powershell
.\local-shazam.exe --olaf-index "D:\AudioIndexes\trial-olaf" bootstrap "D:\Music\SmallFolder" --workers 2
.\local-shazam.exe --olaf-index "D:\AudioIndexes\trial-olaf" match "D:\Clips\snippet.mp3"
.\local-shazam.exe --olaf-index "D:\AudioIndexes\trial-olaf" --json status
```

`bootstrap` has `add` and `index` aliases. It accepts multiple directories;
`match` accepts multiple snippets. `--force` reindexes files even if their saved
identities appear unchanged. Successful records are retained when other files
fail; inspect errors before retrying the same folder. CLI failures return a
nonzero exit code. `--json` selects machine-readable output; diagnostics go to
stderr.

### Rust comparison workflow

```powershell
.\local-shazam.exe --backend rust --db "D:\AudioIndexes\trial-rust.db" bootstrap "D:\Music\SmallFolder" --workers 2
.\local-shazam.exe --backend rust --db "D:\AudioIndexes\trial-rust.db" match "D:\Clips\snippet.mp3"
.\local-shazam.exe --backend rust --db "D:\AudioIndexes\trial-rust.db" --json status
```

The Rust-only `remove PATH` command removes index entries, not source audio.
`compact-db` reclaims unused database pages. Neither command is exposed for Olaf.
Rust's indexing `--compact` flag is different: it reduces fingerprint fan-out
from five to three, a storage/recognition tradeoff, not database compaction.

## Storage and migration

Defaults are relative to the **executable**, not the current working directory:

| Engine | Default | Override |
| --- | --- | --- |
| Olaf + Rust verification | `local-olaf/` | `--olaf-index DIRECTORY` |
| Rust comparison | `local-shazam.db` | `--backend rust --db FILE` |

Choose a writable path explicitly if the executable directory is not writable.
`--db` is rejected with Olaf. There is no automatic conversion or shared index
between Olaf, Rust and the legacy Python database. Build a separate index from
your chosen music folders; Rust refuses writes into legacy Python databases.

Olaf indexes retain their own runtime/configuration and manifest. Replacing the
application's runtime does not silently upgrade an existing index. Incompatible
versions, runtime hashes or configurations require attention; rebuild separately
rather than editing the index metadata. Details: [Olaf guide](OLAF.md).

## Architecture and limits

- **Olaf path:** local subprocess retrieval from an LMDB index, then Rust DSP
  verification of nearby windows in the shortlisted original files. Only the
  first 30 seconds of each query are analyzed; indexed tracks are processed in
  full. Results are evidence-filtered suggestions, not guaranteed matches.
- **Rust comparison path:** FFmpeg streams complete-file mono PCM into RustFFT
  constellation-landmark extraction. Bounded channels feed a transactional
  SQLite writer; matching uses time-aligned hash votes. It does not impose the
  Olaf 30-second query cap. Its displayed percentage-like confidence scores are
  heuristic, not calibrated probabilities.
- File identity includes size, modification time and a digest of the first
  8 KiB, not a full-content checksum. Edits preserving these attributes may
  need `--force`. Keep originals available for Olaf verification.
- Rust probes unfamiliar extensions with FFprobe, while Olaf scans its recognized
  extension list. Neither promises every codec, DRM input or malformed file.
- Bounded queues are not a fixed total-memory guarantee. File-level landmarks,
  vote maps, scanner/manifest state, caches and temporary files can grow.
  A six-worker default is not a hardware-stability guarantee. Start with two
  workers and stop if the machine is unstable.

Historical native build gates are not current-HEAD validation, privacy approval
or a held-out accuracy result for the integrated pipeline. Related recordings
are not automatically grouped. Short/noisy clips,
quiet sections, speed/pitch edits, covers and live performances can fail.
See the [root limitations](../README.md#good-to-know) and
[changelog](../CHANGELOG.md) for release-evidence boundaries.

## License scope

Original application code: [MIT](../LICENSE). Separately shipped, modified Olaf
runtime: **AGPL-3.0-or-later**, not MIT. See the
[Third-party notices](../THIRD_PARTY_NOTICES.md) for runtime/dependency attribution
and the release guide for matching source and distribution materials.
