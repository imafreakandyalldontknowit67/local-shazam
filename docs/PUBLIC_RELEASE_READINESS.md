# Public release readiness: Windows v0.2.1

The repository remains **private**. This record does not authorize a visibility
change or claim a clean-host test has passed.

## Completed engineering checks

- Verified x64 and x86 release packages, matching app/Olaf source archives and
  checksums. Both downloaded sets passed independent verification; the seven
  latest-release assets remain intact. Their built commit is
  `d32716df0be1a5ea2d919d0b8ceb560de17bd77c`; attribution-only branch history
  changes did not change their files, tags or recorded provenance.
- Generated-audio end-to-end checks passed on the existing Windows 10 x64 PC:
  index two tracks with two workers, match the correct track from seven seconds,
  reject an unrelated clip, reopen, skip unchanged files and reject cross-arch
  index reuse without changing its marker. See [scoped results](release-smoke-0.2.1.json).
  This is not an accuracy benchmark, native 32-bit test or clean-PC validation.
- Scanned 631 unique blobs and 117 commits reachable from remote branch/tag tips
  at review time. Three findings were reviewed demo paths/test fixtures; no live
  credential or personal path was found in that scope. See [review evidence](public-history-review.json).
- Removed four obsolete pre-privacy CI artifacts. Historical releases and the
  unpromoted multi-platform draft were not removed or relabeled.
- Collected both target-filtered Cargo graphs offline from the retained build
  snapshots: each selects the app and the same 72 dependencies/features, with no
  Apple-only or sqlite-wasm-rs package selected. See [target graphs](../licenses/review/windows-0.2.1-target-graphs.json).
  This is not a linker map or a legal conclusion.

## Still required before calling the launch ready

1. **Clean-PC setup check.** Follow [this checklist](CLEAN_WINDOWS_TEST.md) on
   another Windows PC or existing fresh VM. The current host has no Windows
   Sandbox available. Merely restricting PATH does not remove installed DLLs.
2. **Maintainer licensing/publication decision.** Review the scoped
   [Windows distribution review](../licenses/WINDOWS_DISTRIBUTION.md). Preserve
   third-party grants and complete matching source access. The owner selected `badger` for the app's MIT copyright header. This
   source-checkout update does not change the license files inside existing
   v0.2.1 downloads; reflect it in the next packaged release. Technical checks are not blanket legal approval.
3. **Final explicit visibility approval.** Keep the repository private until the
   owner approves the public launch after reviewing the remaining results.

## Housekeeping, not a binary release blocker

About 10 GiB of local disposable build/tool staging remains. Exact workspace
paths were checked for containment, reparse points and running executables.
The deletion command was rejected by the execution policy; **no local cleanup is
claimed**. Verified recovery archives and evidence must be kept. Local staging is
ignored by Git and is not included in the source or release ZIPs.

Do not rebuild solely for documentation or attribution changes. A code, dependency
or packaged-license change needs a new reviewed release snapshot and corresponding
package verification, rather than changing existing provenance to a new commit.
