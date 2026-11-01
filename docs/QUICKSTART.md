# Local Shazam: Windows quickstart

Local Shazam searches only music you explicitly index on your computer. It
does not upload audio, search an internet catalog, or use the Shazam API.
Opening the app does **not** automatically index your music.

## 1. Prepare the app

- Install **both FFmpeg and FFprobe** separately from Local Shazam and make
  both available on Windows **PATH**. PATH is the list of folders Windows
  checks when an app needs to find a tool; include the folder containing these
  tools. Python is not required.
- Check the [root README](../README.md) for current download availability.
  When a Windows ZIP is available, extract the **complete ZIP** to a folder
  you can write to. Preserve all its contents, including notices, and keep
  `olaf-runtime` beside `local-shazam.exe`. Do not run from inside the ZIP.
- Downloads may be unsigned, and Windows may show security warnings. Check
  the download's source and release information; if unsure, stop rather than
  bypass protections or dismiss warnings blindly.

## 2. Open the console menu

Run `local-shazam.exe` from the extracted folder. In the console window,
type a menu number and press **Enter**. Windows folder and file selection
dialogs open when needed.

![Local Shazam Windows console menu with numbered options to add music, identify clips, view library stats, and exit](../assets/screenshots/windows-menu.png)

## 3. Add your music first

Type **1**, then press Enter for **[1] Add a music folder**. In the folder
dialog, select a folder containing complete tracks; start with a small folder.

At the **Worker count** prompt, explicitly type **2** and press Enter. This
means two indexing workers, **not menu option 2**. It is a conservative starting
choice, not a guarantee of safety or stability. Do not resume indexing on a
computer with unresolved crashes.

Wait for indexing to finish and inspect any reported failures before trying
to identify a clip.

## 4. Identify a local clip

Back at the menu, type **2** and press Enter for **[2] Identify audio clips**.
Use the file dialog to select an existing **local audio file**.

A seven-second snippet is one example, not a promise of recognition.
**30 seconds is the maximum analyzed query duration, not a minimum.** Shorter
clips are allowed; longer files use only their first 30 seconds. The complete
tracks you indexed are processed in full.

Review up to **three suggestions**; there may be fewer or none. Results and
their labels reflect supporting audio evidence, not certainty or a measured
chance of being correct. Listen to the original files in your own audio player
to check suggestions. The app looks for matching audio, not similar-song
recommendations.

## 5. Check and keep your library

Type **3** and press Enter for **[3] View library stats** to see the indexed
song count and storage information.

Keep original music files available at their indexed paths, and retain the
default `local-olaf` index folder beside the executable. Moving, deleting, or
changing source files can prevent verification. **The index does not replace
your music.**

## Troubleshooting

- **Missing FFmpeg or FFprobe:** install both, correct Windows PATH, then
  reopen the app.
- **Missing Olaf runtime:** restore the complete matching package, keeping
  `olaf-runtime` beside `local-shazam.exe`.
- **No match:** confirm indexing finished and the originals remain available
  at their indexed paths. Try a clearer or longer local snippet with useful
  audio within its first 30 seconds. No result does not prove the song is absent.

For optional CLI commands and settings, see the
[native application guide](../rust-app/README.md). For technical matching
details, see [how matching works](../rust-app/OLAF.md).
