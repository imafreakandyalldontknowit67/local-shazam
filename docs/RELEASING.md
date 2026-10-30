# Private native preview: release-readiness checklist

## Decision: not release-ready

This reconciles the existing **Rust 0.2.0** preview, not a new release or legal
approval. Keep the repository private. No workflows were dispatched, artifacts
executed, draft edited, tags created/moved, or visibility changed in this review.
Final release decisions and any later owner visibility change are outside this
task. Changing visibility alone resolves no source, privacy or legal obligation.

### What is actually verified (2026-10-30)

Historical preview commit: `92a983a57ff92ad4b9342fb4dd992edf728b5a97`.
[Native run 41023384988](https://github.com/imafreakandyalldontknowit67/local-shazam/actions/runs/41023384988)
completed successfully on Windows x64, Linux x64, macOS arm64 and macOS x64.
Authenticated read-only GitHub metadata confirms those four job conclusions.
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

Authenticated release listing confirms private draft **`v0.2.0-native.1`**,
release ID `428787114`, with `draft: true`, `prerelease: true`, no publication
timestamp, and `target_commitish` equal to the preview commit. Its twelve archive
and combined `SHA256SUMS` API digests/sizes match the local files. Remote asset
bytes were not downloaded; uploader identity/signature was not authenticated.
The release-by-tag/commit lookup did not resolve and the authenticated tag list
had no matching ref: the draft's `tag_name` is **not a verified existing tag**.
Do not rename or recreate this release to resolve that distinction here.

The [baseline privacy audit](PRIVACY_AUDIT.md) records hosted-build paths in
Linux/macOS executables. That prior finding was not rerun as a binary privacy
audit here. Existing artifacts cannot be promoted as compiler-sanitized merely
because source hygiene or checksum verification passes. Source vendoring notes
that say builds were unverified describe that earlier capture phase; the native
run above supersedes only their build-status uncertainty, not their legal limits.

## Completed factual checks

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

## Outstanding gates — parent and maintainers

### Parent-owned post-integration validation (pending)

- [ ] Integrate separately owned compiler-privacy work and inspect its
  `docs/BUILD_PRIVACY.md` implementation notes. This review did **not** inspect
  or approve that implementation. Verify the final source inventory and source
  snapshot/provider behavior after integration, including required docs/assets.
- [ ] Verify the repository-only Python relocation to `legacy/python/README.md`
  and all owned links after integration. Preserve historical Python tags and
  changelog entries. Native packages must not acquire Python app/runtime inputs.
- [ ] With explicit parent authorization, perform **fresh hosted native rebuilds**
  for all four targets at the exact integrated commit. Re-run the explicit
  dataset-free gates; do not reuse the historical run as current approval.
- [ ] Independently verify every rebuilt binary and both source archives:
  checksums, commit/source/payload hashes, complete source inventory, matching
  provenance, notices, architecture/modes, archive headers/metadata and compiler
  path/privacy policy. Verify extracted source with the source-only checker;
  do not apply it blindly to executables or weaken it to allow binaries.
- [ ] Retain sanitized per-target selected-feature/link/toolchain/SDK evidence.
  Existing provenance has no resolved target feature graph or complete emitted
  compiler-runtime inventory. Do not infer these from Cargo.lock alone.
- [ ] Perform the **final history/publication-surface audit** after integration:
  newly reachable commits/refs and metadata, tags, release descriptions/assets,
  workflow logs, remote branches, Pages/wiki and other publication surfaces.
  Recheck private visibility. Report findings redacted, retain public attribution,
  and leave any sensitive history remediation to an explicitly authorized task.
  Moving Python files does not erase their history.

### Maintainer/legal and distribution decisions (open)

- [ ] Resolve seven Apple-family attribution/SDK reviews for applicable native
  and source distributions. No generic MIT template or author list closes them.
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
- [ ] Decide acceptable unsigned Windows / non-Developer-ID-signed,
  non-notarized macOS distribution policy. Do not advise disabling OS security.
  Signing/notarization and bit-for-bit reproducibility remain unverified, not
  silently supplied by normalized tar/ZIP metadata.

FFmpeg and FFprobe stay external, user-installed tools. Any bundling change needs
a new build-specific license/source audit. Accuracy/stability claims need separate
validation; dataset-free gates do not establish them.

## Existing workflow boundaries (not authorization to run them)

`portable-build.yml` uses `contents: read`; private branch pushes, pull requests,
manual dispatch and reusable calls can build, but cannot create a release/tag.
Native jobs use pinned actions, verified tool downloads and locked single-job
Cargo builds. Only three archives plus checksums per target are uploaded, with
seven-day artifact retention. No toolchains/caches/raw logs are release assets.

`private-draft.yml` is manual-only, with `create_draft` defaulting to **false**.
Preflight requires a private repository. For draft creation it also requires an
**existing reviewed tag** resolving to the selected full commit, an exact typed
confirmation, all four fresh native builds and independent aggregate verification.
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

## Asset and final owner review

Each target needs its binary archive, matching app-source archive, matching
Olaf-source archive and checksums. The writer consolidates checksums for all
**12 archives**; per-target sources include target-specific provenance and must
not be omitted. Binary packages contain the separate app/Olaf executables,
setup, licenses/notices and provenance. App source contains the locked app and
build tooling; Olaf source includes native runtime/Zigzag/embedded C code,
patches and build/test inputs. Source obligations still need the review above.

Uploads are not transactional. Failure can leave an incomplete private draft;
leave it unpublished for an authorized maintainer to inspect. Do not mutate the
existing draft in this task. Verify expected assets and both flags before any
future owner decision. `release/targets.json` retains conservative `unverified`
support/minimum-OS labels; historical native-gate success does not upgrade them.
