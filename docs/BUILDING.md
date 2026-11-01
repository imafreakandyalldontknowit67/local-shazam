# Building staged portable artifacts

## Current status: recorded private v0.2.1 Windows release

The existing [release record](PREVIEW_STATUS.md) identifies **v0.2.1 as Latest
inside the PRIVATE repository**, built at
`d32716df0be1a5ea2d919d0b8ceb560de17bd77c`. Later documentation commits do not
change either binary's identity. This is the Rust terminal/menu application,
with a separate modified Olaf **3.3.3** runtime, not a Node application; there is
no root `package.json` workflow. Only Windows x64 and x86 are in this release.

The retained records in `dist/readiness-audit/` are
`release-0.2.1-verification.json`, `0.2.1-x64-manifest.json`,
`0.2.1-x86-manifest.json`, `0.2.1-x64-menu.log`, `0.2.1-x86-menu.log`,
`windows-0.2.1-notes.md` and `tests-0.2.1-final.log`. They record 16 dataset-free
gates per package, architecture/import and privacy checks, archive verification,
menu/exit checks without index creation, actual downloaded-byte comparisons for
all seven assets, and independent verification of both downloaded archive sets.
x64 execution was native; x86 execution was **WOW64 on x64 Windows**, not native
32-bit Windows validation. The static-test log records 140 tests, 3 skipped
(137 passed); its mocked packaging output is not additional native build evidence.
Ignored evidence may be absent from a source checkout; absence is not a new pass.

These are **recorded completed checks**, not checks rerun here, newly queried
remote state or current-HEAD validation. Public-release approval remains pending.
Clean-host compatibility, minimum Windows version, native 32-bit OS validation,
audio accuracy, hardware stability, signing and historical privacy/legal review
remain open; see [Releasing](RELEASING.md).

## Historical v0.2.0 / four-platform preview evidence

All four native jobs passed at historical Rust **0.2.0** preview commit
`92a983a57ff92ad4b9342fb4dd992edf728b5a97` in
[run 41023384988](https://github.com/imafreakandyalldontknowit67/local-shazam/actions/runs/41023384988).
Read-only review on 2026-10-30 independently checked all twelve existing local
archives, source/payload hashes, checksums and embedded gate records; see
[the evidence record](../licenses/review/native-preview.json).

That is **historical evidence, not current v0.2.1 Linux/macOS releases** or a
general compatibility, privacy, accuracy or legal approval. The recorded baseline
[privacy audit](PRIVACY_AUDIT.md) reports hosted-build paths in Windows, Linux and macOS
binaries. Compiler-privacy implementation is integrated and documented in
[`BUILD_PRIVACY.md`](BUILD_PRIVACY.md). The v0.2.1 Windows records do not sanitize
older binaries or close the historical privacy audit. Linux/macOS replacement
builds and independent privacy/correspondence checks remain pending. The earlier
Windows x64 replacement at `d639ab2a2c49` and v0.2.0 release history retain the
separate boundaries described in [Releasing](RELEASING.md).

## Staging scope

This tool does not read an older development checkout, copy its private Olaf
executable, restore private source with secrets, replace root executables, or
adopt its music, indexes, caches or toolchains. All generated build inputs,
toolchains, temporary files and packages belong under the release checkout's
`build/` or `dist/`. A fresh staging subdirectory is required for every build;
the tool never recursively deletes or overwrites an existing build.

## Build matrix and developer prerequisites

The current [portable workflow](../.github/workflows/portable-build.yml) has
**five targets**, with no Windows-only dispatch input. This matrix is build
configuration, not evidence of five v0.2.1 releases or a fresh hosted run.

| Package target | Rust target | Olaf target | Configured runner / host | Release evidence |
|---|---|---|---|---|
| `windows-x64` | `x86_64-pc-windows-msvc` | `x86_64-windows-gnu` | `windows-2025`, x64 | v0.2.1 native gates recorded |
| `windows-x86` | `i686-pc-windows-msvc` | `x86-windows-gnu` | `windows-2025`, **x64 host tools** | v0.2.1 WOW64 gates recorded; not native 32-bit OS |
| `linux-x64` | `x86_64-unknown-linux-gnu` | `x86_64-linux-musl` | `ubuntu-24.04`, x64 | Historical only; not in v0.2.1 |
| `macos-arm64` | `aarch64-apple-darwin` | `aarch64-macos.11.0.0-none` | `macos-15`, ARM64 | Historical only; not in v0.2.1 |
| `macos-x64` | `x86_64-apple-darwin` | `x86_64-macos.11.0.0-none` | `macos-15-intel`, x64 | Historical only; not in v0.2.1 |

Host architecture is checked before provisioning. Both Windows outputs require
a Windows x64 host: x86 uses the pinned x64 Rustup/Zig tools plus the i686 Rust
output component. Native x86 build hosts and Windows ARM hosts are not accepted.
Other targets require their matching native hosts; Rosetta or relabeling an
unreviewed cross-build is not a substitute. PE/ELF/Mach-O headers of **both**
executables must match the output target. Runner labels are not hermetic image
pins, minimum OS claims or clean-host tests; future availability and billing
still require maintainer review.

Developer requirements: Git, Python **3.11+** (standard-library `tomllib` and
`hashlib.file_digest`; no third-party Python packages). **Python 3.13.1** is the
CI pin and the version recorded in both v0.2.1 manifests. Builds also require
HTTPS access to official tool and Cargo registry endpoints, and native system
build prerequisites. Windows needs MSVC C/C++ Build Tools, the linker/libraries
for the selected x64 or x86 output, a Windows SDK, and **clang-cl on PATH** for
privacy-capable native dependency compilation. There is **no cl.exe fallback**;
missing tools fail closed. No particular SDK version or clean-host support is
established by these records.

Linux needs a C compiler/linker, libc development headers, `pkg-config` and
`readelf`; macOS needs Xcode Command Line Tools/SDK and `otool`. If dependencies
require additional native development packages, stop and review rather than
copy libraries from another computer. Linux CI installs
`pkg-config libwayland-dev libxkbcommon-dev libgtk-3-dev` on its disposable host.
The local build script itself does not make system package-manager changes;
clean-user-host dialog/runtime behavior remains unverified.

Recipients do **not** need Python, Rust, Zig or developer build tools. They need
the complete matching ZIP, adjacent `olaf-runtime/`, external **FFmpeg AND
FFprobe on PATH**, and applicable architecture-appropriate Microsoft runtime
components from official installers. See [recipient setup](QUICKSTART.md) and
the dependency section below. The dataset-free release gates deliberately need
neither an audio dataset nor audio tools; their success is not a recipient test.

## Pins and isolated provisioning

`rust-toolchain.toml` and `release/targets.json` pin **Rust 1.99.0**, matching
both v0.2.1 manifests. The Rust 2021 application uses a v4 Cargo lockfile,
including rfd 0.17/rusqlite 0.41 dependencies, not the legacy Python requirements.
The recorded builds do not validate current HEAD. At build time, locked Cargo
metadata is checked for any dependency declaring an MSRV above this pin.
Never resolve a new lockfile to make a failing build appear successful.

The Rustup 1.28.2 bootstrap executable is downloaded from its versioned official
archive and checked against the SHA256 pinned per native host in targets.json.
Rustup then verifies official Rust distribution component checksums. Both
`RUSTUP_HOME` and `CARGO_HOME` are inside the new staging directory; installation
uses `--no-modify-path` and does not set a machine-wide default or edit shell
startup files. Cargo commands use `rustup run 1.99.0` and `--locked -j 1`.
No preexisting Cargo registry/target directory is copied into the build.

**Zig 0.16.0** is required by Olaf's build manifest. Downloads use the official
versioned URLs and SHA256 values reviewed from the
[Zig download manifest](https://ziglang.org/download/index.json). Extraction
rejects links and traversal. PATH and `ZIG` are set only in child processes;
Zig caches and temporary files are staging-local. The runtime provider must use
this pin and `-j1` (the environment also sets `ZIG_BUILD_JOBS=1`; that environment
variable alone is not a Zig CLI concurrency guarantee). The selected regression
commands explicitly pass `-j1`. The integrated provider checks `zig version`,
passes `-j1`, and uses
`ReleaseFast` with baseline CPU selection. Historical native gate evidence is
not a substitute for rechecking the provider after any integration change.

## Integrated input contract (fail closed)

These inputs are integrated. Before each new build, review and commit the
exact versions in **this** checkout:

* `rust-app/Cargo.toml`, `rust-app/Cargo.lock`, all required Rust source/build inputs.
* `vendor/olaf`, `vendor/zigzag`, `patches/olaf`, including build manifests,
  complete native CLI/core/embedded dependency source, relevant tests, licenses,
  local modifications, patch descriptions and origin metadata.
* `scripts/build_olaf.py`, `scripts/check_release_hygiene.py`, `LICENSE`,
  `THIRD_PARTY_NOTICES.md`, `licenses/**`.
* All tooling, inventory, workflow and build/release documentation files.

Runtime provider interface:

```text
python scripts/build_olaf.py --target TARGET --out-dir DIRECTORY
```

It must build the reviewed vendored sources, using the vendored Zigzag dependency
rather than a private checkout, and produce
`DIRECTORY/olaf-runtime/olaf.exe` (Windows) or `olaf` (Unix), plus nonempty license,
notices and a nonempty structured JSON provenance document. Metadata filenames
must identify `license`, `notice` and `provenance` (case-insensitive); additional
runtime files are restricted to reviewed text/JSON metadata, not arbitrary DLLs.
The release layer snapshots source hashes before and after provider invocation
and binds those hashes, all runtime metadata and the actual executable hash in
one manifest. Provider-specific provenance is preserved, not replaced. The
provider emits `OLAF-LICENSE`, `OLAF-NOTICES.txt`, `notices/`,
`PROVENANCE.json`, `BUILDING.md` and `BUILD-INFO.json`. Its only Zig package
dependency is the committed sibling Zigzag; it does not download tools.
The release layer provisions tools and invokes the provider from the snapshot.

Hygiene interface:

```text
python scripts/check_release_hygiene.py --root DIRECTORY
python scripts/check_release_hygiene.py --root DIRECTORY --staged
```

The explicit inventory is in `release/targets.json`: mandatory files plus
allowlisted source subtrees/extensions. Only tracked files matching that policy
are included. Unknown files in protected build-source roots fail for review,
not silent omission. Audio, databases, handoffs, evidence/benchmarks, secrets,
diagnostics, caches, toolchains and build outputs cannot enter the archives.
The inventory intentionally excludes upstream evaluation, unrelated embedded
examples and presentation documentation, not source needed for the shipped
native runtime. Source or documentation added by future integration may require
a narrowly reviewed inventory amendment. Do not broaden it to an entire workspace
or Git HEAD.

## Build commands (not executed by this review)

Future maintainer procedures only; none were executed for this documentation
reconciliation. Run in a clean, reviewed, committed release checkout on the
permitted host for the selected output. Record a new build's actual commit;
do not label it as the existing v0.2.1 binaries merely because the version agrees.
No command below should be pointed at a personal index or music directory.

```powershell
# Windows x64, new staging directory only:
python scripts/release.py build --target windows-x64 --out-dir build/release/windows-x64
python scripts/release.py test --target windows-x64 --out-dir build/release/windows-x64
python scripts/release.py package --target windows-x64 --out-dir build/release/windows-x64
python scripts/release.py verify --out-dir build/release/windows-x64
# Equivalent wrapper (build only unless -Package is explicitly present):
.\Build-Rust.ps1 -Target windows-x64 -OutDir build/release/windows-x64-new -Package
# x86 output also uses an x64 Windows host; execution gates use WOW64:
.\Build-Rust.ps1 -Target windows-x86 -OutDir build/release/windows-x86-new -Package
```

```sh
# Future non-release builds, NOT current v0.2.1 artifacts:
# Linux x64; substitute macos-arm64 or macos-x64 on their native machines:
python3 scripts/release.py build --target linux-x64 --out-dir build/release/linux-x64
python3 scripts/release.py test --target linux-x64 --out-dir build/release/linux-x64
python3 scripts/release.py package --target linux-x64 --out-dir build/release/linux-x64
python3 scripts/release.py verify --out-dir build/release/linux-x64
```

`build` creates an inventory-only staging source snapshot (untracked workspace
files cannot become compiler inputs), provisions isolated tools, compiles the app
with its lockfile, invokes
the runtime provider, checks architecture and native executable modes, and stages
`payload/`. It records compiler versions, source commit, source hashes, host,
target, binary hashes, unresolved dependency requirements and distribution limits
in `build-manifest.json`. `test` is an additional, explicit gate command; it
does not run during `build` implicitly. `package` refuses an untested build or
any change in sources, commit or payload after compilation.
Snapshot input hashes are checked too; unreviewed ancestor `.cargo/config` or
`.cargo/config.toml` overrides are rejected rather than importing developer
settings. The runtime provider is invoked from the snapshot, with its output
under that snapshot's `build/provider/`, still inside the release staging tree.

Both v0.2.1 manifests and the historical preview manifests record
**16 completed dataset-free gates per target**: ten exact
Rust test selections, three Olaf regression steps and three CLI smoke commands.
The Rust test allowlist is exact (missing/zero-test matches fail): extrema,
SQLite rollback/matching, manifest/verification policy, worker-selection tests.
It excludes the synthetic audio streaming test and ignored manifest benchmark.
The Olaf steps are `test-matcher-v3`, `test-db-safety`, `test-config-safety` only,
run from an inventory-only staging copy with ReleaseSafe and one build job.
They must remain dataset-free after any integration change. Never invoke
unrestricted
`zig build test`, dataset download steps, developer validation/benchmark scripts,
library indexing, or the interactive menu. CLI smoke checks are app `--help`,
app `--version` (must match Cargo.toml), and Olaf `--help`, in a private temporary
HOME. The inspected Olaf CLI has no `--version` command: its source version is
recorded from `build.zig.zon` and tied to the binary/provider/source hashes, not
misrepresented as a successful runtime version query. Help may create sandboxed
configuration/cache directories, but must not index audio.

## Current output and per-target verification

The recorded private v0.2.1 release has **seven assets total**:

| Target | Binary | Matching app source | Matching Olaf source |
|---|---|---|---|
| x64 | `Local-Shazam_0.2.1_x64.zip` | `Local-Shazam_0.2.1_x64_app-source.tar.gz` | `Local-Shazam_0.2.1_x64_olaf-source.tar.gz` |
| x86 | `Local-Shazam_0.2.1_x86.zip` | `Local-Shazam_0.2.1_x86_app-source.tar.gz` | `Local-Shazam_0.2.1_x86_olaf-source.tar.gz` |

The seventh asset is combined **`SHA256SUMS.txt`**, covering the six archives.
Each build's `OUT/dist/` instead contains exactly its three matching archives
and a target-only `SHA256SUMS.txt`. Preserve the original combined download
unchanged and its independently recorded hash/size. To verify a downloaded
release, make separate x64/x86 verification directories, each containing only
that target's three archives and a `SHA256SUMS.txt` derived from the three
corresponding lines of the combined file. Keep original downloads, ledgers,
screenshots and other evidence outside those directories. Do not feed all seven
assets or the six-entry checksum manifest to the single-target verifier.

The app source archive includes the locked Rust source and release tooling; Cargo
registry dependencies are fetched by their lockfile checksums, not vendored into
that archive. The Olaf source archive includes the native runtime, Zigzag,
embedded LMDB/PFFFT/c-algorithms source, native build/test inputs, modifications,
patches, instructions and licenses. The archives are intended to supply the
reviewed native build inputs; source hash/file-set checks are recorded for
v0.2.1 and separately for the historical set. This does not settle AGPL
corresponding-source sufficiency or combined-work obligations: see
[release review](../licenses/RELEASE_REVIEW.md). Overlay both archives into a new
reviewed checkout when rebuilding both executables. The release packaging
command requires a clean reviewed Git commit, not a fabricated claim that
extracted files are HEAD.
The historical Python reference is repository-only at the agreed
[`legacy/python/README.md`](../legacy/python/README.md) archive location.
It is not part of native packages; retained
Olaf wrapper test source is a different upstream component, not a Python runtime
dependency of the native app.
The runtime can separately be rebuilt with the provider command from its source
archive, subject to that provider's documented prerequisites.

All three archives **within a target set** embed the same `BUILD-PROVENANCE.json`;
x64 and x86 provenance is target-specific. Verification reads
archives without executing or extracting their contents: it checks checksums,
exact file sets, source digests, cross-archive provenance, notices, executable
headers, permissions and test-gate records. It rejects links, traversal,
duplicates, case collisions, unexpected files and incomplete source bundles.
For a future independent check of the prepared per-target directories (not run here):

```sh
python scripts/release.py verify --out-dir build/downloaded/windows-x64
python scripts/release.py verify --out-dir build/downloaded/windows-x86
```

`verify` is read-only and can accept an artifact directory outside staging too.
Checksums demonstrate consistency, **not publisher authentication**; compare
against the reviewed commit and build records (CI run when applicable).
Normalized archive metadata is not
proof of bit-for-bit binary reproducibility; no such claim is made.

### Historical naming and verification boundaries

The verifier also understands complete historical
`local-shazam-COMMIT12-TARGET` sets, `-app-source.tar.gz` and
`-olaf-source.tar.gz`, with `SHA256SUMS` (Windows `.zip`, Unix `.tar.gz`). Unix
packaging still uses that convention. Historical native provenance fields are
accepted where applicable; mixed naming/checksum conventions, incomplete sets
and ambiguous checksum files fail. This compatibility does **not** waive the
current compiler-privacy policy: old artifacts lacking its record require a
rebuild, not altered evidence. Preserve original historical names and results.

The old four-platform draft comparison was API digest/size **metadata only**,
not downloaded bytes. v0.2.1 has recorded actual downloaded-byte comparisons;
neither statement claims checks performed by this documentation update.

## Dynamic dependencies and unsigned distribution

Windows normal **and delay-load** PE imports are inspected without loading either
program. Both v0.2.1 manifests record the app's `vcruntime140.dll` import and
Universal CRT (`api-ms-win-crt-*`) imports in app/runtime, alongside Windows
system DLLs. Availability on a clean user machine remains unresolved. Obtain
applicable Microsoft Visual C++/Universal CRT components through official
Microsoft installers or supported Windows servicing, never copied development
DLLs or third-party DLL sites. Runtime architecture must match the executable:
x64 for the x64 app; x86 for the x86 app **even on x64 Windows under WOW64**.
External FFmpeg/FFprobe builds must run on the recipient's OS; a 32-bit OS needs
compatible 32-bit tools. See [Windows distribution review](../licenses/WINDOWS_DISTRIBUTION.md).
Windows packages are unsigned; SmartScreen reputation is not established.

### Historical Linux/macOS dependency limits (not v0.2.1 releases)

Linux records `readelf -d -V` (including dependency and symbol-version needs).
The historical Rust app records Wayland and glibc dependencies, including a
`GLIBC_2.39` symbol requirement; the separate Olaf recipe uses musl. Neither
that recipe nor an empty Olaf dynamic-dependency list makes the whole package
a static or older-glibc-compatible distribution.
macOS records `otool -L` and `otool -l`. Shared libraries remain external. Do not
infer the oldest compatible glibc/macOS/Windows version from the runner name or
linker metadata alone: minimum versions and clean-host execution are unverified.
macOS is not Developer ID signed or notarized (an ad-hoc linker signature is not
publisher signing). Document Gatekeeper warnings; never advise disabling system
security globally. Both Unix executables must retain mode 0755 in tar archives.

## Scope of this documentation reconciliation

Validation is limited to reading source and existing records, static relative-link
and version/filename checks, and `git diff --check`. No builds, tool installations,
test suites, menu/screenshot capture, audio/index access, CI dispatch, remote
query, cleanup or release mutation were performed. Future procedures above are
not completed-check claims. Parent/maintainers own clean-host feasibility, audio
smoke tests, historical privacy review, retention and any authorized cleanup.
