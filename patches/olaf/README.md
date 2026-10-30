# Olaf patch series

Apply `series` in order with `git apply` from an Olaf source root at public
upstream `f6f7cbefb50485953f71100c9d08c625f01780ba`. The vendored tree is already
patched. These are source diffs, not binary patches; no private repository is
needed. Do not run the old setup helper over a working checkout.

1. `0001-windows-lmdb-paths.patch`: all code changes in fork commit
   `1240e2552f64ea2d5727c05f859e8303f88aebca`; the non-source private handoff is omitted.
2. `0002-working-matcher-config-db.patch`: all nine modified tracked files and
   the untracked matcher test captured on 2026-10-29, including build registration.
3. `0003-release-local-source-build.patch`: local dependency/build inventory,
   offline fixture handling, full-suite opt-in gate and release test notes.

4. `0004-release-build-privacy.patch`: build-only compiler privacy controls,
   module debug suppression and generated C prefix-map response-file integration
   for runtime and regression artifacts (2026-10-30). No engine source change.

After patching, select only the explicit source inventory in
`vendor/olaf/PROVENANCE.json`; this source distribution intentionally omits
upstream audio, binaries and other non-desktop material. Supply the unchanged
Zigzag package source as sibling `vendor/zigzag`. Added distribution documentation,
notices, provenance, attributes, build helper and Python source tests are provided
by this repository rather than being changes to upstream code in the series.
All these inputs are hashed in provenance; the manifest excludes its own hash.

The Python source tests reverse/replay this exact series, compare the captured
working-source hashes, and recover the public-base hashes for every retained
Olaf source file. Nothing here claims native tests or target builds passed.
Olaf changes retain AGPL-3.0-or-later terms; the LMDB patch retains its component
terms. Do not label the combined Olaf runtime MIT.
