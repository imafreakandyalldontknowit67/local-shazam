"""Isolated release-source policy tests; no application/audio imports or builds."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
CHECKER = REPO / 'scripts' / 'check_release_hygiene.py'


class HygieneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='source-hygiene-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env['PYTHONDONTWRITEBYTECODE'] = '1'
        self.env['PYTHONIOENCODING'] = 'utf-8'

    def write(self, name, content='safe text\n'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding='utf-8')
        return path

    def git(self, *args):
        if not shutil.which('git'):
            self.skipTest('Git is required for miniature index fixtures')
        result = subprocess.run(['git', '-C', str(self.root), *args], env=self.env,
                                capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, 'miniature Git fixture command failed')
        return result.stdout

    def init_git(self):
        self.git('init', '--quiet')

    def run_check(self, *args, expected=0):
        result = subprocess.run([sys.executable, '-B', str(CHECKER), '--root', str(self.root), *args],
                                capture_output=True, text=True, encoding='utf-8', env=self.env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_reviewed_screenshot_requires_exact_path_and_bytes(self):
        name = 'assets/screenshots/windows-menu.png'
        data = (REPO / name).read_bytes()
        self.write(name, data)
        self.run_check()
        self.write(name, data + b'unreviewed metadata')
        self.run_check(expected=1)
        self.write(name, data)
        self.write('assets/screenshots/other.png', data)
        self.run_check(expected=1)

    def test_nested_case_variant_artifacts_in_source(self):
        forbidden = ['deep/SONG.Mp3', 'nested/a.FLAC', 'video/clip.MOV', 'deep/clip.F32LE',
                     'nested/state.SQLITE3-WaL', 'db/data.MdB', 'deep/cache.LMDB-lock',
                     'deep/program.ExE', 'deep/archive.ZIP', 'deep/crash.DMP',
                     'deep/access.LOG', 'deep/.ENV.production', 'deep/HANDOFF.md',
                     'deep/RECOVERY-NOTES.txt', 'deep/cloud.PEM',
                     'deep/LIBRARY-BENCHMARK.JsOn', 'deep/RUST-VALIDATION.json',
                     'deep/OLAF-APP-INTEGRATION-RESULTS.json', 'deep/.git-credentials',
                     'deep/.cargo/credentials.toml']
        for name in forbidden:
            self.write(name)
        result = self.run_check(expected=1)
        self.assertEqual(result.count('FAIL '), len(forbidden))
        self.assertIn('redacted path; id=', result)

    def test_local_directories_are_rejected_without_reading_contents(self):
        dirs = ['nested/TaRgEt', 'nested/BuIlD', 'nested/DiSt', 'nested/BeNcHmArKs',
                'nested/LoCaL-OlAf', 'nested/OlAf-RuNtImE', 'nested/ExPeRiMeNtS',
                'nested/EvIdEnCe', 'nested/.VeNv', 'nested/.CaChE', 'nested/ToolChains',
                'nested/.CaRgO/ReGiStRy']
        for directory in dirs:
            self.write(directory + '/private.txt', 'gh' + 'p_' + 'A' * 36)
        result = self.run_check(expected=1)
        self.assertEqual(result.count('local-artifact-directory'), len(dirs))
        self.assertNotIn('likely-credential', result)

    def test_already_tracked_and_force_added_ignored_files_fail(self):
        self.init_git()
        self.write('deep/song.MP3', b'not real audio')
        self.git('add', '.')
        self.write('.gitignore', '*.MP3\n')
        self.git('add', '.gitignore')
        self.run_check(expected=1)
        self.run_check('--staged', expected=1)
        self.assertTrue((self.root / 'deep/song.MP3').exists())

    def test_checkout_does_not_scan_ignored_or_untracked_data(self):
        self.init_git()
        self.write('source.py', 'print("safe")\n')
        self.git('add', 'source.py')
        self.write('personal.wav', b'not real audio')
        self.write('.gitignore', '*.wav\n')
        self.run_check()
        self.run_check('--staged')

    def test_staged_content_not_clean_worktree(self):
        self.init_git()
        payload = 'gh' + 'p_' + 'B' * 36
        self.write('source.txt', payload)
        self.git('add', 'source.txt')
        self.write('source.txt', 'now safe')
        result = self.run_check('--staged', expected=1)
        self.assertIn('likely-credential', result)
        self.assertNotIn(payload, result)
        self.run_check()

    def test_staged_safe_content_not_dirty_worktree(self):
        self.init_git()
        self.write('source.txt')
        self.git('add', 'source.txt')
        self.write('source.txt', 'gh' + 'p_' + 'C' * 36)
        self.run_check('--staged')
        self.run_check(expected=1)

    def test_staged_whole_index_not_only_new_changes(self):
        self.init_git()
        self.write('source.txt', 'gh' + 'p_' + 'D' * 36)
        self.git('add', 'source.txt')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.write('new.txt')
        self.git('add', 'new.txt')
        self.run_check('--staged', expected=1)

    def test_staged_deleted_entries_are_not_read(self):
        self.init_git()
        self.write('source.txt', 'gh' + 'p_' + 'E' * 36)
        self.git('add', 'source.txt')
        self.git('rm', '--cached', 'source.txt')
        self.run_check('--staged')
        self.assertTrue((self.root / 'source.txt').exists())

    def test_credentials_redacted_in_every_file_kind(self):
        cases = {
            'vendor/component/a.c': 'api_' + 'key = "notpublic123"',
            'patches/change.patch': '+pass' + 'word: "hunter2"',
            'Cargo.toml': 'auth_to' + 'ken = "dont-publish-me"',
            'LICENSE': '-----BEGIN ' + 'RSA PRIVATE KEY-----',
            'docs/basic.md': 'https://account:' + 'privatevalue@host.invalid/',
            'source.txt': 'Authorization: Bearer ' + 'private-token-value',
        }
        for name, content in cases.items():
            self.write(name, content)
        result = self.run_check(expected=1)
        self.assertEqual(result.count('likely-credential'), len(cases))
        for value in ('notpublic123', 'hunter2', 'dont-publish-me', 'privatevalue', 'private-token-value'):
            self.assertNotIn(value, result)
        self.assertIn('"Cargo.toml":1', result)

    def test_bare_env_and_yaml_credentials_are_redacted(self):
        self.write('config.txt', 'API_' + 'KEY=unquotedvalue\npass' + 'word: hunter2\n')
        result = self.run_check(expected=1)
        self.assertEqual(result.count('likely-credential'), 2)
        self.assertNotIn('unquotedvalue', result)
        self.assertNotIn('hunter2', result)

    def test_personal_paths_redacted(self):
        values = ['C:/' + 'Users/' + 'PrivatePerson/Documents/music',
                  'C:\\' + 'Users\\' + 'PrivatePerson\\Documents',
                  '/home/' + 'PrivatePerson/library', '/Users/' + 'PrivatePerson/Desktop',
                  '/root/' + 'private-project', '\\\\' + 'PrivateServer\\Library',
                  'D:/' + 'PrivateProject/library', '/home/' + 'user/PrivateCollection',
                  '/Volumes/' + 'PrivateDrive/music', '/mnt/d/' + 'PrivateDrive/music',
                  '/media/' + 'PrivateDrive/music']
        self.write('notes.txt', '\n'.join(values))
        result = self.run_check(expected=1)
        self.assertEqual(result.count('personal-absolute-path'), len(values))
        for value in ('PrivatePerson', 'PrivateServer', 'PrivateProject', 'PrivateCollection', 'PrivateDrive'):
            self.assertNotIn(value, result)

    def test_inherited_alternate_git_index_does_not_change_root(self):
        self.init_git()
        self.write('source.txt', 'gh' + 'p_' + 'H' * 36)
        self.git('add', 'source.txt')
        self.env['GIT_INDEX_FILE'] = str(Path(self.temp.name) / 'empty-index')
        self.run_check('--staged', expected=1)

    def test_secret_in_filename_is_redacted(self):
        payload = 'gh' + 'p_' + 'F' * 36
        self.write(payload + '.txt', 'safe content')
        result = self.run_check(expected=1)
        self.assertNotIn(payload, result)
        self.assertIn('redacted path; id=', result)

    def test_source_patch_license_lock_and_generic_example_allowances(self):
        names = ['vendor/olaf/src/mdb.c', 'vendor/zigzag/src/root.zig',
                 'licenses/third-party/LICENSE', 'licenses/LICENSE-APACHE',
                 'rust-app/Cargo.lock', 'pyproject.toml', 'patches/fix.patch',
                 'assets/banner.svg', 'scripts/build.py', '.gitattributes', '.gitignore',
                 '.cargo/config.toml', 'vendor/textual/index.ts', 'vendor/textual/module.mts']
        for name in names:
            self.write(name)
        self.write('docs/examples.md', '\n'.join([
            'https://example.org/home/someone/project',
            'https://github.com/author/project',
            'C:/Music', 'D:/Clips/example.wav', '/path/to/music', '/usr/local/bin',
            '/home/<user>/project', 'C:/Users/<user>/Music', '/home/user/project',
            'api_' + 'key = "${API_KEY}"', 'pass' + 'word: "<password>"',
        ]))
        self.run_check()

    def test_renamed_binary_media_database_and_invalid_encoding_fail(self):
        for i, content in enumerate([b'hello\x00world', b'\xff\xfeA\0', b'\x7fELF',
                                     b'RIFFthisisnotanaudiofixture', b'SQLite format 3\0',
                                     b'ID3renamed', b'\x1bcontrol', b'MZnot-an-executable-fixture']):
            self.write(f'vendor/lib/source{i}.txt', content)
        result = self.run_check(expected=1)
        self.assertEqual(result.count('binary-source'), 8)

    def test_oversized_source_fails_without_unbounded_read(self):
        path = self.write('oversized.txt', b'')
        with path.open('wb') as stream:
            stream.seek(32 * 1024 * 1024)
            stream.write(b'X')
        self.assertIn('oversized-source', self.run_check(expected=1))
        self.init_git()
        self.git('add', 'oversized.txt')
        self.assertIn('no blob content was read', self.run_check('--staged', expected=1))

    def test_extracted_tree_never_honors_gitignore(self):
        self.write('.gitignore', '*.MP3\n')
        self.write('nested/leak.MP3')
        self.run_check(expected=1)

    def test_no_git_metadata_excludes_nested_git_and_worktrees(self):
        self.write('source.txt')
        self.write('.worktrees/another/private.wav')
        self.write('nested/.GiT/objects/private.wav')
        self.write('nested/.WoRkTrEeS/another/private.wav')
        self.run_check()

    def test_staging_inside_checkout_uses_recursive_mode(self):
        self.init_git()
        self.root = self.root / 'staging'
        self.root.mkdir()
        self.write('leak.wav')
        self.run_check(expected=1)

    def test_staged_requires_checkout(self):
        self.run_check('--staged', expected=2)

    def test_invalid_root_is_redacted(self):
        self.root = self.root / 'private-missing-directory'
        result = self.run_check(expected=2)
        self.assertNotIn('private-missing-directory', result)

    def test_staged_symlink_git_mode_rejected_even_without_os_links(self):
        self.init_git()
        blob = subprocess.run(['git', '-C', str(self.root), 'hash-object', '-w', '--stdin'],
                              input=b'../../outside', capture_output=True, env=self.env, check=True).stdout.strip()
        self.git('update-index', '--add', '--cacheinfo', '120000,' + blob.decode() + ',link')
        self.run_check('--staged', expected=1)

    def make_link(self, target, link, is_directory=False):
        try:
            link.symlink_to(target, target_is_directory=is_directory)
        except (OSError, NotImplementedError):
            self.skipTest('OS symlink creation is unavailable; Git symlink-mode test still runs')

    def test_extracted_symlink_not_followed(self):
        outside = Path(self.temp.name) / 'outside.txt'
        outside.write_text('gh' + 'p_' + 'G' * 36)
        self.make_link(outside, self.root / 'link')
        result = self.run_check(expected=1)
        self.assertIn('symlink-or-reparse-point', result)
        self.assertNotIn('likely-credential', result)

    def test_tracked_file_beneath_symlink_not_followed(self):
        self.init_git()
        self.write('directory/source.txt')
        self.git('add', '.')
        (self.root / 'directory/source.txt').unlink()
        (self.root / 'directory').rmdir()
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (outside / 'source.txt').write_text('safe')
        self.make_link(outside, self.root / 'directory', True)
        result = self.run_check(expected=1)
        self.assertIn('symlink-or-reparse-point', result)
        self.run_check('--staged')

    def test_ignore_patterns_cover_case_and_depth_without_hiding_source(self):
        self.init_git()
        self.write('.gitignore', (REPO / '.gitignore').read_text())
        blocked = ['nested/a.Mp3', 'nested/a.SQLITE3-WaL', 'nested/BeNcHmArKs/a.txt',
                   'a/LoCaL-OlAf/state.txt', 'a/TaRgEt/foo', 'a/.ENV.local',
                   'a/CLAUDE.MD', 'a/private.HANDOFF.md', 'a/app.ExE', 'a/sample.F32LE',
                   'a/.WoRkTrEeS/state.txt', 'a/.CaRgO/registry/index.txt',
                   'a/.cargo/credentials.toml']
        allowed = ['rust-app/Cargo.lock', 'vendor/olaf/src/mdb.c', 'vendor/zigzag/LICENSE',
                   'licenses/third-party/LICENSE', 'patches/0001-fix.patch', 'build.zig',
                   'scripts/build.py', 'pyproject.toml', '.cargo/config.toml',
                   'vendor/textual/index.ts', 'vendor/textual/module.mts']
        for name in blocked:
            result = subprocess.run(['git', '-C', str(self.root), '-c', 'core.ignorecase=false',
                                     'check-ignore', '--no-index', name], env=self.env, capture_output=True)
            self.assertEqual(result.returncode, 0, name)
        for name in allowed:
            result = subprocess.run(['git', '-C', str(self.root), '-c', 'core.ignorecase=false',
                                     'check-ignore', '--no-index', name], env=self.env, capture_output=True)
            self.assertEqual(result.returncode, 1, name)


class LicenseInventoryTests(unittest.TestCase):
    def test_olaf_notice_copy_hashes(self):
        inventory = json.loads((REPO / 'licenses/olaf-inventory.json').read_text(encoding='utf-8'))
        for record in inventory['copies']:
            data = (REPO / record['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'], record['path'])
            # Existing vendor attributes normalize source text; compare text
            # semantically across checkout line endings, not by machine newline.
            self.assertEqual(data.replace(b'\r\n', b'\n'),
                             (REPO / record['source']).read_bytes().replace(b'\r\n', b'\n'))

    def test_license_file_evidence_hashes_and_paths(self):
        inventory = json.loads((REPO / 'licenses/rust-inventory.json').read_text(encoding='utf-8'))
        self.assertTrue(inventory['packages'])
        for package in inventory['packages']:
            self.assertEqual(len(package['checksum']), 64)
            self.assertTrue(package['source'].startswith('https://static.crates.io/crates/'))
            for record in package['files']:
                path = REPO / record['path']
                path.resolve().relative_to(REPO / 'licenses')
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'], record['path'])

    def test_inventory_matches_lock_without_cargo_or_audio(self):
        # The application supports Python 3.10; tomllib is available from 3.11.
        # Use only the lockfile's simple package fields rather than a new dependency.
        import re
        lock = (REPO / 'rust-app/Cargo.lock').read_bytes().replace(b'\r\n', b'\n')
        inventory = json.loads((REPO / 'licenses/rust-inventory.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(lock).hexdigest(), inventory['cargo_lock_sha256_lf'])
        locked = set()
        for section in lock.decode().split('[[package]]')[1:]:
            if 'source = "registry+' not in section:
                continue
            fields = dict(re.findall(r'^(name|version|checksum) = "([^"]+)"', section, re.M))
            locked.add((fields['name'], fields['version'], fields['checksum']))
        listed = {(p['name'], p['version'], p['checksum']) for p in inventory['packages']}
        self.assertEqual(listed, locked)


class PublicFixtureScopeTests(unittest.TestCase):
    def test_public_fixture_exception_is_exact_and_path_scoped(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('hygiene_gate', CHECKER)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        name = 'patches/olaf/0003-release-local-source-build.patch'
        lines = (REPO / name).read_text(encoding='utf-8').splitlines()
        allowed = [line for line in lines if gate.public_upstream_fixture(name, line)]
        self.assertEqual(len(allowed), 1)
        self.assertFalse(gate.public_upstream_fixture('other.patch', allowed[0]))
        self.assertFalse(gate.public_upstream_fixture(name, allowed[0] + ' extra'))


if __name__ == '__main__':
    unittest.main()
