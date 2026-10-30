# Building staged portable artifacts

## Status and scope

All four targets are **unverified** until their actual native CI jobs succeed.
The initial tooling checkout has not yet integrated the Rust app, vendored Olaf,
runtime provider, hygiene checker or full legal material. Mocked archive tests
are not compiler, runtime, operating-system compatibility or accuracy tests.
Do not run compilation, audio indexing or stress tests as part of this local
tooling review. Commands below are for a later, explicitly authorized build.

This tool does not read an older development checkout, copy its private Olaf
executable, restore private source with secrets, replace root executables, or
adopt its music, indexes, caches or toolchains. All generated build inputs,
toolchains, temporary files and packages belong under the release checkout's
`build/` or `dist/`. A fresh staging subdirectory is required for every build;
the tool never recursively deletes or overwrites an existing build.

## Native matrix and prerequisites

| Package target | Rust target | Hosted runner | Verification |
|---|---|---|---|
| `windows-x64` | `x86_64-pc-windows-msvc` | `windows-2025` x64 | Unverified |
| `linux-x64` | `x86_64-unknown-linux-gnu` | `ubuntu-24.04` x64 | Unverified |
| `macos-arm64` | `aarch64-apple-darwin` | `macos-15` ARM64 | Unverified |
| `macos-x64` | `x86_64-apple-darwin` | `macos-15-intel` x64 | Unverified |

The runner labels follow [GitHub's runner architecture table](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
Their availability/billing for this private repository has not been tested.
OS-image labels are pinned, but hosted image contents can change; this is not a
hermetic image pin. Native builds are mandatory: host architecture is checked
before provisioning, and PE/ELF/Mach-O headers of **both** executables must match.
Rosetta translation or relabeled cross-compilation is not a substitute.

Requirements: Git, Python 3.13.1 (CI pin; Python 3.11+ for the release script),
HTTPS access to official tool and Cargo registry endpoints, and native system
build prerequisites. Windows needs MSVC C/C++ Build Tools and Windows SDK;
Linux needs a C compiler/linker, libc development headers, `pkg-config` and
`readelf`; macOS needs Xcode Command Line Tools/SDK and `otool`. If dependencies
require additional native development packages, stop and review rather than
copy libraries from another computer. These prerequisites have not been exercised
by the local mocked tests. The tool makes no system package-manager changes.

FFmpeg and FFprobe are **external user-installed runtime prerequisites**. Neither
binary belongs in a package. The release gate tests deliberately need neither
an audio dataset nor audio tools. Upstream distribution information is available
at [FFmpeg downloads](https://ffmpeg.org/download.html).

## Pins and isolated provisioning

`rust-toolchain.toml` and `release/targets.json` pin **Rust 1.99.0**. This released
compiler was selected after inspecting the actual Rust 2021 application and v4
Cargo lockfile, including rfd 0.17/rusqlite 0.41 dependencies, rather than using
the obsolete Python checkout's requirements. Availability was checked against
the [official Rust distribution manifest](https://static.rust-lang.org/dist/channel-rust-1.99.0.toml).
Compilation compatibility remains unverified. At build time, locked Cargo
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
commands explicitly pass `-j1`. Provider pin/job behavior must be verified when
its branch is integrated; there is no license to use an ignored old executable.

## Integrated input contract (fail closed)

Before a real build, review and commit these files in **this** checkout:

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
one manifest. Provider-specific provenance is preserved, not replaced. Its schema,
local dependency wiring and job control still need cross-branch integration review.

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
native runtime. Source added by integration may require a narrowly reviewed
inventory amendment. Do not broaden it to an entire workspace or Git HEAD.

## Future build commands

Run in the integrated, clean, committed release checkout on the matching host.
No command below should be pointed at a personal index or music directory.

```powershell
# Windows x64, new staging directory only:
python scripts/release.py build --target windows-x64 --out-dir build/release/windows-x64
python scripts/release.py test --target windows-x64 --out-dir build/release/windows-x64
python scripts/release.py package --target windows-x64 --out-dir build/release/windows-x64
python scripts/release.py verify --out-dir build/release/windows-x64
# Equivalent wrapper (build only unless -Package is explicitly present):
.\Build-Rust.ps1 -Target windows-x64 -OutDir build/release/windows-x64-new -Package
```

```sh
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

The Rust test allowlist is exact (missing/zero-test matches fail): extrema,
SQLite rollback/matching, manifest/verification policy, worker-selection tests.
It excludes the synthetic audio streaming test and ignored manifest benchmark.
The Olaf steps are `test-matcher-v3`, `test-db-safety`, `test-config-safety` only,
run from an inventory-only staging copy with ReleaseSafe and one build job.
They must remain dataset-free after integration. Never invoke unrestricted
`zig build test`, dataset download steps, developer validation/benchmark scripts,
library indexing, or the interactive menu. CLI smoke checks are app `--help`,
app `--version` (must match Cargo.toml), and Olaf `--help`, in a private temporary
HOME. The inspected Olaf CLI has no `--version` command: its source version is
recorded from `build.zig.zon` and tied to the binary/provider/source hashes, not
misrepresented as a successful runtime version query. Help may create sandboxed
configuration/cache directories, but must not index audio.

## Output and verification

`OUT/dist/` contains exactly:

* `local-shazam-COMMIT12-TARGET.zip` on Windows or `.tar.gz` on Unix;
* matching `...-app-source.tar.gz`;
* matching `...-olaf-source.tar.gz`;
* `SHA256SUMS` covering all three archives.

The app source archive includes the locked Rust source and release tooling; Cargo
registry dependencies are fetched by their lockfile checksums, not vendored into
that archive. The **complete corresponding native Olaf source** includes Zigzag,
embedded LMDB/PFFFT/c-algorithms source, native build/test inputs, modifications,
patches, instructions and licenses. The combined source archives are sufficient
inputs to the same build tooling; overlay them into a new reviewed checkout when
rebuilding both executables. The release packaging command requires Git identity
and a clean reviewed commit, not a fabricated claim that extracted files are HEAD.
The runtime can separately be rebuilt with the provider command from its source
archive, subject to that provider's documented prerequisites.

Every archive embeds the **same** `BUILD-PROVENANCE.json`. Verification reads
archives without executing or extracting their contents: it checks checksums,
exact file sets, source digests, cross-archive provenance, notices, executable
headers, permissions and test-gate records. It rejects links, traversal,
duplicates, case collisions, unexpected files and incomplete source bundles.
Verify downloaded artifacts independently with:

```sh
python3 scripts/release.py verify --out-dir build/downloaded/portable-linux-x64
```

`verify` is read-only and can accept an artifact directory outside staging too.
Checksums demonstrate consistency, **not publisher authentication**; compare
against the reviewed commit/private CI run. Normalized archive metadata is not
proof of bit-for-bit binary reproducibility; no such claim is made.

## Dynamic dependencies and unsigned distribution

Windows normal **and delay-load** PE imports are inspected without loading either
program. DLL names are recorded; no arbitrary local DLL is bundled, and their
availability on a clean user machine remains unresolved. Obtain any required
Microsoft redistributable only from Microsoft. Windows packages are unsigned;
SmartScreen reputation is not established.

Linux records `readelf -d -V` (including dependency and symbol-version needs).
macOS records `otool -L` and `otool -l`. Shared libraries remain external. Do not
infer the oldest compatible glibc/macOS/Windows version from the runner name or
linker metadata alone: minimum versions and clean-host execution are unverified.
macOS is not Developer ID signed or notarized (an ad-hoc linker signature is not
publisher signing). Document Gatekeeper warnings; never advise disabling system
security globally. Both Unix executables must retain mode 0755 in tar archives.

## Lightweight local checks only

```sh
python -B -m unittest discover -s tests/release -p test_packaging.py -v
python -B -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text()) for p in ['scripts/release.py','tests/release/test_packaging.py']]"
git diff --check
```

Tests use synthetic PE/ELF/Mach-O headers and temporary source trees; they block
all subprocess/download calls. They do not build or execute application code,
access datasets, trigger CI or create remote objects. A Windows symlink-creation
test can be skipped when the host does not grant that privilege.

### Linux native dialog prerequisites

On Ubuntu/Debian, install `pkg-config libwayland-dev libxkbcommon-dev libgtk-3-dev`
before a native build. CI installs these only on its disposable Linux runner.
