# Proposed repository metadata

Recommendations only. This file does not change remote settings, topics,
visibility, releases or tags. Keep the repositories private; no visibility action
is part of this proposal.

## GitHub description

> Recognize clips against your own local music library. Native Rust app with experimental Olaf retrieval and local verification. No cloud recognition.

## Recommended topics

- `audio-fingerprinting`
- `music-recognition`
- `local-first`
- `rust`
- `command-line`
- `audio-analysis`
- `music-library`
- `ffmpeg`

These describe the project, not verified platform support, performance or
accuracy. Avoid topics or descriptions implying a Shazam API integration,
global-catalog access, universal codecs or guaranteed identification.

## Release-facing guardrails

- Lead with recognition against the user's own indexed library; never imply
  affiliation with the Shazam service.
- Describe Olaf retrieval plus Rust candidate-window verification as
  experimental. Keep `--backend rust` visible as the comparison backend.
- Native source version is `0.2.0`; historical `1.0.x` tags are Python releases.
  Do not infer or propose a new tag from those unrelated version sequences.
- Windows x64, Linux x64 and macOS arm64/x64 passed native gates only at
  historical commit `92a983a57ff92ad4b9342fb4dd992edf728b5a97`, in run
  `41023384988`. Do not translate that into current-HEAD, privacy, minimum-OS
  support, clean-host or release approval badges. No latest-public-release promise.
- Keep unresolved stability/resource caveats visible. At most six default
  workers is a concurrency policy, not a proven fix for development crashes.
- Scores and suggestions are not probabilities. Held-out accuracy for the
  integrated pipeline remains unverified; do not reuse historical benchmark
  numbers as current product claims.
- Scope [MIT](../LICENSE) to original application code, not the whole package.
  The modified Olaf runtime is AGPL-3.0-or-later; link attribution and matching
  source materials rather than implying a blanket MIT distribution.

## Documentation integration checklist

Existing presentation links: [overview](../README.md),
[changelog](../CHANGELOG.md), [native guide](../rust-app/README.md),
[Olaf guide](../rust-app/OLAF.md), [local SVG banner](../assets/banner.svg) and
[application license](../LICENSE).

Integrated documentation:

- [Building](BUILDING.md)
- [Releasing and pending gates](RELEASING.md)
- [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [License review](../licenses/RELEASE_REVIEW.md)

The repository-only Python archive destination is `legacy/python/README.md`;
post-integration relocation verification is pending with the parent. Native
packages do not ship the historical Python app.

## Historical preview status (reviewed 2026-10-30)

Authenticated read-only GitHub metadata confirms a private repository, successful
native run `41023384988` at the commit above, and draft/prerelease flags for
`v0.2.0-native.1` with 12 archives and consolidated checksums. API asset sizes and
digests match the existing local files. No corresponding tag ref was resolved;
the draft's tag name must not be advertised as an existing verified tag.
See [the bounded evidence record](../licenses/review/native-preview.json).

The run used the push-triggered build workflow, not evidence that the separate
manual draft workflow or its authorization paths were exercised. No publication
or remote metadata changes were made by this review. Licensing/SDK and
compiler-privacy gates remain open, along with unsigned/non-notarized and
compatibility limitations. Final release decisions and any later owner visibility
change are outside this task; visibility alone resolves none of the source,
privacy or legal obligations.
