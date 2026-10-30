# Archived Python application (1.0.1)

This is the obsolete, opt-in Python implementation of Local Shazam, preserved as
historical source. It is **not the native product**, a native runtime dependency,
or a new release. The distribution name remains `local-shazam`, the Python
package and CLI remain `shazam`, and the version remains `1.0.1`.

In the full repository, the native application and its original Rust comparison
engine remain in `rust-app/`. The separate Olaf runtime/source, vendor inputs,
patches and notices remain in their native locations. Neither native engine was
archived here. Native binary and corresponding-source inventories exclude this
legacy application; native Python build/release scripts are still required.

## Future opt-in installation

These are instructions for a deliberate future installation, **not commands run
as part of the archival work**. Use a separate virtual environment, not a global
installation or the native build environment. Requires Python **3.10+**, pip and
venv support. Install **FFmpeg** separately on `PATH` for decoding; available
formats depend on its codecs. Tkinter and a working desktop/display are needed
only for the optional launcher's file/folder pickers.

Choose one of the following starting locations. No activation or system setting
change is necessary when using the virtual environment's explicit executables.

### From the repository root

POSIX shell:

```sh
python3 -m venv legacy/python/.venv
legacy/python/.venv/bin/python -m pip install ./legacy/python
legacy/python/.venv/bin/shazam --help
legacy/python/.venv/bin/python -m shazam --help
```

PowerShell (use a Python 3.10+ interpreter):

```powershell
py -3 -m venv legacy\python\.venv
.\legacy\python\.venv\Scripts\python.exe -m pip install .\legacy\python
.\legacy\python\.venv\Scripts\shazam.exe --help
.\legacy\python\.venv\Scripts\python.exe -m shazam --help
```

There is intentionally no root `pyproject.toml`, `start.py`, or compatibility
launcher. Do not use `pip install .` at the repository root for this archive.

### From the archive directory (or a standalone source copy)

In a full checkout, first `cd legacy/python`. In a standalone source copy, start
in the directory containing this README and `pyproject.toml`.

POSIX shell:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/shazam --help
.venv/bin/python -m shazam --help
```

PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\shazam.exe --help
.\.venv\Scripts\python.exe -m shazam --help
```

`pyproject.toml` discovers only the `shazam` package and its subpackages relative
to this directory. It installs the console entrypoint `shazam = shazam.cli:cli`;
`python -m shazam` invokes the same CLI. `requirements.txt` contains the same
minimum runtime dependencies: Click, NumPy, SciPy and tqdm. Installing the project
already installs these; a requirements-only install does **not** install the
`shazam` console command. There is no resolved dependency lock and no bundled
dependencies. Opt-in pip installation may download build/runtime dependencies.

The build backend requires setuptools 77.0.3+ for the existing SPDX license
metadata and explicit local license inclusion. `MANIFEST.in` retains this README,
`LICENSE`, `requirements.txt`, `start.py` and the archived regression file in a
future source distribution. The optional launcher and regression file are source
tools, not installed console scripts. Keep the complete source archive together;
no parent-directory requirements or license file is needed.

## CLI and database selection

Use the virtual environment's executables as above. If that environment is
already activated, the short forms are `shazam` and `python -m shazam`.
Historical commands are `bootstrap`, `add`, `match`, `status` and `remove`.

The CLI's `DEFAULT_DB` is the relative string **`shazam.db`**. Thus all five
commands default to the **current working directory**, not the package, script,
repository or native executable directory. Installation does not select or
migrate a database. Changing working directory can select a different default.
Prefer an explicit `--db FILE` on each command, **after the subcommand**.

Future opt-in examples with placeholders you must replace deliberately:

```sh
shazam bootstrap "/path/to/chosen-small-folder" --db "/path/to/new-python.db" --workers 1
python -m shazam match "/path/to/chosen-clip.wav" --db "/path/to/new-python.db"
shazam status --db "/path/to/new-python.db"
```

Choose a writable database location whose parent directory already exists.
`bootstrap` and `add` create/update the selected Python database; `remove`
changes its index entries. Even opening an existing database for matching or
statistics uses SQLite's writable connection and schema initialization, not a
read-only inspector. Databases and output can contain private file paths and
metadata: do not publish them or use personal libraries as test fixtures.

There is **no automatic migration**, relocation, conversion or shared index
between Python, the Rust comparison backend and Olaf. Moving this source does
not move or search for an old root database or any music. Never point legacy
`--db` at a native database or Olaf storage; these are not interchangeable.
Any future native indexing must be a separate, explicitly chosen operation.

## Optional interactive launcher

From the repository root, using the isolated environment:

```sh
legacy/python/.venv/bin/python legacy/python/start.py
```

PowerShell equivalent:

```powershell
.\legacy\python\.venv\Scripts\python.exe .\legacy\python\start.py
```

From the archive directory, use `.venv/bin/python start.py` (PowerShell:
`.\.venv\Scripts\python.exe start.py`). The launcher checks for FFmpeg and then
checks Click, NumPy, SciPy and tqdm. **When actually invoked**, if a dependency
import fails it runs the current interpreter's `pip install -r` using the adjacent
`requirements.txt`. This can install/download packages; it is not an offline or
side-effect-free launcher. Preinstall into the isolated environment as above.

The index and match pickers require Tkinter plus GUI/display support. The menu
uses a fixed database next to `start.py`: now **`legacy/python/shazam.db`** in a
checkout, regardless of working directory. It does not discover an old root
database. There is no launcher `--db` option; use the CLI for explicit selection.
Opening the menu alone does not start indexing; choose an action deliberately.

## Historical limitations and regression suite

The original Python algorithms and module source are retained. In particular:

- Decoding uses only the first **120 seconds**, with a **30-second FFmpeg
  timeout** per file. This is not the complete-track native indexing behavior.
- Identity checks use file size and the first **8 KiB**, not a full-file digest.
- Scanning is extension-based. CLI indexing defaults to four workers; the
  interactive launcher caps its CPU-based default at six. Neither is a stability
  guarantee, and resource use can be substantial.
- Matching uses Python constellation hashes and heuristic confidence labels,
  not the native Olaf retrieval/Rust verification pipeline. Scores are not
  calibrated probabilities; historical results are not new accuracy evidence.

`tests/test_indexing.py` is the **archived regression suite**, moved intact from
the old root tests. Its five tests are historical Python database/indexing tests,
not native release gates. It has not been imported or run for this relocation.

The independent `tests/release/test_legacy_archive.py` in the full repository uses
standard-library AST/TOML/text and synthetic policy checks only. From the
repository root with Python 3.11+, run:

```sh
python -B -m unittest discover -s tests/release -p test_legacy_archive.py -v
```

These checks do not import/launch the legacy app, install dependencies, build a
wheel, run either native engine, or access a database or music library. Static
validation is not an installation, runtime or platform-support guarantee.

## License

The complete original MIT application license, including its copyright and
permission notice, is preserved verbatim in [LICENSE](LICENSE) and explicitly
included by the packaging metadata. This is not a blanket license for separately
distributed native runtimes or third-party dependencies; Olaf's separate
AGPL-3.0-or-later obligations remain outside this Python archive.
