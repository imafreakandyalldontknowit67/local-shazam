# Required release review — not a readiness certification

## Open blockers

1. **Source hygiene resolved during integration:** the removed fixture line in
   the release patch is published upstream, not operator-private data. Its exact
   line digest and path are recognized by the checker; all other content is still
   scanned. Evidence: https://github.com/JorenSix/Olaf/blob/f6f7cbefb50485953f71100c9d08c625f01780ba/tests/olaf_tests.c#L106
   Retaining the line preserves an accurately replayable patch. Recheck all source
   and staged bytes before publishing.
2. **Apple-family attribution and SDK terms:** `block2 0.6.2`, `dispatch2 0.3.1`,
   `objc2 0.6.5`, `objc2-app-kit 0.3.2`, `objc2-core-foundation 0.3.2`,
   `objc2-encode 4.1.0`, and `objc2-foundation 0.3.2` omit complete license texts
   from their published archives. The exact-revision upstream `LICENSE.md`
   documents the declared MIT / alternative terms but supplies links rather
   than complete attributed grants and explicitly raises uncertainty about
   Apple-SDK-derived code. Those documents are preserved per crate. The generic
   [MIT template](terms/MIT-template.txt) supplies the linked standard terms,
   **not** missing copyright attribution or SDK permission. Obtain maintainer/
   legal confirmation for the actual source/binary distribution; do not silently
   claim that crate metadata settles it. Non-Apple builds still need an explicit
   applicability decision if dependency source containing these crates is shipped.
3. **Wasm musl shim attribution/source provenance:** `sqlite-wasm-rs 0.6.2`
   includes and compiles sources under `shim/musl/`. The root crate MIT text and
   qsort/printf notices are preserved, but the archive does not include a musl-wide
   COPYRIGHT or identify the exact musl import revision for the remaining files
   lacking individual headers. Obtain the matching upstream provenance and full
   notices; the separate Olaf/Zig musl notice cannot be assumed to cover this
   source. This is relevant when that dependency source or target binary is shipped.
4. **AGPL corresponding source and integration:** confirm that every runtime
   binary matches the supplied modified source, all patches, dependency source,
   build instructions/configuration, modification notices, and any required
   installation information. Audit the combined application's licensing and
   network-service/source-offer obligations against the actual integration. A
   private repository URL or a subprocess boundary does not close this blocker.
5. **Binary-specific closure:** no binaries were built or inspected in this task.
   Review actual target feature graphs/link inputs, Rust standard library and
   compiler runtime, Zig/CRT/SDK components and all applicable embedded notices.
   Include any additional required full texts and matching source. Audit Python
   artifacts separately if a packaging change includes them. FFmpeg remains
   external and is not redistributed.

Also retain the original application's existing attribution, confirm the release
owner's rights without inventing a named holder for the unchanged MIT notice, and
review Olaf's upstream patent warning. None of these reviews is replaced by the
license inventory. Re-audit on lockfile, source, feature, target or toolchain changes.

## Read-only source privacy interface

Run from any directory, with Python 3.10+ and Git available for checkout mode:

```text
python scripts/check_release_hygiene.py --root DIRECTORY
python scripts/check_release_hygiene.py --root DIRECTORY --staged
python -B -m unittest discover -s tests/release -p test_hygiene.py -v
```

- A root containing `.git` is a checkout: the default checks **all tracked source
  candidates** using working-tree bytes. It does not read ignored/untracked local
  music/indexes. Ignoring a file is not sufficient if it is already tracked.
- `--staged` checks the **entire Git index**, including unchanged tracked entries,
  using blob IDs, not working-tree bytes. Staged deletions are absent. Symlink,
  gitlink/submodule and unresolved-conflict entries fail. Requires a checkout root.
- With no `.git` entry at that root, recursively check **all** extracted/staged
  source files, regardless of `.gitignore`. This also works for a staging directory
  nested inside another checkout. `.git` and `.worktrees` metadata at any depth are
  excluded from traversal; they must not be included in delivered archives by the
  packager. These exclusions are not general vendor/source exclusions.
- Forbidden local directories are rejected without reading their contents. Audio,
  video, PCM, databases/sidecars, evidence, environments, logs/dumps, credentials,
  build outputs, binary/archive files and personal reports are forbidden in source.
  Paths are checked case-insensitively. Symlinks, junctions, escapes and special
  files fail. Source must be UTF-8 text without binary controls, at most 32 MiB per
  file. SVG source is text; compiled assets and arbitrary binary blobs are not.
- Content checks apply to vendor files, patches, lockfiles, licenses and manifests
  too. They detect common credential formats, literal credential assignments and
  personal absolute paths. Prefer `${VARIABLE}` / `<placeholder>` for credentials
  and `/path/to/music`, `C:/Music`, or `/home/<user>/project` for docs. Attribution
  URLs are permitted, but credentials embedded in URLs are not. A small vocabulary
  of generic test accounts/paths is allowed; concrete private suffixes are not
  excused by simply using `user` as the account name.
- Diagnostics give a rule and line number without quoting matched values. Unsafe
  or artifact pathnames are replaced with a 12-hex SHA-256 ID of the UTF-8 relative
  path. To locate an ID, compute `hashlib.sha256(relative_path.encode()).hexdigest()[:12]`
  locally over your candidate inventory; do not paste private paths into reports.
  OS/Git error details and absolute checkout locations are not printed.
- Exit status: **0** passed, **1** policy findings, **2** invalid invocation or
  unreadable/inconsistent inventory. This is a heuristic gate, not a guarantee
  against obfuscated secrets, human-private prose, or malicious concurrent file
  replacement. Run against an immutable staging snapshot and manually review it.

This checker has **source-only semantics**; there is deliberately no `allow-binary`
switch or blanket executable exception. Do not run it on a finished binary package
and then weaken source policy to make that pass. Packaging should validate its
intentionally generated binary members with an explicit allowlist and hashes,
then run this checker on the separately extracted corresponding-source artifact.
It never deletes local data, rotates secrets, changes the index, or changes Git
configuration. Resolve findings by excluding data from release staging/tracking,
not by removing local music or indexes. Rotate any real exposed credentials.

## Inventory verification limits

All 115 Cargo registry archive checksums match the lockfile. 107 packages supplied
license evidence in the archive; `rsqlite-vfs` needed its pinned upstream LICENSE.
The seven Apple-family packages and the wasm musl shim above remain explicitly
blocked for the applicable distributions. The inventory
records original notice hashes, not a claim that a name-based scan proves all
copyrights were found. Complete license files, relevant embedded comment blocks,
SQLite dedications and Wayland XML grants were inspected and retained. Review
actual dependency source and binary closure before relying on these notices.

The miniature tests do not import the app/audio packages, compile, read production
data, index music, download datasets or use service credentials. OS symlink tests
may skip on Windows when link privileges are unavailable; Git symlink-index tests
still run. A fresh-platform run should exercise both real links and junctions.
