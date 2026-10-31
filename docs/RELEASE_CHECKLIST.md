# Existing private draft refresh checklist

Parent-owned procedure for the Rust **0.2.0 native terminal/menu app** and its
separate Olaf runtime, not a web UI. There is no root `package.json` workflow.
This document records no fresh builds, execution, screenshots or remote checks.
Only the parent may perform the operational steps below on appropriate safe
hosts; do not execute native/audio workloads on the crash-affected review host.
Mark an item complete only with explicit parent-supplied evidence.

## Historical baseline only

[Releasing](RELEASING.md) and the [README](../README.md) record:

- Source commit `92a983a57ff92ad4b9342fb4dd992edf728b5a97` and native CI run
  `41023384988`: historical four-target build/artifact evidence, **not current
  HEAD verification** or evidence of compiler-path privacy in fresh binaries.
- Existing draft `v0.2.0-native.1`, release ID `428787114`: **recorded baseline
  identifiers requiring parent reconfirmation**, not newly checked remote facts.
  The draft name / `tag_name` is not proof that a Git tag exists.
- Historical API asset digest/size comparisons did not download release asset
  bytes. They do not satisfy the post-upload check below.

## 1. Freeze scope and record current evidence

- [ ] Parent reconfirms repository identity and private visibility, the existing
  release ID/name, `draft=true`, `prerelease=true` and no publication timestamp.
  Stop on any mismatch; do not create, rename or recreate a release or tag.
- [ ] Record the exact **40-character post-integration source commit**, clean
  reviewed checkout, date, reviewer and selected refresh targets. Neither this
  task branch's commit nor the historical commit substitutes for integrated HEAD.
- [ ] Parent authorizes fresh native CI at that exact commit after reviewing
  workflow trust, runner availability and billing; record run URL/ID, attempt,
  tested SHA, per-target job conclusion and retained artifact IDs.

The existing [portable workflow](../.github/workflows/portable-build.yml) uses
all four targets; it has **no Windows-only dispatch input**. Do not change the
workflow to follow this checklist. A **Windows-x64-first private refresh** may
upload only the newly verified Windows set; it does not require presenting other
targets as newly verified. Record their actual results and keep historical assets
clearly identified by old commit, or mark replacement assets pending/absent.

| Target | Native runner from [targets.json](../release/targets.json) | Current-commit CI / independent verification |
| --- | --- | --- |
| `windows-x64` | `windows-2025` x64 | Pending / pending |
| `linux-x64` | `ubuntu-24.04` x64 | Pending; historical evidence only / pending |
| `macos-arm64` | `macos-15` ARM64 | Pending; historical evidence only / pending |
| `macos-x64` | `macos-15-intel` x64 | Pending; historical evidence only / pending |

## 2. Verify each replacement set before upload

- [ ] For each selected target, require successful fresh native build, explicit
  dataset-free tests, app help/version and Olaf help gates, packaging and
  verification from [Building](BUILDING.md). Record all gate results; do not use
  music, indexing, matching, personal databases, unrestricted tests or benchmarks.
- [ ] Download the CI artifacts and independently verify the complete target
  set: binary archive, **matching app-source and Olaf-source archives**, and
  `SHA256SUMS`. Never pair new binaries with historical source archives or omit
  per-target sources. Check source inventory equality across fresh targets.
- [ ] Record exact filenames, byte sizes and SHA-256 values in a retained
  pre-upload ledger, including the checksum file and each executable's payload
  hash. Expected archive stem: `local-shazam-COMMIT12-TARGET`; Windows binary
  suffix `.zip`, Unix `.tar.gz`, sources `-app-source.tar.gz` and
  `-olaf-source.tar.gz`. Filename prefixes alone are not provenance.
- [ ] Verify each set's identical embedded `BUILD-PROVENANCE.json`, full source
  commit, target, source/payload hashes, toolchain/provider records, test gates,
  complete file inventory, required notices, executable architecture/modes and
  canonical archive headers/metadata. Preserve sanitized feature/link/SDK
  evidence and explicitly record gaps; Cargo.lock alone does not close them.
- [ ] Verify **actual rebuilt app and Olaf executables**, source members,
  provenance and archive metadata against [Build privacy](BUILD_PRIVACY.md),
  including `compiler-paths-and-artifacts-v1`, compiler/linker path controls and
  personal/hosted-build path checks. Record native response-file handling,
  especially Windows clang-cl and Zig's Clang subprocess. Apply source-only
  hygiene to extracted source separately; never weaken it to admit binaries.
  Do not patch old binaries, relabel them sanitized or infer privacy from hashes.

Checksums prove byte correspondence, not publisher authentication. Successful
gates do not establish minimum OS support, accuracy, stability, reproducibility,
signing/notarization or legal approval. Keep those limitations in the draft.

## 3. Parent-only real terminal screenshot

- [ ] On an appropriate safe native host, the parent uses the **verified fresh
  package** (complete adjacent `olaf-runtime/`) and records its commit, target,
  executable SHA-256 and capture date. This manual capture is separate from CI
  gates; no agent captures screenshots or executes the app for this task.
- [ ] Prepare a neutral demonstration directory, for example
  `C:\LocalShazamDemo`, with a new, unused index path
  `C:\LocalShazamDemo\empty-index`. Launch the verified app with
  `--olaf-index` pointing there and **no subcommand**, solely to display its menu.
  The [menu code](../rust-app/src/main.rs) prints the index path. Do not use a
  personal directory/database or choose options 1, 2 or 3; exit with option 4.
- [ ] Capture a **REAL screenshot of the running app's actual terminal menu**:
  title/backend, neutral index path, experimental warning, options 1-4 and prompt.
  No generated artwork, mockup, browser UI or reconstructed terminal output.
  No music, matching or indexing is required.
- [ ] Inspect the terminal prompt/title, tabs, visible paths and surrounding UI
  for usernames, hostnames or other personal information; inspect image metadata
  too. Recapture safely or remove sensitive metadata before sharing, then retain
  the approved image's filename/hash and capture record. Do not falsify app output.

## 4. Parent-only refresh and byte-for-byte confirmation

The [private-draft workflow](../.github/workflows/private-draft.yml) **creates**
drafts and refuses existing releases; it is **not an update mechanism**. Do not
dispatch it to refresh this draft or bypass its existing-tag, confirmation,
four-target verification, private-repository or approval safeguards.

- [ ] Parent reviews and authorizes the exact existing-release edit/asset plan,
  then refreshes only the reconfirmed draft. Retain private repository visibility,
  `draft=true` and `prerelease=true` throughout; no publish/promote, tag creation
  or movement, visibility change, or new release. Stop if identity/flags change.
- [ ] Before uploading, prepare and hash an unambiguous combined `SHA256SUMS` for
  the final archive inventory (including retained historical archives only with
  their own exact hashes). Do not confuse per-target files with the same checksum
  filename. Preserve the verified pre-upload files and ledger.
- [ ] Upload only verified replacement sets and reviewed supporting assets.
  Record the new full commit, per-target CI/verification evidence, Windows-first
  scope if applicable, and historical/pending targets in the draft notes. Keep
  retained old binary/source trios grouped by their historical commit; never
  describe them as rebuilt or combine old sources with a new binary. Record all
  final asset names/IDs/sizes.
- [ ] **Download the uploaded asset bytes from the existing draft** into a
  separate location. Recompute SHA-256 for every uploaded archive, checksum file
  and supporting asset; compare with the verified pre-upload files/ledger.
  Re-run independent archive/provenance verification on downloaded replacement
  trios. API digest metadata alone is insufficient. Check any retained historical
  archive bytes too before accepting the final checksum inventory.
- [ ] Reconfirm expected final assets, private visibility, both release flags,
  no publication and accurate draft notes. Retain redacted evidence. Uploads are
  not transactional: on failure leave the draft unpublished, record the incomplete
  state and preserve local evidence; do not claim a completed refresh.

## 5. Cleanup and open public-release gate

- [ ] Only after downloaded-byte/hash verification succeeds and evidence is
  retained, parent reviews [Build cleanup](BUILD_CLEANUP.md) before any separately
  authorized cleanup. That companion document is integrated separately; if
  unavailable, defer cleanup. This checklist authorizes no deletion.
- [ ] **OPEN / DEFERRED: licensing review and public-release approval.** Keep the
  existing [release review](../licenses/RELEASE_REVIEW.md) and
  [maintainer gates](RELEASING.md) unresolved here. Do not resolve, reinterpret or
  edit legal text. A private refresh, source archives, screenshot or green build
  does not close licensing, corresponding-source or public-release gates.
