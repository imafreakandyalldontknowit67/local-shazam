"""Click CLI for Local Shazam."""

import os
import sys
import shutil
import click
from shazam import __version__
from shazam.database import Database, DEFAULT_DB


def _fmt_size(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.1f} MB"


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        click.echo(click.style("Error: ", fg="red", bold=True) +
                    "ffmpeg not found in PATH. Install it from https://ffmpeg.org", err=True)
        raise SystemExit(1)


@click.group()
@click.version_option(__version__, prog_name="shazam")
def cli():
    """Local Shazam — fingerprint and match your audio collection."""


@cli.command()
@click.argument("directories", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-w", "--workers", default=4, show_default=True, help="Parallel workers.")
@click.option("--compact", is_flag=True, help="Smaller DB at cost of needing longer snippets.")
@click.option("--db", "db_path", default=DEFAULT_DB, show_default=True, help="Database path.")
def bootstrap(directories, workers, compact, db_path):
    """Index audio files from one or more directories.

    Recursively scans for all supported audio formats and builds
    a fingerprint database. Already-indexed files are skipped.
    """
    _check_ffmpeg()
    from shazam.indexer import bootstrap_directory

    db = Database(db_path)
    try:
        click.echo(f"Scanning {len(directories)} director{'y' if len(directories) == 1 else 'ies'}...")
        stats = bootstrap_directory(list(directories), db, workers=workers, compact=compact)

        click.echo()
        if stats["indexed"] > 0:
            click.echo(click.style(f"  Indexed:  {stats['indexed']}", fg="green"))
        if stats["skipped"] > 0:
            click.echo(click.style(f"  Skipped:  {stats['skipped']}", fg="yellow") + " (already indexed)")
        if stats["failed"] > 0:
            click.echo(click.style(f"  Failed:   {stats['failed']}", fg="red"))
        click.echo(f"  Total:    {stats['total']} files found")

        click.echo()
        db_stats = db.get_stats()
        click.echo(f"  Database: {db_stats['songs']:,} songs / "
                    f"{db_stats['fingerprints']:,} fingerprints / "
                    f"{_fmt_size(db_stats['db_size_mb'])}")
    finally:
        db.close()


@cli.command()
@click.argument("snippet", type=click.Path(exists=True))
@click.option("-n", "--top", default=10, show_default=True, help="Max results to show.")
@click.option("--db", "db_path", default=DEFAULT_DB, show_default=True, help="Database path.")
def match(snippet, top, db_path):
    """Identify a song from an audio snippet.

    Takes any audio file (recording, clip, re-encode) and finds
    the best matching songs in the indexed collection.
    """
    _check_ffmpeg()
    from shazam.matcher import match_snippet, confidence_label

    if not os.path.isfile(db_path):
        click.echo(click.style("Error: ", fg="red", bold=True) +
                    f"No database at {db_path}. Run 'shazam bootstrap' first.", err=True)
        raise SystemExit(1)

    db = Database(db_path)
    try:
        click.echo(f"Analyzing: {os.path.basename(snippet)}")
        results = match_snippet(snippet, db, top_n=top)

        if not results:
            click.echo(click.style("\nNo matches found.", fg="yellow"))
            return

        click.echo()
        for i, r in enumerate(results, 1):
            pct = r["confidence"] * 100
            label = confidence_label(r["confidence"])

            if label == "HIGH":
                color = "green"
            elif label == "PROBABLE":
                color = "cyan"
            elif label == "POSSIBLE":
                color = "yellow"
            else:
                color = "red"

            rank = click.style(f"#{i}", bold=True)
            conf = click.style(f"{pct:5.1f}%", fg=color, bold=True)
            tag = click.style(f"[{label}]", fg=color)
            aligned = f"{r['aligned_hashes']} aligned hashes"

            click.echo(f"  {rank}  {conf} {tag}  {aligned}")
            click.echo(click.style(f"      {r['filename']}", bold=True))
            click.echo(f"      {r['filepath']}")
            if i < len(results):
                click.echo()
    finally:
        db.close()


@cli.command()
@click.option("--db", "db_path", default=DEFAULT_DB, show_default=True, help="Database path.")
def status(db_path):
    """Show database statistics."""
    if not os.path.isfile(db_path):
        click.echo(f"No database at: {db_path}")
        return

    db = Database(db_path)
    try:
        stats = db.get_stats()
        click.echo(f"  Songs:         {stats['songs']:,}")
        click.echo(f"  Fingerprints:  {stats['fingerprints']:,}")
        click.echo(f"  Database size: {_fmt_size(stats['db_size_mb'])}")
    finally:
        db.close()


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("-w", "--workers", default=4, show_default=True, help="Parallel workers.")
@click.option("--db", "db_path", default=DEFAULT_DB, show_default=True, help="Database path.")
def add(directory, workers, db_path):
    """Add a directory to the index (incremental — skips existing files)."""
    _check_ffmpeg()
    from shazam.indexer import bootstrap_directory

    db = Database(db_path)
    try:
        stats = bootstrap_directory([directory], db, workers=workers)
        click.echo()
        if stats["indexed"] > 0:
            click.echo(click.style(f"  Indexed:  {stats['indexed']}", fg="green"))
        if stats["skipped"] > 0:
            click.echo(click.style(f"  Skipped:  {stats['skipped']}", fg="yellow"))
        if stats["failed"] > 0:
            click.echo(click.style(f"  Failed:   {stats['failed']}", fg="red"))
        if stats["indexed"] == 0 and stats["skipped"] > 0:
            click.echo("  All files already indexed.")
    finally:
        db.close()


@cli.command()
@click.argument("path")
@click.option("--db", "db_path", default=DEFAULT_DB, show_default=True, help="Database path.")
def remove(path, db_path):
    """Remove a file or directory from the index."""
    if not os.path.isfile(db_path):
        click.echo(f"No database at: {db_path}")
        return

    db = Database(db_path)
    try:
        song = db.get_song_by_filepath(os.path.abspath(path))
        if song:
            db.remove_song(song["id"])
            click.echo(click.style(f"  Removed: {song['filename']}", fg="green"))
            return

        abs_path = os.path.abspath(path)
        count = db.remove_songs_by_path_prefix(abs_path)
        if count:
            click.echo(click.style(f"  Removed {count} songs", fg="green") +
                        f" matching: {abs_path}")
        else:
            click.echo(click.style("  No indexed files found", fg="yellow") +
                        f" matching: {path}")
    finally:
        db.close()
