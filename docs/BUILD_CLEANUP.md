# Maintainer-operated build staging cleanup

This is a checklist, not a cleanup script or deletion authorization. Cleanup
requires explicit authorization for the named directories. Use with
the [release checklist](RELEASE_CHECKLIST.md), [build guide](BUILDING.md),
[release review](RELEASING.md) and [privacy gates](BUILD_PRIVACY.md); the gates
below are repeated here so this cleanup checklist stands on its own.

**Licensing review is deferred and explicitly OPEN before public release.**
Cleanup and verified uploads do not close it or authorize publication. Leave
legal text unchanged.

## Current status: recorded private v0.2.1 Windows release

The [release status](PREVIEW_STATUS.md) records **v0.2.1 as Latest inside the
PRIVATE repository**, built at
`d32716df0be1a5ea2d919d0b8ceb560de17bd77c`. Later documentation commits do not
change those binaries. This restates existing evidence, not newly queried remote
state or a claim that cleanup has been approved. Linux/macOS are not in v0.2.1.

`dist/readiness-audit/release-0.2.1-verification.json` records actual
downloaded-byte comparisons for all **seven assets** and independent downloaded
archive verification for both Windows targets. The adjacent
`0.2.1-x64-manifest.json` and `0.2.1-x86-manifest.json` record the exact source
commit, architecture/import/privacy checks and 16 dataset-free gates per target.
x64 execution was native; x86 was WOW64 on x64 Windows, not native 32-bit Windows
validation. The menu logs record menu/exit checks, not audio accuracy or clean-host
tests. These checks were **not rerun here**. Ignored evidence may not be included
in a source checkout; missing records must be recovered or reported, not invented.

The recorded assets are:

- `Local-Shazam_0.2.1_x64.zip`
- `Local-Shazam_0.2.1_x64_app-source.tar.gz`
- `Local-Shazam_0.2.1_x64_olaf-source.tar.gz`
- `Local-Shazam_0.2.1_x86.zip`
- `Local-Shazam_0.2.1_x86_app-source.tar.gz`
- `Local-Shazam_0.2.1_x86_olaf-source.tar.gz`
- Combined `SHA256SUMS.txt` for the six archives (its own hash/size is retained
  separately in the verification record).

Successful upload/download verification is **not a retention decision or deletion
authorization**. The parent owns clean-host feasibility, audio smoke testing,
historical privacy scanning, retention decisions, directory approval and cleanup.
No clean-host, native 32-bit OS, accuracy, signing, historical privacy or legal
gate is closed by this checklist.

### Historical v0.2.0 / four-platform evidence

The old four-target preview at `92a983a57ff92ad4b9342fb4dd992edf728b5a97`
and draft `v0.2.0-native.1` retain their own records. Its twelve local archives
were verified, but the old release comparison checked API digests/sizes only,
**not downloaded remote bytes**. The later Windows x64 replacement at
`d639ab2a2c49` has a separate uploaded-download checksum record; see
[release history](PREVIEW_STATUS.md). v0.2.0 remains historical release material.
Neither the later Windows evidence nor v0.2.1 replaces or sanitizes historical
Linux/macOS artifacts. Do not rename or rewrite historical evidence.

## Future maintainer procedure: verify, upload, download, retain, then review

The existing v0.2.1 download checks above are recorded as completed, not pending.
The steps below govern a future separately authorized replacement and the review
of retained material; they do not instruct a new upload or require the existing
private Latest release to become an unpublished old draft.

1. **Finish replacement verification first.** Record the full integrated commit,
   intended targets, build/run identities and verification results. Verify fresh
   replacement artifacts against that commit, including source inventory, binary
   privacy, provenance, payload correspondence and required native gate records
   under the build/privacy guides. Historical success is not current validation.
   Retain a pre-upload inventory of every intended asset's exact filename, byte
   size and SHA-256, including the checksum file itself and screenshots if any.
   Each Windows target needs its binary ZIP, matching `_app-source.tar.gz` and
   `_olaf-source.tar.gz`, plus `SHA256SUMS.txt` from `OUT/dist/`. The v0.2.1 names
   above are the recorded inventory, not permission to overwrite it. Combine
   checksum entries only for the authorized final archive set and inventory the
   final upload bytes, not an earlier per-target checksum file.
2. **Any future upload needs its own maintainer authorization.** Confirm the
   intended release identity, private repository state and authorized asset/state
   plan first. Do not create a substitute release, change visibility, publish,
   demote or infer a tag from a release name. The draft-creation workflow refuses
   existing releases and is not an update mechanism. Record actual asset
   identities and upload results; this cleanup document authorizes none of them.
3. **Maintainer downloads the actual uploaded bytes** for every intended release
   asset into a separate verification location, distinct from build/upload
   staging and outside every proposed deletion target. Do not substitute local
   originals, CI artifacts or remote API digest metadata for these downloads.
4. **Compare every downloaded asset with the retained pre-upload inventory:**
   exact filename, byte size and independently computed SHA-256. Include both
   source archives, `SHA256SUMS.txt` itself and screenshot hash comparisons if
   screenshots were uploaded. Account for the complete intended asset set;
   reconcile unexpected assets rather than silently ignoring them. Remote API
   digests, upload success and CI success alone do **not** satisfy downloaded-byte
   verification.
5. **Reverify downloaded archive/source/payload correspondence.** Check the full
   recorded integrated commit, matching cross-archive `BUILD-PROVENANCE.json`,
   source/payload hashes and file sets, architecture/modes, notices, native gate
   records, archive metadata and privacy policy. The verifier in
   `scripts/release.py` accepts exactly three archives plus `SHA256SUMS.txt` per
   target: for a combined upload, use separate per-target verification views with
   the relevant downloaded checksum entries, retaining the original combined
   checksum bytes unchanged outside those views. Each view contains only one
   target's trio and a checksum file with its three relevant entries; do not
   pass all seven assets to one verifier. Keep screenshots outside those views.
   Historical `local-shazam-COMMIT12-TARGET` sets with `SHA256SUMS` and applicable
   legacy native provenance remain supported, without renaming. Mixed formats
   and ambiguous checksum files fail; historical-format support does not waive
   the current compiler-privacy requirement or retroactively validate old bytes.
   Confirm the actual release state against the authorized plan and retain the
   observed private visibility and asset inventory, not obsolete draft assumptions.
6. **Retain recovery material before considering any removal.** Keep the
   pre-upload inventory, download comparisons, verification records, commit/run
   and release/asset identities, retention decisions and a verified recovery copy
   of required artifacts/evidence outside **every** proposed deletion target.
   Confirm that copy is usable and contains any otherwise unique retained
   evidence. A remote release (draft or Latest) or expiring CI artifact alone is
   not a recovery copy.
7. **Only then consider individually named staging directories.** Complete the
   table and path-safety review below; explicit maintainer approval is required for
   each exact directory, not a class of outputs.

**Any failure, missing asset, mismatch or unresolved verification means retain
staging and stop cleanup.** The Windows x64+x86 release does not justify deleting
historical Linux/macOS packages without verified replacements or an explicit
maintainer retention decision preserving the required artifacts/evidence.

## Cleanup approval register

Paths are exact repository-relative directories in the maintainer's release
workspace. These task-reported candidates are not claims of current existence,
completed replacement builds or disposability. Directory existence or a familiar
name does not authorize deletion.

| Exact directory | Purpose | Replacement/upload evidence | Maintainer approval/status |
| --- | --- | --- | --- |
| `dist/ci-92a983a` | Historical evidence: four-target native preview artifacts | Historical checks only; v0.2.1 Windows evidence does not replace its Linux/macOS sets or prove old remote bytes | PENDING explicit maintainer approval; retain |
| `dist/source-layout-check-755a194` | Source-layout check staging; maintainer to confirm retained evidence | Replacement/download evidence and retention review pending | PENDING explicit maintainer approval; retain |
| `dist/source-layout-check-complete` | Source-layout check staging; name does not prove completion | Replacement/download evidence and retention review pending | PENDING explicit maintainer approval; retain |

Enter newly created staging paths individually with their exact names; do not
preapprove invented paths. For each row, the maintainer must record evidence and
recovery locations, target coverage/retention decisions, approver and date before
changing its status.

## Final maintainer path-safety review

- Resolve each approved literal target against the selected release-workspace
  root and record the resulting absolute path. Reject filesystem/workspace roots,
  ancestors and anything outside that workspace. Check target, ancestors and
  contained links/reparse points; reject symlink/junction escapes or ambiguity.
- Confirm no active user, build or process needs the target and that no unique
  artifact or evidence remains only there. Recheck containment and retained-copy
  separation immediately before any later maintainer-owned removal. Use literal
  paths only, without globs or name-based recursive selection.
- Never delete all of `dist/`, `build/`, `.worktrees/`, caches or toolchains by
  category. Exclude source, `.git`, other worktrees, music/indexes, audit evidence
  and unrelated directories. `dist/local-tools`, `dist/readiness-audit` and
  `dist/brand` are **not** blanket cleanup targets. Stop if an exclusion overlaps
  a proposed target; retain it for maintainer review.
