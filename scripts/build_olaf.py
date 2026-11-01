#!/usr/bin/env python3
"""Build the separately licensed Olaf runtime from reviewed, local source only.

No downloads, global installs, prebuilt runtime fallback, audio or index access.
--check-only validates source without requiring or executing a toolchain.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('release_policy', Path(__file__).with_name('release.py'))
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)
ZIG_VERSION = "0.16.0"
TARGETS = {
    "windows-x64": ("x86_64-windows-gnu", "olaf.exe"),
    "windows-x86": ("x86-windows-gnu", "olaf.exe"),
    "linux-x64": ("x86_64-linux-musl", "olaf"),
    "macos-arm64": ("aarch64-macos.11.0.0-none", "olaf"),
    "macos-x64": ("x86_64-macos.11.0.0-none", "olaf"),
}
SOURCE_PREFIXES = ("vendor/olaf/", "vendor/zigzag/", "patches/olaf/")
INTEGRATION_FILES = {"scripts/build_olaf.py", "scripts/release.py", "scripts/check_release_hygiene.py",
                     "tests/release/test_olaf_source.py", "tests/release/test_build_privacy.py", "docs/BUILD_PRIVACY.md"}
REQUIRED_FILES = {
    "vendor/olaf/LICENSE", "vendor/olaf/NOTICES.txt", "vendor/olaf/BUILDING.md",
    "vendor/olaf/build.zig", "vendor/olaf/build.zig.zon",
    "vendor/olaf/src/mdb.c", "vendor/olaf/src/olaf_fp_matcher.c",
    "vendor/olaf/cli/olaf_cli.zig", "vendor/olaf/cli/tui/olaf_tui.zig",
    "vendor/olaf/cli/rest/olaf_rest.zig", "vendor/olaf/cli/ui/olaf_ui.zig",
    "vendor/olaf/tests/olaf_matcher_v3_tests.c",
    "vendor/olaf/tests/olaf_db_concurrency_tests.c",
    "vendor/olaf/tests/olaf_config_tests.c",
    "vendor/olaf/notices/OpenLDAP-LICENSE.txt",
    "vendor/zigzag/build.zig", "vendor/zigzag/build.zig.zon",
    "vendor/zigzag/src/root.zig", "vendor/zigzag/LICENSE", "patches/olaf/series",
} | INTEGRATION_FILES


class BuildError(RuntimeError):
    """A prerequisite, source validation or build failed."""

    def __init__(self, message):
        super().__init__(message.split(':', 1)[0])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_hash(path: Path) -> str:
    # Hash preferred-form text consistently even with Git autocrlf enabled.
    data = path.read_bytes()
    data.decode("utf-8")
    if b"\0" in data:
        raise BuildError(f"Unexpected binary source input: {path.name}")
    return sha256(data.replace(b"\r\n", b"\n"))


def validate_sources(root: Path = ROOT) -> dict:
    """Validate the entire pinned inventory; never execute Zig or use Git/cache."""
    root = root.resolve()
    manifest = root / "vendor/olaf/PROVENANCE.json"
    try:
        provenance = json.loads(manifest.read_text(encoding="utf-8"))
        records = provenance["files"]
        if provenance["schema_version"] != 1 or not isinstance(records, dict):
            raise BuildError("Unsupported Olaf provenance schema")
        if provenance["build"]["targets"] != {name: row[0] for name, row in TARGETS.items()}:
            raise BuildError("Olaf provenance target policy mismatch")
        missing = REQUIRED_FILES - records.keys()
        if missing:
            raise BuildError("Incomplete source inventory: " + ", ".join(sorted(missing)))
        for name, record in records.items():
            rel = PurePosixPath(name)
            if (rel.is_absolute() or ".." in rel.parts or "\\" in name
                    or not (name.startswith(SOURCE_PREFIXES) or name in INTEGRATION_FILES)):
                raise BuildError(f"Unsafe source inventory path: {name}")
            path = root / name
            if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
                raise BuildError(f"Missing or unsafe source file: {name}")
            if source_hash(path) != record["sha256"]:
                raise BuildError(f"Source hash mismatch: {name}; review changes and update provenance")

        # Reject accidentally bundled fixtures/binaries, including unlisted files.
        for prefix in ("vendor/olaf", "vendor/zigzag", "patches/olaf"):
            for path in (root / prefix).rglob("*"):
                if path.is_symlink():
                    raise BuildError(f"Symlink in source distribution: {path.relative_to(root)}")
                if path.is_file():
                    name = path.relative_to(root).as_posix()
                    if name not in records and name != "vendor/olaf/PROVENANCE.json":
                        raise BuildError(f"Unlisted source distribution file: {name}")

        olaf_manifest = (root / "vendor/olaf/build.zig.zon").read_text(encoding="utf-8")
        zigzag_manifest = (root / "vendor/zigzag/build.zig.zon").read_text(encoding="utf-8")
        local = r'\.dependencies\s*=\s*\.\{\s*\.zigzag\s*=\s*\.\{\s*\.path\s*=\s*"../zigzag"\s*,?\s*\}\s*,?\s*\}'
        if not re.search(local, olaf_manifest) or re.search(r"\.(url|hash)\s*=", olaf_manifest):
            raise BuildError("Olaf must depend only on committed ../zigzag source")
        if not re.search(r"\.dependencies\s*=\s*\.\{\s*\}", zigzag_manifest):
            raise BuildError("Zigzag must have no transitive dependencies")
        for name in provenance["olaf"]["dirty_files"]:
            if f"vendor/olaf/{name}" not in records:
                raise BuildError(f"Missing dirty working source: {name}")
        return provenance
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BuildError(f"Cannot validate Olaf source distribution: {exc}") from exc


def find_zig() -> str:
    requested = os.environ.get("ZIG", "zig")
    executable = shutil.which(requested)
    if not executable:
        raise BuildError("Zig 0.16.0 is required: provision it on PATH or set ZIG to its executable. Nothing was downloaded.")
    try:
        result = subprocess.run([executable, "version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError(f"Could not execute installed Zig: {exc}") from exc
    if result.stdout.strip() != ZIG_VERSION:
        raise BuildError(f"Expected Zig {ZIG_VERSION}; installed version rejected")
    return executable


def build_runtime(target: str, out_dir: Path, root: Path = ROOT) -> Path:
    if target not in TARGETS:
        raise BuildError(f"Unsupported target: {target}")
    provenance = validate_sources(root)
    root = root.resolve()
    out_dir = out_dir.resolve()
    runtime = out_dir / "olaf-runtime"
    for protected in (root / "vendor", root / "patches", root / "scripts", root / "tests"):
        if runtime.is_relative_to(protected):
            raise BuildError("Output must not be inside source, patch or test directories")
    if runtime.exists():
        raise BuildError("Refusing to replace existing runtime; choose a fresh --out-dir")
    zig = find_zig()
    triple, executable = TARGETS[target]
    # A fresh build/install prefix and isolated caches prevent prebuilt reuse.
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="olaf-build-", dir=out_dir) as tmp:
        work = Path(tmp)
        prefix = work / "install"
        flags = [f"-Dtarget={triple}", "-Dcpu=baseline", "-Doptimize=ReleaseFast", "-j1"]
        privacy_flags = policy.olaf_privacy_arguments(root, work, Path(zig))
        command = [zig, "build", "install", *flags, *privacy_flags,
                   "--prefix", str(prefix), "--cache-dir", str(work / "cache"),
                   "--global-cache-dir", str(work / "global-cache")]
        try:
            env = policy.clean_build_environment()
            env.update(TMP=str(work), TEMP=str(work), TMPDIR=str(work),
                       ZIG_LOCAL_CACHE_DIR=str(work / 'cache'), ZIG_GLOBAL_CACHE_DIR=str(work / 'global-cache'))
            subprocess.run(command, cwd=root / "vendor/olaf", env=env, check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            if isinstance(exc, subprocess.CalledProcessError):
                policy.report_safe_diagnostics(exc.stderr)
            raise BuildError(f"Olaf source build failed for {target}; diagnostic values withheld") from exc
        binary = prefix / "bin" / executable
        if not binary.is_file() or binary.is_symlink() or binary.stat().st_size == 0:
            raise BuildError(f"Zig did not produce the required fresh binary: bin/{executable}")
        if policy.architecture(binary.read_bytes()) != target:
            raise BuildError("Olaf output architecture mismatch")
        if target in policy.WINDOWS_TARGETS:
            policy.pe_imports(binary.read_bytes())
        policy.check_privacy(executable, binary.read_bytes(), forbidden_roots=(root, work, Path(zig).resolve().parent))

        out_dir.mkdir(parents=True, exist_ok=True)
        # Stage on the output filesystem, then publish the complete directory.
        with tempfile.TemporaryDirectory(prefix=".olaf-package-", dir=out_dir) as package_tmp:
            package = Path(package_tmp) / "olaf-runtime"
            package.mkdir()
            shutil.copy2(binary, package / executable)
            for source, destination in (
                ("vendor/olaf/LICENSE", "OLAF-LICENSE"),
                ("vendor/olaf/NOTICES.txt", "OLAF-NOTICES.txt"),
                ("vendor/olaf/PROVENANCE.json", "PROVENANCE.json"),
                ("vendor/olaf/BUILDING.md", "BUILDING.md"),
                ("vendor/zigzag/LICENSE", "notices/Zigzag-LICENSE.txt"),
            ):
                dest = package / destination
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / source, dest)
            for name in sorted(provenance["files"]):
                if name.startswith("vendor/olaf/notices/"):
                    shutil.copyfile(root / name, package / "notices" / Path(name).name)
            build_info = {
                "target": target, "zig_version": ZIG_VERSION, "zig_target": triple,
                "cpu": "baseline", "optimize": "ReleaseFast", "jobs": 1,
                "executable": executable, "executable_sha256": sha256(binary.read_bytes()),
                "source_provenance_sha256": source_hash(root / "vendor/olaf/PROVENANCE.json"),
                "build_arguments": ["build", "install", *flags],
                "privacy_policy": policy.PRIVACY_POLICY,
                "validation": "Source, architecture and Windows import checks only; this helper does not run the runtime or tests.",
            }
            (package / "BUILD-INFO.json").write_text(json.dumps(build_info, indent=2) + "\n", encoding="utf-8", newline="\n")
            for member in package.rglob('*'):
                if member.is_file():
                    policy.check_privacy(member.relative_to(package).as_posix(), member.read_bytes())
            if runtime.exists():
                raise BuildError(f"Output appeared during build; refusing to overwrite: {runtime}")
            package.rename(runtime)
    return runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--check-only", action="store_true", help="Validate source/dependencies without Zig, compilation or output writes")
    args = parser.parse_args(argv)
    if not args.check_only and (not args.target or args.out_dir is None):
        parser.error("building requires --target TARGET and --out-dir DIRECTORY")
    try:
        if args.check_only:
            provenance = validate_sources()
            print(f"Olaf source/dependency validation passed ({len(provenance['files'])} pinned text files); no compilation or audio tests run.")
        else:
            build_runtime(args.target, args.out_dir)
            print('Built Olaf runtime in requested staging directory')
        return 0
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, (BuildError, policy.ReleaseError)) and len(message) <= 250 and not policy.hygiene.privacy_violations('', message.encode('utf-8')):
            print('error: ' + message, file=sys.stderr)
        else:
            print('error: Olaf build/source gate rejected input; diagnostic values withheld (' + type(exc).__name__ + ')', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
