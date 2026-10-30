# Changelog

## Unreleased — native application preparation

Native source version is `0.2.0`; historical `1.0.x` tags identify the Python
application. This section does not announce a new version, tag or downloadable
release.

### Prepared functionality

- Native Rust executable with the four-option index/match/stats/exit menu,
  file/folder pickers, CLI and JSON output; no Python runtime needed by users.
- Experimental default Olaf retrieval with local Rust candidate-window
  verification. Retains `--backend rust` as a separate comparison backend.
- Complete-track native indexing, explicit folder selection, incremental work
  and partial-success reporting. Defaults to no more than six indexing workers.
- Separate, versioned Olaf runtime/index directories and a separate Rust SQLite
  database; no automatic conversion from Python or between native backends.
- Olaf query analysis limited to the first 30 seconds; up to three evidence-filtered
  suggestions with `strong_match`, `possible_matches` or `insufficient_evidence`.
- Release-facing documentation and an original, accessible vector banner.

### Evidence and release gates

- Behavior above is documented from source inspection, not a new test or
  benchmark run. No indexing, audio tests or compilation were performed for
  this presentation update.
- Windows x64, Linux x64 and macOS arm64/x64 are planned CI targets awaiting
  verification. Build, packaging, installation and platform support are not
  asserted as passing. See [Building](docs/BUILDING.md) and
  [Releasing](docs/RELEASING.md), planned cross-branch additions.
- Integrated Olaf/verifier held-out accuracy remains unverified. Development
  smoke checks and older backend measurements do not establish its accuracy,
  throughput or false-positive rate. Labels and scores are not probabilities.
- Resource use and stability require further validation. Development system
  crashes have an unresolved cause; the worker default is not a proven fix,
  and post-crash index integrity is not established.
- Olaf removal/compaction, automatic recording-family grouping and persistent
  verification caching are not implemented. Formats depend on external
  FFmpeg/FFprobe and the installed codecs.
- MIT application and AGPL-3.0-or-later Olaf runtime attribution must remain
  distinct. [Third-party notices](THIRD_PARTY_NOTICES.md), matching runtime
  source and required distribution materials are a release gate, not a
  compliance claim made by this documentation update.

The legacy Python reference is unchanged and retains its older decoding and
identity limits.

## v1.0.1 — 2026-09-24 (legacy Python)

### Improved

- Re-indexing a changed file now replaces its fingerprints in one database
  transaction instead of failing on its existing path.
- Indexing reuses its worker pool across bounded batches, deduplicates overlapping
  input directories, and counts files that disappear during scanning as failures.
- Directory removal no longer matches similarly named sibling folders or fails
  when more than 999 songs are selected.
- Added five regression tests and documented the decoding and file identity limits.

### Historical verification and limits

- The original release notes recorded five passing regression tests and small
  local indexing/matching smoke checks. These have not been rerun for the native
  presentation update.
- Historical timings are not carried forward as current performance results.
  Cold lookups on a large Python database were substantially slower than small
  smoke checks; no sub-second lookup guarantee was established.
- Only the first 120 seconds were decoded, with a 30-second decoder timeout.
  Identity checks used file size and the first 8 KiB.
- `ffmpeg` had to be installed separately and available on `PATH`.

The local music database and test audio are not included in the repository.
