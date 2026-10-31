"""Compiler command/policy tests only: never execute compilers or applications."""
import contextlib
import importlib.util
import io
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

    def test_four_targets_encoded_rust_and_native_flags_with_spaces(self):
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
                    prefix = '/clang:' if target == 'windows-x64' else ''
                    for kind in ('ffile', 'fdebug', 'fmacro'):
                        flag = f'{prefix}-{kind}-prefix-map={snapshot}=/source'
                        if target == 'windows-x64':
                            self.assertIn(subprocess.list2cmdline([flag]), native_response)
                        else:
                            self.assertIn(flag, shlex.split(native_response))
                    self.assertEqual(env['CC_SHELL_ESCAPED_FLAGS'], '1')
                    self.assertEqual(env['CFLAGS'], env['CXXFLAGS'])
                    if target == 'windows-x64':
                        self.assertEqual(env['CC'], 'clang-cl')
                        self.assertIn('-Clink-arg=/DEBUG:NONE', flags)
                        self.assertIn('-Clink-arg=/PDBALTPATH:local-shazam.pdb', flags)

    def test_hostile_environment_is_not_a_release_override(self):
        hostile = {key: 'hostile-value' for key in (
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
            'CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_RUSTFLAGS', 'CARGO_BUILD_RUSTC',
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
