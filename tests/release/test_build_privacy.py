"""Compiler command/policy tests only: never execute compilers or applications."""
import contextlib
import importlib.util
import io
import json
import struct
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('privacy_release', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class CompilerPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(release.subprocess, "run", side_effect=AssertionError("Unmocked tool execution")).start()
        patch.object(release.urllib.request, "urlopen", side_effect=AssertionError("No network")).start()

    def test_olaf_strip_is_set_before_install_registration(self):
        source = (ROOT / 'vendor/olaf/build.zig').read_text()
        installs = 0
        for index, line in enumerate(source.splitlines()):
            if 'b.installArtifact(' not in line:
                continue
            artifact = line.split('b.installArtifact(')[1].split(')')[0]
            self.assertEqual(source.splitlines()[index - 1].strip(),
                             f'if (release_privacy) {artifact}.root_module.strip = true;')
            installs += 1
        self.assertEqual(installs, 3)

    def test_relocation_bytes_are_not_windows_path_components(self):
        # Colon cannot start a Windows filename; stop at it, including ADS syntax.
        noise = ':#:9:>:F:U:' + chr(92) + ':n:s:{:'
        for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
            self.assertFalse(release.hygiene.privacy_violations('', noise.encode(encoding)))
            private = noise + 'C:/' + 'Users/' + 'PrivatePerson/song.wav:stream'
            self.assertIn('personal-absolute-path', release.hygiene.privacy_violations('', private.encode(encoding)))

    def test_safe_compiler_diagnostic_headers_only(self):
        private = 'C:/' + 'Users/' + 'PrivatePerson/source.rs'
        marker = 'gh' + 'p_' + 'Q' * 36
        text = '\n'.join(['error[E0308]: mismatched types',
                          'build.zig:12:3: error: missing field',
                          'error: ' + private, 'error: ' + marker,
                          'compiler command with unreviewed arguments'])
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            release.report_safe_diagnostics(text.encode())
        self.assertEqual(output.getvalue().splitlines(), [
            'error[E0308]: mismatched types', 'build.zig:12:3: error: missing field'])

    def test_five_targets_encoded_rust_and_native_flags_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='privacy space ') as tmp:
            root = Path(tmp).resolve()
            for target in release.TARGETS:
                out = root / 'build/release space' / target
                snapshot = out / 'work/build-source'
                with self.subTest(target=target), patch.object(release.shutil, 'which', side_effect=lambda tool, **kw: tool):
                    env = release.build_env(out)
                    release.apply_compiler_privacy(env, out, snapshot, target, root)
                    flags = env['CARGO_ENCODED_RUSTFLAGS'].split('\x1f')
                    if flags[0].startswith('@'):
                        flags = Path(flags[0][1:]).read_text().splitlines()
                    self.assertIn(f'--remap-path-prefix={snapshot}=/source', flags)
                    self.assertIn(f'--remap-path-prefix={out / "work/cargo-home"}=/build/cargo', flags)
                    self.assertIn(f'--remap-path-prefix={out / "work/rustup-home"}=/toolchain/rust', flags)
                    self.assertIn(f'--remap-path-prefix={out / "work/cargo-target"}=/build/target', flags)
                    self.assertIn('-Cdebuginfo=0', flags)
                    self.assertIn('-Cstrip=debuginfo', flags)
                    self.assertEqual(env['CARGO_ENCODED_RUSTDOCFLAGS'], env['CARGO_ENCODED_RUSTFLAGS'])
                    response_arg, = shlex.split(env['CFLAGS'])
                    self.assertTrue(response_arg.startswith('@'))
                    native_response = Path(response_arg[1:]).read_text()
                    prefix = '/clang:' if target in release.WINDOWS_TARGETS else ''
                    for kind in ('ffile', 'fdebug', 'fmacro'):
                        flag = f'{prefix}-{kind}-prefix-map={snapshot}=/source'
                        if target in release.WINDOWS_TARGETS:
                            self.assertIn(subprocess.list2cmdline([flag]), native_response)
                        else:
                            self.assertIn(flag, shlex.split(native_response))
                    self.assertEqual(env['CC_SHELL_ESCAPED_FLAGS'], '1')
                    self.assertEqual(env['CFLAGS'], env['CXXFLAGS'])
                    if target in release.WINDOWS_TARGETS:
                        self.assertEqual(env['CC'], 'clang-cl')
                        self.assertIn('-Clink-arg=/DEBUG:NONE', flags)
                        self.assertIn('-Clink-arg=/INCREMENTAL:NO', flags)
                        self.assertTrue(env['CARGO_ENCODED_RUSTFLAGS'].startswith('@'))
                        self.assertIn('-Clink-arg=/PDBALTPATH:local-shazam.pdb', flags)

    def test_supported_hosts_and_truthful_wow64_policy(self):
        cfg = release.config(ROOT)
        for target in release.TARGETS:
            host_target = "windows-x64" if target == "windows-x86" else target
            host = cfg["targets"][host_target]
            with patch.object(release.platform, "system", return_value=host["os"]), \
                    patch.object(release.platform, "machine", return_value=host["arch"]):
                execution = release.check_host(target, cfg)
            self.assertEqual(execution["host_target"], host_target)
            self.assertEqual(execution["output_target"], target)
            self.assertEqual(execution["native"], target != "windows-x86")
            self.assertEqual(execution["cross_target"], target == "windows-x86")
            self.assertEqual(execution["execution_mode"], "wow64" if target == "windows-x86" else "native")
        for target, system, machine in (("windows-x86", "Windows", "i686"),
                                        ("windows-x86", "Windows", "ARM64"),
                                        ("windows-x86", "Linux", "x86_64"),
                                        ("windows-x64", "Windows", "x86"),
                                        ("macos-x64", "Darwin", "arm64"),
                                        ("linux-x64", "Darwin", "x86_64")):
            with patch.object(release.platform, "system", return_value=system), \
                    patch.object(release.platform, "machine", return_value=machine):
                with self.assertRaisesRegex(release.ReleaseError, "Unsupported host/target"):
                    release.check_host(target, cfg)

    def test_x86_output_provisions_only_pinned_x64_host_tools(self):
        cfg = release.config(ROOT)
        self.assertEqual(cfg["targets"]["windows-x86"]["host_tools"], "windows-x64")
        self.assertNotIn("rustup_sha256", cfg["targets"]["windows-x86"])
        self.assertNotIn("zig_sha256", cfg["targets"]["windows-x86"])
        for target in release.WINDOWS_TARGETS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                env = release.build_env(out)
                downloads, commands = [], []
                def fake_download(url, sha, dest):
                    downloads.append((url, sha))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(b"synthetic host tool; never executed")
                def fake_extract(archive, destination):
                    path = destination / "zig-x86_64-windows-0.16.0/zig.exe"
                    path.parent.mkdir()
                    path.write_bytes(b"synthetic tool")
                def fake_run(command, **kwargs):
                    commands.append([str(arg) for arg in command])
                    return "0.16.0" if command[-1] == "version" else ""
                with patch.object(release.platform, "system", return_value="Windows"), \
                        patch.object(release.platform, "machine", return_value="AMD64"), \
                        patch.object(release, "download", side_effect=fake_download), \
                        patch.object(release, "extract_tool", side_effect=fake_extract), \
                        patch.object(release, "run", side_effect=fake_run):
                    release.provision(target, out, cfg, env)
                self.assertEqual(downloads, [
                    ("https://static.rust-lang.org/rustup/archive/1.28.2/x86_64-pc-windows-msvc/rustup-init.exe",
                     "88d8258dcf6ae4f7a80c7d1088e1f36fa7025a1cfd1343731b4ee6f385121fc0"),
                    ("https://ziglang.org/download/0.16.0/zig-x86_64-windows-0.16.0.zip",
                     "68659eb5f1e4eb1437a722f1dd889c5a322c9954607f5edcf337bc3684a75a7e")])
                self.assertEqual(commands[0][commands[0].index("--default-host") + 1], "x86_64-pc-windows-msvc")
                self.assertEqual(commands[1][-2:], ["--target", cfg["targets"][target]["rust"]])
                self.assertNotIn("i686", " ".join(url for url, _ in downloads))

    def test_download_hash_and_redirect_checks_with_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool"
            response = io.BytesIO(b"synthetic download")
            response.url = "https://static.rust-lang.org/reviewed/tool"
            with patch.object(release.urllib.request, "urlopen", return_value=response):
                with self.assertRaisesRegex(release.ReleaseError, "Tool checksum mismatch"):
                    release.download(response.url, "0" * 64, path)
            response = io.BytesIO(b"synthetic download")
            response.url = "https://example.org/unreviewed/tool"
            with patch.object(release.urllib.request, "urlopen", return_value=response):
                with self.assertRaisesRegex(release.ReleaseError, "Unexpected download redirect"):
                    release.download("https://static.rust-lang.org/reviewed/tool", "0" * 64, Path(tmp) / "other")

    def mocked_build_and_gates(self, target, *, fail_regression=False):
        cfg = release.config(ROOT)
        with tempfile.TemporaryDirectory(prefix="mocked target ") as tmp:
            root = Path(tmp).resolve()
            out = root / "build/job"
            inputs = {"rust-app/Cargo.toml": b'[package]\nname="local-shazam"\nversion="7.8.9"\n',
                      "vendor/olaf/build.zig.zon": b'.{ .version = "3.3.3" }',
                      "LICENSE": b"license fixture", "THIRD_PARTY_NOTICES.md": b"notice fixture"}
            for name, data in inputs.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            source = {"app": {n: release.digest(d) for n, d in inputs.items() if not n.startswith("vendor/")},
                      "olaf": {n: release.digest(d) for n, d in inputs.items() if n.startswith("vendor/")}}
            # Complete PE headers and file-backed section, never executable code.
            x86 = target == "windows-x86"
            data = bytearray(1024)
            data[:2] = b"MZ"
            struct.pack_into("<I", data, 60, 128)
            data[128:132] = b"PE\0\0"
            struct.pack_into("<HH", data, 132, 0x14C if x86 else 0x8664, 1)
            size, base = (224, 96) if x86 else (240, 112)
            struct.pack_into("<HHH", data, 148, size, 2, 0x10B if x86 else 0x20B)
            struct.pack_into("<I", data, 212, 512)
            struct.pack_into("<I", data, 152 + base - 4, 16)
            struct.pack_into("<4I", data, 152 + size + 8, 512, 4096, 512, 512)
            calls = []
            def fake_provision(t, directory, config, env):
                self.assertEqual(t, target)
                tools = directory / "work/tools"
                tools.mkdir()
                paths = tuple(tools / name for name in ("rustup.exe", "zig.exe"))
                for path in paths:
                    path.write_bytes(b"tool fixture")
                return paths
            def fake_run(command, **kwargs):
                args = [str(arg) for arg in command]
                calls.append(args)
                if "rustc" in args:
                    return "release: 1.99.0\nhost: x86_64-pc-windows-msvc"
                if "metadata" in args:
                    return json.dumps({"packages": [{"name": "local-shazam", "version": "7.8.9"}]})
                if "cargo" in args and "build" in args:
                    self.assertEqual(args[args.index("--target") + 1], cfg["targets"][target]["rust"])
                    path = Path(kwargs["env"]["CARGO_TARGET_DIR"]) / cfg["targets"][target]["rust"] / "release/local-shazam.exe"
                    path.parent.mkdir(parents=True)
                    path.write_bytes(data)
                    return ""
                if len(args) > 1 and args[1].endswith("build_olaf.py"):
                    self.assertEqual(args[args.index("--target") + 1], target)
                    runtime = Path(args[args.index("--out-dir") + 1]) / "olaf-runtime"
                    runtime.mkdir(parents=True)
                    for name, content in {"olaf.exe": data, "LICENSE.txt": b"license", "NOTICE.txt": b"notice",
                                          "PROVENANCE.json": b'{"fixture":true}'}.items():
                        (runtime / name).write_bytes(content)
                    return ""
                if "cargo" in args and "test" in args:
                    self.assertEqual(args[args.index("--target") + 1], cfg["targets"][target]["rust"])
                    self.assertIn("--test-threads=1", args)
                    self.assertIn("CARGO_ENCODED_RUSTFLAGS", kwargs["env"])
                    return "1 passed; 0 failed"
                if len(args) > 2 and args[1] == "build" and args[2] in cfg["olaf_regressions"]:
                    self.assertIn("-Dtarget=" + cfg["targets"][target]["olaf"], args)
                    self.assertIn("-Dcpu=baseline", args)
                    self.assertIn("-j1", args)
                    self.assertIn("-Drelease-privacy=true", args)
                    self.assertTrue(any(arg.startswith("-Dprivacy-cflags=") for arg in args))
                    self.assertEqual(Path(kwargs["cwd"]), out / "work/regression-source/vendor/olaf")
                    if fail_regression:
                        raise release.ReleaseError("Mock target execution unavailable")
                    return ""
                if args[-1] == "--version" and args[0].endswith("local-shazam.exe"):
                    return "local-shazam 7.8.9"
                if args[-1] in ("--help", "--version", "version"):
                    return "synthetic output"
                if len(args) > 1 and args[1].endswith("check_release_hygiene.py"):
                    return ""
                raise AssertionError("Unexpected mocked command")
            with patch.object(release, "config", return_value=cfg), \
                    patch.object(release, "inventory", return_value=source), \
                    patch.object(release, "clean_commit", return_value="a" * 40), \
                    patch.object(release, "provision", side_effect=fake_provision), \
                    patch.object(release.platform, "system", return_value="Windows"), \
                    patch.object(release.platform, "machine", return_value="AMD64"), \
                    patch.object(release.shutil, "which", return_value="clang-cl"), \
                    patch.object(release, "run", side_effect=fake_run):
                release.build(target, out, root)
                p = release.read_manifest(out)
                self.assertEqual(p["gates"]["dataset_free_tests"], "not-run")
                self.assertEqual(p["toolchains"]["downloads"], cfg["targets"]["windows-x64"])
                if fail_regression:
                    with self.assertRaisesRegex(release.ReleaseError, "execution unavailable"):
                        release.test_build(target, out, root)
                    p = release.read_manifest(out)
                    self.assertEqual(p["gates"], {"dataset_free_tests": "not-run"})
                    self.assertEqual(p["support_status"], "unverified")
                else:
                    release.test_build(target, out, root)
                    p = release.read_manifest(out)
                    self.assertEqual(p["gates"]["execution_mode"], "wow64" if x86 else "native")
                    self.assertEqual(p["build"]["native"], not x86)
                    self.assertEqual(p["host"]["arch"], "x86_64")
                    self.assertEqual(p["build"]["output_target"], target)
                    self.assertEqual(len([args for args in calls if len(args) > 2 and args[2] in cfg["olaf_regressions"]]), 3)
                    self.assertEqual(p["gates"]["dataset_free_tests"], "passed")

    def test_mocked_build_and_every_gate_use_requested_windows_architecture(self):
        for target in release.WINDOWS_TARGETS:
            with self.subTest(target=target):
                self.mocked_build_and_gates(target)

    def test_failed_x86_regression_is_not_native_fallback_or_success(self):
        self.mocked_build_and_gates("windows-x86", fail_regression=True)

    def test_hostile_environment_is_not_a_release_override(self):
        hostile = {key: 'hostile-value' for key in (
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
            'CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_RUSTFLAGS', 'CARGO_TARGET_I686_PC_WINDOWS_MSVC_RUNNER',
            'CFLAGS_i686-pc-windows-msvc', 'CARGO_BUILD_RUSTC',
            'CARGO_PROFILE_RELEASE_BUILD_OVERRIDE_DEBUG', 'RUSTDOCFLAGS', 'RUSTUP_TOOLCHAIN',
            'CC', 'CXX', 'CFLAGS_x86_64-pc-windows-msvc', 'TARGET_CFLAGS', 'HOST_CFLAGS',
            'CC_SHELL_ESCAPED_FLAGS', 'CC_KNOWN_WRAPPER_CUSTOM', 'CL', '_CL_', 'LINK', '_LINK_',
            'LIBSQLITE3_FLAGS', 'SQLITE3_LIB_DIR', 'CMAKE_TOOLCHAIN_FILE', 'LDFLAGS',
            'ZIG_LIB_DIR', 'ZIG_GLOBAL_CACHE_DIR', 'CARGO_HOME', 'GIT_CONFIG_COUNT',
            'CRATE_CC_NO_DEFAULTS', 'DYLD_INSERT_LIBRARIES', 'LD_PRELOAD', 'CPATH')}
        hostile['PATH'] = 'platform-tool-path'
        self.assertEqual(release.clean_build_environment(hostile), {'PATH': 'platform-tool-path'})

    def test_windows_slashes_extended_prefixes_and_overlap(self):
        path = 'C:\\' + 'Users\\Build Person\\stage'
        variants = release.path_variants(path)
        self.assertIn(path.replace('\\', '/'), variants)
        self.assertIn('\\\\?\\' + path, variants)
        self.assertIn(path[0].lower() + path[1:], variants)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            maps = release.privacy_maps(root / 'build/job', root / 'build/job/work/build-source', {}, root)
            def remap(value):
                for old, new in reversed(maps):
                    if value.startswith(old):
                        return new + value[len(old):]
            self.assertEqual(remap(str(root / 'build/job/work/build-source/rust-app') + '/src/main.rs'),
                             '/source/rust-app/src/main.rs')
            self.assertEqual(sorted(len(old) for old, _ in maps), [len(old) for old, _ in maps])
            self.assertFalse(any(old in ('/', '\\', 'C:') for old, _ in maps))

    def test_ancestor_and_cargo_home_configuration_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / 'source'
            snapshot.mkdir()
            config = root / '.cargo/config.toml'
            config.parent.mkdir()
            config.write_text('[build]\nrustflags = []\n')
            with self.assertRaisesRegex(release.ReleaseError, 'ancestor Cargo configuration') as error:
                release.check_cargo_configuration(snapshot)
            self.assertNotIn(tmp, str(error.exception))
            config.unlink()
            config = root / 'cargo-home/config'
            config.parent.mkdir()
            config.write_text('[build]\nrustflags = []\n')
            with self.assertRaisesRegex(release.ReleaseError, 'Cargo home configuration'):
                release.check_cargo_configuration(snapshot, {'CARGO_HOME': str(config.parent)})

    def test_olaf_policy_uses_build_options_not_invented_zig_flags(self):
        with tempfile.TemporaryDirectory(prefix='zig space ') as tmp:
            root = Path(tmp).resolve()
            args = release.olaf_privacy_arguments(root / 'source', root / 'work', root / 'tools/zig')
            self.assertEqual(args[0], '-Drelease-privacy=true')
            self.assertTrue(args[1].startswith('-Dprivacy-cflags='))
            native = shlex.split(Path(args[1].split('=', 1)[1]).read_text())
            for kind in ('ffile', 'fmacro', 'fdebug'):
                self.assertIn(f'-{kind}-prefix-map={root / "tools"}=/toolchain/zig', native)
        build = (ROOT / 'vendor/olaf/build.zig').read_text()
        self.assertIn('artifact.root_module.getGraph().modules', build)
        self.assertIn('mod.strip = true', build)
        self.assertIn('cflags_file', build)
        workflow = (ROOT / '.github/workflows/portable-build.yml').read_text()
        self.assertNotIn('cargo build', workflow)
        self.assertNotIn('cargo test', workflow)
        self.assertNotIn('zig build', workflow)

    def test_subprocess_errors_do_not_echo_commands_or_output(self):
        marker = 'gh' + 'p_' + 'Q' * 36
        with patch.object(release.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, marker, marker)):
            with self.assertRaises(release.ReleaseError) as error:
                release.run(['private-compiler', marker])
        self.assertNotIn(marker, str(error.exception))

    def test_cli_os_errors_and_unsafe_member_diagnostics_are_redacted(self):
        marker = 'gh' + 'p_' + 'T' * 36
        private = 'C:/' + 'Users/' + 'PrivatePerson/' + marker
        for name in (private, '../' + marker):
            with self.assertRaises(release.ReleaseError) as error:
                release.safe_name(name)
            self.assertNotIn(marker, str(error.exception))
            self.assertNotIn('PrivatePerson', str(error.exception))
        output = io.StringIO()
        with patch.object(release.sys, 'argv', ['release.py', 'verify', '--out-dir', '.']), \
                patch.object(release, 'verify', side_effect=OSError(private)), contextlib.redirect_stderr(output):
            self.assertEqual(release.main(), 1)
        self.assertNotIn(marker, output.getvalue())
        self.assertNotIn('PrivatePerson', output.getvalue())


class ArtifactPrivacyTests(unittest.TestCase):
    def test_instruction_bytes_and_embedded_urls_are_not_private_paths(self):
        for data in (bytes.fromhex('ff 5a 3a 2f 90 ff 00'),
                     b'Xhttps://example.org/project',
                     b'Xhttps://example.org/home/author/project',
                     b'not an http:// or https:// URL',
                     b'unrecognized to' + b'ken: "%s"', b'unrecognized to' + b'ken: "%T"',
                     ('\\Device' + '\\\\DosDeviDevices\\Voluume{').encode('utf-16-le')):
            release.check_privacy('artifact', data)
        for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
            release.check_privacy('artifact', b'X' + 'https://example.org/project'.encode(encoding))
            private = ('C:/' + 'Users/' + '\u6e2c\u8a66' + '/project/file.rs').encode(encoding)
            with self.assertRaises(release.ReleaseError):
                release.check_privacy('artifact', b'\xff' + private + b'\xff')

    def test_adjacent_single_character_drive_instruction_fragments(self):
        for data in (bytes.fromhex('3b443a5c3d'), bytes.fromhex('3b463a5c3d'),
                     bytes.fromhex('33453a5c35'), bytes.fromhex('2c76433a5c3d'),
                     bytes.fromhex('23463a5c25')):
            release.check_privacy('artifact', data)
        for value in ('Q:' + '/x', 'Q:' + '/private', 'prefixQ:' + '/x/y'):
            with self.assertRaises(release.ReleaseError):
                release.check_privacy('artifact', value.encode())
        with self.assertRaises(release.ReleaseError):
            release.check_privacy('artifact', bytes.fromhex('3b443a5c3d'), source=True)

    def test_private_strings_in_every_encoding_and_alignment(self):
        values = ['C:/' + 'Users/' + 'Private Person/project/file.rs',
                  '/home/' + 'runner/work/project/file.c', '/Users/' + 'PrivatePerson/work',
                  '/root/' + '.cargo/registry/file.rs', '\\\\' + 'PrivateServer\\source',
                  'gh' + 'p_' + 'Q' * 36, 'api_' + 'key="private-value-12345"',
                  '/private/var/' + 'folders/ab/private-build/file.c',
                  '/tmp/' + 'rustcABCD/file.c']
        for value in values:
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                for pad in (b'\0', b'\0\0', b'X', b'XY'):
                    with self.subTest(encoding=encoding, length=len(value), pad=len(pad)):
                        with self.assertRaises(release.ReleaseError) as error:
                            release.check_privacy('artifact', pad + value.encode(encoding) + b'\0\0')
                        self.assertNotIn(value, str(error.exception))

    def test_boundaries_known_roots_and_legitimate_attribution(self):
        value = ('gh' + 'p_' + 'W' * 36).encode()
        with self.assertRaises(release.ReleaseError):
            release.check_privacy('artifact', b'\0' * (65536 - 9) + value + b'\0')
        value = '/opt/' + 'operator-specific/location'
        for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
            with self.assertRaises(release.ReleaseError):
                release.check_privacy('artifact', b'X' + value.encode(encoding), forbidden_roots=(value,))
        release.check_privacy('LICENSE', b'Copyright 2026 Example Author\nhttps://example.org/home/author/project\n', source=True)

    def test_public_fixture_is_only_allowed_in_exact_source_context(self):
        name = 'patches/olaf/0003-release-local-source-build.patch'
        lines = (ROOT / name).read_text().splitlines()
        line = next(line for line in lines if release.hygiene.public_upstream_fixture(name, line))
        release.check_privacy(name, line.encode(), source=True)
        for other, data, source in ((name, line.encode(), False), ('other.patch', line.encode(), True),
                                    (name, (line + ' extra').encode(), True)):
            with self.assertRaises(release.ReleaseError):
                release.check_privacy(other, data, source=source)


if __name__ == '__main__':
    unittest.main()
