"""Static archive/package policy checks; no legacy imports, builds or audio/data I/O.

Run from a full checkout with Python 3.11+. The archived indexing suite is not
discovered or executed here. Inventory fixtures contain synthetic text only.
"""
import ast
import copy
import fnmatch
import importlib.util
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
ARCHIVE = REPO / "legacy/python"
MODULES = (
    "__init__", "__main__", "audio", "cli", "config", "database",
    "fingerprint", "indexer", "matcher", "scanner",
)
MOVED = tuple(f"shazam/{name}.py" for name in MODULES) + (
    "start.py", "pyproject.toml", "requirements.txt", "tests/test_indexing.py",
)
ARCHIVED = MOVED + ("README.md", "LICENSE", "MANIFEST.in")

# Only the standard-library release inventory helper is imported, never shazam.
SPEC = importlib.util.spec_from_file_location(
    "legacy_archive_release_policy", REPO / "scripts/release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def source(relative):
    return (ARCHIVE / relative).read_text(encoding="utf-8")


def syntax(relative):
    return ast.parse(source(relative), filename=relative)


def assignment(tree, name):
    return next(node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name
                        for target in node.targets))


class LegacyArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = tomllib.loads(source("pyproject.toml"))
        cls.project = cls.manifest["project"]
        cls.cfg = release.config(REPO)

    def test_source_layout_and_no_obsolete_root_entrypoints(self):
        for name in ARCHIVED:
            with self.subTest(path=name):
                self.assertTrue((ARCHIVE / name).is_file())
                self.assertFalse((ARCHIVE / name).is_symlink())
                if name.endswith(".py"):
                    syntax(name)  # Parse only; never import/execute application code.
        for name in MOVED:
            with self.subTest(old_path=name):
                self.assertFalse((REPO / name).exists())
        # Do not walk old directories: ignored operator files may remain there.

    def test_version_and_both_cli_entrypoints(self):
        self.assertEqual(self.project["name"], "local-shazam")
        self.assertEqual(self.project["version"], "1.0.1")
        self.assertEqual(self.project["requires-python"], ">=3.10")
        version = ast.literal_eval(assignment(syntax("shazam/__init__.py"), "__version__"))
        self.assertEqual(version, self.project["version"])
        self.assertEqual(self.project["scripts"], {"shazam": "shazam.cli:cli"})
        main = syntax("shazam/__main__.py")
        self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == "shazam.cli"
                            and any(a.name == "cli" for a in n.names) for n in main.body))
        self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == "cli" for n in ast.walk(main)))
        cli = syntax("shazam/cli.py")
        commands = {n.name for n in cli.body if isinstance(n, ast.FunctionDef)
                    and any(isinstance(d, ast.Call) and ast.unparse(d.func) == "cli.command"
                            for d in n.decorator_list)}
        self.assertEqual(commands, {"bootstrap", "add", "match", "status", "remove"})

    def test_discovery_is_local_and_excludes_nonpackages(self):
        settings = self.manifest["tool"]["setuptools"]
        find = settings["packages"]["find"]
        self.assertEqual(find["where"], ["."])
        self.assertEqual(find["include"], ["shazam", "shazam.*"])
        self.assertIs(find["namespaces"], False)
        self.assertIs(settings["include-package-data"], False)
        for name, expected in (("shazam", True), ("shazam.child", True),
                               ("shazam_other", False), ("tests", False),
                               ("rust-app", False), ("vendor", False), (".venv", False)):
            with self.subTest(package=name):
                self.assertEqual(any(fnmatch.fnmatchcase(name, p) for p in find["include"]),
                                 expected)
        known = {"shazam"} | {f"shazam.{name}" for name in MODULES}
        for name in MODULES:
            for node in ast.walk(syntax(f"shazam/{name}.py")):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("shazam"):
                    self.assertIn(node.module, known)

    def test_standalone_metadata_and_source_manifest(self):
        self.assertEqual(self.manifest["build-system"], {
            "requires": ["setuptools>=77.0.3"], "build-backend": "setuptools.build_meta",
        })
        self.assertEqual(self.project["readme"], "README.md")
        self.assertEqual(self.project["license"], "MIT")
        self.assertEqual(self.project["license-files"], ["LICENSE"])
        included = set()
        for line in source("MANIFEST.in").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            command, *names = line.split()
            self.assertEqual(command, "include")  # No recursive workspace/data inclusion.
            for name in names:
                self.assertNotIn("*", name)
                self.assertNotIn("..", Path(name).parts)
                self.assertTrue((ARCHIVE / name).is_file())
            included.update(names)
        self.assertEqual(included, {
            "LICENSE", "README.md", "requirements.txt", "start.py", "tests/test_indexing.py",
        })

    def test_license_is_a_complete_verbatim_copy(self):
        original = (REPO / "LICENSE").read_bytes()
        self.assertEqual((ARCHIVE / "LICENSE").read_bytes(), original)
        self.assertTrue(original.startswith(b"MIT License"))
        self.assertIn(b"Copyright (c) 2026", original)
        self.assertIn(b"Permission is hereby granted", original)
        self.assertIn(b'THE SOFTWARE IS PROVIDED "AS IS"', original)
        self.assertTrue(original.rstrip().endswith(b"SOFTWARE."))

    def test_runtime_requirements_and_launcher_agree(self):
        requirements = [line.strip() for line in source("requirements.txt").splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
        expected = ["click>=8.0", "numpy>=1.24", "scipy>=1.10", "tqdm>=4.60"]
        self.assertEqual(requirements, expected)
        self.assertEqual(self.project["dependencies"], expected)
        external = set()
        for name in (*[f"shazam/{n}.py" for n in MODULES], "start.py"):
            for node in ast.walk(syntax(name)):
                if isinstance(node, ast.Import):
                    external.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    external.add(node.module.split(".")[0])
        self.assertEqual(external - sys.stdlib_module_names - {"shazam"},
                         {"click", "numpy", "scipy", "tqdm"})
        installer = next(n for n in syntax("start.py").body
                         if isinstance(n, ast.FunctionDef) and n.name == "auto_install_deps")
        loop = next(n for n in installer.body if isinstance(n, ast.For))
        self.assertEqual(ast.literal_eval(loop.iter), ["click", "numpy", "scipy", "tqdm"])

    def test_database_and_requirements_paths_remain_distinct(self):
        self.assertEqual(ast.literal_eval(assignment(syntax("shazam/database.py"), "DEFAULT_DB")),
                         "shazam.db")
        launcher = syntax("start.py")
        for name, expression in {
            "SCRIPT_DIR": "os.path.dirname(os.path.abspath(__file__))",
            "DB_PATH": "os.path.join(SCRIPT_DIR, 'shazam.db')",
            "REQUIREMENTS": "os.path.join(SCRIPT_DIR, 'requirements.txt')",
        }.items():
            with self.subTest(name=name):
                self.assertEqual(ast.dump(assignment(launcher, name)),
                                 ast.dump(ast.parse(expression, mode="eval").body))
        cli = syntax("shazam/cli.py")
        options = [n for n in ast.walk(cli) if isinstance(n, ast.Call)
                   and ast.unparse(n.func) == "click.option"
                   and any(isinstance(a, ast.Constant) and a.value == "--db" for a in n.args)]
        self.assertEqual(len(options), 5)
        for option in options:
            self.assertTrue(any(k.arg == "default" and isinstance(k.value, ast.Name)
                                and k.value.id == "DEFAULT_DB" for k in option.keywords))

    def test_historical_limits_and_regression_suite_are_retained(self):
        decode = next(n for n in syntax("shazam/audio.py").body
                      if isinstance(n, ast.FunctionDef) and n.name == "decode_audio")
        self.assertEqual([ast.literal_eval(n) for n in decode.args.defaults], [120, 30])
        self.assertEqual(ast.literal_eval(assignment(syntax("shazam/config.py"), "FILE_HASH_BYTES")),
                         8192)
        archived_tests = syntax("tests/test_indexing.py")
        cases = [n for n in ast.walk(archived_tests)
                 if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        self.assertEqual(len(cases), 5)
        readme = source("README.md")
        for phrase in ("archived regression suite", "no automatic migration",
                       "current working directory", "legacy/python/shazam.db",
                       "pip install -r", "Tkinter", "python -m shazam"):
            self.assertIn(phrase, readme)

    def test_native_source_allowlists_exclude_old_and_archived_application(self):
        rules = self.cfg["source_inventory"]
        candidates = list(MOVED) + [f"legacy/python/{name}" for name in ARCHIVED]
        candidates += ["legacy/python/shazam/extra.py", "legacy/python/shazam.db",
                       "legacy/python/.venv/pyvenv.cfg"]  # Names only, never opened.
        for group in ("app", "olaf"):
            for name in candidates:
                with self.subTest(group=group, path=name):
                    self.assertFalse(release.matches(name, rules["common"] + rules[group]))
                    self.assertFalse(release.matches(name, rules["required"]))

    def test_native_engines_and_build_inputs_remain_in_place_and_allowlisted(self):
        paths = {
            "app": ("rust-app/Cargo.toml", "rust-app/Cargo.lock", "rust-app/src/main.rs",
                    "rust-app/src/lib.rs", "rust-app/src/audio.rs", "rust-app/src/dsp.rs",
                    "rust-app/src/index.rs", "rust-app/src/store.rs", "rust-app/src/olaf.rs"),
            "olaf": ("vendor/olaf/build.zig", "vendor/olaf/build.zig.zon",
                     "vendor/olaf/cli/olaf_cli.zig", "vendor/olaf/src/mdb.c",
                     "vendor/olaf/LICENSE", "vendor/zigzag/build.zig",
                     "vendor/zigzag/LICENSE", "vendor/olaf/wasm/package.json",
                     "patches/olaf/0003-release-local-source-build.patch"),
            "common": ("scripts/release.py", "scripts/build_olaf.py",
                       "scripts/check_release_hygiene.py", "Build-Rust.ps1",
                       "rust-toolchain.toml", "LICENSE", "THIRD_PARTY_NOTICES.md",
                       "licenses/olaf/AGPL-3.0.txt"),
        }
        rules = self.cfg["source_inventory"]
        for group, names in paths.items():
            for name in names:
                with self.subTest(group=group, path=name):
                    self.assertTrue((REPO / name).is_file())
                    self.assertTrue(release.matches(name, rules[group]))
        native = (REPO / "rust-app/src/main.rs").read_text(encoding="utf-8")
        self.assertIn("Backend::Rust", native)
        self.assertIn("Backend::Olaf", native)

    def test_inventory_api_ignores_legacy_without_reading_it(self):
        cfg = copy.deepcopy(self.cfg)
        # This fixture isolates selection; production required inputs are unchanged.
        cfg["source_inventory"]["required"] = []
        native = ("rust-app/src/main.rs", "vendor/olaf/src/mdb.c", "scripts/build_olaf.py")
        legacy = list(MOVED) + [f"legacy/python/{name}" for name in ARCHIVED]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in native:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic source fixture\n", encoding="utf-8")
            # Legacy paths deliberately do not exist: opening any would fail.
            with patch.object(release, "run", side_effect=AssertionError("No subprocesses")):
                result = release.inventory(root, cfg, names=[*native, *legacy])
            selected = set(result["app"]) | set(result["olaf"])
            self.assertEqual(selected, set(native))
            self.assertTrue(selected.isdisjoint(legacy))

    def test_binary_payload_policy_has_no_legacy_application_inputs(self):
        # Inspect the existing final binary allowlist, without staging/executing a build.
        tree = ast.parse((REPO / "scripts/release.py").read_text(encoding="utf-8"))
        verify = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "verify")
        allowed = assignment(verify, "allowed")
        self.assertEqual(ast.dump(allowed), ast.dump(ast.parse(
            "{PROVENANCE, 'SETUP.txt', 'LICENSE', 'THIRD_PARTY_NOTICES.md', "
            "'local-shazam' + exe} | set(legal)", mode="eval").body))
        guards = [n for n in ast.walk(verify) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name) and n.func.id == "require"
                  and any(isinstance(a, ast.Constant) and a.value == "Unreviewed binary payload"
                          for a in n.args)]
        self.assertEqual(len(guards), 1)
        self.assertEqual(ast.dump(guards[0].args[0]), ast.dump(ast.parse(
            "all(n in allowed or n.startswith('olaf-runtime/') for n in binary)",
            mode="eval").body))
        # Runtime metadata must not smuggle in Python application modules either.
        fixture = {"olaf": b"synthetic text; never executed", "LICENSE.txt": b"license fixture",
                   "NOTICES.txt": b"notice fixture", "provenance.json": b'{"fixture": true}'}
        release.check_runtime_metadata(fixture, "olaf")
        for name in ("start.py", "shazam/cli.py", "legacy/python/start.py", "pyproject.toml"):
            with self.subTest(path=name), self.assertRaises(release.ReleaseError):
                release.check_runtime_metadata(fixture | {name: b"synthetic source fixture"}, "olaf")


if __name__ == "__main__":
    unittest.main()
