#!/usr/bin/env python3
"""Staging-only, native release builder. No third-party Python dependencies.

Archive verification is intentionally independent of compilers and of a checkout.
Build/test commands are opt-in; importing this module never starts a build.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import shlex
import stat
import struct
import subprocess
import sys
import tarfile
import tomllib
import urllib.request
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('release_hygiene', Path(__file__).with_name('check_release_hygiene.py'))
hygiene = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hygiene)
PRIVACY_POLICY = 'compiler-paths-and-artifacts-v1'
PROVENANCE = "BUILD-PROVENANCE.json"
TARGETS = ("windows-x64", "linux-x64", "macos-arm64", "macos-x64")
FORBIDDEN_PARTS = {
    ".git", ".env", ".venv", ".claude", ".codex", "__pycache__", "node_modules",
    "benchmarks", "evidence", "diagnostics", "music", "audio", "dataset", "datasets",
    "target", "zig-out", ".zig-cache", "zig-cache", "toolchains", "caches", "credentials",
}
FORBIDDEN_SUFFIXES = {
    ".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".mp4", ".raw", ".pcm",
    ".db", ".sqlite", ".sqlite3", ".mdb", ".pem", ".key", ".pfx", ".pyc",
}
SETUP = """Local Shazam portable experimental distribution

Keep local-shazam and olaf-runtime together. Olaf is a separate executable,
not a linked MIT component; see its AGPL license and all included notices.
Install FFmpeg AND FFprobe separately, from a trusted distribution appropriate
to your OS, and put them on PATH. They are deliberately NOT bundled.
Check: ffmpeg -version; ffprobe -version; local-shazam --help; local-shazam --version.
See https://ffmpeg.org/download.html for upstream information.

Windows builds are unsigned: SmartScreen/reputation warnings are expected.
The import tables recorded in BUILD-PROVENANCE.json identify required DLLs.
Install required Microsoft runtimes from Microsoft, never random DLL sites.
macOS builds are not Developer ID signed or notarized. A toolchain may add an
ad-hoc signature; that is not publisher authentication. Gatekeeper may block use.
Do not disable OS security globally. Verify checksums and provenance before use.
Linux glibc and other shared-library requirements are recorded, not bundled.
Minimum supported Windows/macOS/glibc versions have NOT been established.

Use a writable, dedicated application/data directory, not a system folder.
No automatic indexing or index migration is performed by these build tools.
Do not adopt an existing personal library/index as a test fixture.
These packages have no accuracy, stability or bit-for-bit reproducibility claim.
See docs/BUILDING.md and docs/RELEASING.md in the matching source archives.
"""


class ReleaseError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        # Callers historically include a path/member after a colon. Retain the
        # useful rule, never the untrusted value (including tokens in filenames).
        raise ReleaseError(message.split(':', 1)[0])


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def olaf_source_version(data):
    match = re.search(rb'\.version\s*=\s*"([^"\r\n]+)"', data)
    require(match, "Missing Olaf source version in build.zig.zon")
    return match.group(1).decode("ascii")


def config(root=ROOT):
    return json.loads((root / "release/targets.json").read_text(encoding="utf-8"))


def safe_name(name):
    p = PurePosixPath(name)
    require(name and "\\" not in name and ":" not in name and not p.is_absolute()
            and all(x not in ("", ".", "..") for x in name.split("/")),
            f"Unsafe archive path: {name!r}")
    require(not any(ord(c) < 32 for c in name), f"Control character in path: {name!r}")
    return p


def private_name(name):
    p = safe_name(name)
    lower = name.lower()
    return (bool({x.lower() for x in p.parts} & FORBIDDEN_PARTS)
            or p.suffix.lower() in FORBIDDEN_SUFFIXES
            or any(x in lower for x in ("handoff", "benchmark", "credential", "diagnostic"))
            or p.name.lower().startswith((".env", "id_rsa", "id_ed25519")))


def regular(path):
    require(path.is_file() and not path.is_symlink(), f"Missing/nonregular file: {path}")
    # Reject symlinked parent directories too (including Windows junctions).
    for parent in (path, *path.parents):
        require(not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)(),
                f"Linked input/output path: {parent}")


def staging(out, root=ROOT):
    raw = Path(out)
    if not raw.is_absolute():
        raw = root / raw
    for part in (raw, *raw.parents):
        require(not part.is_symlink() and not getattr(part, "is_junction", lambda: False)(),
                f"Linked staging path: {part}")
    out = raw.resolve()
    root = root.resolve()
    require(any(out.is_relative_to(root / d) and out != root / d for d in ("build", "dist")),
            "--out-dir must be a subdirectory of this checkout's build/ or dist/")
    return out


def report_safe_diagnostics(output):
    """Expose bounded compiler error headers, never raw command/path context."""
    if isinstance(output, bytes):
        output = output.decode('utf-8', 'replace')
    for line in (output or '')[-24000:].splitlines():
        if (len(line) <= 400 and re.match(
                r'^(?:[A-Za-z0-9_.+-]+\.(?:zig|rs|c|h):\d+(?::\d+)?:\s*)?'
                r'(?:fatal )?error(?:\[[A-Z0-9]+\])?:', line)
                and not hygiene.privacy_violations('', line.encode('utf-8'))):
            print(line, file=sys.stderr)


def run(args, *, cwd=ROOT, env=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        report_safe_diagnostics(result.stderr)
        # Compiler output/commands may contain source paths, usernames or tokens.
        raise ReleaseError(f"Build command failed (exit {result.returncode}); output withheld for privacy")
    return result.stdout.strip()


def tracked(root):
    return run(["git", "ls-files", "-z"], cwd=root).split("\0")


def matches(path, patterns):
    # Unlike fnmatch, a single * cannot cross a directory boundary.
    for pattern in patterns:
        expression = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?")
        expression = expression.replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        if re.fullmatch(expression, path):
            return True
    return False


def inventory(root, cfg, names=None):
    """Only reviewed tracked paths; never git archive HEAD or walk the workspace."""
    rules = cfg["source_inventory"]
    groups = {"app": {}, "olaf": {}}
    names = tracked(root) if names is None else names
    for name in sorted(set(names) - {""}):
        allowed = [g for g in groups if matches(name, rules["common"] + rules[g])]
        if not allowed:
            if name.startswith(("rust-app/src/", "vendor/", "patches/olaf/")):
                require(any(name.startswith(p) for p in rules["excluded_vendor_prefixes"]),
                        f"Unreviewed source input (update inventory deliberately): {name}")
            continue
        require(not private_name(name), f"Private/unsafe source input: {name}")
        p = root / name
        regular(p)
        check_privacy(name, p.read_bytes(), source=True)
        if name.startswith("licenses/") or any(token in p.name.lower() for token in ("license", "copying", "notice")):
            content = p.read_bytes()
            require(content.strip(), f"Empty legal input: {name}")
            require(p.suffix.lower() not in (".exe", ".dll", ".so", ".dylib", ".a", ".o", ".zip", ".gz")
                    and "\0" not in content.decode("utf-8"), f"Non-text legal input: {name}")
        if name.startswith("vendor/"):
            require(p.suffix in rules["vendor_extensions"]
                    or p.name.startswith(("LICENSE", "COPYING", "NOTICE", "README"))
                    or p.name in ("Makefile", ".gitattributes", ".zigversion"), f"Unreviewed vendor file type: {name}")
        for group in allowed:
            groups[group][name] = file_hash(p)
    all_names = set(groups["app"]) | set(groups["olaf"])
    for pattern in rules["required"]:
        require(matches_any(all_names, pattern), f"Incomplete source inventory: {pattern}")
    return groups


def matches_any(names, pattern):
    return any(matches(n, [pattern]) for n in names)


def clean_commit(root):
    require(not run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root),
            "Commit reviewed tracked changes before building")
    commit = run(["git", "rev-parse", "HEAD"], cwd=root)
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "Invalid source commit")
    return commit


def check_host(target, cfg):
    t = cfg["targets"][target]
    arch = {"AMD64": "x86_64", "arm64": "aarch64"}.get(platform.machine(), platform.machine())
    require(platform.system() == t["os"] and arch == t["arch"],
            f"Native {t['os']}/{t['arch']} required; refusing to relabel a cross-build")


def download(url, expected, destination):
    require(url.startswith(("https://static.rust-lang.org/", "https://ziglang.org/download/")),
            "Only official tool distribution URLs are allowed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        require(response.url.startswith(url.rsplit("/", 1)[0] + "/"), "Unexpected download redirect")
        with destination.open("xb") as output:
            shutil.copyfileobj(response, output)
    require(file_hash(destination) == expected, f"Tool checksum mismatch: {destination.name}")


def extract_tool(archive, destination):
    # Extract only regular files and directories, with no links or traversal.
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                name = item.filename.rstrip("/")
                safe_name(name)
                mode = item.external_attr >> 16
                require(not stat.S_ISLNK(mode), "Linked tool archive entry")
                if item.is_dir():
                    continue
                dest = destination / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as f:
                    f.write(z.read(item))
    else:
        with tarfile.open(archive) as t:
            for item in t:
                safe_name(item.name.rstrip("/"))
                require(item.isfile() or item.isdir(), "Nonregular tool archive entry")
                if item.isdir():
                    continue
                dest = destination / item.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as f:
                    shutil.copyfileobj(t.extractfile(item), f)
                dest.chmod(item.mode & 0o755)


def clean_build_environment(inherited=None):
    env = dict(os.environ if inherited is None else inherited)
    prefixes = ('CARGO', 'RUST', 'ZIG', 'CC', 'CXX', 'CFLAGS', 'CPPFLAGS',
                'LDFLAGS', 'AR', 'RANLIB', 'HOST_', 'TARGET_', 'CMAKE', 'GIT_',
                'SQLITE', 'LIBSQLITE3', 'BINDGEN', 'LLVM', 'CLANG', 'SCCACHE',
                'DISTCC', 'CRATE_CC', 'PKG_CONFIG', 'DYLD_', 'LD_')
    for key in list(env):
        if key.upper().startswith(prefixes) or key.upper() in {
            'CL', '_CL_', 'LINK', '_LINK_', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH',
            'CPATH', 'LIBRARY_PATH', 'COMPILER_PATH', 'GCC_EXEC_PREFIX', 'MAKEFLAGS',
            'MFLAGS', 'RUSTDOCFLAGS', 'DEVELOPER_DIR', 'DESTDIR', 'MACOSX_DEPLOYMENT_TARGET',
            'LD', 'AS', 'ASFLAGS', 'RC', 'RCFLAGS', 'NM', 'STRIP', 'OBJC', 'OBJCXX', 'OBJCFLAGS',
        }:
            env.pop(key)
    return env


def build_env(out):
    env = clean_build_environment()
    for key, rel in {
        "CARGO_HOME": "cargo-home", "RUSTUP_HOME": "rustup-home",
        "CARGO_TARGET_DIR": "cargo-target", "ZIG_GLOBAL_CACHE_DIR": "zig-global-cache",
        "ZIG_LOCAL_CACHE_DIR": "zig-local-cache", "TMPDIR": "tmp", "TMP": "tmp", "TEMP": "tmp",
    }.items():
        path = out / "work" / rel
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(CARGO_BUILD_JOBS="1", ZIG_BUILD_JOBS="1", CMAKE_BUILD_PARALLEL_LEVEL="1",
               RUSTUP_DIST_SERVER="https://static.rust-lang.org",
               RUSTUP_UPDATE_ROOT="https://static.rust-lang.org/rustup")
    return env


def path_variants(path):
    """Rust prefix replacement is textual, not a filesystem comparison."""
    value = str(path)
    require(not any(c in value for c in '\x00\x1f\r\n='), 'Unsupported build path character')
    variants = {value, value.replace('\\', '/')}
    if re.match(r'^(?:[A-Za-z]:|\\\\|//)', value):
        plain = value.replace('\\', '/')
        if plain.startswith('//?/UNC/'):
            plain = '//' + plain[8:]
        elif plain.startswith('//?/'):
            plain = plain[4:]
        variants.update((plain, plain.replace('/', '\\')))
        if plain.startswith('//'):
            variants.update(('//?/UNC/' + plain[2:], '\\\\?\\' + 'UNC\\' + plain[2:].replace('/', '\\')))
        if re.match(r'^[A-Za-z]:', plain):
            for drive in (plain[0].lower(), plain[0].upper()):
                variant = drive + plain[1:]
                variants.update((variant, variant.replace('/', '\\'),
                                 '\\\\?\\' + variant.replace('/', '\\'), '//?/' + variant))
    return variants


def privacy_maps(out, snapshot, env, root=ROOT):
    pairs = {}
    def add(path, label):
        if not path:
            return
        for spelling in path_variants(path):
            pairs[spelling.rstrip('/\\')] = label
        # realpath handles e.g. macOS temporary-directory aliases; Windows
        # extended/slash spellings above are needed even when resolve omits them.
        if Path(path).is_absolute():
            for spelling in path_variants(Path(path).resolve()):
                pairs[spelling.rstrip('/\\')] = label
    # Never map a filesystem root: retain useful logical filenames and avoid
    # converting unrelated system/runtime paths into misleading source paths.
    for key in ('HOME', 'USERPROFILE', 'TMP', 'TEMP', 'TMPDIR', 'LOCALAPPDATA',
                'APPDATA', 'RUNNER_TEMP', 'RUNNER_WORKSPACE', 'GITHUB_WORKSPACE',
                'CARGO_HOME', 'RUSTUP_HOME', 'XDG_CACHE_HOME', 'SDKROOT',
                'VCToolsInstallDir', 'WindowsSdkDir'):
        add(os.environ.get(key), '/build/host')
        add(env.get(key), '/build/host')
    for parent in reversed(root.resolve().parents):
        if parent != Path(parent.anchor):
            add(parent, '/build/host')
    add(root, '/source/checkout')
    add(out, '/build/stage')
    add(out / 'work', '/build/work')
    add(out / 'work/regression-source', '/source')
    for key, label in {
        'CARGO_HOME': '/build/cargo', 'CARGO_TARGET_DIR': '/build/target',
        'RUSTUP_HOME': '/toolchain/rust', 'ZIG_GLOBAL_CACHE_DIR': '/build/zig-global',
        'ZIG_LOCAL_CACHE_DIR': '/build/zig-local', 'TMP': '/build/tmp',
        'TEMP': '/build/tmp', 'TMPDIR': '/build/tmp',
    }.items():
        add(env.get(key), label)
    add(out / 'work/tools', '/toolchain')
    add(snapshot, '/source')
    add(snapshot / 'rust-app', '/source/rust-app')
    # Last match wins in rustc/Clang: enclosing paths MUST precede children.
    return sorted(((p, v) for p, v in pairs.items() if p and p not in ('/', '\\')
                   and not re.fullmatch(r'[A-Za-z]:', p)), key=lambda pair: (len(pair[0]), pair[0]))


def apply_compiler_privacy(env, out, snapshot, target, root=ROOT):
    maps = privacy_maps(out, snapshot, env, root)
    flags = [f'--remap-path-prefix={old}={new}' for old, new in maps]
    flags += ['-Cdebuginfo=0', '-Cstrip=debuginfo']
    windows = target == 'windows-x64'
    if windows:
        flags += ['-Clink-arg=/DEBUG:NONE', '-Clink-arg=/INCREMENTAL:NO',
                  '-Clink-arg=/PDBALTPATH:local-shazam.pdb']
    # Windows command lines are limited to 32767 UTF-16 code units. The complete
    # maps can exceed that, especially after native macro/debug duplication.
    # rustc response files contain one argument per line, without shell quoting.
    rust_args = ['@' + str(privacy_response(out, 'rust', '\n'.join(flags) + '\n'))] if windows else flags
    env['CARGO_ENCODED_RUSTFLAGS'] = '\x1f'.join(rust_args)
    env['CARGO_ENCODED_RUSTDOCFLAGS'] = '\x1f'.join(rust_args)
    # cc 1.10.0 (Cargo.lock) supports shell-escaped flags on all hosts.
    # Use clang-cl for bundled SQLite on MSVC: cl.exe has no supported equivalent
    # of Clang's file/macro/debug prefix maps. Missing clang-cl fails closed.
    compiler = 'clang-cl' if windows else ('clang' if target.startswith('macos') else 'cc')
    cxx = 'clang-cl' if windows else ('clang++' if target.startswith('macos') else 'c++')
    for key, tool in (('CC', compiler), ('CXX', cxx)):
        found = shutil.which(tool, path=env.get('PATH'))
        require(found, 'Required privacy-capable native C/C++ compiler unavailable')
        env[key] = found
    native = [f'-{kind}-prefix-map={old}={new}' for old, new in maps
              for kind in ('ffile', 'fmacro', 'fdebug')]
    native += ['-g0']
    if windows:
        native = ['/clang:' + flag for flag in native]
    env['CC_SHELL_ESCAPED_FLAGS'] = '1'
    response = subprocess.list2cmdline(native) if windows else shlex.join(native)
    native_args = ['@' + str(privacy_response(out, 'native', response + '\n'))]
    env['CFLAGS'] = env['CXXFLAGS'] = shlex.join(native_args)
    env['CARGO_PROFILE_RELEASE_DEBUG'] = '0'
    env['CARGO_PROFILE_RELEASE_STRIP'] = 'debuginfo'
    return env


def privacy_response(out, kind, content):
    path = out / 'work/privacy-flags' / (kind + '.rsp')
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode('utf-8')
    if path.exists():
        regular(path)
        require(path.read_bytes() == data, 'Compiler privacy response changed; fresh build required')
    else:
        with path.open('xb') as stream:
            stream.write(data)
    return path


def check_privacy(name, data, *, source=False, forbidden_roots=()):
    require(not hygiene.privacy_violations('', name.encode('utf-8')), 'Privacy gate: unsafe member name')
    require(not hygiene.privacy_violations(name, data, source=source), 'Privacy gate: private content (values withheld)')
    for root in forbidden_roots:
        for spelling in path_variants(root):
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                require(spelling.encode(encoding) not in data, 'Privacy gate: build root in artifact (value withheld)')
    if source:
        findings = hygiene.Findings()
        hygiene.check_bytes(name, data, findings)
        require(not findings.count, 'Privacy gate: source hygiene failed')


def olaf_privacy_arguments(root, work, zig):
    env = {'ZIG_GLOBAL_CACHE_DIR': str(work / 'global-cache'),
           'ZIG_LOCAL_CACHE_DIR': str(work / 'cache')}
    maps = dict(privacy_maps(work, root, env, root))
    for spelling in path_variants(zig.resolve().parent):
        maps[spelling] = '/toolchain/zig'
    flags = [f'-{kind}-prefix-map={old}={new}' for old, new in
             sorted(maps.items(), key=lambda row: (len(row[0]), row[0]))
             for kind in ('ffile', 'fmacro', 'fdebug')]
    flags += ['-g0']
    # Zig's Clang driver uses GNU response tokenization (not clang-cl mode),
    # including on Windows. Do not repeat thousands of flags for every C file
    # in the Zig compiler command; that can exceed the OS command-line limit.
    response = privacy_response(work, 'olaf-native', shlex.join(flags) + '\n')
    return ['-Drelease-privacy=true', '-Dprivacy-cflags=' + str(response)]


def source_snapshot(root, out, source):
    """Compile only the reviewed inventory, never untracked workspace inputs."""
    snapshot = out / "work/build-source"
    for name in sorted(set(source["app"]) | set(source["olaf"])):
        copy_file(root / name, snapshot / name)
    check_snapshot(snapshot, source)
    return snapshot


def check_snapshot(snapshot, source):
    for files in source.values():
        for name, sha in files.items():
            path = snapshot / name
            regular(path)
            require(file_hash(path) == sha, f"Build snapshot changed: {name}")
    # Cargo's parent-directory configuration must not import local developer
    # overrides into a release, even with a fresh CARGO_HOME.
    check_cargo_configuration(snapshot)


def check_cargo_configuration(cwd, env=None):
    for parent in (cwd, *cwd.parents):
        for filename in ("config", "config.toml"):
            require(not os.path.lexists(parent / ".cargo" / filename),
                    "Unreviewed ancestor Cargo configuration (path withheld)")
    if env:
        for filename in ('config', 'config.toml'):
            require(not os.path.lexists(Path(env['CARGO_HOME']) / filename),
                    'Unreviewed Cargo home configuration (path withheld)')


def provision(target, out, cfg, env):
    t = cfg["targets"][target]
    windows = t["os"] == "Windows"
    tools = out / "work/tools"
    init = tools / ("rustup-init.exe" if windows else "rustup-init")
    download(f"https://static.rust-lang.org/rustup/archive/{cfg['rustup']}/{t['rust']}/{init.name}",
             t["rustup_sha256"], init)
    init.chmod(0o755)
    run([init, "-y", "--no-modify-path", "--default-toolchain", "none", "--profile", "minimal"], env=env)
    rustup = Path(env["CARGO_HOME"]) / "bin" / ("rustup.exe" if windows else "rustup")
    run([rustup, "toolchain", "install", cfg["rust"], "--profile", "minimal", "--no-self-update",
         "--target", t["rust"]], env=env)
    extension = ".zip" if windows else ".tar.xz"
    base = f"zig-{t['zig_platform']}-{cfg['zig']}"
    archive = tools / (base + extension)
    download(f"https://ziglang.org/download/{cfg['zig']}/{archive.name}", t["zig_sha256"], archive)
    extract_tool(archive, tools)
    zig = tools / base / ("zig.exe" if windows else "zig")
    env["PATH"] = str(zig.parent) + os.pathsep + str(rustup.parent) + os.pathsep + env.get("PATH", "")
    env["ZIG"] = str(zig)
    env["RUSTUP_TOOLCHAIN"] = cfg["rust"]
    require(run([zig, "version"], env=env) == cfg["zig"], "Wrong Zig compiler")
    return rustup, zig


def architecture(data):
    try:
        if data[:2] == b"MZ":
            pe = struct.unpack_from("<I", data, 60)[0]
            require(data[pe:pe + 4] == b"PE\0\0", "Invalid PE signature")
            machine = struct.unpack_from("<H", data, pe + 4)[0]
            return {0x8664: "windows-x64"}.get(machine, "unsupported-pe")
        if data[:4] == b"\x7fELF":
            require(data[4:6] == b"\x02\x01", "Expected little-endian ELF64")
            return {62: "linux-x64"}.get(struct.unpack_from("<H", data, 18)[0], "unsupported-elf")
        if data[:4] == b"\xcf\xfa\xed\xfe":
            return {0x01000007: "macos-x64", 0x0100000C: "macos-arm64"}.get(
                struct.unpack_from("<I", data, 4)[0], "unsupported-mach-o")
    except (struct.error, IndexError) as exc:
        raise ReleaseError("Truncated executable header") from exc
    raise ReleaseError("Unsupported executable format (fat/cross-target artifacts are not accepted)")


def pe_imports(data):
    """Read normal AND delay imports without loading or executing the PE."""
    require(architecture(data) == "windows-x64", "Expected PE x64")
    try:
        pe = struct.unpack_from("<I", data, 60)[0]
        count, opt_size = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
        opt = pe + 24
        require(struct.unpack_from("<H", data, opt)[0] == 0x20B and opt_size >= 240, "Expected PE32+")
        sections = [struct.unpack_from("<IIII", data, opt + opt_size + i * 40 + 8) for i in range(count)]

        def offset(rva):
            for size, address, raw_size, raw in sections:
                if address <= rva < address + max(size, raw_size):
                    require(rva - address < raw_size, "Import outside file-backed section")
                    return raw + rva - address
            raise ReleaseError("Unmapped PE import RVA")

        imports = set()
        for index, width, name_offset in ((1, 20, 12), (13, 32, 4)):
            rva, size = struct.unpack_from("<II", data, opt + 112 + 8 * index)
            if not rva:
                continue
            pos = offset(rva)
            require(size >= width and pos + size <= len(data), "Truncated PE import directory")
            terminated = False
            for cursor in range(pos, pos + size - width + 1, width):
                entry = data[cursor:cursor + width]
                if not any(entry):
                    terminated = True
                    break
                if index == 13:
                    require(struct.unpack_from("<I", entry)[0] == 1, "Unsupported VA-based delay imports")
                name_rva = struct.unpack_from("<I", entry, name_offset)[0]
                start = offset(name_rva)
                end = data.index(b"\0", start, min(start + 512, len(data)))
                name = data[start:end].decode("ascii")
                require(re.fullmatch(r"[A-Za-z0-9_.-]+\.dll", name, re.I), "Invalid DLL import name")
                imports.add(name.lower())
            require(terminated, "Unterminated PE import directory")
        return sorted(imports)
    except (struct.error, ValueError, UnicodeError) as exc:
        raise ReleaseError("Malformed PE import table") from exc


def inspect_binary(path, target):
    data = path.read_bytes()
    check_privacy(path.name, data)
    require(architecture(data) == target, f"Architecture mismatch: {path.name}")
    result = {"architecture": target, "sha256": digest(data)}
    if target == "windows-x64":
        result["imports_and_delay_imports"] = pe_imports(data)
        result["unresolved_requirements"] = "DLLs must be provided by Windows or official runtime installers; availability not proven"
    else:
        require(path.stat().st_mode & 0o111, f"Not executable: {path}")
        args = ["readelf", "-d", "-V", path] if target.startswith("linux") else ["otool", "-L", path]
        result["dynamic_inspection"] = run(args).replace(str(path), "$ARTIFACT")
        if target.startswith("macos"):
            result["load_commands"] = run(["otool", "-l", path]).replace(str(path), "$ARTIFACT")
        result["unresolved_requirements"] = "Reported shared libraries/loader and OS versions are not bundled; minimum supported OS/glibc unverified"
    return result


def runtime_files(directory, target):
    executable = "olaf.exe" if target == "windows-x64" else "olaf"
    require(directory.is_dir(), "Provider did not create olaf-runtime/")
    files = {}
    for p in sorted(directory.rglob("*")):
        require(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)(), "Linked runtime entry")
        if p.is_dir():
            continue
        regular(p)
        name = p.relative_to(directory).as_posix()
        safe_name(name)
        require(not private_name(name), f"Unsafe runtime entry: {name}")
        require(name == executable or p.suffix.lower() in (".md", ".txt", ".json")
                or (not p.suffix and p.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "OLAF-LICENSE"))),
                f"Unexpected runtime dependency/file: {name}")
        files[name] = p
    check_runtime_metadata({n: p.read_bytes() for n, p in files.items()}, executable)
    return files


def check_runtime_metadata(files, executable):
    require(executable in files, "Missing separate Olaf executable")
    for name in files:
        p = safe_name(name)
        require(not private_name(name), f"Unsafe runtime entry: {name}")
        require(name == executable or p.suffix.lower() in (".md", ".txt", ".json")
                or (not p.suffix and p.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "OLAF-LICENSE"))),
                f"Unexpected runtime dependency/file: {name}")
        if name != executable:
            text = files[name].decode("utf-8")
            require("\0" not in text, f"Binary data in runtime metadata: {name}")
    for token in ("license", "notice", "provenance"):
        candidates = [n for n in files if token in n.lower() and files[n].strip()]
        require(candidates, f"Missing runtime {token}")
        if token == "provenance":
            require(any(n.endswith(".json") and isinstance(json.loads(files[n]), dict)
                        and json.loads(files[n]) for n in candidates), "Missing structured runtime provenance")


def copy_file(src, dst, executable=False):
    regular(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("xb") as out, src.open("rb") as inp:
        shutil.copyfileobj(inp, out)
    dst.chmod(0o755 if executable else 0o644)


def tree_records(directory):
    result = {}
    for p in sorted(directory.rglob("*")):
        if p.is_dir():
            require(not p.is_symlink(), "Linked payload directory")
            continue
        regular(p)
        name = p.relative_to(directory).as_posix()
        check_privacy(name, p.read_bytes())
        require(not private_name(name), f"Unsafe payload: {name}")
        mode = 0o755 if p.name in ("local-shazam", "olaf", "local-shazam.exe", "olaf.exe") else 0o644
        if os.name != "nt" and mode == 0o755:
            require(p.stat().st_mode & 0o111, f"Staged executable lost execute permission: {name}")
        result[name] = {"sha256": file_hash(p), "mode": mode}
    return result


def build(target, out, root=ROOT):
    cfg = config(root)
    check_host(target, cfg)
    source = inventory(root, cfg)
    commit = clean_commit(root)
    require(not out.exists(), "Build output already exists; use a fresh staging subdirectory (no destructive cleanup)")
    out.mkdir(parents=True)
    env = build_env(out)
    run([sys.executable, root / "scripts/check_release_hygiene.py", "--root", root], cwd=root)
    snapshot = source_snapshot(root, out, source)
    rustup, zig = provision(target, out, cfg, env)
    apply_compiler_privacy(env, out, snapshot, target, root)
    check_cargo_configuration(snapshot, env)
    rust = [rustup, "run", cfg["rust"]]
    compiler = run([*rust, "rustc", "-vV"], env=env)
    require(f"release: {cfg['rust']}" in compiler, "Wrong Rust compiler")
    # Rustup validates official distribution component hashes. Cargo validates
    # registry checksums and cannot rewrite the committed dependency resolution.
    cargo = [*rust, "cargo"]
    manifest = snapshot / "rust-app/Cargo.toml"
    metadata = json.loads(run([*cargo, "metadata", "--locked", "--format-version", "1",
                               "--manifest-path", manifest], env=env, cwd=snapshot))
    pinned = tuple(int(x) for x in cfg["rust"].split("."))
    for dependency in metadata["packages"]:
        msrv = dependency.get("rust_version")
        if msrv:
            require(tuple(int(x) for x in msrv.split(".")) <= pinned,
                    f"Rust pin below declared MSRV of {dependency['name']}: {msrv}")
    run([*cargo, "build", "--locked", "--release", "-j", "1", "--manifest-path", manifest,
         "--target", cfg["targets"][target]["rust"]], env=env, cwd=snapshot)
    provider = snapshot / "build/provider"
    run([sys.executable, snapshot / "scripts/build_olaf.py", "--target", target, "--out-dir", provider],
        env=env, cwd=snapshot)
    runtime = runtime_files(provider / "olaf-runtime", target)
    exe = ".exe" if target == "windows-x64" else ""
    app = Path(env["CARGO_TARGET_DIR"]) / cfg["targets"][target]["rust"] / "release" / ("local-shazam" + exe)
    inspections = {"app": inspect_binary(app, target), "olaf": inspect_binary(runtime["olaf" + exe], target)}
    for binary in (app, runtime['olaf' + exe]):
        check_privacy(binary.name, binary.read_bytes(), forbidden_roots=[old for old, _ in privacy_maps(out, snapshot, env, root)])
    check_snapshot(snapshot, source)
    require(source == inventory(root, cfg) and commit == clean_commit(root), "Sources changed during build")
    payload = out / "payload"
    copy_file(app, payload / app.name, True)
    for name, path in runtime.items():
        copy_file(path, payload / "olaf-runtime" / name, name == "olaf" + exe)
    for name in source["app"]:
        if name in ("LICENSE", "THIRD_PARTY_NOTICES.md") or name.startswith("licenses/"):
            copy_file(root / name, payload / name)
    (payload / "SETUP.txt").write_text(SETUP, encoding="utf-8", newline="\n")
    provenance = {
        "schema": 1, "commit": commit, "target": target, "rust_target": cfg["targets"][target]["rust"],
        "source_inventory": source, "source_inventory_sha256": digest(encoded(source)),
        "toolchains": {"rustc": compiler, "cargo": run([*cargo, "--version"], env=env),
                       "zig": run([zig, "version"], env=env), "python": platform.python_version(),
                       "rustup": cfg["rustup"], "downloads": cfg["targets"][target]},
        "olaf_source_version": olaf_source_version((snapshot / "vendor/olaf/build.zig.zon").read_bytes()),
        "build": {"cargo_locked": True, "jobs": 1, "native": True, "profile": "release",
                  "privacy_policy": PRIVACY_POLICY,
                  "runtime_provider": "python scripts/build_olaf.py --target TARGET --out-dir DIRECTORY"},
        "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "binary_inspections": inspections, "payload": tree_records(payload),
        "gates": {"dataset_free_tests": "not-run"}, "support_status": "unverified",
        "distribution": {"publisher_signed": False, "notarized": False, "minimum_os": "unverified",
                         "bit_for_bit_reproducibility": "not verified", "ffmpeg_ffprobe": "external; not bundled"},
    }
    (out / "build-manifest.json").write_bytes(encoded(provenance))
    (out / "tool-paths.json").write_bytes(encoded({"rustup": str(rustup), "zig": str(zig)}))
    print(f"Staged {target}; release tests and packaging still required")


def read_manifest(out):
    regular(out / "build-manifest.json")
    return json.loads((out / "build-manifest.json").read_bytes())


def check_stage(out, target, root):
    p = read_manifest(out)
    require(p["target"] == target, "Staging target mismatch")
    require(p["source_inventory"] == inventory(root, config(root)), "Source/runtime correspondence changed")
    require(p["commit"] == clean_commit(root), "Commit changed since build")
    require(p["payload"] == tree_records(out / "payload"), "Staged payload changed since build")
    return p


def test_build(target, out, root=ROOT):
    cfg = config(root)
    check_host(target, cfg)
    p = check_stage(out, target, root)
    snapshot = out / "work/build-source"
    check_snapshot(snapshot, p["source_inventory"])
    paths = json.loads((out / "tool-paths.json").read_bytes())
    for path in paths.values():
        require(Path(path).resolve().is_relative_to(out / "work"), "External tool path")
        regular(Path(path))
    env = build_env(out)
    env["PATH"] = str(Path(paths["zig"]).parent) + os.pathsep + env.get("PATH", "")
    env["RUSTUP_TOOLCHAIN"] = cfg["rust"]
    apply_compiler_privacy(env, out, snapshot, target, root)
    home = out / "work/test-home"
    home.mkdir(exist_ok=True)
    env.update(HOME=str(home), USERPROFILE=str(home), XDG_CONFIG_HOME=str(home / "config"),
               XDG_CACHE_HOME=str(home / "cache"))
    check_cargo_configuration(home, env)
    cargo = [paths["rustup"], "run", cfg["rust"], "cargo", "test", "--locked", "--release", "-j", "1",
             "--manifest-path", snapshot / "rust-app/Cargo.toml", "--target", cfg["targets"][target]["rust"]]
    completed = []
    for kind, names in cfg["rust_tests"].items():
        for name in names:
            selection = ["--lib"] if kind == "lib" else ["--bin", "local-shazam"]
            output = run([*cargo, *selection, name, "--", "--exact", "--test-threads=1"], env=env, cwd=home)
            require("1 passed; 0 failed" in output, f"Expected one actual Rust test: {name}")
            completed.append(name)
    # Copy only reviewed corresponding source; regression builds cannot write into vendor/.
    regression = out / "work/regression-source"
    require(not regression.exists(), "Use a new build to rerun gates")
    for name in p["source_inventory"]["olaf"]:
        copy_file(snapshot / name, regression / name)
    for step in cfg["olaf_regressions"]:
        require(step in ("test-matcher-v3", "test-db-safety", "test-config-safety"), "Unreviewed Zig step")
        privacy_args = olaf_privacy_arguments(regression, out / 'work', Path(paths['zig']))
        run([paths["zig"], "build", step, "-j1", "-Doptimize=ReleaseSafe", *privacy_args,
             "--cache-dir", out / "work/regression-cache", "--global-cache-dir", env["ZIG_GLOBAL_CACHE_DIR"]],
            cwd=regression / "vendor/olaf", env=env)
        completed.append(step)
    exe = ".exe" if target == "windows-x64" else ""
    app_version = tomllib.loads((snapshot / "rust-app/Cargo.toml").read_text(encoding="utf-8-sig"))["package"]["version"]
    for name, args in (("local-shazam" + exe, ["--help"]), ("local-shazam" + exe, ["--version"]),
                       ("olaf-runtime/olaf" + exe, ["--help"])):
        output = run([out / "payload" / name, *args], cwd=home, env=env)
        require(output, f"Empty CLI output: {name} {args}")
        if args == ["--version"]:
            require(output == f"local-shazam {app_version}", "CLI version does not match compiled Cargo manifest")
        completed.append(name + " " + args[0])
    p = check_stage(out, target, root)
    check_snapshot(snapshot, p["source_inventory"])
    p["gates"] = {"dataset_free_tests": "passed", "completed": completed}
    # This records only this native gate run, not general compatibility/accuracy.
    p["support_status"] = "native gates passed; minimum OS and broader compatibility unverified"
    (out / "build-manifest.json").write_bytes(encoded(p))
    print("Dataset-free release gates passed")


def write_archive(path, entries):
    """entries: relative path -> (bytes, Unix mode); normalized order/metadata."""
    require(not path.exists(), f"Refusing to replace archive: {path}")
    for name, (data, _) in entries.items():
        safe_name(name)
        check_privacy(name, data, source=path.name.endswith('-source.tar.gz'))
    if path.suffix == ".zip":
        with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for name, (data, mode) in sorted(entries.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
    else:
        with path.open("xb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for name, (data, mode) in sorted(entries.items()):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(data), mode, 0
                    tar.addfile(info, io.BytesIO(data))


def read_archive(path):
    entries = {}
    folded = set()

    def add(name, data, mode):
        safe_name(name)
        check_privacy(name, data, source=path.name.endswith('-source.tar.gz'))
        require(not private_name(name), f"Private archive entry: {name}")
        require(name.casefold() not in folded, f"Duplicate/case-colliding archive path: {name}")
        require(mode in (0o644, 0o755), f"Unexpected archive mode: {name}")
        folded.add(name.casefold())
        entries[name] = (data, mode)

    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            require(not z.comment, 'Unsafe ZIP archive comment')
            raw = path.read_bytes()
            cursor = 0
            for info in z.infolist():
                require(not info.is_dir() and stat.S_ISREG(info.external_attr >> 16), "Nonregular ZIP entry")
                require(not info.comment and not info.extra, 'Unsafe ZIP member metadata')
                require(info.date_time == (1980, 1, 1, 0, 0, 0) and info.create_system == 3
                        and info.internal_attr == 0 and info.flag_bits in (0, 0x800)
                        and info.compress_type == zipfile.ZIP_DEFLATED, 'Noncanonical ZIP metadata')
                # zipfile exposes central metadata only. Inspect local headers too:
                # a local-only extra field can leak even when the central one is empty.
                require(info.header_offset == cursor, 'Unsafe ZIP layout')
                header = struct.unpack_from('<4s5H3I2H', raw, cursor)
                sig, version, flags, method, time, date, crc, compressed, size, nlen, extra = header
                name = info.filename.encode('utf-8' if flags & 0x800 else 'ascii')
                require(sig == b'PK\x03\x04' and version == 20 and flags == info.flag_bits
                        and method == 8 and time == 0 and date == 33 and crc == info.CRC
                        and compressed == info.compress_size and size == info.file_size
                        and extra == 0 and raw[cursor + 30:cursor + 30 + nlen] == name,
                        'Unsafe ZIP local metadata')
                cursor += 30 + nlen + compressed
                compressed_data = raw[cursor - compressed:cursor]
                inflater = zlib.decompressobj(-15)
                inflater.decompress(compressed_data)
                require(inflater.eof and not inflater.unused_data, 'Unsafe ZIP compressed member trailer')
                add(info.filename, z.read(info), stat.S_IMODE(info.external_attr >> 16))
            require(cursor == z.start_dir, 'Unsafe ZIP directory layout')
            for info in z.infolist():
                require(raw[cursor:cursor + 4] == b'PK\x01\x02', 'Unsafe ZIP central metadata')
                nlen, extra, comment = struct.unpack_from('<3H', raw, cursor + 28)
                name = info.filename.encode('utf-8' if info.flag_bits & 0x800 else 'ascii')
                require(extra == comment == 0 and raw[cursor + 46:cursor + 46 + nlen] == name,
                        'Unsafe ZIP central metadata')
                canonical_header = struct.pack('<4s6H3I5H2I', b'PK\x01\x02', (3 << 8) | 20, 20,
                    info.flag_bits, 8, 0, 33, info.CRC, info.compress_size, info.file_size,
                    len(name), 0, 0, 0, 0, (stat.S_IFREG | stat.S_IMODE(info.external_attr >> 16)) << 16,
                    info.header_offset)
                require(raw[cursor:cursor + 46] == canonical_header, 'Noncanonical ZIP central metadata')
                cursor += 46 + nlen
            end = struct.unpack_from('<4s4H2IH', raw, cursor)
            require(end == (b'PK\x05\x06', 0, 0, len(entries), len(entries), cursor - z.start_dir, z.start_dir, 0)
                    and cursor + 22 == len(raw), 'Unsafe ZIP trailing metadata')
    else:
        raw = path.read_bytes()
        require(raw[:10] == b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff', 'Unsafe gzip header metadata')
        decompressor = zlib.decompressobj(31)
        unpacked = decompressor.decompress(raw) + decompressor.flush()
        require(decompressor.eof and not decompressor.unused_data, 'Unsafe gzip trailing data')
        with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as tar:
            for info in tar:
                require(info.isfile() and not info.linkname, "Nonregular tar entry")
                require(info.uid == info.gid == info.mtime == 0 and not info.uname and not info.gname
                        and set(info.pax_headers) <= {'path'}, 'Unsafe tar owner/PAX metadata')
                add(info.name, tar.extractfile(info).read(), info.mode)
        # Rebuild only metadata, never executables. Byte equality catches hidden
        # global/duplicate PAX headers, overridden owner fields, padding and links.
        canonical = io.BytesIO()
        with tarfile.open(fileobj=canonical, mode='w', format=tarfile.PAX_FORMAT) as tar:
            for name, (data, mode) in sorted(entries.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), mode, 0
                tar.addfile(info, io.BytesIO(data))
        require(unpacked == canonical.getvalue(), 'Noncanonical tar metadata or layout')
    return entries


def package(target, out, root=ROOT):
    p = check_stage(out, target, root)
    require(p["gates"]["dataset_free_tests"] == "passed", "Dataset-free native gates have not passed")
    dist = out / "dist"
    require(not dist.exists(), "Distribution already exists; use a fresh staging directory")
    dist.mkdir()
    common = {PROVENANCE: (encoded(p), 0o644)}
    binary = {name: ((out / "payload" / name).read_bytes(), row["mode"]) for name, row in p["payload"].items()}
    stem = f"local-shazam-{p['commit'][:12]}-{target}"
    extension = ".zip" if target == "windows-x64" else ".tar.gz"
    write_archive(dist / (stem + extension), binary | common)
    for group in ("app", "olaf"):
        files = {name: ((root / name).read_bytes(), 0o644) for name in p["source_inventory"][group]}
        write_archive(dist / f"{stem}-{group}-source.tar.gz", files | common)
    sums = "".join(f"{file_hash(path)}  {path.name}\n" for path in sorted(dist.iterdir()))
    (dist / "SHA256SUMS").write_text(sums, encoding="ascii", newline="\n")
    verify(dist)
    print('Verified staged distribution')


def verify(out):
    # Works on a downloaded artifact directory too; no external tools or execution.
    dist = out / "dist" if (out / "dist").is_dir() else out
    regular(dist / "SHA256SUMS")
    expected = {}
    for line in (dist / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        require(match, "Malformed checksum line")
        sha, name = match.groups()
        require(name not in expected, "Duplicate checksum entry")
        expected[name] = sha
    require(len(expected) == 3, "Exactly one binary and both corresponding source archives are required")
    actual = {p.name for p in dist.iterdir()}
    require(actual == set(expected) | {"SHA256SUMS"}, "Unchecksummed or missing distribution files")
    archives = {}
    for name, sha in expected.items():
        path = dist / name
        regular(path)
        require(file_hash(path) == sha, f"Checksum mismatch: {name}")
        require(name.endswith((".tar.gz", ".zip")), "Unexpected distributable type")
        archives[name] = read_archive(path)
    manifests = [a.get(PROVENANCE) for a in archives.values()]
    require(all(manifests) and all(m == manifests[0] for m in manifests), "Source/runtime provenance mismatch")
    p = json.loads(manifests[0][0])
    require(p["schema"] == 1 and p["target"] in TARGETS, "Unknown provenance schema/target")
    require(re.fullmatch(r"[0-9a-f]{40}", p["commit"]), "Missing source commit")
    require(p["source_inventory_sha256"] == digest(encoded(p["source_inventory"])), "Source inventory hash mismatch")
    require(p["gates"]["dataset_free_tests"] == "passed" and p["gates"].get("completed"), "Native gates incomplete")
    require(p["build"]["cargo_locked"] and p["build"]["jobs"] == 1 and p["build"]["native"], "Build policy mismatch")
    require(p['build'].get('privacy_policy') == PRIVACY_POLICY, 'Missing compiler privacy policy; rebuild required')
    stem = f"local-shazam-{p['commit'][:12]}-{p['target']}"
    binary_name = stem + (".zip" if p["target"] == "windows-x64" else ".tar.gz")
    require(set(archives) == {binary_name, f"{stem}-app-source.tar.gz", f"{stem}-olaf-source.tar.gz"}, "Archive naming/target mismatch")
    for group in ("app", "olaf"):
        entries = archives[f"{stem}-{group}-source.tar.gz"]
        wanted = p["source_inventory"][group]
        require(set(entries) == set(wanted) | {PROVENANCE}, f"Incomplete or unexpected {group} source")
        for name, sha in wanted.items():
            require(entries[name] == (entries[name][0], 0o644) and digest(entries[name][0]) == sha, f"Source mismatch: {name}")
    app_source = archives[f"{stem}-app-source.tar.gz"]
    olaf_source = archives[f"{stem}-olaf-source.tar.gz"]
    require("release/targets.json" in app_source and "release/targets.json" in olaf_source, "Missing inventory policy")
    cfg = json.loads(app_source["release/targets.json"][0])
    require(app_source["release/targets.json"] == olaf_source["release/targets.json"], "Inventory policies differ")
    completed = [name for names in cfg["rust_tests"].values() for name in names] + cfg["olaf_regressions"]
    suffix = ".exe" if p["target"] == "windows-x64" else ""
    completed += ["local-shazam" + suffix + " --help", "local-shazam" + suffix + " --version",
                  "olaf-runtime/olaf" + suffix + " --help"]
    require(sorted(p["gates"]["completed"]) == sorted(completed), "Incomplete or unexpected native test gates")
    require(p["olaf_source_version"] == olaf_source_version(olaf_source["vendor/olaf/build.zig.zon"][0]),
            "Olaf source version mismatch")
    for group, entries in (("app", app_source), ("olaf", olaf_source)):
        require(all(matches(n, cfg["source_inventory"]["common"] + cfg["source_inventory"][group])
                    for n in entries if n != PROVENANCE), "Source outside reviewed inventory")
    for pattern in cfg["source_inventory"]["required"]:
        require(matches_any(set(app_source) | set(olaf_source), pattern), f"Missing required source: {pattern}")
    binary = archives[binary_name]
    require(set(binary) == set(p["payload"]) | {PROVENANCE}, "Unexpected/missing binary payload")
    for name, row in p["payload"].items():
        require(digest(binary[name][0]) == row["sha256"] and binary[name][1] == row["mode"], f"Payload mismatch: {name}")
    exe = ".exe" if p["target"] == "windows-x64" else ""
    for name, key in (("local-shazam" + exe, "app"), ("olaf-runtime/olaf" + exe, "olaf")):
        require(name in binary and binary[name][1] == 0o755, f"Missing executable/mode: {name}")
        require(architecture(binary[name][0]) == p["target"], f"Wrong executable architecture: {name}")
        require(digest(binary[name][0]) == p["binary_inspections"][key]["sha256"], "Inspection hash mismatch")
        if exe:
            require(pe_imports(binary[name][0]) == p["binary_inspections"][key]["imports_and_delay_imports"], "DLL inspection mismatch")
    check_runtime_metadata({n.removeprefix("olaf-runtime/"): v[0] for n, v in binary.items()
                            if n.startswith("olaf-runtime/")}, "olaf" + exe)
    require("SETUP.txt" in binary and b"FFmpeg" in binary["SETUP.txt"][0] and b"FFprobe" in binary["SETUP.txt"][0], "Missing dependency setup instructions")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        require(name in binary and binary[name][0].strip() and binary[name] == app_source[name] == olaf_source[name], "Missing/mismatched legal material")
    legal = [n for n in app_source if n.startswith("licenses/")]
    require(legal and all(binary.get(n) == app_source[n] == olaf_source.get(n) and app_source[n][0].strip()
                         for n in legal), "Incomplete dependency licenses")
    allowed = {PROVENANCE, "SETUP.txt", "LICENSE", "THIRD_PARTY_NOTICES.md", "local-shazam" + exe} | set(legal)
    require(all(n in allowed or n.startswith("olaf-runtime/") for n in binary), "Unreviewed binary payload")
    require(not any(PurePosixPath(n).name.lower() in ("ffmpeg", "ffmpeg.exe", "ffprobe", "ffprobe.exe") for n in binary), "FFmpeg/FFprobe must not be bundled")
    print(f"Verified {p['target']} commit {p['commit']}: binary, matching sources, modes, notices, architecture and SHA256SUMS")
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "test", "package", "verify"):
        cmd = sub.add_parser(command)
        cmd.add_argument("--out-dir", type=Path, required=True)
        if command != "verify":
            cmd.add_argument("--target", choices=TARGETS, required=True)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            verify(args.out_dir.resolve())
        else:
            out = staging(args.out_dir)
            {"build": build, "test": test_build, "package": package}[args.command](args.target, out)
    except Exception as exc:
        # Malformed untrusted JSON/archives can raise unexpected parser types;
        # never turn those into tracebacks containing absolute operator paths.
        message = str(exc)
        if isinstance(exc, ReleaseError) and len(message) <= 250 and not hygiene.privacy_violations('', message.encode('utf-8')):
            print('release: ' + message, file=sys.stderr)
        else:
            print('release: operation rejected; diagnostic values withheld for privacy (' + type(exc).__name__ + ')', file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
