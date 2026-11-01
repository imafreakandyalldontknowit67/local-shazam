<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/mark-white.svg">
  <img src="assets/brand/mark-black.svg" alt="Local Shazam" width="96" height="96">
</picture>

<h1>Local Shazam</h1>

<p><strong>Find the source of a clip in your own music collection.</strong></p>

<p>Local audio recognition. No uploads. No Shazam API.</p>

<p>
  <a href="#download">Download</a> &middot;
  <a href="#features">Features</a> &middot;
  <a href="#getting-started">Get started</a> &middot;
  <a href="#building-from-source">Build from source</a> &middot;
  <a href="#reporting-a-problem">Report a problem</a>
</p>

</div>

![Local Shazam interactive menu on Windows](assets/screenshots/windows-menu.png)

*The native Windows app. All recognition runs against your own local library.*

> [!WARNING]
> Local Shazam is an experimental native preview. Matches are suggestions, not
> guarantees. Packages are unsigned and remain in a private draft release;
> distribution and license review is still open before public release.

There is no published native release yet. The private draft contains a newly
built and verified Windows package at `d639ab2a2c49`; Linux and macOS packages
remain historical builds awaiting replacement and verification.
See the [release checklist](docs/RELEASE_CHECKLIST.md) and
[verified-upload cleanup procedure](docs/BUILD_CLEANUP.md).

## About

Local Shazam recognizes audio snippets against a library you choose. Index a music
folder, give it a clip, and review the matching files. Recognition runs on your
machine, without uploading audio or querying a global music catalog.

The native app is built in Rust. Its experimental Olaf backend retrieves candidate
tracks, then Rust checks the source audio before showing suggestions. The original
Rust-only backend remains available for comparison.

## Features

**Recognition**

- Index complete tracks, not just their opening minutes.
- Match clips from anywhere in an indexed track; Olaf analyzes the first 30 seconds of each query.
- Review up to three candidates, with evidence-based result labels rather than accuracy promises.
- Keep audio local, including candidate verification.

**Workflow**

- Interactive menu with file/folder pickers, or a command-line interface.
- Choose how many indexing workers to use.
- Inspect index statistics and request JSON output.
- Use separate Olaf and Rust indexes for comparison.

**Native packages**

- Windows x64, Linux x64, Apple Silicon and Intel Mac builds.
- No Python runtime required for the native app.
- Matching Olaf runtime and corresponding source archives supplied with preview packages.
- FFmpeg and FFprobe installed separately.

## Download

Open the [private draft release](https://github.com/imafreakandyalldontknowit67/local-shazam/releases)
with a repository account that can view drafts. These are not public downloads yet.

| Platform | Preview package |
| --- | --- |
| Windows (x64) | Portable ZIP containing `local-shazam.exe` |
| Linux (x64) | Tar archive containing `local-shazam` |
| macOS (Apple Silicon) | ARM64 tar archive containing `local-shazam` |
| macOS (Intel) | x64 tar archive containing `local-shazam` |

The historical four-platform baseline passed the [native CI build and packaging gates](https://github.com/imafreakandyalldontknowit67/local-shazam/actions/runs/41023384988)
at source commit `92a983a57ff92ad4b9342fb4dd992edf728b5a97`, not current HEAD.
The Windows package has since been replaced with a local build at `d639ab2a2c49`,
with native test/packaging gates and uploaded-download checksum verification passed.
Linux and macOS remain on the historical baseline.
Read-only [artifact and draft metadata review](licenses/review/native-preview.json)
confirmed the historical set. Checksums are not publisher authentication; these
gates do not establish minimum OS support, privacy, snippet accuracy or hardware
stability. Source archives and SHA256 checksums accompany the private draft
(planned version `v0.2.0-native.1`; no release tag has been verified). Native source
version: `0.2.0`; older `1.0.x` tags are Python releases.

Extract the complete package into a writable folder and keep `olaf-runtime/`
beside the app. These are portable command-line/menu apps, not installers or
macOS app bundles. Packages are unsigned and macOS builds are not notarized.

## Requirements

The default workflow needs the app, its matching Olaf runtime, and **FFmpeg and
FFprobe installed separately on `PATH`**. Native users need no Python. Codecs
depend on the FFmpeg build; SQLite is bundled for the Rust backend.

The package layout keeps the runtime beside the app:

```text
local-shazam.exe                 # local-shazam on Linux/macOS
olaf-runtime/
  olaf.exe                      # olaf on Linux/macOS
```

For setup and packaging, see [Building](docs/BUILDING.md),
[Releasing](docs/RELEASING.md) and [Third-party notices](THIRD_PARTY_NOTICES.md).
Windows is verified at `d639ab2a2c49`; Linux/macOS remain at `92a983a57ff9`.
This is build and packaging evidence, not a new snippet-accuracy or hardware-stability
claim. Historical Linux/macOS binaries still require a compiler-privacy rebuild
and independent verification; see the [release-readiness checklist](docs/RELEASING.md).

## Getting started

Run the prepared executable without arguments for the menu:

1. **Index music folder** — choose a folder, then a worker count.
2. **Match snippets** — choose one or more existing audio files.
3. **View database stats** — inspect the selected backend's index.
4. **Exit**.

Opening the menu does not start indexing. Choose a small folder and a new,
writable index location outside your source audio. Default workers are available
parallelism capped at **six**, or four if detection fails. More workers are not
necessarily faster or safer.

PowerShell examples; replace these paths with your own. `bootstrap` writes the
index, not your music files:

```powershell
.\local-shazam.exe --olaf-index "D:\AudioIndexes\trial-olaf" bootstrap "D:\Music\SmallFolder" --workers 2
.\local-shazam.exe --olaf-index "D:\AudioIndexes\trial-olaf" match "D:\Clips\snippet.mp3"
.\local-shazam.exe --olaf-index "D:\AudioIndexes\trial-olaf" --json status
```

Use `./local-shazam` and your own POSIX paths on a prepared Linux/macOS target.
See the [native command guide](rust-app/README.md) for the comparison backend.

## How recognition works

**Index → retrieve with Olaf → verify source windows with Rust → review.**
Original files must remain available for local candidate verification.

Olaf is the **experimental default**. It shortlists up to ten files; Rust checks
alignment and independent supporting moments before showing up to three
suggestions. Only the **first 30 seconds of an Olaf query** are analyzed; indexed
tracks are processed in full, so queries can originate later in a track.

| Olaf result | What it means |
| --- | --- |
| `strong_match` | Stronger heuristic evidence and a lead over other verified candidates; not a guarantee. |
| `possible_matches` | Up to three files meet minimum evidence requirements; review them yourself. |
| `insufficient_evidence` | No candidate passes; a clearer or more distinctive clip may help. |

These labels and the Rust backend's percentage-like scores are **not calibrated
probabilities**. See [Olaf behavior and limits](rust-app/OLAF.md).

### Separate backends, separate indexes

| Backend | Selection | Default storage beside the executable |
| --- | --- | --- |
| Olaf + Rust verification | Default, or `--backend olaf` | `local-olaf/`; override with `--olaf-index DIRECTORY` |
| Rust comparison engine | `--backend rust` | `local-shazam.db`; override with `--db FILE` |

There is **no automatic index conversion** between Python, Rust and Olaf. Index
selected folders separately. `--db` requires `--backend rust`.

## Limits to understand

- Held-out accuracy and Rust-equivalent accuracy for the integrated pipeline
  are unverified. Short/noisy clips, quiet sections, pitch/speed edits, covers
  and live performances can fail or yield ambiguous suggestions.
- No automatic recording-family grouping, quality-version selection or playback
  controls. Different encodes, mixes and masters may appear separately.
- No Olaf `remove` or `compact-db`. Rust maintenance affects only Rust indexes;
  Olaf runtime/config changes can require a fresh index.
- Olaf scans recognized extensions; unlike Rust, it does not probe unfamiliar
  extensions. DRM, malformed files and unavailable codecs may prevent decoding.
- Metadata/leading-file identity checks can miss edits; forced reindexing may
  be needed. Missing or changed sources can prevent verification.
- Large libraries and long tracks can consume substantial CPU, memory, disk and
  temporary space despite bounded queues. Development crashes have an unresolved
  cause and post-crash index integrity is unverified. The six-worker default cap
  is **not a stability fix**; do not resume work on a machine with unresolved crashes.

## Building from source

See the [native build guide](docs/BUILDING.md) for toolchain pins, platform
prerequisites and portable packaging. The [native command guide](rust-app/README.md)
covers development commands and backend selection. Release packaging and source
obligations are documented in [Releasing](docs/RELEASING.md).

## Reporting a problem

[Open an issue](https://github.com/imafreakandyalldontknowit67/local-shazam/issues/new)
with your app version, operating system, backend, worker count and the error text.
Include the command or menu steps that reproduce it. Redact personal paths and
metadata before sharing logs; do not upload private audio or your index database.

## Legacy Python reference

The Python `1.0.1` reference is archived in
[legacy/python/README.md](https://github.com/imafreakandyalldontknowit67/local-shazam/tree/main/legacy/python).
It requires Python 3.10+ and its dependencies and is
repository-only historical source, not included in native packages. It is not
the native release path: its first-120-second decoding, 30-second decode timeout
and size/first-8-KiB identity checks still apply, unlike complete-track native indexing.

## Project notes and licensing

[Changelog](CHANGELOG.md) · [Native guide](rust-app/README.md) ·
[Olaf design](rust-app/OLAF.md) · [Proposed repository metadata](docs/REPOSITORY_METADATA.md)

Original application code: [MIT](LICENSE). The separately shipped, modified Olaf
runtime is **AGPL-3.0-or-later**, not MIT. See
[Third-party notices](THIRD_PARTY_NOTICES.md); packages must retain matching Olaf
source, patches and required notices. MIT is not a blanket label for the package.
