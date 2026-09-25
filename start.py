"""Local Shazam — Interactive entry point."""

import os
import sys
import shutil
import subprocess

# ── Ensure we can import the shazam package next to this script ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

DB_PATH = os.path.join(SCRIPT_DIR, "shazam.db")
REQUIREMENTS = os.path.join(SCRIPT_DIR, "requirements.txt")

# ── ANSI helpers ──
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print(f"\n{RED}ffmpeg not found in PATH.{RESET}")
        print("Install it from https://ffmpeg.org and make sure it's in your PATH.")
        print("On Windows: download, extract, add the bin/ folder to your PATH.\n")
        return False
    return True


def auto_install_deps():
    missing = []
    for pkg in ["numpy", "scipy", "tqdm"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return True

    print(f"\n{YELLOW}Missing packages: {', '.join(missing)}{RESET}")
    print(f"Installing from requirements.txt...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"{RED}pip install failed:{RESET}")
        print(result.stderr)
        return False
    print(f"{GREEN}Dependencies installed.{RESET}\n")
    return True


def fmt_size(mb):
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.1f} MB"


def do_index():
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="Select your music folder")
    root.destroy()

    if not folder:
        print(f"{YELLOW}Cancelled.{RESET}")
        return

    print(f"\nIndexing: {BOLD}{folder}{RESET}")

    from shazam.database import Database
    from shazam.indexer import bootstrap_directory

    db = Database(DB_PATH)
    try:
        stats = bootstrap_directory([folder], db, workers=min(os.cpu_count() or 4, 6))
        print()
        if stats["indexed"] > 0:
            print(f"  {GREEN}Indexed:  {stats['indexed']}{RESET}")
        if stats["skipped"] > 0:
            print(f"  {YELLOW}Skipped:  {stats['skipped']}{RESET} (already indexed)")
        if stats["failed"] > 0:
            print(f"  {RED}Failed:   {stats['failed']}{RESET}")
        print(f"  Total:    {stats['total']} files found")

        print()
        db_stats = db.get_stats()
        print(f"  Database: {db_stats['songs']:,} songs / "
              f"{db_stats['fingerprints']:,} fingerprints / "
              f"{fmt_size(db_stats['db_size_mb'])}")
    finally:
        db.close()


def do_match():
    if not os.path.isfile(DB_PATH):
        print(f"\n{RED}No database found.{RESET} Index a music folder first (option 1).")
        return

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    files = filedialog.askopenfilenames(
        title="Select audio snippet(s) to identify",
        filetypes=[
            ("Audio files", "*.mp3 *.flac *.wav *.ogg *.opus *.m4a *.aac *.wma *.mp4 *.mkv *.webm"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()

    if not files:
        print(f"{YELLOW}Cancelled.{RESET}")
        return

    from shazam.database import Database
    from shazam.matcher import match_snippet, confidence_label

    db = Database(DB_PATH)
    try:
        for snippet in files:
            print(f"\n{BOLD}Analyzing: {os.path.basename(snippet)}{RESET}")
            results = match_snippet(snippet, db, top_n=10)

            if not results:
                print(f"  {YELLOW}No matches found.{RESET}")
                continue

            print()
            for i, r in enumerate(results, 1):
                pct = r["confidence"] * 100
                label = confidence_label(r["confidence"])

                if label == "HIGH":
                    color = GREEN
                elif label == "PROBABLE":
                    color = CYAN
                elif label == "POSSIBLE":
                    color = YELLOW
                else:
                    color = RED

                print(f"  {BOLD}#{i}{RESET}  {color}{BOLD}{pct:5.1f}%{RESET} {color}[{label}]{RESET}  {r['aligned_hashes']} aligned hashes")
                print(f"      {BOLD}{r['filename']}{RESET}")
                print(f"      {r['filepath']}")
                if i < len(results):
                    print()
    finally:
        db.close()


def do_stats():
    if not os.path.isfile(DB_PATH):
        print(f"\n{YELLOW}No database found.{RESET} Index a music folder first (option 1).")
        return

    from shazam.database import Database

    db = Database(DB_PATH)
    try:
        stats = db.get_stats()
        print(f"\n  Songs:         {stats['songs']:,}")
        print(f"  Fingerprints:  {stats['fingerprints']:,}")
        print(f"  Database size: {fmt_size(stats['db_size_mb'])}")
    finally:
        db.close()


def main():
    # Enable ANSI escape codes on Windows
    if sys.platform == "win32":
        os.system("")

    print(f"\n{BOLD}Local Shazam{RESET}")
    print("=" * 30)

    if not check_ffmpeg():
        input("\nPress Enter to exit...")
        sys.exit(1)

    if not auto_install_deps():
        input("\nPress Enter to exit...")
        sys.exit(1)

    while True:
        print(f"""
{BOLD}[1]{RESET} Index music folder
{BOLD}[2]{RESET} Match snippets
{BOLD}[3]{RESET} View database stats
{BOLD}[4]{RESET} Exit
""")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            do_index()
        elif choice == "2":
            do_match()
        elif choice == "3":
            do_stats()
        elif choice == "4":
            print("Bye!")
            break
        else:
            print(f"{YELLOW}Invalid option.{RESET}")


if __name__ == "__main__":
    main()
