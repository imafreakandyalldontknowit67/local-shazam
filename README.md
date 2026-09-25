# Local Shazam

Identify songs from audio snippets — like Shazam, but for your local music collection.

## Setup

1. Install [Python 3.10+](https://python.org)
2. Install [ffmpeg](https://ffmpeg.org) and make sure it's in your PATH
3. Run:
   ```
   pip install -r requirements.txt
   python start.py
   ```

The script auto-installs missing dependencies and walks you through everything with native file picker dialogs.

## How it works

1. **Index** — Select a music folder. Every audio file gets decoded via ffmpeg, converted to a spectrogram, and fingerprinted using constellation hashing (the same algorithm behind Shazam). Fingerprints are stored in a local SQLite database.
2. **Match** — Select one or more audio snippets (recordings, clips, re-encodes). Their fingerprints are compared against the database using time-aligned hash matching.
3. **Results** — Matches are ranked by confidence. Works with partial clips, low-bitrate re-encodes, and noisy speaker recordings.

## Performance

Performance depends on audio length, CPU, storage, and database size. Indexing runs in
parallel with a bounded number of queued files; fingerprints are committed in batches.
Large databases can take substantially longer to match on a cold disk cache; do not
assume sub-second lookups at multi-gigabyte scale.

## Current limitations

- Only the first 120 seconds of each file are decoded. Snippets from later in a song
  will not match that song unless the indexed file contains that section near its start.
- Incremental identity checks use the file size and first 8 KiB. Same-sized edits
  outside that region may require removing and re-indexing the file manually.
- `ffmpeg` is required. A decoder that takes longer than 30 seconds for one file
  is treated as a failed file.

Run regression tests with `python -m unittest discover -s tests -v`.

## Advanced

Power users can still use the CLI directly:

```
pip install -e .
shazam bootstrap ~/Music
shazam match snippet.mp3
shazam status
```

## License

MIT
