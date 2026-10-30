"""Offline release-review evidence checks, not native execution or legal approval.

Reads only documentation, manifests and notices. No network, Cargo, subprocess,
artifact execution, music/index access, temporary repositories or compilation.
Historical summaries are checked for internal consistency, not live authenticity.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]
PREVIEW = "92a983a57ff92ad4b9342fb4dd992edf728b5a97"
APPLE = {"block2", "dispatch2", "objc2", "objc2-app-kit",
         "objc2-core-foundation", "objc2-encode", "objc2-foundation"}
DOCS = ["README.md", "CHANGELOG.md", "docs/BUILDING.md", "docs/RELEASING.md",
        "docs/REPOSITORY_METADATA.md", "rust-app/README.md", "rust-app/OLAF.md",
        "THIRD_PARTY_NOTICES.md", "licenses/README.md",
        "licenses/RELEASE_REVIEW.md", "licenses/RUST_DEPENDENCIES.md"]


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReleaseReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read_json("licenses/rust-inventory.json")
        cls.packages = {(p["name"], p["version"]): p
                        for p in cls.inventory["packages"]}
        cls.preview = read_json("licenses/review/native-preview.json")

    def test_lockfile_correspondence(self):
        raw = (ROOT / "rust-app/Cargo.lock").read_bytes()
        self.assertEqual(digest(raw.replace(b"\r\n", b"\n")),
                         self.inventory["cargo_lock_sha256_lf"])
        lock = tomllib.loads(raw.decode("utf-8-sig"))["package"]
        registry = {(p["name"], p["version"]): p for p in lock if "source" in p}
        self.assertEqual(len(registry), 115)
        self.assertEqual(len(self.inventory["packages"]), len(self.packages))
        self.assertEqual(set(registry), set(self.packages))
        summary = (ROOT / "licenses/RUST_DEPENDENCIES.md").read_text(encoding="utf-8")
        for key, p in self.packages.items():
            with self.subTest(package=key):
                self.assertEqual(p["checksum"], registry[key]["checksum"])
                self.assertEqual(p["source"],
                                 f"https://static.crates.io/crates/{key[0]}/{key[0]}-{key[1]}.crate")
                row = next(line for line in summary.splitlines()
                           if line.startswith(f'| [{key[0]}]({p["source"]}) | {key[1]} |'))
                self.assertIn(f'`{p["license"]}`', row)
                self.assertEqual("BLOCKED:" in row, p["status"].startswith("BLOCKED"))
        app = [p for p in lock if "source" not in p]
        self.assertEqual([(p["name"], p["version"]) for p in app],
                         [("local-shazam", "0.2.0")])

    def test_original_notice_hashes(self):
        records = [f for p in self.packages.values() for f in p["files"]]
        records += read_json("licenses/olaf-inventory.json")["copies"]
        for record in records:
            with self.subTest(path=record["path"]):
                data = (ROOT / record["path"]).read_bytes()
                self.assertTrue(data.strip())
                self.assertEqual(digest(data), record["sha256"])
                if record.get("source", "").startswith("vendor/"):
                    self.assertEqual(data, (ROOT / record["source"]).read_bytes())

    def test_exact_archive_metadata_copies(self):
        records = read_json("licenses/review/source-records.json")["copies"]
        self.assertEqual(len({r["path"] for r in records}), len(records))
        reviewed = set()
        for record in records:
            with self.subTest(path=record["path"]):
                path = ROOT / record["path"]
                self.assertTrue(path.resolve().is_relative_to(ROOT / "licenses/review/crates"))
                self.assertEqual(digest(path.read_bytes()), record["sha256"])
                candidates = [p for p in self.packages.values()
                              if p["source"] == record["archive"]]
                self.assertEqual(len(candidates), 1)
                p = candidates[0]
                reviewed.add(p["name"])
                self.assertEqual(p["checksum"], record["archive_sha256"])
                self.assertEqual(p["published_vcs"]["git"]["sha1"], record["published_revision"])
                prefix = f'{p["name"]}-{p["version"]}/'
                self.assertTrue(record["member"].startswith(prefix))
                if path.name == ".cargo_vcs_info.json":
                    self.assertEqual(json.loads(path.read_bytes()), p["published_vcs"])
                if path.name == "Cargo.toml":
                    manifest = tomllib.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(manifest["package"]["name"], p["name"])
                    self.assertEqual(manifest["package"]["version"], p["version"])
        self.assertEqual(reviewed, APPLE | {"rfd", "rusqlite", "libsqlite3-sys", "sqlite-wasm-rs"})

    def test_blockers_and_immutable_upstream_records(self):
        blocked = {p["name"] for p in self.packages.values()
                   if p["status"].startswith("BLOCKED")}
        self.assertEqual(blocked, APPLE | {"sqlite-wasm-rs"})
        investigation = read_json("licenses/review/investigation.json")
        self.assertEqual({r["name"] for r in investigation["apple"]}, APPLE)
        for row in investigation["apple"]:
            p = self.packages[row["name"], row["version"]]
            self.assertEqual(row["checksum"], p["checksum"])
            self.assertEqual(row["revision"], p["published_vcs"]["git"]["sha1"])
            self.assertIn(row["revision"], row["tree_url"])
            self.assertEqual(row["license_paths"], ["LICENSE.md"])
            self.assertEqual(row["upstream_license_sha256"], p["files"][0]["sha256"])
            self.assertIn(row["revision"], p["files"][0]["origin"])
            self.assertIn("maintainer/legal", p["review_note"])
        wasm = investigation["sqlite_wasm"]
        self.assertEqual(wasm["revision"], self.packages["sqlite-wasm-rs", "0.6.2"]
                         ["published_vcs"]["git"]["sha1"])

    def test_target_predicates_not_whole_lock_selection(self):
        base = ROOT / "licenses/review/crates"
        rusqlite = tomllib.loads((base / "rusqlite-0.41.1/Cargo.toml").read_text())
        wasm = 'cfg(all(target_family = "wasm", target_os = "unknown"))'
        native = 'cfg(not(all(target_family = "wasm", target_os = "unknown")))'
        self.assertIn("sqlite-wasm-rs", rusqlite["target"][wasm]["dependencies"])
        self.assertNotIn("sqlite-wasm-rs", rusqlite["target"][native]["dependencies"])
        self.assertIn("libsqlite3-sys", rusqlite["target"][native]["dependencies"])
        self.assertIn("ffi-sqlite-wasm-rs", rusqlite["features"]["default"])
        rfd = tomllib.loads((base / "rfd-0.17.2/Cargo.toml").read_text())
        deps = rfd["target"]['cfg(target_os = "macos")']["dependencies"]
        self.assertTrue((APPLE - {"objc2-encode"}) <= deps.keys())
        objc = tomllib.loads((base / "objc2-0.6.5/Cargo.toml").read_text())
        self.assertIn("objc2-encode", objc["dependencies"])

    def test_historical_gates_and_explicit_limitations(self):
        self.assertEqual(self.preview["commit"], PREVIEW)
        cfg = read_json("release/targets.json")
        self.assertEqual(set(self.preview["targets"]), set(cfg["targets"]))
        for target, entry in self.preview["targets"].items():
            with self.subTest(target=target):
                exe = ".exe" if target == "windows-x64" else ""
                expected = [t for group in cfg["rust_tests"].values() for t in group]
                expected += cfg["olaf_regressions"]
                expected += [f"local-shazam{exe} --help", f"local-shazam{exe} --version",
                             f"olaf-runtime/olaf{exe} --help"]
                self.assertEqual(sorted(entry["gates"]["completed"]), sorted(expected))
                self.assertEqual(len(expected), 16)
                self.assertEqual(entry["gates"]["dataset_free_tests"], "passed")
                self.assertIn("unverified", entry["support_status"])
                self.assertEqual(entry["distribution"]["minimum_os"], "unverified")
                self.assertEqual(entry["distribution"]["bit_for_bit_reproducibility"], "not verified")
                self.assertFalse(entry["distribution"]["publisher_signed"])
                self.assertFalse(entry["distribution"]["notarized"])
                self.assertFalse(entry["target_feature_graph_available"])
                self.assertFalse(entry["cargo_dependency_source_bundled"])
                self.assertFalse(entry["legacy_python_bundled"])
        self.assertTrue(self.preview["cross_target_source_inventories_equal"])
        self.assertEqual(len({t["source_inventory_sha256"]
                              for t in self.preview["targets"].values()}), 1)

    def test_recorded_github_metadata_is_bounded(self):
        github = self.preview["github"]
        self.assertTrue(github["repository_private"])
        self.assertEqual(github["run"]["id"], 41023384988)
        self.assertEqual(github["run"]["head_sha"], PREVIEW)
        self.assertEqual(github["run"]["event"], "push")
        self.assertEqual(github["run"]["conclusion"], "success")
        self.assertEqual(len(github["jobs"]), 4)
        self.assertTrue(all(j["conclusion"] == "success" for j in github["jobs"]))
        release = github["release"]
        self.assertTrue(release["draft"] and release["prerelease"])
        self.assertIsNone(release["published_at"])
        self.assertEqual(release["tag_name"], "v0.2.0-native.1")
        self.assertEqual(release["target_commitish"], PREVIEW)
        self.assertIn("not proof of an existing tag", github["tag_resolution"])
        self.assertEqual(len(release["assets"]), 13)
        assets = {a["name"]: a for a in release["assets"]}
        local = [a for t in self.preview["targets"].values() for a in t["archives"]]
        self.assertEqual(len(local), 12)
        self.assertEqual(set(assets), {a["name"] for a in local} | {"SHA256SUMS"})
        for a in local:
            self.assertEqual(assets[a["name"]]["digest"], "sha256:" + a["sha256"])
            self.assertEqual(assets[a["name"]]["size"], a["size"])
            self.assertIn(PREVIEW[:12], a["name"])

    def test_pins_and_documentation_status(self):
        cfg = read_json("release/targets.json")
        pin = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())
        self.assertEqual(pin["toolchain"]["channel"], cfg["rust"])
        self.assertEqual((cfg["rust"], cfg["zig"]), ("1.99.0", "0.16.0"))
        for name in ["docs/BUILDING.md", "docs/RELEASING.md", "licenses/RELEASE_REVIEW.md"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(PREVIEW, text)
            self.assertIn("41023384988", text)
            self.assertIn("current-HEAD validation", text)
            self.assertIn("docs/BUILD_PRIVACY.md", text)
            self.assertIn("pending", text.lower())
            self.assertIn("bit-for-bit", text)
            self.assertNotIn("initial tooling checkout has not yet integrated", text)
        for name in ["docs/RELEASING.md", "licenses/RELEASE_REVIEW.md"]:
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            text = re.sub(r"\s+", " ", text)
            self.assertIn("final history/publication-surface audit", text)
            self.assertIn("outside this task", text)

    def test_owned_documentation_references(self):
        for name in DOCS:
            path = ROOT / name
            text = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^\s)]+)\)", text):
                if re.match(r"[a-z]+:", link) or link.startswith("#"):
                    continue
                destination = (path.parent / link.split("#", 1)[0]).resolve()
                self.assertTrue(destination.is_relative_to(ROOT))
                # Deliberately not claiming another agent's relocation is integrated.
                if destination == ROOT / "legacy/python/README.md" and not destination.exists():
                    self.assertIn("relocation verification", text)
                    continue
                self.assertTrue(destination.exists(), f"{name}: unresolved local reference {link}")
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("legacy/python/README.md", root_readme)
        self.assertNotIn("`shazam/`, `start.py`", root_readme)
        self.assertIn('srcset="assets/brand/mark-white.svg"', root_readme)
        self.assertIn('src="assets/brand/mark-black.svg"', root_readme)
        self.assertIn("## v1.0.1", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_owned_text_hygiene_without_history_or_artifact_scan(self):
        spec = importlib.util.spec_from_file_location("review_hygiene", ROOT / "scripts/check_release_hygiene.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        paths = {ROOT / p for p in DOCS}
        paths.update(p for p in (ROOT / "licenses").rglob("*") if p.is_file())
        findings = checker.Findings()
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            for path in sorted(paths):
                checker.check_bytes(path.relative_to(ROOT).as_posix(), path.read_bytes(), findings)
        self.assertEqual(findings.count, 0, output.getvalue())


if __name__ == "__main__":
    unittest.main()
