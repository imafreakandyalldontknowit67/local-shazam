# Publication-surface privacy review

## Baseline reviewed on 2026-10-30

This is an evidence record, not a guarantee that arbitrary private information
cannot exist. The repository remains private. Do not change visibility until
the current release checklist is complete.

The baseline main commit was `57f229c531f3c344f13f8d447a90d90c81d22194`.
The review covered the remote main branch, the merged native migration branch,
and the historical `v1.0.1` tag: 22 reachable commits and 594 distinct
path/blob pairs. The source policy checked both filenames and blob contents.

- No credential or operator-personal-path finding remained after review.
- One historical packaging test deliberately contained an invalid absolute
  path. It was a synthetic rejection fixture, not an operator path. It does
  not justify a general test/vendor exclusion from privacy checks.
- Commit messages produced no credential or personal-path heuristic findings.
  Reviewed commit author addresses used GitHub noreply addresses.
- No history rewrite was performed. Moving a file does not erase its history;
  a future sensitive finding must be addressed across every affected ref.

## Existing preview artifacts

All twelve archives associated with preview commit
`92a983a57ff92ad4b9342fb4dd992edf728b5a97` were inventoried locally: four binary
packages and eight source archives. An operator-account check found no hits.
Binary inspection nevertheless found hosted-build home/workspace paths in
Windows, Linux and macOS executables. Those artifacts are **not** evidence of successful
compiler path sanitization. Rebuild from source with the new privacy policy;
do not patch executable strings or merely rename the archives.

The existing tar files had normalized zero owner/group IDs, empty owner/group
names, no links, and no detected private paths in PAX metadata. The Windows ZIP
had no archive or member comments. Source path candidates were generic examples,
test fixtures, and the separately documented exact public upstream fixture.

New artifacts require independent checksum, source correspondence, binary
privacy, and archive-metadata verification after hosted compilation. A clean
source tree cannot prove that a compiler omitted build paths from a binary.

## Other GitHub surfaces

- The repository was verified private; Pages and wiki were disabled.
- The issue listing was empty at inspection.
- Logs for the four existing native CI runs were reviewed for the operator
  account string; none contained it. Hosted-runner path mentions remain in CI
  logs and are distinct from operator-private paths.
- The old Python release had no uploaded assets. It has been labeled
  **Legacy Python v1.0.1 (archived)**; its original notes and tag are preserved.
- The native preview remained a draft during this baseline review.

Local raw audit details and downloaded logs are excluded from version control.
Do not upload them as release assets. No source audio, production index,
diagnostic dump, or development executable was read or bundled for this review.

## Required final pass

Re-run the source policy and inspect all newly reachable commits, tags, release
bodies, assets, workflow logs, and remote branches after integration. Verify
repository visibility again. Publish only the exact verified artifact set with
its corresponding source and checksums, under the release checklist; this
baseline record alone is not authorization to make the repository public.
