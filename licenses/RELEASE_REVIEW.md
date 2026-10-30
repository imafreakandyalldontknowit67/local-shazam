# Required release review — not a readiness certification

## Scope and factual closures (2026-10-30)

This is a bounded reconciliation, not a new release, a replay of the completed
license/presentation tasks, or legal approval. Keep the repository private.
Original application [MIT](../LICENSE) bytes and all preexisting third-party
notice bytes are unchanged; public names, emails and attribution URLs are
intentional. Do not infer a named holder from Cargo authors or fill the generic
MIT template as though it were an attributed grant.

- [x] Compared all **115 registry packages** (plus the app) with Cargo.lock,
  LF-normalized lockfile hash, and supplied notice hashes. This rechecks the
  recorded whole-lock inventory; it does not claim every package is linked.
- [x] Re-fetched **11 exact checksum-verified Cargo archives**: seven Apple-family
  crates plus sqlite-wasm-rs, rfd, rusqlite and libsqlite3-sys. Rechecked published
  `.cargo_vcs_info.json`; retained exact metadata, relevant manifests and build
  scripts with [copy hashes and archive URLs](review/source-records.json).
  No Cargo, compiler, dependency scripts or downloaded tools were executed.
- [x] Examined each Apple crate's immutable upstream tree at its published VCS
  revision and compared the already-retained `UPSTREAM-LICENSE.md` bytes. No
  additional attributed grant was located; the result is **not** factual closure
  of its attribution/SDK blocker. See [investigation record](review/investigation.json).
- [x] Independently verified twelve local historical archives, embedded source/
  payload hashes, exact gate records and cross-target source inventory equality
  at **`92a983a57ff92ad4b9342fb4dd992edf728b5a97`**. Each target records 16
  dataset-free gates. Authenticated read-only GitHub metadata confirms run
  **`41023384988`** succeeded, repository private, draft/prerelease flags for
  **`v0.2.0-native.1`**, and matching API sizes/digests for all 13 assets. Remote
  bytes were not downloaded; no matching tag ref was resolved. These are
  historical facts, not current-HEAD validation or publisher authentication.
  [Native evidence](review/native-preview.json) excludes raw build logs/paths.
- [x] Historical app archives include Cargo.lock and license evidence, **not**
  vendored Cargo dependency implementations or the legacy Python app. The
  selected metadata/build definitions added here are review evidence, not a full
  dependency source bundle. Shipped source and linked binaries require separate
  applicability decisions.
- [x] Owned documentation/evidence checked with lightweight static hash,
  lockfile, status/reference and source-hygiene checks. No operator-personal-path
  or credential finding remained in that scope; no attribution was scrubbed.
  History review was limited to commit metadata and relevant public release/doc
  changes around the preview, not an audit or rewrite of historical private blobs.

## Unresolved license decisions and scoped applicability

### 1. Seven Apple-family crates — maintainer/legal review remains open

`block2 0.6.2`, `dispatch2 0.3.1`, `objc2 0.6.5`, `objc2-app-kit 0.3.2`,
`objc2-core-foundation 0.3.2`, `objc2-encode 4.1.0`, `objc2-foundation 0.3.2`:
exact archives omit complete license documents; the exact upstream trees examined
supply `LICENSE.md` rather than additional attributed grants. That document
links MIT/alternative standard terms and explicitly leaves Apple-SDK-derived
code uncertain. A generic [MIT template](terms/MIT-template.txt), author metadata
or newer moving-branch license cannot repair this evidence gap.

The exact [rfd 0.17.2 manifest](review/crates/rfd-0.17.2/Cargo.toml) declares
six of these under `cfg(target_os = "macos")`; objc2 declares objc2-encode.
The historical macOS app's recorded link inputs include AppKit, Foundation,
CoreFoundation and libobjc. Thus this is a concrete macOS review path, not merely
a name appearing in a whole-lock inventory. No complete target-resolved feature
graph was retained; Windows/Linux selection is not inferred from the lockfile.
Any redistribution of these crates' implementation source also requires review,
even in a non-Apple source bundle.

Consult the preserved [pinned upstream statement](rust/objc2-0.6.5/UPSTREAM-LICENSE.md)
and [Apple's SDK agreement](https://www.apple.com/legal/sla/docs/xcode.pdf).
The current Apple publication is context, not proof of the exact SDK agreement
used by historical runners or permission for these crates. Obtain maintainer/
legal resolution; do not silently declare the SDK issue either permitted or illegal.

### 2. sqlite-wasm-rs 0.6.2 — unresolved source/wasm concern, scoped out by native predicate

Its exact archive and [build.rs](review/crates/sqlite-wasm-rs-0.6.2/build.rs)
include 36 musl C compile inputs plus shim headers and printf. Existing root MIT,
SQLite dedication and qsort/printf notices remain intact. Inspection of published
revision `4b5c931e88ac09a114bd58368402a74761cec311` found no musl-wide COPYRIGHT
or precise musl import revision to support the other files. An unrelated
Olaf/Zig musl COPYRIGHT is **not** a substitute. No authentic missing musl grant
was found to add; this blocker was not papered over with a generic text.

The [rusqlite 0.41.1 manifest](review/crates/rusqlite-0.41.1/Cargo.toml) enables
`ffi-sqlite-wasm-rs` by default but places the dependency under
`cfg(all(target_family = "wasm", target_os = "unknown"))`. Its non-wasm predicate
selects libsqlite3-sys instead; the application enables `bundled`. None of the
four native target triples satisfies the wasm predicate. **Static inference:**
the shim is not selected on this dependency path for those native binaries;
it is not an established native-binary blocker merely because it is locked.
A complete resolved feature/link graph remains unavailable and was not generated.

Before shipping that shim source, a wasm binary, a newly vendored registry bundle
or different target/features, obtain exact import provenance and complete notices.
The small metadata/build-script evidence copies here do not ship the shim
implementation or constitute its corresponding source.

### 3. AGPL corresponding source and integration — owner/legal approval open

Historical artifact checks establish byte/hash correspondence, not legal
sufficiency. Review each modified runtime's preferred-form source, ordered patches,
embedded dependencies, Zigzag, configuration, build/install scripts, modification
notices/dates and any required installation information. Ensure recipients can
obtain exactly that source through a license-compliant delivery method. A private
repository URL alone does not meet this plan; visibility change alone does not
complete it either.

Review the application's actual integration and intended deployment, including
combined-work/aggregation and remote-network source-offer questions. Olaf's
retained CLI includes REST modules; do not infer all deployment obligations from
the native app's subprocess usage. Neither a subprocess boundary nor green CI
establishes AGPL compliance. Consult sections 1, 5, 6 and 13 of the supplied
[AGPL text](olaf/AGPL-3.0.txt) and [FSF publication](https://www.gnu.org/licenses/agpl-3.0.html).
Confirm original-app rights without inventing a copyright holder, and review the
upstream patent warning. This is an evidence checklist, not a legal conclusion.

### 4. Target-specific binary/toolchain/SDK closure — incomplete

Cargo.lock inventories registry packages, not all Rust std/compiler runtime,
Zig/CRT, SDK or linker contributions. Historical manifests retain limited import/
link observations, not a resolved feature graph, link map or complete license BOM:

| Target | Available historical observation | Still required |
| --- | --- | --- |
| Windows x64 | App uses MSVC target; recorded imports include VCRUNTIME140/UCRT. Olaf uses Zig GNU target and UCRT imports. PE import tables rechecked read-only. | Exact emitted Rust/Zig/mingw/CRT inputs and redistribution terms; clean-host availability. |
| Linux x64 | App records libc, libm, libgcc_s, loader and Wayland dependencies, with GLIBC_2.39 among symbol needs. Olaf musl recipe has no recorded dynamic needs. | Exact runtime/static components, system-library terms and source duties; no blanket static/minimum-glibc claim. |
| macOS arm64/x64 | App records Apple frameworks, libobjc/libiconv/libSystem; Olaf records libSystem. | Exact SDK/compiler inputs and accepted terms, emitted runtime notices, Apple-family resolution. |

Existing Zig 0.16.0/mingw-w64/musl notices are preserved from vendor provenance,
not newly downloaded toolchains, and do not establish complete emitted coverage.
Actual target-selected dependencies and source duties must be recorded on the
fresh parent builds. FFmpeg/FFprobe remain external; any bundling requires its own
audit. Python wheels/interpreters are not in native packages; review separately
if that changes. Minimum OS/glibc, clean-host behavior, signing/notarization and
bit-for-bit reproducibility remain unverified.

## Parent-owned and final release checklist — pending

- [ ] Integrate compiler-privacy implementation and inspect `docs/BUILD_PRIVACY.md`;
  this task has not inspected or approved the other agent's implementation.
- [ ] Verify historical Python relocation to `legacy/python/README.md` and links;
  preserve old tags/history; keep it repository-only, outside native packages.
- [ ] Fresh parent-run hosted rebuilds at the integrated commit on all four hosts;
  explicit dataset-free gates, not substitution of run 41023384988.
- [ ] Independent rebuilt artifact/source checks: hashes, source correspondence,
  notices, exact file inventory, executable/archive metadata and compiler-path
  privacy. Baseline [privacy audit](../docs/PRIVACY_AUDIT.md) findings in historical
  executables remain a reason to rebuild, not a reason to edit binary strings.
- [ ] Approve the four license decisions above, recipient source delivery and
  target-specific binary closure; record maintainer/legal approval separately
  from factual evidence closure.
- [ ] Final history/publication-surface audit after integration: reachable refs,
  commit metadata, tags, release bodies/assets, workflow logs, remote branches
  and other publication surfaces, with private visibility rechecked. Redact
  findings, retain legitimate attribution; no historical private-blob audit or
  history rewrite is performed by this task.
- [ ] Final release decision remains with the owner outside this task, as does
  any later visibility change. Private status alone is not license compliance;
  making the repository public alone resolves no privacy/source/legal obligation.

Full operational checklist: [Releasing](../docs/RELEASING.md).

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

The prior inventory recorded checksum verification for all 115 Cargo archives.
This reconciliation checks lockfile correspondence and local notice hashes and
re-fetches only the 11 specified archives. The recorded license-text coverage is
107 archives (including incomplete sqlite-wasm-rs embedded provenance) plus
rsqlite-vfs's pinned upstream LICENSE; seven Apple-family rows remain blocked.
These counts are evidence categories, not approvals. The wasm row remains
blocked for applicable source/wasm distribution, not declared native-selected.

Review evidence is hashed in `review/source-records.json`; immutable investigation
URLs/statuses are in `review/investigation.json`. Existing notice hashes in
`rust-inventory.json` and `olaf-inventory.json` were not replaced or normalized.
Static tests in `tests/release/test_release_review.py` require no network, Cargo,
compilers, application execution, music/index access or new repositories. Existing
mocked packaging and Olaf source tests are separate from historical native gates.
The parent must rerun relevant checks after integration; no guessed test counts
or broad current-build approval are recorded here.

Local reconciliation results on 2026-10-30: `test_release_review.py` 10 passed;
`test_packaging.py` 28 run, 27 passed, one skipped because Windows symlink
creation privilege is unavailable; `test_olaf_source.py` 13 passed. These are
static/synthetic source checks, not native compilation or current-build approval.
