# Building the separate Olaf desktop runtime

This is a reviewed source distribution, not a prebuilt runtime or a copy of a
developer's benchmark directory. Olaf and the modifications remain
**AGPL-3.0-or-later**, with component terms preserved in `LICENSE`, `NOTICES.txt`,
and `notices/`. Zigzag is separately MIT licensed. Process separation is not a
blanket licensing conclusion about the surrounding application or its release.

## Supported integration interface

From the repository root, with Python **3.11+** and installed **Zig 0.16.0**:

```sh
python scripts/build_olaf.py --check-only
python scripts/build_olaf.py --target windows-x64 --out-dir dist/windows-x64
python scripts/build_olaf.py --target windows-x86 --out-dir dist/windows-x86
python scripts/build_olaf.py --target linux-x64 --out-dir dist/linux-x64
python scripts/build_olaf.py --target macos-arm64 --out-dir dist/macos-arm64
python scripts/build_olaf.py --target macos-x64 --out-dir dist/macos-x64
```

Zig must be on `PATH`, or `ZIG` must name its installed executable. Development
snapshots and other versions are rejected. The packaging workflow provisions
toolchains; this helper never downloads or installs anything. `--check-only`
does not need Zig, invoke Git, create output directories, compile, or run audio
tests. It optionally accepts `--target` and `--out-dir` without building.

All targets use `ReleaseFast`, `-Dcpu=baseline`, and sequential `-j1` builds:

| Integration target | Zig target | Runtime binary |
| --- | --- | --- |
| windows-x64 | x86_64-windows-gnu | olaf.exe |
| windows-x86 | x86-windows-gnu | olaf.exe |
| linux-x64 | x86_64-linux-musl | olaf |
| macos-arm64 | aarch64-macos.11.0.0-none | olaf |
| macos-x64 | x86_64-macos.11.0.0-none | olaf |

The Linux recipe selects musl rather than a host-dependent glibc baseline.
These are build recipes, **not verified portability claims**. No target was
compiled during source vendoring. Prefer matching-host CI, particularly macOS;
any SDK/linker prerequisites of a chosen Zig host must be provisioned by CI.
The helper reports build failures; it never substitutes an old executable.

Each invocation uses fresh staging-local install/local/global cache directories.
Compiler/privacy policy is described in `docs/BUILD_PRIVACY.md` in the matching
source archive. The helper enables the build-only fourth patch: module-relative
Zig source identities, no emitted debug information, and C file/macro/debug
prefix maps via a generated response file. No existing binary is rewritten.
No host-native CPU tuning, prebuilt local runtime, private repository, ignored
source checkout, global Zig package cache, music, index or settings is used.
Keep `vendor/olaf` and `vendor/zigzag` as siblings; `.path = "../zigzag"` is the
only package dependency. The package needs no other downloaded dependencies.
Do not distribute `vendor/olaf` alone as a standalone Zig package.

The output is `DIRECTORY/olaf-runtime/`, containing:

- `olaf.exe` or `olaf`, newly built from the validated source;
- `OLAF-LICENSE`, `OLAF-NOTICES.txt`, and `notices/` (including Zigzag's license);
- `PROVENANCE.json`, `BUILDING.md`, and `BUILD-INFO.json` (target, flags, binary
  SHA-256 and source-manifest SHA-256, with no private build paths).

An existing `olaf-runtime` directory is never replaced. Use a fresh output
directory. The helper does not run the binary. FFmpeg/FFprobe are external
runtime tools, not build prerequisites and not bundled here. Package their
licenses/source separately if shipping them. The helper does not emit the app's
index-specific configuration: that is owned by the application integration.

## Reconstructing and checking source

`PROVENANCE.json` records the public Olaf base
`f6f7cbefb50485953f71100c9d08c625f01780ba`, the Windows-fix fork commit
`1240e2552f64ea2d5727c05f859e8303f88aebca`, and all ten dirty working files,
including the previously untracked `tests/olaf_matcher_v3_tests.c`. It also
records Zigzag revision `e16e2523972d174d7ca9783631cc90e2609fa55e`, the original
Zig package hash, an explicit file inventory, source/capture/final SHA-256s,
excluded tracked paths, and release-only changes. Captured CRLF text is
normalized to LF; copyright notices and substantive source are preserved.

The ordered patches in `../../patches/olaf/series` are relative to an Olaf
source root, not the repository root. Apply them to the public base, in order,
then select the source inventory and supply the sibling Zigzag inventory and
distribution metadata. No private fork access is required. The source tests
reverse and replay every patch and compare all retained source files with the
recorded upstream, working-source and final hashes. Do not reapply patches to
this already-patched directory. The build helper and packaging metadata are
hashed alongside source; `PROVENANCE.json` cannot contain its own hash.

```sh
python -B -m unittest discover -s tests/release -p test_olaf_source.py -v
```

This checks integrity/completeness, dependency locality, patch reconstruction,
dirty-change coverage, and mocked build/output behavior. It is **not** a native
compilation, recognition test, accuracy benchmark or proof of bit-identical
binaries across different host environments. Binary reproducibility still
needs clean CI rebuild comparison for each target and toolchain environment.

## Dataset-free native tests for later CI (not run here)

From `vendor/olaf`, on the matching host with Zig 0.16.0:

```sh
zig build test-matcher-v3 -Dcpu=baseline -Doptimize=ReleaseFast -j1
zig build test-db-safety -Dcpu=baseline -Doptimize=ReleaseFast -j1
zig build test-config-safety -Dcpu=baseline -Doptimize=ReleaseFast -j1
```

These are the existing isolated matcher voting/boundary, synthetic DB/writer
ownership/concurrency, and constructor/configuration safety steps. They do not
download audio. DB safety uses temporary test databases, never a user's index.
`test-config-safety` uses the retained text snapshot as a reader input and the
upstream memory-backend C fingerprint fixture, not an audio recording.

Do **not** use `zig build test` as a lightweight release check. This distribution
makes that command fail explicitly by default. Enabling `-Daudio-tests=true`
is reserved for a separately authorized upstream-suite job with manually
provided fixtures; its dataset helper is patched to validate required files
and **never download** them. Missing dataset files are errors, not passes.
Upstream tests can still skip for unavailable FFmpeg, Node, raw fixtures, or
snapshot environment mismatch: collect and report those skips explicitly.
No full-suite result is claimed. The legacy `make test` needs the excluded
`tests/16k_samples.raw`; it is not a source-only validation command.

## Deliberate source boundary and remaining review

All desktop core C/headers, CLI/TUI/REST/UI Zig modules, embedded HTML,
configuration assets, Zig/Make build definitions and regression-test sources
are retained. The small upstream `src/olaf_fp_ref_mem.h` C array is retained
because memory-backend configuration tests compile it; it is not a copied user
database. Python wrapper sources needed by constructor tests and the WASM
loader/test source are retained; browser demos and their audio/precompiled
libsamplerate bundle are not. No precompiled WASM is included.

The manifest lists all excluded tracked paths. Untracked caches, Git data,
toolchains, datasets, databases, evidence, diagnostics and agent handoffs were
never copy inputs. The Zigzag upstream package itself omits its standalone
`examples/` and `tests/`, although its original build definition mentions them.
Its complete runtime `src/` module and original MIT license are retained
unchanged; do not claim its missing standalone example/test steps pass.
The bundled c-algorithms files have optional `ALLOC_TESTING` branches referring
to `alloc-testing.h`, which is absent from upstream Olaf as well. That macro is
not enabled by Olaf's supported build or its regression steps; the unrelated
c-algorithms allocation-test harness is not included. Standard C/Zig headers
are provided by the separately provisioned toolchain.

The source distribution addresses the desktop runtime build inputs, not every
upstream platform/demo. Preserve the matching source, patches and build helper
with a binary distribution. Final application/combined-distribution licensing,
network-service obligations, external FFmpeg, toolchain/CRT subcomponent notices
for actual emitted binaries, and any patent questions require release review;
this document does not certify legal compliance or general accuracy.
Upstream specifically calls attention to patents US7627477 B2 and US6990453;
their applicability or current status was not assessed here.

## Windows x86 integration update (2026-11-01)

The x86 recipe emits a genuine 32-bit runtime using the pinned x64 Zig host tool.
An x64 Windows host can execute its checks under WOW64; this is not a native
32-bit OS validation. The x86 LMDB map is limited to 512 MiB. Use a fresh index
when switching architectures; original x64 indexes and comparator rules are
unchanged. Patches 0006/0007 record the full-width fingerprint comparisons,
alignment-safe reads, checked writes, MinGW C-import macro and portable temporary
counters. Matching fingerprint settings were not changed by these fixes.
