# Native preview status and recorded build history

[Back to the user guide](../README.md)

Local Shazam is an **experimental native preview with no published native
release**. Existing packages remain in a private draft; distribution and license
review remains open. Native source version: `0.2.0`. Older `1.0.x` tags refer to
the [legacy Python implementation](../legacy/python/README.md), not native releases.

This page moves the release introduction's detailed status notes out of the
README. It summarizes existing repository records, without updating or
reinterpreting the underlying audits or provenance. It is **not new verification
or current-HEAD validation**; no remote state or package bytes were checked for
this documentation change.

## Recorded package history

### Historical four-target baseline

[Releasing](RELEASING.md), [Building](BUILDING.md) and the
[artifact and draft metadata record](../licenses/review/native-preview.json)
record successful native build/package gates at commit
`92a983a57ff92ad4b9342fb4dd992edf728b5a97`, in
[CI run 41023384988](https://github.com/imafreakandyalldontknowit67/local-shazam/actions/runs/41023384988).
That baseline covers Windows x64, Linux x64, macOS Apple Silicon (arm64) and
macOS Intel (x64), not current HEAD.

The recorded read-only review checked twelve local archives: a binary package,
matching app-source archive and matching Olaf-source archive per target. It
checked checksums, source/payload hashes, file sets, architecture/modes and
cross-archive provenance. Each manifest records 16 dataset-free gates: ten
selected Rust tests, three Olaf regressions and three help/version smoke checks.
These are historical build records, not production validation.

The historical draft review compared API asset digests and sizes with local
files; it **did not download remote asset bytes** or authenticate the uploader.
Do not treat that metadata comparison as a post-upload byte check.

### Subsequently recorded Windows replacement

The README at commit `98a54f3` records a later **Windows x64 package built locally
at `d639ab2a2c49`**, with native test/packaging gates and uploaded-download
checksum verification passed. This restates that existing README record; it
does not extend the historical four-target evidence file or claim those checks
were performed again here.

Linux and macOS packages remain historical builds at `92a983a57ff9`, awaiting
replacement and independent verification, including compiler-privacy rebuilds.
The later Windows record must not be read as an all-platform refresh or
validation of this documentation commit.

## Draft, packaging and checksum boundaries

- The repository records identify private draft `v0.2.0-native.1`, release ID
  `428787114`, with draft/prerelease flags and no publication timestamp. These
  are recorded identifiers requiring maintainer reconfirmation, not newly
  checked remote facts. The [release listing](https://github.com/imafreakandyalldontknowit67/local-shazam/releases)
  requires an account with draft access; it is not a public native download.
- **No release tag has been verified.** A draft name or `tag_name` does not prove
  that a corresponding Git tag exists.
- Packages are portable ZIP (Windows) or tar archives (Linux/macOS), not
  installers or macOS app bundles. Keep the matching `olaf-runtime/` beside the
  executable. FFmpeg and FFprobe are external prerequisites, not bundled tools;
  native users do not need Python.
- Matching app-source and Olaf-source archives and SHA256 checksums accompany
  the recorded private draft. Checksums establish byte consistency, **not
  publisher authentication**. They do not prove bit-for-bit reproducibility or
  close corresponding-source obligations.
- Packages are unsigned; macOS builds are not Developer ID signed or notarized.
  An ad-hoc signature is not publisher signing. Do not disable OS security to
  bypass warnings.

## What these records do not establish

Build and packaging gates do **not** establish minimum OS/glibc support,
clean-host compatibility, privacy, snippet accuracy, hardware stability or legal
approval. The integrated recognition pipeline has no established held-out
accuracy or accuracy equivalence with the Rust comparison backend. Historical
platform builds must not be presented as verified user support.

The [baseline privacy audit](PRIVACY_AUDIT.md) and
[compiler-privacy requirements](BUILD_PRIVACY.md) retain their own scope.
Source changes or passing checksums do not retroactively sanitize historical
binaries. Fresh package claims require checks of the exact binaries, matching
source archives and recorded commit; no such current-HEAD checks are claimed here.

The original application code is [MIT](../LICENSE), while the separately shipped,
modified Olaf runtime is **AGPL-3.0-or-later**, not MIT. The
[third-party notices](../THIRD_PARTY_NOTICES.md) and
[license review](../licenses/RELEASE_REVIEW.md) retain the unresolved distribution,
combined-work, corresponding-source and dependency review boundaries. A private
draft, source archives or successful build does not close those reviews.

## Maintainer references

- [Build instructions and verification scope](BUILDING.md)
- [Release-readiness decisions and outstanding gates](RELEASING.md)
- [Existing-draft refresh checklist](RELEASE_CHECKLIST.md), including actual
  uploaded-byte download checks
- [Verified-upload cleanup procedure](BUILD_CLEANUP.md): separate authorization
  and retained evidence required; this page authorizes no cleanup or publication
- [Proposed repository metadata](REPOSITORY_METADATA.md)
