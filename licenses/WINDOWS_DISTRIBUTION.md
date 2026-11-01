# Windows distribution evidence — v0.2.1 x64 and x86

## Scope and decision (2026-11-01)

The supplied parent record identifies **private v0.2.1, Windows x64+x86**, built
from `d32716df0be1a5ea2d919d0b8ceb560de17bd77c`. This bounded static review is
**not legal approval or public-release certification**. It authorizes no public
launch, visibility change, music upload or hosted recognition service.
Public-release approval remains pending.

The [applicability record](review/windows-x86-applicability.json) contains exact
archive filenames, SHA-256 values, input identifiers, methods, results and gaps.
Three evidence categories must remain separate:

- **Historical:** [windows-selected-dependencies.json](review/windows-selected-dependencies.json)
  is retained `x86_64-pc-windows-msvc` evidence: app plus 72 dependencies,
  including build dependencies, not an x86 resolution or linker map.
  [RELEASE_REVIEW.md](RELEASE_REVIEW.md) preserves earlier multi-platform findings;
  its native tests and upstream investigations were not repeated.
- **Parent-supplied:** `dist/readiness-audit/release-0.2.1-verification.json`
  records private visibility, download/hash checks and menu exit. The accompanying
  `0.2.1-x64-manifest.json` and `0.2.1-x86-manifest.json` record 16 gates each,
  x64 native and x86 **WOW64 on x64**, not native 32-bit Windows. Remote visibility,
  downloads, builds and execution were not independently repeated here.
- **Performed here:** standard-library, in-memory archive/JSON/hash and PE
  descriptor checks of the six top-level archives and `SHA256SUMS.txt` in the
  supplied parent's `dist/verified-windows-0.2.1`. No extraction, compiler,
  Cargo metadata, dependency-script execution, install, native/audio test,
  clean-host work or historical privacy scan was performed.

This document and the new evidence postdate those archives; they do not change
their contents or validate later builds.

## Established artifact observations

All six archive sizes/hashes match both supplied checksum and verification
records. Each target's binary/app-source/Olaf-source `BUILD-PROVENANCE.json`
matches byte-for-byte and agrees with the parent manifest, commit and target.
All recorded payload/source member sets, hashes and permission modes match.

| Binary archive | Rust 1.99.0 output | Olaf / Zig 0.16.0 output |
| --- | --- | --- |
| `Local-Shazam_0.2.1_x64.zip` | `x86_64-pc-windows-msvc` | `x86_64-windows-gnu` |
| `Local-Shazam_0.2.1_x86.zip` | `i686-pc-windows-msvc` | `x86-windows-gnu` |

Each target has 315 payload files, 349 app-source inventory files and 556
Olaf-source inventory files, each archive plus generated provenance. Source
inventories and bytes are equal across architectures except build provenance.
Binary ZIPs differ only in build provenance, two executables and Olaf
`BUILD-INFO.json`. Full hashes and all four exact source-archive names are in the
[record](review/windows-x86-applicability.json).

The 297 common legal/evidence members (295 under `licenses/`, plus root MIT and
third-party notices) match all three archives per target. Runtime provenance,
AGPL, notices, build documentation and ten runtime notice files match source,
including Zigzag attribution. All 251 final hashes in
[`PROVENANCE.json`](../vendor/olaf/PROVENANCE.json) match archived source using
its CRLF-to-LF convention. `BUILD-INFO.json` binds runtime hash, source-provenance
hash and target. These establish **internal byte correspondence**, not independent
proof of compilation from that source or legal sufficiency.

### x86 modifications and source boundaries

Both Olaf-source archives contain the seven patches in the order recorded by
[`series`](../patches/olaf/series) and provenance. All eight new-side hunks of
[`0006`](../patches/olaf/0006-x86-database-width.patch) and five of
[`0007`](../patches/olaf/0007-x86-cli-compatibility.patch) match the already-patched
archived source at their declared offsets:

- 0006: 512 MiB 32-bit mapping, full-width comparisons, alignment-safe reads,
  checked writes and wide-key/duplicate regression source.
- 0007: MinGW `_X86_` C-import definition and mutex-protected full-width temporary
  counters, including the UI module.

The [patch README](../patches/olaf/README.md) dates both **2026-11-01**;
changed DB/core/threading/UI source also carries that date. No full-series replay
or native regression was performed. **Documentation gaps:** archived
[`NOTICES.txt`](../vendor/olaf/NOTICES.txt) still summarizes modifications captured
on 2026-10-29; [`BUILDING.md`](../vendor/olaf/BUILDING.md) omits x86 from its
command/table examples. Scripts, targets and provenance do include x86.
The maintainer/reviewer must reconcile these gaps and assess prominent
modification notices/dates and adequate build/install instructions. This review
changed no notice, patch or provenance file.

Relevant C/headers, CLI/TUI/REST/UI, configuration example/schema, build scripts,
tests and sibling Zigzag module source are present. Olaf's manifest uses local
`../zigzag`; Zigzag declares no package dependencies. LMDB/OpenLDAP/btree,
PFFFT/FFTPACK, c-algorithms and Zigzag attribution remains intact. Existing
exclusions include Zigzag standalone examples/tests and optional fixtures/harnesses
described in BUILDING.md. Inventory equality does not prove complete build/link
closure or settle the appropriateness of every exclusion.

App-source includes Cargo.lock, notices and small review manifest/build-script
copies, **not vendored registry implementations**. No Apple-family or
sqlite-wasm-rs implementation bundle is present. The evidence copies are
redistributed source material, not complete crate source or a substitute for
applicable dependency-source obligations.

## Dependency applicability: observations and static inference

Cargo.lock's 115 registry entries match the retained inventory by
name/version/checksum and LF lock hash. All 240 Rust notice-copy hashes,
11 Olaf notice-copy hashes and 20 retained crate-evidence hashes match their
records. No published crate archives were fetched again.

**Static inference on the examined paths, for both Windows output triples:**

- [`rfd 0.17.2`](review/crates/rfd-0.17.2/Cargo.toml) selects `windows-sys`
  (locked 0.61.2) under `cfg(target_os = "windows")`, not its macOS, Linux/BSD
  or wasm32 dependencies. Six Apple-family direct dependencies are macOS-only
  on this path; retained objc2 metadata supplies the `objc2-encode` edge.
  This is not a claim those crates can never support Windows elsewhere.
- [`rusqlite 0.41.1`](review/crates/rusqlite-0.41.1/Cargo.toml) restricts
  sqlite-wasm-rs to `cfg(all(target_family = "wasm", target_os = "unknown"))`.
  Both Windows targets satisfy its negation, selecting libsqlite3-sys 0.39.1.
  The default `ffi-sqlite-wasm-rs` feature label does not override that predicate.
- The app requests `rusqlite/bundled`, forwarding bundled SQLite/modern bindings.
  The exact [libsqlite3-sys build script](review/crates/libsqlite3-sys-0.39.1/build.rs)
  contains SQLite C amalgamation, MSVC/optional `crt-static`, and environment/
  feature override branches. [`release.py`](../scripts/release.py) removes
  relevant inherited overrides, but this recipe is not emitted-object proof.
  The binding's MIT terms do not relicense SQLite's retained dedication as MIT.

**Unproven:** a newly resolved x86 feature/package graph, every transitive target
predicate, build-script output and full linked-object/runtime contents. rfd
declares `build.rs`, but that script is not retained; exact windows-sys/windows-link
manifests/implementations are absent. Four Apple-family crates have VCS metadata
only. Missing inputs were not regenerated. The historical x64 list excludes all
seven Apple-family crates and sqlite-wasm-rs; it cannot be relabeled as x86.

Lock membership, resolved feature labels, target-selected dependencies, emitted
objects and redistributed source are different categories. For example, x64
metadata lists rfd Wayland features although its Windows dependency path excludes
those packages. **Absence on one path is not complete link closure.** Apple
attribution/SDK and wasm-musl questions remain conditional on applicable targets,
features or implementation-source redistribution, not newly established Windows
blockers. Historical Linux/macOS findings are not reopened as Windows requirements.

## Toolchains, runtimes and external prerequisites

[`targets.json`](../release/targets.json), [`rust-toolchain.toml`](../rust-toolchain.toml)
and [`build_olaf.py`](../scripts/build_olaf.py) distinguish Rust MSVC i686/x86_64
outputs from Olaf Zig GNU x86/x86_64 outputs. Both use pinned x64 host tools;
host download metadata is not the x86 output identity. **Static build inference:**
Olaf's native CLI adds LMDB/PFFFT/c-algorithms, local Zigzag and REST, and links
libc. This does not identify every object that survived linking.

The [Rust library copyright inventory](runtime/rust-1.99.0/COPYRIGHT-library.html)
and 12 accompanying texts match across packages, as do Zig MIT,
[mingw-w64 COPYING](olaf/mingw-w64-COPYING.txt) and musl COPYRIGHT. Earlier
installed-toolchain comparisons are historical, not repeated here. No
`licenses/toolchains/` directory was available. Broad copyright inventories and
generic terms are not linked-component proof or substitute attributed grants.
MinGW COPYING has component exceptions; musl notice presence proves neither
Windows linkage nor coverage of sqlite-wasm-rs's separate shim. Exact emitted
Rust/compiler-builtins/Zig/MinGW/CRT/SDK terms and source duties remain open.

Independent PE descriptor checks confirm x86 `0x014c`/PE32 and x64
`0x8664`/PE32+ for both executables. Normal-import DLL names match the records;
all four delay-import directories are empty. Both apps import `vcruntime140.dll`,
UCRT API sets and Windows DLLs. Olaf imports UCRT API sets and Windows DLLs;
x64 Olaf additionally lists `api-ms-win-crt-private-l1-1-0.dll`. Exact DLL lists
and executable hashes are in the new record. Descriptor checks do not expose
all static code, dynamic loading, SDK contributions or license obligations.

Neither ZIP bundles Microsoft runtime DLLs/installers, SDK/compiler executables
or **FFmpeg/FFprobe**. CRT/UCRT/OS DLLs and FFmpeg/FFprobe remain external
prerequisites. Required Microsoft runtime software should come from official
Microsoft distribution, never copied development DLLs. Nothing was installed or
copied here. Imports establish neither clean-host availability nor a minimum OS;
WOW64 gates establish no native 32-bit Windows compatibility.

## Source delivery and unresolved rights questions

The inspected v0.2.1 archives contain the original app MIT notice
`Copyright (c) 2026`. The owner subsequently selected **badger**, and the current
[repository MIT license](../LICENSE) now names that holder; existing release
archives were not silently modified. Modified Olaf
remains **AGPL-3.0-or-later**, with component attribution intact. Confirm the
original-app rights/attribution basis separately; manifest labels do not license
the entire combined distribution.

The required delivery plan is **both exact source archives alongside each binary
ZIP**, equivalent recipient access, no additional source charge and clear
directions for as long as required. Preserve preferred-form modified sources,
ordered patches, needed dependency/configuration/build/install material and
notices. Do not substitute autogenerated GitHub source, a moving branch or a
private fork link. This is the intended designated-place mechanism in the supplied
[AGPL section 6(d)](olaf/AGPL-3.0.txt), **not a finding that every recipient currently
has sufficient source/access**. Private access controls cannot replace source
access or restrict licensed modification/redistribution rights. Do not impose an
NDA, proprietary-only terms or additional restrictions (section 10).

Qualified review remains necessary for sections 1/5/6 corresponding-source
sufficiency, combined-work versus aggregation, modification/UI notices and any
applicable installation information. Hash correspondence and packaging success
settle none of these. Evaluate missing registry implementation sources against the
actual covered-work scope, not presumed automatic sufficiency or failure. The
portable-software plan describes no transferred locked hardware product; reassess
section 6 if deployment changes rather than assert a universal exemption.

The inspected [`olaf.rs`](../rust-app/src/olaf.rs) generates local configuration,
pins a copied runtime digest and invokes `store`/`query` with isolated
HOME/USERPROFILE; candidate verification uses external FFmpeg. This path does not
start REST. Nevertheless Olaf's build imports REST and retains UI/server source:
**subprocess separation and private status are not blanket AGPL exemptions**.
Review section 13/source-offer obligations before future remote-network operation.
Upstream patent warnings, applicability and rights remain unresolved; no patent
permission or current patent-status conclusion is inferred.

## Before public release — parent / qualified reviewer actions

1. Retain actual x86 resolved features and target-specific link/runtime/SDK
   evidence; close applicable notice/source-duty gaps for both architectures.
2. Reconcile x86 build instructions and modification summaries; assess complete
   corresponding source, exclusions, UI notices and installation information.
3. Verify recipient access to both exact source archives and downstream license
   rights; resolve combined-work and original-app rights questions.
4. Resolve applicable patent/deployment questions; keep future hosted service,
   other targets and any new FFmpeg bundling subject to separate review.
5. Parent owns prerequisite/compatibility work and final publication-surface,
   private-visibility and release checks. Record approval separately:
   **public-release approval remains pending**.

## Parent follow-up for 0.2.2-beta.1 (2026-11-01)

The preceding review and JSON are a frozen assessment of v0.2.1, not a claim
that later source changes are inside those old archives. Subsequent engineering
closures are recorded here without rewriting the historical evidence:

- [Both target graphs](review/windows-0.2.1-target-graphs.json) were collected
  with pinned Cargo, offline and locked, from each retained build snapshot.
  x86 and x64 select the same app plus 72 dependency/feature records; the
  Apple-only and sqlite-wasm-rs packages are absent. This closes the missing x86
  resolved-graph evidence, not a full linker/SDK or legal analysis.
- Current vendor/olaf/BUILDING.md now includes the x86 recipe and index limit.
  NOTICES.txt adds dated modification summaries for patches 0004 through 0007;
  all existing upstream notices remain unchanged. Final distribution hashes
  were refreshed in PROVENANCE.json; the seven source patches are unchanged.
- The owner selected badger for the original-app MIT copyright header. The beta
  packages must include that updated notice and corresponding reviewed sources.
- FFmpeg, FFprobe and Microsoft runtime installers/DLLs are still not bundled.
  Official architecture-matched prerequisite guidance is provided; a clean-PC
  test and native 32-bit Windows execution are explicitly unverified.
- The owner requested a public beta, contingent on fresh package checks. This is
  a publication decision, not a qualified legal opinion. No blanket AGPL
  subprocess exemption, patent clearance, license relicensing, or closure of
  every legal interpretation above is claimed. Keep original MIT/AGPL notices,
  both matching source archives, and recipients' licensed rights intact.
