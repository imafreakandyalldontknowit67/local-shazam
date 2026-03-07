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

- **Indexing**: ~4 songs/second with 4 workers
- **Matching**: Under 1 second for most snippets
- **Storage**: ~0.6 MB per song in the database

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
