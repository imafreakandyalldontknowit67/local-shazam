# Private Windows release status and maintainer gates

## Current status: recorded private v0.2.1 Latest

The existing [release status](PREVIEW_STATUS.md) identifies **v0.2.1 as Latest
inside the PRIVATE repository**, with tag/build commit
`d32716df0be1a5ea2d919d0b8ceb560de17bd77c`. Later documentation commits do not
change the binaries' identity. This restates recorded evidence, **not newly
queried remote state or current-HEAD validation**. It is a Rust terminal/menu
application, not a Node app; there is no root `package.json` workflow.

Only Windows x64+x86 are in this release. Linux/macOS artifacts below are
historical, not v0.2.1 releases. The private Latest record is not an instruction
to retain an unpublished old draft, and it does not grant **public-release
approval, which remains pending**. No remote action is authorized here.

### Recorded completed v0.2.1 checks

The retained `dist/readiness-audit/release-0.2.1-verification.json` identifies
release ID `430903426`, the build commit above, private visibility, actual
downloaded-byte comparisons for all seven assets and independent verification of
both downloaded target sets. `0.2.1-x64-manifest.json` and
`0.2.1-x86-manifest.json` record 16 dataset-free gates each, matching sources and
payloads, architecture/import inspection and `compiler-paths-and-artifacts-v1`.
The current status record reports archive/privacy verification passed. These
are bounded recorded checks, not a claim of zero private data or a history audit.

`0.2.1-x64-menu.log` and `0.2.1-x86-menu.log`, together with the verification
record, document menu/exit checks without creating an index. Startup shows the
plain **Local Shazam** heading and **[1] Add a music folder**,
**[2] Identify audio clips**, **[3] View library stats**, **[4] Exit**; backend,
index path and development banner no longer print at startup.
`windows-0.2.1-notes.md` records the release scope and caveats.
`tests-0.2.1-final.log` reports 140 static tests with 3 skipped (137 passed);
its mocked packaging output does not demonstrate additional native releases.
All these filenames refer to retained local records, which may be absent from
source-only checkouts. No checks were rerun or evidence invented here.

| Output | Rust target | Olaf target | Recorded execution |
| --- | --- | --- | --- |
| Windows x64 | `x86_64-pc-windows-msvc` | `x86_64-windows-gnu` | Native on x64 Windows |
| Windows x86 | `i686-pc-windows-msvc` | `x86-windows-gnu` | **WOW64 on x64 Windows**, not native 32-bit OS validation |

Both outputs use x64 host tools. Manifests/configuration agree on **Rust 1.99.0**,
**Zig 0.16.0**, **Rustup 1.28.2** and recorded Python **3.13.1**. Future builders
need Git, Python 3.11+ (standard library only), appropriate MSVC build tools/SDK
and **clang-cl on PATH, with no cl.exe fallback**. Recipients need no Python or
compiler: they need the complete matching package, adjacent `olaf-runtime/`,
external **FFmpeg AND FFprobe on PATH**, and architecture-appropriate Microsoft
runtime components from official installers. The app imports `vcruntime140.dll`;
both executables record Universal CRT/system imports. An x86 process needs x86
runtime components even under WOW64. This does not establish a clean-host test
or supported minimum Windows version. See [Building](BUILDING.md) and
[Quickstart](QUICKSTART.md).

### Recorded seven release assets

- `Local-Shazam_0.2.1_x64.zip`
- `Local-Shazam_0.2.1_x64_app-source.tar.gz`
- `Local-Shazam_0.2.1_x64_olaf-source.tar.gz`
- `Local-Shazam_0.2.1_x86.zip`
- `Local-Shazam_0.2.1_x86_app-source.tar.gz`
- `Local-Shazam_0.2.1_x86_olaf-source.tar.gz`
- Combined `SHA256SUMS.txt` for the six archives.

The single-target verifier requires separate verification directories: each has
only one target's three matching archives and a `SHA256SUMS.txt` derived from its
three lines in the combined checksum file. Preserve the original combined bytes
and their hash/size separately. Do not pass all seven assets to one invocation.
Historical `local-shazam-COMMIT12-TARGET` sets with `SHA256SUMS` and applicable
legacy native provenance are also understood, without rewriting names/evidence;
mixed conventions and incomplete sets fail. This is not a waiver of the current
privacy-policy requirement for old artifacts. See [verification details](BUILDING.md).

No build, application/menu/audio execution, screenshot capture, CI dispatch,
remote query, tag/release change or cleanup was performed for this documentation
reconciliation. Its checks are reading/static link and filename consistency plus
`git diff --check`; future maintainer procedures are not completed-check claims.

## Historical v0.2.0 / native-preview review

The earlier **Rust 0.2.0** multi-platform preview was not release-ready in its
reviewed scope. Keep that historical conclusion separate from the later private
Windows release. The historical review did not dispatch workflows, execute
artifacts, edit the draft, create/move tags or change visibility. Neither review
is legal approval; changing visibility alone resolves no source/privacy obligation.

### Historical verification (2026-10-30)

Historical preview commit: `92a983a57ff92ad4b9342fb4dd992edf728b5a97`.
[Native run 41023384988](https://github.com/imafreakandyalldontknowit67/local-shazam/actions/runs/41023384988)
completed successfully on Windows x64, Linux x64, macOS arm64 and macOS x64.
The historical authenticated read-only GitHub metadata review recorded those
four job conclusions; it is not a fresh remote query.
This was a **push** run of `portable-build.yml`, not evidence of a successful
manual draft workflow, environment approval or denial-path test.

All four existing local artifact sets in `dist/ci-92a983a` were independently
read without extraction/execution: all twelve archive checksums, embedded
source/payload hashes, archive file sets/modes, executable architectures and
cross-archive provenance passed verification. The four source inventories agree.
Each manifest records the exact commit and **16 completed dataset-free gates**:
ten selected Rust tests, three Olaf regression steps, and app help/version plus
Olaf help. See [Building](BUILDING.md) for the allowlist and
[the redacted evidence record](../licenses/review/native-preview.json) for hashes.
A checksum proves consistency, **not publisher authentication**. These are
historical records, **not current-HEAD validation** or a compatibility, privacy,
recognition-accuracy, hardware-stability or legal approval.

The historical authenticated release listing recorded private draft **`v0.2.0-native.1`**,
release ID `428787114`, with `draft: true`, `prerelease: true`, no publication
timestamp, and `target_commitish` equal to the preview commit. Its twelve archive
and combined `SHA256SUMS` API digests/sizes match the local files. Remote asset
bytes were not downloaded; uploader identity/signature was not authenticated.
The release-by-tag/commit lookup did not resolve and the authenticated tag list
had no matching ref: the draft's `tag_name` is **not a verified existing tag**.
That finding is about the old draft, not the recorded v0.2.1 tag. Do not rename
or recreate any release to resolve that historical distinction here.

The [baseline privacy audit](PRIVACY_AUDIT.md) records hosted-build paths in
Linux/macOS executables. That prior finding was not rerun as a binary privacy
audit here. Existing artifacts cannot be promoted as compiler-sanitized merely
because source hygiene or checksum verification passes. Source vendoring notes
that say builds were unverified describe that earlier capture phase; the native
run above supersedes only their build-status uncertainty, not their legal limits.

### Historical completed factual checks

- [x] Integrated Rust app, vendored Olaf/Zigzag, provider, inventory, hygiene
  checker and build workflows inspected; Rust **1.99.0**, Zig **0.16.0**, and
  Rustup **1.28.2** pins agree with the build configuration.
- [x] Historical native results and artifact/source correspondence checked as
  scoped above; minimum OS and broader compatibility remain unverified.
- [x] Private draft flags and API asset digests/sizes checked read-only; no
  claim of a preexisting tag or manual draft-workflow approval.
- [x] Full 115-registry-package inventory compared with Cargo.lock; notice
  hashes checked. Exact archives/VCS metadata for seven Apple-family blockers,
  sqlite-wasm-rs and their rfd/rusqlite/libsqlite3-sys selection evidence reviewed
  without Cargo. [License review](../licenses/RELEASE_REVIEW.md) records limits.
- [x] Wasm shim applicability narrowed by exact manifests: not selected by the
  inspected rusqlite dependency predicate for the four native triples. This is
  not complete target-feature/link closure or permission to ship shim source.
- [x] Historical app-source archives contain no vendored Cargo dependency
  implementations and no legacy Python app. Notices for other targets are
  inventory evidence, not evidence that their implementations were shipped.
- [x] Owned documentation and evidence checked for operator paths/private
  details, retaining original public attribution. See the license review for
  static-check scope; no new history/private-blob audit is claimed.

### Historical post-integration static checks

- [x] Integrated and reviewed compiler path-remapping/privacy gates, including
  regressions for binary-string false positives; see `docs/BUILD_PRIVACY.md`.
  Local checkout: 108 lightweight
  tests passed with three Windows symlink skips; no local native compilation.
- [x] Verified Python relocation and native source exclusion. Combined exported
  native source: 96 lightweight tests passed with four skips (including the
  intentionally absent legacy archive). Source includes required docs/assets and
  Git text/ignore policy files. Both native engines are unchanged.

### Subsequently recorded Windows replacement / v0.2.0 history

The README at `98a54f3`, as restated in [release history](PREVIEW_STATUS.md),
records a Windows x64 package built locally at `d639ab2a2c49` with native
test/packaging gates and uploaded-download checksum verification passed. This
separate record does not expand the old four-target metadata comparison into
downloaded-byte verification. v0.2.0 remains release history. Linux/macOS at
`92a983a57ff9` still await replacement and independent compiler-privacy checks.

## Still-open gates - parent and maintainers

### Parent-owned validation (pending, not satisfied by private Latest)

- [ ] Linux/macOS replacement builds at a reviewed commit and independent
  privacy/correspondence checks remain pending. Any future changed build,
  including Windows, needs its own exact-commit evidence and explicit gates;
  do not reuse v0.2.1 or historical success as current-HEAD approval.
- [ ] For future rebuilds, independently verify every binary and both source
  archives:
  checksums, commit/source/payload hashes, complete source inventory, matching
  provenance, notices, architecture/modes, archive headers/metadata and compiler
  path/privacy policy. Verify extracted source with the source-only checker;
  do not apply it blindly to executables or weaken it to allow binaries.
- [ ] Retain sanitized per-target selected-feature/link/toolchain/SDK evidence.
  Existing provenance has no complete emitted compiler-runtime inventory.
  The [Windows distribution review](../licenses/WINDOWS_DISTRIBUTION.md) records
  a selected x64 dependency graph, not an exact linker map or automatic
  x86/all-target closure. Do not infer these from Cargo.lock alone.
- [ ] Perform the **final history/publication-surface audit** after integration:
  newly reachable commits/refs and metadata, tags, release descriptions/assets,
  workflow logs, remote branches, Pages/wiki and other publication surfaces.
  Recheck private visibility. Report findings redacted, retain public attribution,
  and leave any sensitive history remediation to an explicitly authorized task.
  Moving Python files does not erase their history.

### Maintainer/legal and distribution decisions (open)

- [ ] Resolve seven Apple-family attribution/SDK reviews for applicable native
  and source distributions. No generic MIT template or author list closes them.
  The recorded Windows x64 graph excludes these crates; this is not evidence
  that their implementations ship in the current Windows package.
- [ ] Resolve sqlite-wasm-rs musl provenance/notices **if** its shim source or
  wasm binary is distributed; retain this lockfile concern, without calling it
  an established blocker for the current native binaries. Re-evaluate changed
  features/targets/source-bundling decisions.
- [ ] Approve AGPL integration/combined-work and corresponding-source plan,
  including runtime/dependency source, modifications/dates, build/install inputs,
  recipient access and any installation/network-service obligations. A private
  source URL, subprocess boundary or green CI run is not sufficient approval.
- [ ] Close target-specific Rust std/compiler runtime, Zig/CRT, system-library
  and SDK obligations. Review original-app rights and the upstream patent warning.
- [ ] Establish clean-host behavior and minimum OS/glibc support before making
  support claims. The historical Linux app records `GLIBC_2.39` and Wayland needs;
  Olaf's musl recipe does not remove the app's glibc requirements.
- [ ] Native 32-bit Windows OS validation is still open: x86 v0.2.1 execution
  evidence is WOW64 only. Parent owns clean-host feasibility and audio smoke
  tests; dataset-free gates/menu checks do not prove audio recognition accuracy.
- [ ] Validate resource use, stability and post-crash index integrity before
  making safety claims. Start conservatively with two workers/a small folder;
  even the default cap of six is not a proven crash fix. The x86 **512 MiB
  database mapping limit is not a total-RAM bound**. Switching architecture
  requires a fresh index and reindexing; never replace a pinned index runtime
  in place or reuse the other architecture's database.
- [ ] Decide acceptable unsigned Windows / non-Developer-ID-signed,
  non-notarized macOS distribution policy. Do not advise disabling OS security.
  Signing/notarization and bit-for-bit reproducibility remain unverified, not
  silently supplied by normalized tar/ZIP metadata.

FFmpeg and FFprobe stay external, user-installed tools. Any bundling change needs
a new build-specific license/source audit. Accuracy/stability claims need separate
validation; dataset-free gates do not establish them.

## Existing workflow boundaries (not authorization to run them)

[`portable-build.yml`](../.github/workflows/portable-build.yml) currently has
**five targets**: Windows x64+x86, Linux x64, macOS arm64 and macOS x64. It has
no Windows-only dispatch input; its scope is not the recorded two-target release.
It uses `contents: read`; branch pushes, pull requests,
manual dispatch and reusable calls can build, but cannot create a release/tag.
The read-only build workflow also works after an eventual owner visibility change;
it does not change visibility itself. New builds supersede older runs on the same
workflow/ref. The separate draft-publication workflow still requires a private repo.
Build jobs use pinned actions, verified tool downloads and locked single-job
Cargo builds. Only three archives plus checksums per target are uploaded, with
seven-day artifact retention. No toolchains/caches/raw logs are release assets.

[`private-draft.yml`](../.github/workflows/private-draft.yml) is manual-only,
with `create_draft` defaulting to **false**.
Preflight requires a private repository. For draft creation it also requires an
**existing reviewed tag** resolving to the selected full commit, an exact typed
confirmation, all **five** fresh target builds/gates (x86 via WOW64) and independent
aggregate verification. It refuses existing releases; it is not an update path.
The historical draft's name does not satisfy that tag prerequisite by itself.
Before any future authorized run, review action pins, runner availability/billing,
workflow trust, protected refs and concurrency with administrators. Configure
`private-prerelease` environment protections and reviewer rules where supported;
an environment name alone is not approval. If policy cannot be enforced, leave
draft creation off. This task does not create the tag or enable those settings.

Only the separate `draft` job has `contents: write`. It does not check out or run
repository scripts. It rechecks private visibility, tag/commit identity and
asset hashes. Creation always requests `draft: true`, `prerelease: true` and
`make_latest: false`; there is no publish/promote, tag creation, visibility change
or existing-release modification path. A typed confirmation is an attestation,
not an automated legal opinion. These static properties do not prove live
permissions, approval rules or denial cases were exercised.

These draft-creation restrictions do **not** describe the already recorded
Windows-only v0.2.1 private Latest state and do not require its demotion or
recreation. No workflow dispatch, tag, remote action or policy change is
authorized by this document.

## Future asset and final owner review

Each target needs its binary archive, matching app-source archive, matching
Olaf-source archive and checksums. The current five-target draft writer
consolidates checksums for **15 archives plus one `SHA256SUMS.txt`**, unlike
v0.2.1's six archives plus one checksum asset. Per-target sources include
target-specific provenance and must not be omitted. Binary packages contain the
separate app/Olaf executables,
setup, licenses/notices and provenance. App source contains the locked app and
build tooling; Olaf source includes native runtime/Zigzag/embedded C code,
patches and build/test inputs. Source obligations still need the review above.

For a future authorized draft-creation run, uploads are not transactional.
Failure can leave an incomplete draft; leave that draft unpublished for an
authorized maintainer to inspect. This is not a claim that v0.2.1 is still a
draft. Verify expected assets and the authorized state before any future owner
decision. `release/targets.json` retains conservative `unverified`
support/minimum-OS labels; historical native-gate success does not upgrade them.

Use the [release checklist](RELEASE_CHECKLIST.md) for future verification and
the [cleanup checklist](BUILD_CLEANUP.md) only for separately approved retention
review. Parent owns historical privacy scanning, clean-host/audio work and
cleanup. No directory is disposable merely because upload succeeded, and no
deletion or public-release approval is granted here.
