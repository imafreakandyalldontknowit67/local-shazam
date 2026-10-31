#!/usr/bin/env python3
"""Fail-closed, read-only SOURCE release gate (Python standard library only).

--root CHECKOUT checks every tracked pathname, using working-tree bytes. With
--staged it checks the entire index snapshot, not just changed files and never
working-tree bytes. Without a .git entry at ROOT, recursively check all files
(including ignored/untracked files). A staging directory inside another checkout
is therefore checked recursively. .git and .worktrees metadata are not traversed.

This is NOT a binary-package validator: there is deliberately no binary bypass.
Check the extracted corresponding-source archive here; the packaging workflow
must separately allowlist and authenticate intentionally generated executables.
No path, vendor, manifest, notice or patch gets a content-scanning exemption.
Heuristics are defense in depth, not proof that a file contains no private data.
Exit: 0 clean, 1 policy findings, 2 invocation/inventory failure. Never deletes.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Iterator


MAX_BYTES = 32 * 1024 * 1024
METADATA = {".git", ".worktrees"}
FORBIDDEN_DIRS = {
    "local-olaf", "olaf-runtime", "benchmarks", "experiments", "evidence",
    "target", "build", "dist", "zig-out", ".zig-cache", "zig-cache", "zig-pkg",
    "toolchains", ".toolchains", "toolchain", ".rustup", ".venv", "venv", "env", ".env",
    ".codex", ".claude", ".orchestrator", ".direnv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".cache", "cache", "caches", "node_modules", ".eggs", "htmlcov",
    "logs", "dumps", "diagnostics", "credentials", "secrets", ".ssh", ".aws",
    ".azure", ".gcloud", "test snippets", "music", "recordings",
}
FORBIDDEN_EXTENSIONS = set("""
    mp3 mp2 mp1 wav wave flac aac m4a m4b m4p m4r alac aif aiff aifc ogg oga
    opus wma ape wv caf au snd amr ac3 eac3 dts dsf dff mid midi kar ra ram
    mp4 m4v mov mkv webm avi wmv flv mpg mpeg m2ts mpegts vob 3gp 3g2 ogv
    raw pcm f32 f32le f32be f64 f64le f64be s16 s16le s16be s24le s32le
    db db3 sqlite sqlite3 mdb lmdb ldb sqlite-journal db-journal db-wal db-shm
    exe dll so dylib a lib obj o pdb wasm pyc pyo class jar whl egg bin
    zip 7z rar tar gz bz2 xz zst tgz cab msi msix appx dmg iso
    dmp mdmp dump core log etl evtx har pcap pcapng bak tmp temp swp swo
    pem key p12 pfx jks keystore
""".split())
FORBIDDEN_NAMES = {
    "claude.md", "handoff.md", "recovery-notes.md", "tasks.json",
    "tasks.results.json", "tasks.review.json", ".ds_store", "thumbs.db",
    ".netrc", "_netrc", ".npmrc", ".pypirc", "credentials", "credentials.json",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".env", ".envrc", ".coverage",
    ".git-credentials", "secrets.json", "credentials.toml", ".global-cache",
    ".package-cache", ".package-cache-mutate",
}
PRIVATE_REPORT = re.compile(
    r"(?:^|[-_.])(?:handoff|recovery|evidence|diagnostics?|dumps?|"
    r"benchmark(?:s)?[-_]results|validation[-_]results)(?:[-_.]|$)", re.I
)
LOCAL_REPORT = re.compile(
    r"^(?:library-benchmark|olaf-benchmark|rust-validation|restore-validation|"
    r"benchmark-results|olaf-.*-(?:results|evidence|benchmark))\.(?:md|txt|json|jsonl|csv|html)$", re.I
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
)
SENSITIVE_KEY = (
    r"(?:[a-z][a-z0-9]*[_-])*(?:password|passwd|api[_-]?key|access[_-]?key|"
    r"access[_-]?token|auth[_-]?token|refresh[_-]?token|client[_-]?secret|"
    r"secret[_-]?key|token|secret)"
)
ASSIGNMENT = re.compile(
    r"\b" + SENSITIVE_KEY + r"[\"']?\s*[:=]\s*(?:"
    r"(?P<quote>[\"'])(?P<quoted>[^\r\n]*?)(?P=quote)|"
    r"(?P<bare>[^\s,;#}\]\)]+))", re.I
)
BARE_ASSIGNMENT = re.compile(
    r"[\s+\-]*" + SENSITIVE_KEY + r"\s*[:=]\s*([A-Za-z0-9_+/=.-]+)\s*(?:#.*)?", re.I
)
AUTH = re.compile(r"\bAuthorization[\"']?\s*[:=]\s*[\"']?\s*(?:Bearer|Basic)\s+([A-Za-z0-9_+/=.-]{8,})", re.I)
URL_AUTH = re.compile(r"\b[a-z][a-z0-9+.-]*://([^\s/:@]+):([^\s/@]+)@", re.I)
HOME_PATH = re.compile(
    r"(?<![\w:])(?:[a-z]:[\\/]+|/" r"mnt/[a-z]/|/)(?:Users|home)"
    r"[\\/]+([^\\/\s\"'`;,<>]+|<[^>]+>)", re.I
)
ROOT_HOME = re.compile(r"(?<![:/\w])/" r"root/(?![<>${])[^\s\"'`]+")
WINDOWS_PATH = re.compile(r"\b[a-z]:[\\/]+([^\r\n\"'`|;,]+)", re.I)
UNC_PATH = re.compile(r"(?<![\w\\])\\\\(?![?.]\\)([A-Za-z0-9_.-]+)\\([^\s\"'`]+)")
UNC_FORWARD = re.compile(r"(?<![:/\w])//(?:\?/UNC/)?([A-Za-z0-9_.-]+)/([^\s\"'`]+)", re.I)
MOUNT_PATH = re.compile(r"(?<![:/\w])/" r"(?:Volumes|media|mnt)/([^/\s\"'`]+)", re.I)
PLACEHOLDERS = {
    "", "example", "placeholder", "redacted", "changeme", "change-me", "dummy",
    "test", "testing", "password", "secret", "token", "none", "null", "false",
    "true", "your_api_key", "your-api-key", "your_token", "your-token",
    "your_password", "your-password", "not-a-secret",
}
HOME_EXAMPLES = {"user", "username", "yourname", "your-user", "your_username", "me", "test-user"}
GENERIC_DRIVE_DIRS = {
    "music", "snippets", "clips", "audio", "path", "path-to", "tmp", "temp",
    "example", "examples", "project", "work", "src", "tools", "program files",
    "windows", "audioindexes",
}


def placeholder(value: str) -> bool:
    value = value.strip()
    return value.lower() in PLACEHOLDERS or bool(re.fullmatch(
        r"(?:<[^<>\r\n]+>|\$\{[A-Za-z_][A-Za-z0-9_]*\}|%[A-Za-z_][A-Za-z0-9_]*%)", value
    ))



def public_upstream_fixture(name: str, line: str) -> bool:
    # Exact removed fixture line verified in public JorenSix/Olaf at
    # f6f7cbefb50485953f71100c9d08c625f01780ba, tests/olaf_tests.c line 106.
    # Preserve replayable patch provenance; no general vendor/path exemption.
    return (name == "patches/olaf/0003-release-local-source-build.patch"
            and hashlib.sha256(line.encode("utf-8")).hexdigest() == "0b007ce062fe1f8f5acbff66c03c6570add2110cd80d1f9c2713b304aaabb1a5")

@lru_cache(maxsize=64)
def embedded_pattern(pattern, remove_lookbehind=False):
    value = pattern.pattern.replace(r'\b', '')
    if remove_lookbehind:
        value = re.sub(r'\(\?<\!.*?\)', '', value)
    return re.compile(value, pattern.flags)


def personal_path(line: str, *, embedded: bool = False) -> bool:
    if '/' not in line and '\\' not in line:
        return False
    # URLs, including attribution URLs with /home/ segments, are not local paths.
    url_pattern = r"[a-z][a-z0-9+.-]+://[^\s<>\"']*" if embedded else r"\b(?:https?|ftp)://[^\s<>\"']+"
    local = re.sub(url_pattern, "", line, flags=re.I)
    local = re.sub(r"/" r"mnt/([a-z])/", lambda m: m[1] + ':/', local, flags=re.I)
    def matches(pattern):
        if embedded:
            pattern = embedded_pattern(pattern, True)
        return pattern.finditer(local)
    for match in matches(MOUNT_PATH):
        if match[1].lower() not in {'music', 'audio', 'volume', 'drive'} and not placeholder(match[1]):
            return True
    for match in matches(HOME_PATH):
        user = match[1]
        if not placeholder(user) and user.lower() not in HOME_EXAMPLES:
            return True
        # A generic account name does not excuse a concrete private suffix.
        tail = local[match.end():].split()[0:1]
        if user.lower() in HOME_EXAMPLES and tail:
            suffix = re.split(r"[\"'`,;)]", tail[0], maxsplit=1)[0].strip('\\/')
            if suffix and not re.fullmatch(r"(?:music|project|file|test|\.olaf|bla)(?:[\\/](?:example|file|test|config|db|cache|t)(?:\.[a-z0-9]+)?)*", suffix, re.I):
                return True
    if next(matches(ROOT_HOME), None):
        return True
    for match in matches(WINDOWS_PATH):
        parts = re.split(r"[\\/]+", match[1].strip())
        first = parts[0].lower()
        # Packed instruction bytes can decode to an adjacent drive prefix plus
        # one character (e.g. an immediate operand). This is not enough evidence
        # of a private path. Standalone strings and multi-component paths still
        # fail, and the release layer separately checks exact known build roots.
        if embedded and match.start() > 0 and len(parts) == 1 and len(parts[0]) == 1:
            continue
        if first == "users":  # Account names checked above, including placeholders.
            continue
        if first not in GENERIC_DRIVE_DIRS and not placeholder(parts[0]):
            return True
    for pattern in (UNC_PATH, UNC_FORWARD):
        for match in matches(pattern):
            # Native Windows namespace templates may be adjacent in a binary.
            # A separator inside a device namespace is not a UNC server root.
            if embedded and pattern is UNC_PATH and (
                    re.search(r'(?:^|[^A-Za-z])(?:Device|DosDevices)$', local[:match.start()])
                    or local[:match.start()].endswith('\\??')):
                continue
            if match[1].lower() not in {"server", "localhost"} and not placeholder(match[1]):
                return True
    return False


def privacy_lines(data: bytes) -> Iterator[str]:
    """Strings in arbitrary artifacts, including BOM-less, odd-offset UTF-16.

    Bounded overlapping windows avoid decoding an entire executable five times.
    NUL/control bytes terminate strings, rather than hiding adjacent credentials.
    This does NOT make binary files acceptable in the source-only gate.
    """
    for start in range(0, len(data), 65536):
        block = data[max(0, start - 4096):start + 65536]
        # Invalid byte sequences are boundaries, not pathname characters. Otherwise
        # instruction bytes such as ff 5a 3a 2f 90 look like a drive pathname.
        yield from re.split(r'[\x00-\x08\x0b-\x1f\x7f\ufffd]', block.decode('utf-8', 'replace'))
        for encoding in ('utf-16-le', 'utf-16-be'):
            for offset in (0, 1):
                text = block[offset:len(block) - ((len(block) - offset) % 2)].decode(encoding, 'replace')
                yield from re.split(r'[\x00-\x08\x0b-\x1f\x7f\ufffd]', text)


def privacy_violations(name: str, data: bytes, *, source: bool = False) -> set[str]:
    """Reusable content policy; returns rule names, never offending values."""
    rules = set()
    # Only exact original UTF-8 source lines qualify for the public patch fixture.
    lines = data.decode('utf-8-sig', 'replace').splitlines() if source else privacy_lines(data)
    for text in lines:
        for line in text.splitlines():
            if not source and not re.search(r'[/\\:=_.-]|AKIA|ASIA|AIza', line):
                continue
            if likely_secret(line, embedded=not source):
                rules.add('likely-credential')
            if personal_path(line, embedded=not source) and not (source and public_upstream_fixture(name, line)):
                rules.add('personal-absolute-path')
            # Concrete build/cache roots are private on hosted runners as well.
            # Split literals here keep the detector's own source reviewable.
            boundary = r'(?<![\w:])' if source else ''
            local = re.sub((r'\b' if source else '') + r'(?:https?|ftp)://[^\s<>"\']+', '', line, flags=re.I)
            if re.search(boundary + r'/(?:private/var/' r'folders|workspace|workspaces|__w)/[^\s\x00"\'`<>]+/[^\s\x00"\'`<>]+', local) or re.search(
                    boundary + r'/(?:var/)?' r'tmp/(?:tmp|rustc|cargo|zig|olaf-build-)[^/\s"\'`<>]*/[^\s"\'`<>]+', local):
                rules.add('build-absolute-path')
    return rules


def likely_secret(line: str, *, embedded: bool = False) -> bool:
    # Every supported credential grammar contains one of these markers. Avoid
    # expensive assignment-pattern searches through arbitrary executable bytes.
    lower = line.lower()
    if not any(marker in lower for marker in (
            '-----begin ', 'akia', 'asia', 'ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_',
            'github_pat_', 'xox', 'sk-', 'aiza', 'eyj', 'password', 'passwd',
            'key', 'token', 'secret', 'authorization', '://')):
        return False
    def pattern_for(pattern):
        return embedded_pattern(pattern) if embedded else pattern
    if any(pattern_for(pattern).search(line) for pattern in SECRET_PATTERNS):
        return True
    for match in pattern_for(URL_AUTH).finditer(line):
        if not placeholder(match[2]):
            return True
    for match in pattern_for(AUTH).finditer(line):
        if not placeholder(match[1]):
            return True
    bare = BARE_ASSIGNMENT.fullmatch(line)
    if bare and not placeholder(bare[1]):
        return True
    for match in pattern_for(ASSIGNMENT).finditer(line):
        value = match['quoted'] if match['quote'] else match['bare']
        if placeholder(value):
            continue
        if embedded and re.fullmatch(r'%[-+0 #]*\d*(?:\.\d+)?(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspnT]', value):
            continue  # C diagnostic format argument, not a literal credential.
        if match['quote']:
            return True
        # Bare literals in env/YAML; do not mistake normal source expressions or
        # variable references for credentials. Recognizable token prefixes above
        # are checked regardless of quoting or assignment.
        if len(value) >= 8 and re.fullmatch(r"[A-Za-z0-9_+/=.-]+", value):
            if any(c.isdigit() for c in value) and any(c.isalpha() for c in value):
                return True
    return False


def forbidden_path(name: str) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in {"", ".", ".."} for p in name.split('/')) or '\\' in name or ':' in name:
        return "unsafe-path"
    if likely_secret(name):
        return "credential-in-path"
    parts = [p.casefold() for p in path.parts]
    if any(parts[i] == '.cargo' and parts[i + 1] in {'registry', 'git', 'bin'} for i in range(len(parts) - 1)):
        return "local-artifact-directory"
    if any(p in METADATA or p in FORBIDDEN_DIRS or p.endswith('.egg-info') for p in parts[:-1]):
        return "local-artifact-directory"
    base = parts[-1]
    if base in FORBIDDEN_NAMES or base.startswith('.env.') or PRIVATE_REPORT.search(base) or LOCAL_REPORT.fullmatch(base):
        return "private-artifact-name"
    # SQLite journal/WAL/SHM and LMDB lock variants, including renamed sidecars.
    if re.search(r"\.(?:db\d*|sqlite\d*|lmdb|mdb|ldb)(?:[.-](?:wal|shm|journal|lock))?$", base):
        return "database-or-sidecar"
    if base.rsplit('.', 1)[-1] in FORBIDDEN_EXTENSIONS:
        return "forbidden-artifact-extension"
    if base.endswith('~'):
        return "editor-backup"
    return None


def display_path(name: str) -> str:
    # Never echo malicious/control-character filenames or secret-looking paths.
    if personal_path(name) or likely_secret(name) or forbidden_path(name):
        return '[redacted path; id=' + hashlib.sha256(name.encode('utf-8', 'surrogateescape')).hexdigest()[:12] + ']'
    return json.dumps(name, ensure_ascii=True)


class Findings:
    def __init__(self) -> None:
        self.count = 0

    def add(self, name: str, rule: str, advice: str, line: int | None = None) -> None:
        self.count += 1
        location = display_path(name) + (f":{line}" if line else '')
        print(f"FAIL {location} [{rule}] {advice}", file=sys.stderr)


def check_bytes(name: str, data: bytes, findings: Findings) -> None:
    if len(data) > MAX_BYTES:
        findings.add(name, 'oversized-source', 'Review this oversized source candidate; limit is 32 MiB.')
        return
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError:
        findings.add(name, 'binary-source', 'Source must be UTF-8 text; do not bundle binaries or archives.')
        return
    if any(ord(c) < 32 and c not in '\t\n\r\f' for c in text) or '\x7f' in text:
        findings.add(name, 'binary-source', 'Unexpected binary/control bytes in source; inspect locally.')
        return
    # Signatures also catch deliberately renamed, short ASCII-only media headers.
    if data.startswith((b'RIFF', b'fLaC', b'OggS', b'ID3', b'MZ', b'SQLite format 3')):
        findings.add(name, 'binary-source', 'Media/database signature is forbidden regardless of filename.')
        return
    for number, line in enumerate(text.splitlines(), 1):
        rules = privacy_violations(name, line.encode('utf-8'), source=True)
        if 'likely-credential' in rules:
            findings.add(name, 'likely-credential', 'Remove the literal; use an environment reference. Rotate real exposed credentials.', number)
        if rules & {'personal-absolute-path', 'build-absolute-path'}:
            findings.add(name, 'personal-absolute-path', 'Replace the local path with a generic example or explicit <user> placeholder.', number)


def git_environment() -> dict[str, str]:
    # ROOT, not an inherited alternate-index/worktree/object environment, selects
    # the source snapshot. Disable optional writes by read-only Git operations.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    return env


def git(root: Path, *args: str, input_data: bytes | None = None) -> bytes:
    result = subprocess.run(['git', '-C', str(root), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=git_environment(), input=input_data)
    if result.returncode:
        raise RuntimeError('Git inventory failed; verify ROOT is the checkout root and the index is readable.')
    return result.stdout


def linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def read_source(root: Path, name: str, findings: Findings) -> bytes | None:
    path = root
    try:
        # Inspect every ancestor: a tracked file beneath a swapped directory must
        # never follow a symlink/junction out of the source tree.
        for part in PurePosixPath(name).parts:
            path = path / part
            if linked(path):
                findings.add(name, 'symlink-or-reparse-point', 'Replace links/junctions with reviewed regular source files.')
                return None
        path.resolve().relative_to(root)
        if not stat.S_ISREG(path.stat().st_mode):
            findings.add(name, 'special-file', 'Only regular source files are permitted.')
            return None
        if path.stat().st_size > MAX_BYTES:
            findings.add(name, 'oversized-source', 'Review this oversized source candidate; limit is 32 MiB.')
            return None
        with path.open('rb') as stream:
            return stream.read(MAX_BYTES + 1)
    except (OSError, ValueError):
        findings.add(name, 'unreadable-or-escaped-path', 'Check the tracked file exists, stays inside ROOT, and is readable. No local files were removed.')
        return None


def tree_candidates(root: Path, findings: Findings) -> Iterator[str]:
    def walk(directory: Path) -> Iterator[str]:
        try:
            entries = sorted(os.scandir(directory), key=lambda e: e.name)
        except OSError:
            findings.add(directory.relative_to(root).as_posix(), 'unreadable-directory', 'Cannot inventory directory; inspect permissions locally.')
            return
        for entry in entries:
            # Metadata is excluded by name, never followed, at every depth.
            if entry.name.casefold() in METADATA:
                continue
            path = Path(entry.path)
            name = path.relative_to(root).as_posix()
            try:
                if linked(path):
                    findings.add(name, 'symlink-or-reparse-point', 'Links/junctions are not allowed in source archives.')
                elif entry.is_dir(follow_symlinks=False):
                    if forbidden_path(name + '/[contents]'):
                        findings.add(name + '/[contents]', 'local-artifact-directory', 'Exclude this directory from the source archive; no contents were read.')
                    else:
                        yield from walk(path)
                else:
                    yield name
            except OSError:
                findings.add(name, 'unreadable-path', 'Cannot inventory source candidate; inspect locally.')
    yield from walk(root)


def check(root: Path, staged: bool, findings: Findings) -> int:
    total = 0
    if not os.path.lexists(root / '.git'):
        if staged:
            raise RuntimeError('--staged requires a Git checkout root with .git metadata.')
        for name in tree_candidates(root, findings):
            total += 1
            rule = forbidden_path(name)
            if rule:
                findings.add(name, rule, 'Exclude this candidate from source staging; .gitignore cannot protect tracked files.')
                continue
            data = read_source(root, name, findings)
            if data is not None:
                check_bytes(name, data, findings)
        return total

    top = Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve()
    if top != root:
        raise RuntimeError('--root must be the checkout root, not an enclosing or nested directory.')
    entries = git(root, 'ls-files', '--stage', '-z').split(b'\0')
    process = None
    try:
        if staged:
            # Query sizes first: even an oversized staged artifact must not be
            # streamed into the checker merely to reject it.
            oids = {entry.split(b'\t', 1)[0].split()[1] for entry in entries if entry}
            metadata = git(root, 'cat-file', '--batch-check', input_data=b''.join(oid + b'\n' for oid in sorted(oids)))
            sizes = {}
            for record in metadata.splitlines():
                fields = record.split()
                if len(fields) == 3 and fields[1] == b'blob':
                    sizes[fields[0]] = int(fields[2])
            process = subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, env=git_environment())
        for entry in entries:
            if not entry:
                continue
            header, raw_name = entry.split(b'\t', 1)
            mode, oid, stage = header.split()
            name = os.fsdecode(raw_name)
            total += 1
            rule = forbidden_path(name)
            if rule:
                findings.add(name, rule, 'Remove from the release index/staging, not the local data; ignored tracked files still leak.')
                continue
            if stage != b'0' or mode not in (b'100644', b'100755'):
                findings.add(name, 'non-regular-index-entry', 'Resolve conflicts; symlinks and submodules are not source-file exceptions.')
                continue
            if not staged:
                data = read_source(root, name, findings)
            else:
                assert process is not None and process.stdin and process.stdout
                if oid not in sizes:
                    raise RuntimeError('Cannot read staged blob; index/object database needs inspection.')
                if sizes[oid] > MAX_BYTES:
                    findings.add(name, 'oversized-source', 'Staged source exceeds 32 MiB; no blob content was read.')
                    continue
                process.stdin.write(oid + b'\n')
                process.stdin.flush()
                meta = process.stdout.readline().split()
                if len(meta) != 3 or meta[1] != b'blob':
                    raise RuntimeError('Cannot read staged blob; index/object database needs inspection.')
                size = int(meta[2])
                if size != sizes[oid]:
                    raise RuntimeError('Staged blob size changed during checking; retry with an immutable snapshot.')
                data = process.stdout.read(size)
                if len(data) != size:
                    raise RuntimeError('Truncated staged blob.')
                if process.stdout.read(1) != b'\n':
                    raise RuntimeError('Invalid staged blob response.')
            if data is not None:
                check_bytes(name, data, findings)
    finally:
        if process is not None:
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()
            process.wait()
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path('.'), help='Checkout root or extracted source directory (default: current directory).')
    parser.add_argument('--staged', action='store_true', help='Check the complete staged snapshot, not working-tree content.')
    args = parser.parse_args(argv)
    findings = Findings()
    try:
        if linked(args.root):
            raise RuntimeError('ROOT itself must not be a symlink/junction.')
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise RuntimeError('ROOT must be a directory.')
        count = check(root, args.staged, findings)
    except (OSError, RuntimeError, ValueError) as error:
        # OS/Git errors can contain private paths or data; only our static error
        # messages are safe to print. Never print exception strings from the OS.
        message = str(error) if type(error) is RuntimeError else 'Cannot inventory ROOT; inspect the directory and Git installation locally.'
        print('ERROR: ' + message, file=sys.stderr)
        return 2
    if findings.count:
        print(f'Source hygiene FAILED: {findings.count} finding(s), {count} candidate(s). Diagnostics omit matched values.', file=sys.stderr)
        return 1
    print(f'Source hygiene passed: {count} candidate(s); ' + ('index snapshot.' if args.staged else 'source content.'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
