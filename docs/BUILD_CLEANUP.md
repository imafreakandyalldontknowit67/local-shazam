# Parent-operated build staging cleanup

This is a checklist, not a cleanup script or deletion authorization. Cleanup
remains parent-owned and must not occur during this documentation task. Use with
the [release checklist](RELEASE_CHECKLIST.md), [build guide](BUILDING.md),
[release review](RELEASING.md) and [privacy gates](BUILD_PRIVACY.md); the gates
below are repeated here so this cleanup checklist stands on its own.

**Licensing review is deferred and explicitly OPEN before public release.**
Cleanup and verified uploads do not close it or authorize publication. Leave
legal text unchanged.

## Required order: verify, upload, download, retain, then consider cleanup

1. **Finish replacement verification first.** Record the full integrated commit,
   intended targets, build/run identities and verification results. Verify fresh
   replacement artifacts against that commit, including source inventory, binary
   privacy, provenance, payload correspondence and required native gate records
   under the build/privacy guides. Historical success is not current validation.
   Retain a pre-upload inventory of every intended asset's exact filename, byte
   size and SHA-256, including the checksum file itself and screenshots if any.
   Each intended target needs these matching outputs from `OUT/dist/`:
   - `local-shazam-COMMIT12-TARGET.zip` (Windows) or `.tar.gz` (Unix);
   - `local-shazam-COMMIT12-TARGET-app-source.tar.gz`;
   - `local-shazam-COMMIT12-TARGET-olaf-source.tar.gz`;
   - `SHA256SUMS` covering all intended archives (combined when uploading multiple
     targets). Inventory the final upload bytes, not an earlier checksum file.
2. **Parent uploads to the existing private draft only.** Confirm the intended
   existing draft identity and private repository state first; do not create a
   substitute release, publish, change visibility or infer an existing tag from
   the draft name. Record asset identities and upload results.
3. **Parent downloads the actual uploaded bytes** for every intended release
   asset into a separate verification location, distinct from build/upload
   staging and outside every proposed deletion target. Do not substitute local
   originals, CI artifacts or remote API digest metadata for these downloads.
4. **Compare every downloaded asset with the retained pre-upload inventory:**
   exact filename, byte size and independently computed SHA-256. Include both
   source archives, `SHA256SUMS` itself and screenshot hash comparisons if
   screenshots were uploaded. Account for the complete intended asset set;
   reconcile unexpected assets rather than silently ignoring them. Remote API
   digests, upload success and CI success alone do **not** satisfy downloaded-byte
   verification.
5. **Reverify downloaded archive/source/payload correspondence.** Check the full
   recorded integrated commit, matching cross-archive `BUILD-PROVENANCE.json`,
   source/payload hashes and file sets, architecture/modes, notices, native gate
   records, archive metadata and privacy policy. The verifier in
   `scripts/release.py` accepts exactly three archives plus `SHA256SUMS` per
   target: for a combined upload, use separate per-target verification views with
   the relevant downloaded checksum entries, retaining the original combined
   checksum bytes unchanged. Keep screenshots outside those views. Confirm the
   existing release is still an unpublished draft/prerelease and the repository
   is still private; retain the observed state and asset inventory.
6. **Retain recovery material before considering any removal.** Keep the
   pre-upload inventory, download comparisons, verification records, commit/run
   and draft/asset identities, retention decisions and a verified recovery copy
   of required artifacts/evidence outside **every** proposed deletion target.
   Confirm that copy is usable and contains any otherwise unique retained
   evidence. A remote draft or expiring CI artifact alone is not a recovery copy.
7. **Only then consider individually named staging directories.** Complete the
   table and path-safety review below; explicit parent approval is required for
   each exact directory, not a class of outputs.

**Any failure, missing asset, mismatch or unresolved verification means retain
staging and stop cleanup.** A Windows-first refresh does not justify deleting
historical Linux/macOS packages without verified replacements or an explicit
parent retention decision preserving the required artifacts/evidence.

## Cleanup approval register

Paths are exact repository-relative directories in the parent's release
workspace. These task-reported candidates are not claims of current existence,
completed replacement builds or disposability. Directory existence or a familiar
name does not authorize deletion.

| Exact directory | Purpose | Replacement/upload evidence | Parent approval/status |
| --- | --- | --- | --- |
| `dist/ci-92a983a` | Historical evidence: four-target native preview artifacts | Historical checks only; replacement and actual-upload download proof pending | PENDING explicit parent approval; retain |
| `dist/source-layout-check-755a194` | Source-layout check staging; parent to confirm retained evidence | Replacement/download evidence and retention review pending | PENDING explicit parent approval; retain |
| `dist/source-layout-check-complete` | Source-layout check staging; name does not prove completion | Replacement/download evidence and retention review pending | PENDING explicit parent approval; retain |

Enter newly created staging paths individually with their exact names; do not
preapprove invented paths. For each row, the parent must record evidence and
recovery locations, target coverage/retention decisions, approver and date before
changing its status.

## Final parent path-safety review

- Resolve each approved literal target against the selected release-workspace
  root and record the resulting absolute path. Reject filesystem/workspace roots,
  ancestors and anything outside that workspace. Check target, ancestors and
  contained links/reparse points; reject symlink/junction escapes or ambiguity.
- Confirm no active user, build or process needs the target and that no unique
  artifact or evidence remains only there. Recheck containment and retained-copy
  separation immediately before any later parent-owned removal. Use literal
  paths only, without globs or name-based recursive selection.
- Never delete all of `dist/`, `build/`, `.worktrees/`, caches or toolchains by
  category. Exclude source, `.git`, other worktrees, music/indexes, audit evidence
  and unrelated directories. `dist/local-tools`, `dist/readiness-audit` and
  `dist/brand` are **not** blanket cleanup targets. Stop if an exclusion overlaps
  a proposed target; retain it for parent review.
