"""Source-only release checks: no compilation, audio, indexing or downloads."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_olaf", ROOT / "scripts/build_olaf.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def apply_patch_text(tree: dict[str, str], patch: str, reverse: bool = False) -> None:
    """Strict unified-diff replay, including added files, without Git/network."""
    for block in patch.split("diff --git ")[1:]:
        lines = block.splitlines(keepends=True)
        old = next(line[4:].strip() for line in lines if line.startswith("--- "))
        new = next(line[4:].strip() for line in lines if line.startswith("+++ "))
        before, after = (new, old) if reverse else (old, new)
        path = (after if before == "/dev/null" else before)[2:]
        source = [] if before == "/dev/null" else tree[path].splitlines(keepends=True)
        output, cursor = [], 0
        i = next(j for j, line in enumerate(lines) if line.startswith("@@ "))
        while i < len(lines):
            hunk = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
            if not hunk:
                raise AssertionError(f"Invalid patch hunk: {lines[i]!r}")
            old_start, old_n, new_start, new_n = [int(value) if value is not None else 1 for value in hunk.groups()]
            start, expected_n = (new_start, new_n) if reverse else (old_start, old_n)
            destination_n = old_n if reverse else new_n
            index = start - 1 if expected_n else start
            assert index >= cursor
            output.extend(source[cursor:index])
            cursor = index
            removed, added = 0, 0
            i += 1
            while i < len(lines) and not lines[i].startswith("@@ "):
                line = lines[i]
                sign, text = line[0], line[1:]
                if reverse:
                    sign = {"+": "-", "-": "+"}.get(sign, sign)
                assert sign in (" ", "+", "-"), f"Invalid diff line: {line!r}"
                if sign in (" ", "-"):
                    assert cursor < len(source) and source[cursor] == text, (path, cursor, text)
                    cursor += 1
                    removed += 1
                if sign in (" ", "+"):
                    output.append(text)
                    added += 1
                i += 1
            assert (removed, added) == (expected_n, destination_n), path
        output.extend(source[cursor:])
        if after == "/dev/null":
            assert not output
            del tree[path]
        else:
            tree[path] = "".join(output)


class SourceDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance = json.loads((ROOT / "vendor/olaf/PROVENANCE.json").read_text(encoding="utf-8"))

    def copy_inventory(self, destination: Path):
        for name in [*self.provenance["files"], "vendor/olaf/PROVENANCE.json"]:
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def test_inventory_and_hashes(self):
        self.assertEqual(builder.validate_sources(), self.provenance)
        self.assertGreater(len(self.provenance["files"]), 220)

    def test_source_import_and_embedded_asset_closure(self):
        # Check literal Zig source imports/assets and quoted C local headers.
        for component in ("olaf", "zigzag"):
            base = ROOT / "vendor" / component
            for path in base.rglob("*"):
                if path.suffix not in (".zig", ".c", ".h"):
                    continue
                text = path.read_text(encoding="utf-8")
                for asset in re.findall(r'@(?:import|embedFile)\("([^"\n]+)"\)', text):
                    if "." in asset or "/" in asset:
                        self.assertTrue((path.parent / asset).is_file(), f"{path}: {asset}")
                for header in re.findall(r'^\s*#\s*include\s+"([^"\n]+)"', text, re.M):
                    if header == "assert.h":  # Quoted system header in upstream olaf_runner.c.
                        continue
                    if header == "alloc-testing.h":
                        self.assertIn(path.name, ("hash-table.c", "queue.c"))
                        self.assertRegex(text, r'#ifdef ALLOC_TESTING\s+#include "alloc-testing.h"\s+#endif')
                        # This optional c-algorithms harness is absent upstream
                        # too, and is not enabled by any supported Olaf build.
                        self.assertNotIn("-DALLOC_TESTING", (base / "build.zig").read_text())
                        continue
                    candidates = [path.parent / header, base / "src" / header, base / "tests" / header]
                    self.assertTrue(any(p.is_file() for p in candidates), f"{path}: {header}")
        build = (ROOT / "vendor/olaf/build.zig").read_text(encoding="utf-8")
        for name in re.findall(r'"((?:\./)?(?:cli|src|tests)/[^"\n]+\.(?:c|zig|h|txt))"', build):
            self.assertTrue((ROOT / "vendor/olaf" / name).is_file(), name)

    def test_dependency_is_local_and_transitively_closed(self):
        self.assertEqual(self.provenance["zigzag"]["dependencies"], {})
        self.assertEqual(self.provenance["zigzag"]["upstream_revision"], "e16e2523972d174d7ca9783631cc90e2609fa55e")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.copy_inventory(root)
            path = root / "vendor/olaf/build.zig.zon"
            path.write_text(path.read_text().replace('../zigzag', '../unreviewed'), encoding="utf-8")
            manifest = root / "vendor/olaf/PROVENANCE.json"
            data = json.loads(manifest.read_text())
            data["files"]["vendor/olaf/build.zig.zon"]["sha256"] = builder.source_hash(path)
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(builder.BuildError, "committed ../zigzag"):
                builder.validate_sources(root)

    def test_missing_modified_and_unlisted_inputs_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.copy_inventory(root)
            source = root / "vendor/olaf/tests/olaf_matcher_v3_tests.c"
            original = source.read_bytes()
            source.unlink()
            with self.assertRaisesRegex(builder.BuildError, "Missing or unsafe"):
                builder.validate_sources(root)
            source.write_bytes(original + b"// changed\n")
            with self.assertRaisesRegex(builder.BuildError, "hash mismatch"):
                builder.validate_sources(root)
            source.write_bytes(original)
            (root / "vendor/olaf/accidental.raw").write_bytes(b"not audio")
            with self.assertRaisesRegex(builder.BuildError, "Unlisted"):
                builder.validate_sources(root)

    def test_dirty_change_coverage(self):
        self.assertEqual(set(self.provenance["olaf"]["dirty_files"]), {
            "build.zig", "cli/olaf_cli_config.zig", "cli/olaf_cli_core.zig",
            "cli/olaf_config.schema.json", "src/olaf_config.c", "src/olaf_config.h",
            "src/olaf_db.c", "src/olaf_fp_matcher.c",
            "tests/olaf_db_concurrency_tests.c", "tests/olaf_matcher_v3_tests.c",
        })
        expected = {
            "cli/olaf_cli_config.zig": ["skip_saturated_hashes: bool = false", "independent_time_votes: bool = false"],
            "cli/olaf_cli_core.zig": ["skipSaturatedHashes", "independentTimeVotes"],
            "src/olaf_fp_matcher.c": ["queryFingerprintT1 <= match->queryFingerprintT1", "UINT64_MAX-queryFingerprintHash", "Skipped saturated fingerprint lookup"],
            "src/olaf_db.c": ["while (rc == 0)", "A failed seek has no valid key/value"],
            "tests/olaf_db_concurrency_tests.c": ["assert(result==123)", "UINT64_MAX-5"],
            "tests/olaf_matcher_v3_tests.c": ["matcher v3 regressions passed", "assert(seen_hi==UINT64_MAX"],
            "src/mdb.c": ['MDB_NAME("\\\\data.mdb")', 'MDB_NAME("\\\\lock.mdb")'],
        }
        for name, needles in expected.items():
            text = (ROOT / "vendor/olaf" / name).read_text(encoding="utf-8")
            for needle in needles:
                self.assertIn(needle, text, name)

    def test_patch_series_reproduces_base_working_and_final_source(self):
        series = (ROOT / "patches/olaf/series").read_text().splitlines()
        self.assertEqual(len(series), 3)
        records = {name.removeprefix("vendor/olaf/"): record for name, record in self.provenance["files"].items()
                   if name.startswith("vendor/olaf/") and "source_lf_sha256" in record}
        final = {name: (ROOT / "vendor/olaf" / name).read_text(encoding="utf-8") for name in records}
        tree = final.copy()
        apply_patch_text(tree, (ROOT / "patches/olaf" / series[2]).read_text(encoding="utf-8"), reverse=True)
        for name, record in records.items():
            self.assertEqual(builder.sha256(tree[name].encode()), record["source_lf_sha256"], name)
        for patch in reversed(series[:2]):
            apply_patch_text(tree, (ROOT / "patches/olaf" / patch).read_text(encoding="utf-8"), reverse=True)
        for name, record in records.items():
            if record["upstream_sha256"] is None:
                self.assertNotIn(name, tree)
            else:
                self.assertEqual(builder.sha256(tree[name].encode()), record["upstream_sha256"], name)
        for patch in series:
            apply_patch_text(tree, (ROOT / "patches/olaf" / patch).read_text(encoding="utf-8"))
        self.assertEqual(tree, final)

    def test_no_audio_binaries_private_metadata_or_implicit_download(self):
        forbidden = {".mp3", ".wav", ".raw", ".flac", ".m4a", ".wasm", ".exe", ".dll", ".db", ".mdb"}
        for name in self.provenance["files"]:
            self.assertNotIn(Path(name).suffix.lower(), forbidden)
            self.assertNotIn(".git", Path(name).parts)
            self.assertNotIn("HANDOFF", name)
        text = (ROOT / "vendor/olaf/tests/dataset_download.zig").read_text()
        self.assertNotIn("http.Client", text)
        self.assertNotIn(".fetch(", text)
        self.assertIn("error.MissingAudioFixture", text)
        build = (ROOT / "vendor/olaf/build.zig").read_text()
        self.assertIn("if (!audio_tests)", build)
        self.assertIn("b.addFail(", build)
        for step in ("test-matcher-v3", "test-db-safety", "test-config-safety"):
            self.assertIn(f'b.step("{step}"', build)

    def test_licenses_preserve_component_terms(self):
        self.assertIn("GNU AFFERO GENERAL PUBLIC LICENSE", (ROOT / "vendor/olaf/LICENSE").read_text())
        self.assertIn("any later version", (ROOT / "vendor/olaf/src/olaf_config.c").read_text())
        self.assertIn("Matthew Meszaros", (ROOT / "vendor/zigzag/LICENSE").read_text())
        self.assertIn("Version 2.8", (ROOT / "vendor/olaf/notices/OpenLDAP-LICENSE.txt").read_text())


class BuildInterfaceTests(unittest.TestCase):
    def test_check_only_never_invokes_tools_or_creates_output(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder.subprocess, "run") as run:
            output = Path(tmp) / "absent"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(builder.main(["--check-only", "--target", "windows-x64", "--out-dir", str(output)]), 0)
            run.assert_not_called()
            self.assertFalse(output.exists())

    def test_zig_missing_and_wrong_version_fail_clearly(self):
        with mock.patch.object(builder.shutil, "which", return_value=None):
            with self.assertRaisesRegex(builder.BuildError, "Zig 0.16.0 is required"):
                builder.find_zig()
        with mock.patch.object(builder.shutil, "which", return_value="zig"), mock.patch.object(builder.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "0.15.2\n", "")):
            with self.assertRaisesRegex(builder.BuildError, "Expected Zig 0.16.0"):
                builder.find_zig()

    def test_all_target_output_layouts_and_sequential_baseline_build(self):
        for target, (triple, executable) in builder.TARGETS.items():
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                calls = []

                def fake_run(command, **kwargs):
                    calls.append(command)
                    if command[1:] == ["version"]:
                        return subprocess.CompletedProcess(command, 0, "0.16.0\n", "")
                    self.assertEqual(command[1:3], ["build", "install"])
                    self.assertIn(f"-Dtarget={triple}", command)
                    self.assertIn("-Dcpu=baseline", command)
                    self.assertIn("-j1", command)
                    self.assertIn("-Doptimize=ReleaseFast", command)
                    self.assertEqual(kwargs["cwd"], ROOT / "vendor/olaf")
                    prefix = Path(command[command.index("--prefix") + 1])
                    binary = prefix / "bin" / executable
                    self.assertFalse(binary.exists())
                    binary.parent.mkdir(parents=True)
                    binary.write_bytes(b"mock newly compiled Olaf")
                    return subprocess.CompletedProcess(command, 0)

                with mock.patch.object(builder.shutil, "which", return_value="zig"), mock.patch.object(builder.subprocess, "run", side_effect=fake_run):
                    runtime = builder.build_runtime(target, Path(tmp))
                self.assertEqual(runtime, Path(tmp) / "olaf-runtime")
                for name in (executable, "OLAF-LICENSE", "OLAF-NOTICES.txt", "PROVENANCE.json", "BUILD-INFO.json", "notices/Zigzag-LICENSE.txt", "notices/OpenLDAP-LICENSE.txt"):
                    self.assertTrue((runtime / name).is_file(), name)
                info = json.loads((runtime / "BUILD-INFO.json").read_text())
                self.assertEqual(info["executable_sha256"], builder.sha256(b"mock newly compiled Olaf"))
                self.assertEqual(info["target"], target)
                self.assertEqual(len(calls), 2)

    def test_build_failure_and_missing_artifact_do_not_package_old_runtime(self):
        for effect in (subprocess.CalledProcessError(1, ["zig", "build"]), subprocess.CompletedProcess([], 0)):
            with self.subTest(effect=effect), tempfile.TemporaryDirectory() as tmp:
                with mock.patch.object(builder, "find_zig", return_value="zig"), mock.patch.object(builder.subprocess, "run", side_effect=effect if isinstance(effect, Exception) else None, return_value=effect):
                    with self.assertRaises(builder.BuildError):
                        builder.build_runtime("linux-x64", Path(tmp))
                self.assertFalse((Path(tmp) / "olaf-runtime").exists())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "olaf-runtime"
            runtime.mkdir()
            marker = runtime / "settings.json"
            marker.write_text("preserve")
            with mock.patch.object(builder.subprocess, "run") as run:
                with self.assertRaisesRegex(builder.BuildError, "Refusing to replace"):
                    builder.build_runtime("windows-x64", Path(tmp))
                run.assert_not_called()
            self.assertEqual(marker.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
