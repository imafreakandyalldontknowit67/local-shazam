# Changelog

## 0.2.2

- Public release with Windows x64 and x86 packages.
- Original app copyright now names badger.
- Updated setup guidance, dated Olaf modification notices and x86 build instructions.
- Recognition engine/settings unchanged from 0.2.1. Clean-PC installation and
  native 32-bit Windows compatibility are not yet verified.

## 0.2.1

- Versioned, readable Windows download filenames and separate x64/x86 packages.
- 32-bit Olaf database mapping capped at 512 MiB; full-width fingerprint ordering
  preserved. Failed fingerprint writes are reported instead of silently skipped.
- Separate 32-bit index marker prevents accidental reuse across architectures.
- Windows tutorial distinguishes the packages; license notices no longer count
  toward GitHub language statistics.
- Recognition settings and the Rust comparison engine are unchanged.


## Unreleased — native application preparation

This historical preparation used source version `0.2.0`; `1.0.x` tags identify the Python
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

- Native CI run `41023384988` passed all four targets at historical preview
  commit `92a983a57ff92ad4b9342fb4dd992edf728b5a97`. Each embedded manifest
  records 16 dataset-free gates. Read-only reconciliation verified the twelve
  local archives and authenticated metadata for private draft `v0.2.0-native.1`;
  its 13 asset digests/sizes match the local archives and combined checksums.
  This is not a new release, verified tag, current-HEAD pass or legal approval.
- Source/provider/build tooling is integrated. Compiler-privacy changes require
  fresh parent-run hosted rebuilds plus independent binary/source/archive
  verification. Historical artifacts retain the limitations in
  [Building](docs/BUILDING.md) and [Releasing](docs/RELEASING.md): unverified
  minimum OS/glibc and clean-host behavior, unsigned/not-notarized distribution,
  and no bit-for-bit reproducibility claim.
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

The historical Python reference retains its older decoding and identity limits.
Its agreed repository-only archive location is `legacy/python/README.md`; the
parent must verify relocation after integration. Historical entries below and
old tags retain their original identity.

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
