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
- Windows x64, Linux x64 and macOS arm64/x64 are planned CI targets awaiting
  verification, not a supported-download list. Do not add passing-build badges
  or a latest-release promise without corresponding evidence.
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

Planned cross-branch links, absent from this presentation checkout at authoring
time and requiring verification after integration:

- [Building](BUILDING.md)
- [Releasing](RELEASING.md)
- [Third-party notices](../THIRD_PARTY_NOTICES.md)

These placeholders identify companion work, not completed release evidence.
