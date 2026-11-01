# Windows 0.2.1 packaging and architecture notes

## Downloads

- `Local-Shazam_0.2.1_x64.zip`: recommended for 64-bit Intel/AMD Windows.
- `Local-Shazam_0.2.1_x86.zip`: 32-bit app and 32-bit Olaf runtime.
- Each package has matching `_app-source.tar.gz` and `_olaf-source.tar.gz`
  archives. `SHA256SUMS.txt` lists the published archives.

Architecture comes from both executable headers, not just the filename. Sources,
licenses and build provenance remain included. The app's `--version` is 0.2.1.
The repository remains private; no public launch is implied.

## x86 limits

Use x64 for large libraries. The x86 Olaf database has a **512 MiB mapping limit**
to fit its 32-bit address space. This is a database-capacity limit, not a promise
of 512 MiB total RAM use. Audio decoding and indexing workers use additional memory.
Start with two workers and a small folder. Capacity exhaustion must produce an
error, not a successful-but-incomplete index.

LMDB databases are architecture-specific. Use a **new index folder and reindex**
when moving between x86 and x64; don't copy or replace runtime files inside an
existing index. The application rejects the other architecture's index marker
without rewriting it. Existing x64 markers and comparison rules are preserved.

The x86 implementation uses explicit 64-bit comparisons for fingerprint keys and
values; native-word LMDB comparisons are not sufficient on 32-bit hosts. Synthetic
regression coverage includes thousands of wide keys and duplicate values sharing
the same low 32 bits, with persistence and lookup after reopening the database.
The ordered Olaf patch series records these modifications and their date.

## Validation scope

Release gates must pass separately for both packages. x86 execution on this x64
Windows host is **WOW64 validation**, not testing on a native 32-bit Windows PC.
Minimum Windows version, clean-PC installation, code signing and new snippet
accuracy benchmarks remain outside this build validation. No private music or
production index is used for these tests.

The app's original code remains MIT and modified Olaf remains AGPL-3.0-or-later.
Keep both matching source archives with redistribution. External FFmpeg and FFprobe
must be usable on the recipient's OS; a 32-bit OS needs compatible tool builds.
The prior [Windows distribution review](../licenses/WINDOWS_DISTRIBUTION.md)
describes source delivery and component attribution, not blanket legal approval.
