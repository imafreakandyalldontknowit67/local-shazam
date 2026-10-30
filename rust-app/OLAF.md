# Experimental Olaf retrieval + local Rust verification

This is Local Shazam's default native recognition path. It searches only the
user's explicitly indexed library, without a recognition service or audio
uploads. The integrated pipeline has **not established held-out accuracy or
accuracy equivalence with the retained `--backend rust` comparison engine**.

The Rust executable uses a separately shipped, modified Olaf runtime for
retrieval and its own Rust DSP for verification. Native users need no Python.
FFmpeg and FFprobe remain external prerequisites; codecs depend on their
installed build. See the [native guide](README.md) for commands and the
[building guide](../docs/BUILDING.md) for setup.

## Recognition, step by step

1. **Explicitly index complete tracks.** Select folders through the menu or
   `bootstrap`. Opening the app does not start a library scan. No old index is
   silently converted or adopted.
2. **Analyze a bounded query.** Decode at most the first **30 seconds** of the
   supplied snippet. Both retrieval and verification use that query audio.
   This is a query limit, not a limit on indexed song duration: an excerpt can
   originate beyond 120 seconds in a track.
3. **Retrieve local candidates.** Olaf returns fingerprint hits and predicted
   offsets. The app filters and shortlists up to ten distinct file paths.
4. **Verify source windows.** Decode nearby windows from those original files
   and check them with Rust streaming landmark DSP. Repeated pairs at the same
   query timestamp count once; unrelated offsets cannot pool their evidence.
   Paths must be registered in the manifest and pass the stored identity check.
5. **Return evidence-filtered suggestions.** Rank verified candidates, report
   source paths/offsets and show no more than three. Weak candidates are not
   added just to fill three slots. `match --top` may reduce the output count,
   but cannot increase this cap.

The verifier can reject a retrieved candidate; it cannot recover a track that
retrieval did not shortlist. A missing, moved or changed source can prevent
verification even when its fingerprints remain in the index.

## Result tiers

| Status | Interpretation |
| --- | --- |
| `strong_match` | Leading candidate meets stronger evidence/span requirements and leads the verified runner-up. |
| `possible_matches` | One to three candidates meet minimum requirements; no strong designation. |
| `insufficient_evidence` | None passes verification. This does not prove the song is absent. |

Ambiguous runners, verification errors and a shortlist truncated beyond ten
files block the strong designation. Retrieval-cap warnings are reported too;
they do not prove retrieval was exhaustive. Evidence fields include independent
supporting moments (`anchors`), distinct hashes, evidence span and Olaf votes.

All thresholds are **versioned heuristics**, not calibrated confidence
percentages or guarantees. A longer file only helps if useful evidence is in
its first 30 seconds. Text and JSON output disclose the analysis cap; JSON also
includes analyzed duration, policy and warnings.

## Index and runtime isolation

- Default index: `local-olaf/` beside the executable. Override with
  `--olaf-index DIRECTORY`, preferably a new writable location outside source
  audio for an initial trial.
- Rust comparison database: `local-shazam.db` beside the executable, selected
  with `--backend rust`; `--db FILE` is Rust-only.
- No automatic migration from Python or Rust. Index selected folders separately.
  Incompatible or unversioned Olaf databases are rejected rather than adopted.
- A new index copies the packaged `olaf-runtime/olaf.exe` (Windows) or
  `olaf-runtime/olaf` (Unix-like targets) into its own runtime directory.
  `--olaf-bin FILE` overrides the runtime used to seed a **new** index; it does
  not upgrade existing indexes. Use only the matching prepared runtime.
- Each index owns its configuration, LMDB database, cache, temporary directory,
  manifest and process lock. Its saved runtime SHA-256 and exact configuration
  are checked on open. An isolated home directory prevents global Olaf settings
  from silently changing extraction.

Current source identifiers:

```text
Index:   olaf-local-app-v1-twopeak-time20-verifier1
Policy:  candidate-window-v1-experimental
```

The retrieval profile uses two-peak fingerprints and a temporal filter size of
20. Saturated lookup skipping is enabled; the runtime's independent-time-vote
option is disabled. That runtime option is separate from the Rust verifier's
independent supporting-moment checks. These settings describe the current
profile, not an accuracy or speed recommendation. Configuration/runtime changes
can require rebuilding in a fresh directory; do not bypass version/hash checks.

## Indexing behavior and resource limits

The menu and `--workers` accept 1–64 workers. The default is available parallelism
capped at six, falling back to four when detection fails. Work is submitted in
batches of 16 times the worker count, bounded to 32–512 files. Manifest writes
are buffered and atomically replaced with synchronization.

Confirmed per-file successes are saved even when other files in a batch fail.
Retrying the same folder skips unchanged, recorded files; an unfinished batch
may need to be stored again. Inspect diagnostics and, when present,
`index-errors.log`. This retry behavior is **not a guarantee of integrity after
a system crash**.

Incremental identities combine size, modification time and a leading-8-KiB
digest, not a full-file checksum. `bootstrap --force` also reindexes files whose
identities appear unchanged. Source music is read-only; indexes, manifests,
caches and temporary files are written separately.

Bounded batches, query deadlines and output-readback limits constrain individual
operations, not total library memory or disk use. Scanner/manifest state grows
with library size. More workers can increase CPU, memory and disk pressure
without improving throughput. Development system crashes have an unresolved
cause; the default ceiling is not a proven BSOD fix. Do not restart heavy work
on a machine with unresolved crashes, and do not assume its index is intact.

## Not implemented or not established

- No Olaf `remove` or `compact-db` commands. These fail rather than performing
  maintenance; the Rust equivalents affect only the Rust database.
- No persistent verification cache, playback controls, automatic recording-family
  grouping or automatic selection of the best-quality version. Related encodes,
  mixes and masters may remain separate suggestions.
- No probing of unfamiliar file extensions in this adapter. Recognized
  extensions still depend on available FFmpeg codecs; DRM and malformed inputs
  may fail.
- No guaranteed recognition of short/noisy clips, quiet sections, pitch/speed
  changes, covers or live performances.
- No held-out estimate for the integrated retrieval/verifier pipeline, general
  false-positive rate, performance promise or demonstrated accuracy-equivalence
  gate. Historical backend and development smoke results cannot supply these.
- Windows x64, Linux x64 and macOS arm64/x64 passed native build/package gates
  for preview commit `92a983a57ff9`; older OS compatibility is not established.

## Attribution and distribution

The original application code is [MIT](../LICENSE). The separate, modified Olaf
runtime is **AGPL-3.0-or-later**; it must not be presented as MIT. See the
[Third-party notices](../THIRD_PARTY_NOTICES.md) and
[release guide](../docs/RELEASING.md) for matching runtime source, patches and
required notices. This documentation is not a claim that distribution review
has passed. Native package verification is recorded in the root README.
