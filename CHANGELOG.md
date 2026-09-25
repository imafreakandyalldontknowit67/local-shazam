# Changelog

## v1.0.1 — 2026-09-24

### Improved

- Re-indexing a changed file now replaces its fingerprints in one database
  transaction instead of failing on its existing path.
- Indexing reuses its worker pool across bounded batches, deduplicates overlapping
  input directories, and counts files that disappear during scanning as failures.
- Directory removal no longer matches similarly named sibling folders or fails
  when more than 999 songs are selected.
- Added five regression tests and documented the current decoding and file
  identity limits.

### Verification and known limits

- Five regression tests passed. A four-file local smoke test indexed in about
  2.7 seconds and matched a sample in about 1.3 seconds on the test machine.
- A cold lookup against the existing roughly 9 GB database took 15–20 seconds.
  This release does not claim sub-second matching at that scale.
- `ffmpeg` must be installed separately and available on `PATH`.

The local music database and test audio are not included in the repository.
