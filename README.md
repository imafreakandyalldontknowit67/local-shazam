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
  <a href="#good-to-know">Good to know</a> &middot;
  <a href="#documentation">Documentation</a>
</p>

</div>

![Local Shazam interactive menu on Windows](assets/screenshots/windows-menu.png)

Know the clip, but can't find the file? Local Shazam searches your music collection
and helps you find where it came from. Your audio stays on your computer.

## Download

Downloads aren't public yet. We're preparing the next release.
You can [build from source](docs/BUILDING.md) in the meantime.

## Getting started

1. Install **FFmpeg and FFprobe** and make sure they're on your `PATH`.
2. Extract the app and keep the included `olaf-runtime` folder beside it.
3. Open **Local Shazam**.
4. Choose **Add a music folder** and let it index your collection.
5. Choose **Identify audio clips** to find a clip's source file.

You can choose how many files to index at once. Start with a few workers if you
want to keep using your computer while it runs. No Python required.

## Good to know

- Searches **your library**, not an online music catalog. No uploads or Shazam API.
- Shows up to **three possible matches**. Listen and check when a result is uncertain.
- Short, noisy or heavily edited clips can be harder to recognize.
- Checks the first **30 seconds** of a clip against the full indexed tracks.
- Keep the original music files available after indexing.

## Documentation

- [Commands and settings](rust-app/README.md)
- [How matching works](rust-app/OLAF.md)
- [Build from source](docs/BUILDING.md)
- [Release status](docs/PREVIEW_STATUS.md) and [changelog](CHANGELOG.md)
- [Legacy Python version](legacy/python/README.md)

## Found a problem?

[Open an issue](https://github.com/imafreakandyalldontknowit67/local-shazam/issues/new)
with your app version, operating system and what happened. Remove personal paths
from logs, and don't upload your music or library database.

## License

The app's original code is [MIT licensed](LICENSE). The included Olaf runtime is
**AGPL-3.0-or-later**. See [third-party notices](THIRD_PARTY_NOTICES.md) for details.
