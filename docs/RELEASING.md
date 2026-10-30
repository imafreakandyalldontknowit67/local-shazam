# Private, manually gated draft prereleases

## Current state: not release-ready

**windows-x64, linux-x64, macos-arm64 and macos-x64 are all unverified.**
Only lightweight mocked packaging, archive-content and syntax checks are allowed
in this tooling task. No compilation, original executable execution, audio
indexing, CI dispatch, push, tag, release, visibility or remote changes were made.
The cross-branch source/runtime/legal/hygiene inputs must be integrated and
reviewed before any real run. Refer to [BUILDING.md](BUILDING.md) for exact build
commands, inputs, tools, source inventory and distribution limitations.

Local review on 2026-10-30: 28 synthetic packaging/manifest/archive tests ran,
27 passed and the filesystem-symlink test was skipped for missing Windows
symlink privilege. Python AST, JSON, TOML, YAML, embedded workflow JavaScript
(`node --check`) and PowerShell parser checks passed. `git diff --check` passed.
`actionlint` was not installed; YAML parsing is not a GitHub-hosted workflow run.
Linux/macOS native hosts were unavailable locally; Windows native prerequisites
were not exercised. These results do not change any target's unverified status.

## Permission and event boundary

`portable-build.yml` has read-only contents permission. It can run for private
repository branch pushes, pull requests, manual dispatch or as a reusable
workflow. None of those builds can create a release or push a tag. Its four
native jobs use full-commit-pinned actions, verified tool downloads, locked
single-job Cargo compilation and explicit dataset-free tests. Private artifacts
retain only the three distributable archives and checksums, for seven days;
toolchains, caches, raw build logs and personal data are not uploaded as assets.

`private-draft.yml` accepts **workflow_dispatch only**. `create_draft` defaults
to **false**. Preflight asserts the live repository is private, then invokes
all native build jobs and a separate read-only archive verification job. Only
after all jobs succeed can its separate `draft` job receive `contents: write`.
That write-token job does **not** check out or execute repository scripts. It
rechecks asset hashes, source/archive presence, private visibility and tag/SHA
identity before creating a release and while attaching each asset.

The release API request always sets **both `draft: true` and `prerelease: true`**,
plus `make_latest: false`. No code path publishes/promotes a release, edits an
existing release, auto-creates/pushes a tag, changes visibility or needs private
Olaf checkout secrets. The only credential is GitHub's scoped ephemeral token.
Action pins follow [GitHub's full-SHA security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

## Human gates before a future dispatch

1. Integrate and review application source/manifests, runtime provider, vendored
   Olaf/Zigzag, modifications/patches, complete dependency notices/licenses and
   hygiene checker. Update the explicit inventory narrowly if necessary. Review
   the provider's Zig 0.16.0 pin, verified provisioning, `-j1`, local dependency
   wiring and license/notices/provenance output. Nothing can be borrowed from
   an ignored developer checkout.
2. Review the workflow and all pinned action commits. Confirm native runner
   availability, account billing and build prerequisites for this **private**
   repository. Do not make it public to gain a runner or environment feature.
3. Confirm every allowlisted Rust test and the three Olaf regression steps remain
   dataset-free. Verify app `--help`/`--version` and Olaf `--help` without audio
   indexing in the sandbox HOME. Olaf has no `--version` CLI in the inspected
   source; verify its recorded source-manifest version and runtime/source hashes.
   Run the actual native CI gates in an authorized future session. Retain their
   run links and results; a green mocked archive test is not native success.
4. Review actual DLL/shared-library requirements, dependency licenses, source
   correspondence and source inventory for each target. Validate new clean-host
   behavior before promising OS/glibc minimums or publishing compatibility claims.
   Reconfirm unsigned Windows and non-notarized macOS warnings. These are not
   bit-for-bit reproducibility or recognition-accuracy gates.
5. Use an **existing, reviewed tag** matching the exact tested 40-character commit.
   This workflow will not create it. Protect that tag against update/deletion and
   coordinate against concurrent administrators: GitHub tag lookup and release
   creation are separate API requests, not an atomic transaction. Do not dispatch
   while tag/visibility changes are in flight. Branch protection/review of workflow
   changes is an essential trust boundary; YAML is not protection from an admin
   replacing the workflow.
6. Configure the `private-prerelease` environment and permitted deployment refs
   before enabling draft creation. Where the private repository plan supports it,
   require a separate reviewer, prevent self-review and disallow bypass. The
   workflow's dispatch/typed confirmation is mandatory even without this extra
   environment protection. Environment existence alone is **not** an approval
   rule; available private environment/reviewer features depend on the
   [GitHub plan](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
   If the needed policy cannot be enforced, leave draft creation off.
7. A reviewer must explicitly approve the complete corresponding source/legal
   materials and all four native gate results for this exact commit. The typed
   confirmation is a human attestation of review, not an automated legal opinion.

## Future commands (not executed during implementation)

First, dispatch builds **without** any draft creation. Replace `REVIEWED_REF` with
the authorized branch/commit selection on a repository that already contains the
reviewed workflows. Do not copy these commands into an automated release hook.

```sh
gh workflow run portable-build.yml --ref REVIEWED_REF
# Or exercise the entire private pipeline with draft creation explicitly OFF:
gh workflow run private-draft.yml --ref REVIEWED_REF -F create_draft=false
```

For a later authorized private draft only, an existing tag (example
`v0.2.0-rc.1`) must resolve to `REVIEWED_SHA`, the full 40-character commit:

```sh
gh workflow run private-draft.yml --ref v0.2.0-rc.1 \
  -F create_draft=true \
  -f reviewed_tag=v0.2.0-rc.1 \
  -f reviewed_commit=REVIEWED_SHA \
  -f 'confirmation=DRAFT PRERELEASE v0.2.0-rc.1 AT REVIEWED_SHA'
```

The workflow must already be registered on the default branch for manual
dispatch. Selecting the tag does not trigger a tag-push release; it selects the
commit to test in a manual run. If the ref, reviewed SHA, existing tag, exact
confirmation string or private visibility disagree, preflight fails before
builds. All four builds are rerun at the selected commit; a different historical
green run is not substituted. A missing runner or any failed/skipped build blocks
the aggregate verifier and the write job.

## Required assets and final review

Each native job produces one platform binary archive, its matching app-source
archive, its complete corresponding Olaf-source archive and `SHA256SUMS`.
The read-only aggregate verifier checks all four targets, commit equality and
identical source inventories across native hosts. The writer rechecks exactly
these files and emits one combined `SHA256SUMS` covering all **12 archives**.
Sources may appear once per target because each embeds the matching target's
compiler/runtime provenance. None may be omitted to save space.

Binary archives must contain the app, **separate** `olaf-runtime/olaf[.exe]`, setup
instructions, root license/notices, dependency licenses, runtime legal/provenance
files and `BUILD-PROVENANCE.json`. FFmpeg/FFprobe binaries never accompany them.
App-source includes the lockfile, build tooling and instructions; Olaf-source
includes native runtime source, Zigzag and embedded dependency source, patches,
required tests, instructions and legal materials. No audio/database/evidence,
credentials, handoffs, diagnostics, downloaded toolchains or caches are assets.

Creation and asset uploads are not transactional. If an upload fails, an
incomplete **private draft prerelease** may remain; leave it unpublished and have
an authorized maintainer inspect/remove it. The workflow refuses to overwrite
an existing release on rerun. It does not silently repair, publish or promote.
Verify every expected asset and both draft/prerelease flags in the UI after a
successful authorized future run. Any decision to publish requires a separate
future task and policy review; this pipeline contains no publishing mechanism.

## Deferred integration checks

* Real Rust 1.99.0 compilation of the integrated lockfile on all four hosts.
* Provider output filenames/schema, Zig pin/job control and complete local source
  build, without private checkout credentials or unsupported external dependencies.
* Hygiene checker behavior with reviewed sources and ignored staging directories.
* Native selected Rust tests, Olaf regression builds and both CLI smoke interfaces.
* Actual PE imports, Unix execute modes, ELF symbol/glibc requirements and Mach-O
  dependencies/minimum-OS load commands; clean-host runtime availability.
* GitHub reusable-workflow/event behavior, private runner/environment availability,
  authorization gates, denied-tag/confirmation cases and asset upload behavior.

Do not change a target's `status: unverified` in `release/targets.json` based only
on this tooling implementation. A real run records its narrowly scoped native
gate result in provenance; broader compatibility remains unverified.
