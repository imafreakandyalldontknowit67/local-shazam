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
  <a href="#getting-started">Get started</a> &middot;
  <a href="#limits-to-understand">Limits</a> &middot;
  <a href="#documentation">Documentation</a>
</p>

</div>

![Local Shazam interactive menu on Windows](assets/screenshots/windows-menu.png)

Local Shazam is a Rust native terminal app that identifies clips by searching
**your indexed local collection**, not a global catalog. Recognition runs on your
machine, without uploading audio or using the Shazam API.

## Download

> [!WARNING]
> This is an experimental native preview with **no published native release**.
> Existing packages remain in a private draft. Distribution and license review
> remains open before public release.

The [build guide](docs/BUILDING.md) documents source builds; it is not a public
download offering. See [preview status and build history](docs/PREVIEW_STATUS.md)
for the recorded Windows package and historical Linux/macOS builds. Those records
do not establish platform compatibility or production readiness.

## Getting started

Native users do **not** need Python. With a prepared native package:

1. Install **both FFmpeg and FFprobe separately** from the app, and put both on
   `PATH`. Supported audio formats depend on their installed codecs.
2. Extract the complete package into a writable folder. Keep its matching
   **`olaf-runtime/` directory beside the executable**, along with the notices
   and matching runtime source materials.
3. Launch without arguments for the menu: `.\local-shazam.exe` in PowerShell,
   or `./local-shazam` on a prepared Linux/macOS target.
4. Choose **menu option 1** to index a folder you select, then choose a worker
   count. Start with a small folder and few workers.
5. Choose **menu option 2** to identify one or more existing audio clips, then
   review the suggested source files.

Option **3** shows index statistics; option **4** exits. Opening the menu does
not start indexing. Keep indexes outside your source audio; the default Olaf
index is `local-olaf/` beside the executable. The [native command guide](rust-app/README.md)
explains custom index paths, command-line use and the Rust comparison backend.

## Limits to understand

- Matches are **suggestions, not guarantees**. Scores and result labels are
  **not calibrated probabilities**; recognition accuracy remains unverified.
- Short or noisy clips, quiet sections, pitch/speed changes, covers and live
  performances may fail or give ambiguous results.
- Source files must remain available for local verification. Missing, moved or
  changed files can prevent a match.
- The default Olaf query analyzes only the **first 30 seconds** of each clip.
  Indexed tracks are processed in full, so a clip can come from later in a track.

Large libraries can use substantial CPU, memory, disk and temporary space. Use
a stable machine: development crashes remain unresolved, fewer workers are not
a proven fix, and post-crash index integrity is unverified. Do not resume work
on a machine with unresolved crashes. See [Olaf behavior and limits](rust-app/OLAF.md).

## Documentation

- [Native command guide](rust-app/README.md) and [Olaf limits](rust-app/OLAF.md)
- [Building from source](docs/BUILDING.md), [releasing](docs/RELEASING.md) and
  [release checklist](docs/RELEASE_CHECKLIST.md)
- [Preview status and build history](docs/PREVIEW_STATUS.md) and [changelog](CHANGELOG.md)
- [Legacy Python reference](legacy/python/README.md): historical source only,
  not included in native packages or needed to run the native app.

## Reporting a problem

[Open an issue](https://github.com/imafreakandyalldontknowit67/local-shazam/issues/new)
with your app version, operating system, backend, worker count and the error text.
Include the command or menu steps that reproduce it. Redact personal paths and
metadata before sharing logs; do not upload private audio or your index database.

## Licensing

Original application code: [MIT](LICENSE). The separately shipped, modified Olaf
runtime is **AGPL-3.0-or-later**, not MIT. See
[Third-party notices](THIRD_PARTY_NOTICES.md); packages must retain matching Olaf
source, patches and required notices. MIT is not a blanket label for the package.
