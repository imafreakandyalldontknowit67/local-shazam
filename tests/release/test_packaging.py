"""Small synthetic headers/files only. Never compiles or runs an app/runtime."""
import importlib.util
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("release_tool", REPO / "scripts/release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def binary(target):
    data = bytearray(1024)
    if target == "windows-x64":
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<HH", data, 132, 0x8664, 1)
        struct.pack_into("<H", data, 148, 240)
        struct.pack_into("<H", data, 152, 0x20B)
        # One file-backed section, no imports by default.
        struct.pack_into("<IIII", data, 400, 512, 4096, 512, 512)
    elif target == "linux-x64":
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 62)
    else:
        data[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", data, 4, 0x0100000C if target == "macos-arm64" else 0x01000007)
    return bytes(data)


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cfg = release.config(REPO)
        self.names = set()
        for pattern in self.cfg["source_inventory"]["required"]:
            name = pattern.replace("LICENSE*", "LICENSE").replace("*.patch", "windows.patch")
            name = name.replace("*.zig", "main.zig").replace("*", "dependency.txt")
            self.write(name, b"Synthetic reviewed source/license fixture.\n")
        self.write("release/targets.json", release.encoded(self.cfg))
        self.write("vendor/olaf/build.zig.zon", b'.{ .version = "0.0.0-fixture" }\n')
        self.write("rust-app/src/olaf.rs", b"// no runtime execution\n")
        self.addCleanup(patch.stopall)
        patch.object(release, "tracked", side_effect=lambda root: sorted(self.names)).start()
        patch.object(release, "clean_commit", return_value="a" * 40).start()
        patch.object(release, "run", side_effect=AssertionError("Tests must not execute a subprocess")).start()
        patch.object(release, "download", side_effect=AssertionError("Tests must not download")).start()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.names.add(name)

    def fixture(self, target="linux-x64"):
        out = self.root / "build" / target
        payload = out / "payload"
        payload.mkdir(parents=True)
        suffix = ".exe" if target == "windows-x64" else ""
        source = release.inventory(self.root, self.cfg)
        files = {"local-shazam" + suffix: binary(target), "olaf-runtime/olaf" + suffix: binary(target),
                 "olaf-runtime/LICENSE.txt": b"AGPL fixture", "olaf-runtime/NOTICES.txt": b"dependency notices fixture",
                 "olaf-runtime/provenance.json": release.encoded({"target": target, "fixture": True}),
                 "SETUP.txt": release.SETUP.encode()}
        for name in source["app"]:
            if name in ("LICENSE", "THIRD_PARTY_NOTICES.md") or name.startswith("licenses/"):
                files[name] = (self.root / name).read_bytes()
        for name, data in files.items():
            dest = payload / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            dest.chmod(0o755 if name.endswith(("local-shazam", "olaf", ".exe")) else 0o644)
        inspections = {k: {"sha256": release.digest(binary(target)), "architecture": target,
                            "unresolved_requirements": "synthetic; not a real build"} for k in ("app", "olaf")}
        if suffix:
            for row in inspections.values():
                row["imports_and_delay_imports"] = []
        completed = [name for names in self.cfg["rust_tests"].values() for name in names]
        completed += self.cfg["olaf_regressions"]
        completed += ["local-shazam" + suffix + " --help", "local-shazam" + suffix + " --version",
                      "olaf-runtime/olaf" + suffix + " --help"]
        manifest = {"schema": 1, "target": target, "commit": "a" * 40,
                    "source_inventory": source, "source_inventory_sha256": release.digest(release.encoded(source)),
                    "binary_inspections": inspections, "payload": release.tree_records(payload),
                    "olaf_source_version": "0.0.0-fixture",
                    "build": {"cargo_locked": True, "jobs": 1, "native": True},
                    "gates": {"dataset_free_tests": "passed", "completed": completed}}
        (out / "build-manifest.json").write_bytes(release.encoded(manifest))
        return out

    def packaged(self, target="linux-x64"):
        out = self.fixture(target)
        release.package(target, out, self.root)
        return out

    def rewrite(self, out, group, mutate):
        dist = out / "dist"
        name = next(p for p in dist.iterdir() if p.name.endswith(group))
        entries = release.read_archive(name)
        mutate(entries)
        name.unlink()
        release.write_archive(name, entries)
        self.reseal(out)

    def reseal(self, out):
        dist = out / "dist"
        sums = "".join(f"{release.file_hash(p)}  {p.name}\n" for p in sorted(dist.iterdir()) if p.name != "SHA256SUMS")
        (dist / "SHA256SUMS").write_text(sums, encoding="ascii")

    def test_all_native_formats_and_matching_source_archives(self):
        for target in release.TARGETS:
            with self.subTest(target=target):
                out = self.packaged(target)
                self.assertEqual(release.verify(out)["target"], target)
                for archive in (out / "dist").iterdir():
                    if archive.name != "SHA256SUMS":
                        entries = release.read_archive(archive)
                        self.assertIn(release.PROVENANCE, entries)
                        self.assertFalse(any(release.private_name(n) for n in entries))

    def test_missing_required_sources_fail_closed(self):
        self.names.remove("vendor/olaf/src/mdb.c")
        with self.assertRaisesRegex(release.ReleaseError, "Incomplete source"):
            release.inventory(self.root, self.cfg)

    def test_untracked_and_unrelated_private_files_never_enter_inventory(self):
        (self.root / "rust-app/src/untracked.rs").write_text("private")
        self.write("HANDOFF.md", b"private")
        self.write("benchmarks/private.mp3", b"audio")
        self.write("local-shazam.exe", b"old ignored binary")
        inventory = release.inventory(self.root, self.cfg)
        self.assertFalse(any("HANDOFF" in n or "benchmarks/" in n or "untracked" in n
                             for files in inventory.values() for n in files))

    def test_compiler_snapshot_excludes_untracked_files_and_detects_changes(self):
        (self.root / "rust-app/src/untracked.rs").write_bytes(b"not reviewed")
        source = release.inventory(self.root, self.cfg)
        snapshot = release.source_snapshot(self.root, self.root / "build/snapshot-test", source)
        self.assertFalse((snapshot / "rust-app/src/untracked.rs").exists())
        (snapshot / "rust-app/src/main.rs").write_bytes(b"mutated")
        with self.assertRaisesRegex(release.ReleaseError, "Build snapshot changed"):
            release.check_snapshot(snapshot, source)

    def test_unreviewed_source_is_not_silently_omitted(self):
        self.write("vendor/olaf/new-build-input.custom", b"new input")
        with self.assertRaisesRegex(release.ReleaseError, "Unreviewed source"):
            release.inventory(self.root, self.cfg)

    def test_inventory_globs_do_not_leak_into_neighbor_directories(self):
        self.assertFalse(release.matches("vendor/olaf/eval/private.json", ["vendor/*.json"]))
        self.assertTrue(release.matches("rust-app/src/main.rs", ["rust-app/src/**/*.rs"]))
        self.assertTrue(release.matches("rust-app/src/nested/module.rs", ["rust-app/src/**/*.rs"]))

    def test_empty_legal_material_is_rejected(self):
        (self.root / "vendor/olaf/LICENSE").write_bytes(b"")
        with self.assertRaisesRegex(release.ReleaseError, "Empty legal"):
            release.inventory(self.root, self.cfg)

    def test_private_file_in_reviewed_tree_is_rejected(self):
        self.write("vendor/olaf/src/credentials.json", b"secret")
        with self.assertRaisesRegex(release.ReleaseError, "Private/unsafe"):
            release.inventory(self.root, self.cfg)

    def test_checksum_tampering(self):
        out = self.packaged()
        archive = next((out / "dist").glob("*-app-source.tar.gz"))
        with archive.open("ab") as f:
            f.write(b"tampered")
        with self.assertRaisesRegex(release.ReleaseError, "Checksum mismatch"):
            release.verify(out)

    def test_missing_source_archive(self):
        out = self.packaged()
        next((out / "dist").glob("*-olaf-source.tar.gz")).unlink()
        self.reseal(out)
        with self.assertRaisesRegex(release.ReleaseError, "both corresponding source"):
            release.verify(out)

    def test_changed_source_even_with_new_outer_checksum(self):
        out = self.packaged()
        self.rewrite(out, "-app-source.tar.gz", lambda e: e.update({"rust-app/src/main.rs": (b"changed", 0o644)}))
        with self.assertRaisesRegex(release.ReleaseError, "Source mismatch"):
            release.verify(out)

    def test_source_runtime_provenance_must_be_identical(self):
        out = self.packaged()
        self.rewrite(out, "-olaf-source.tar.gz", lambda e: e.update({release.PROVENANCE: (b"{}", 0o644)}))
        with self.assertRaisesRegex(release.ReleaseError, "provenance mismatch"):
            release.verify(out)

    def test_unix_execute_bit_is_verified(self):
        out = self.packaged()
        def remove_mode(entries):
            entries["local-shazam"] = (entries["local-shazam"][0], 0o644)
        self.rewrite(out, "linux-x64.tar.gz", remove_mode)
        with self.assertRaisesRegex(release.ReleaseError, "Payload mismatch"):
            release.verify(out)

    def test_no_extra_unchecksummed_outputs(self):
        out = self.packaged()
        (out / "dist/extra.txt").write_text("do not distribute")
        with self.assertRaisesRegex(release.ReleaseError, "Unchecksummed"):
            release.verify(out)

    def test_architecture_headers_not_host_labels(self):
        for target in release.TARGETS:
            self.assertEqual(release.architecture(binary(target)), target)
        with self.assertRaises(release.ReleaseError):
            release.architecture(b"not an executable")

    def test_wrong_architecture_cannot_be_packaged_as_another_target(self):
        out = self.fixture()
        (out / "payload/local-shazam").write_bytes(binary("macos-x64"))
        p = release.read_manifest(out)
        p["payload"] = release.tree_records(out / "payload")
        p["binary_inspections"]["app"]["sha256"] = release.digest(binary("macos-x64"))
        (out / "build-manifest.json").write_bytes(release.encoded(p))
        with self.assertRaisesRegex(release.ReleaseError, "Wrong executable architecture"):
            release.package("linux-x64", out, self.root)

    def test_source_change_between_build_and_packaging_is_rejected(self):
        out = self.fixture()
        (self.root / "rust-app/src/main.rs").write_bytes(b"changed after build")
        with self.assertRaisesRegex(release.ReleaseError, "Source/runtime correspondence changed"):
            release.package("linux-x64", out, self.root)

    def test_runtime_rejects_unreviewed_local_dlls(self):
        with self.assertRaisesRegex(release.ReleaseError, "Unexpected runtime dependency"):
            release.check_runtime_metadata({"olaf.exe": binary("windows-x64"), "random-local.dll": b"binary"}, "olaf.exe")

    def test_missing_gate_even_with_passed_flag_is_rejected(self):
        out = self.fixture()
        p = release.read_manifest(out)
        p["gates"]["completed"].pop()
        (out / "build-manifest.json").write_bytes(release.encoded(p))
        with self.assertRaisesRegex(release.ReleaseError, "Incomplete or unexpected native test gates"):
            release.package("linux-x64", out, self.root)

    def test_dll_import_and_delay_import_inspection(self):
        data = bytearray(binary("windows-x64"))
        # import descriptor at section start, followed by a null descriptor
        struct.pack_into("<II", data, 152 + 112 + 8, 4096, 40)
        struct.pack_into("<I", data, 512 + 12, 4200)
        data[616:629] = b"KERNEL32.dll\0"
        struct.pack_into("<II", data, 152 + 112 + 8 * 13, 4300, 64)
        struct.pack_into("<II", data, 716, 1, 4400)
        data[816:830] = b"VCRUNTIME.dll\0"
        self.assertEqual(release.pe_imports(bytes(data)), ["kernel32.dll", "vcruntime.dll"])

    def test_runtime_requires_license_notices_and_provenance(self):
        for missing in ("LICENSE.txt", "NOTICES.txt", "provenance.json"):
            data = {"olaf": binary("linux-x64"), "LICENSE.txt": b"AGPL", "NOTICES.txt": b"notices",
                    "provenance.json": b'{"source":"fixture"}'}
            del data[missing]
            with self.assertRaises(release.ReleaseError):
                release.check_runtime_metadata(data, "olaf")

    def test_package_refuses_untested_build(self):
        out = self.fixture()
        p = release.read_manifest(out)
        p["gates"]["dataset_free_tests"] = "not-run"
        (out / "build-manifest.json").write_bytes(release.encoded(p))
        with self.assertRaisesRegex(release.ReleaseError, "gates have not passed"):
            release.package("linux-x64", out, self.root)

    def test_staging_cannot_escape_checkout_or_replace_root_outputs(self):
        for path in (self.root, self.root.parent, self.root / "build", self.root / "rust-app",
                     self.root / "build/../../outside"):
            with self.assertRaises(release.ReleaseError):
                release.staging(path, self.root)
        self.assertEqual(release.staging("build/release/native", self.root), self.root / "build/release/native")

    def test_safe_archive_paths(self):
        for name in ("../escape", "/absolute", "a\\b", "C:/tmp", "a//b", "a/./b", "a\nfile"):
            with self.assertRaises(release.ReleaseError):
                release.safe_name(name)

    def test_archive_case_collisions_are_rejected(self):
        archive = self.root / "collision.tar.gz"
        release.write_archive(archive, {"NOTICE.txt": (b"one", 0o644), "notice.txt": (b"two", 0o644)})
        with self.assertRaisesRegex(release.ReleaseError, "Duplicate/case-colliding"):
            release.read_archive(archive)

    def test_archive_links_are_rejected_without_extraction(self):
        archive = self.root / "linked.tar.gz"
        with release.tarfile.open(archive, "w:gz") as tar:
            member = release.tarfile.TarInfo("link")
            member.type = release.tarfile.SYMTYPE
            member.linkname = "../../outside"
            tar.addfile(member)
        with self.assertRaisesRegex(release.ReleaseError, "Nonregular tar"):
            release.read_archive(archive)

    def test_no_symlink_source_inputs(self):
        source = self.root / "vendor/olaf/src/mdb.c"
        source.unlink()
        try:
            source.symlink_to(self.root / "LICENSE")
        except OSError:
            self.skipTest("Symlink creation is unavailable without Windows privilege")
        with self.assertRaisesRegex(release.ReleaseError, "nonregular"):
            release.inventory(self.root, self.cfg)

    def test_action_pins_and_manual_write_boundary(self):
        build = (REPO / ".github/workflows/portable-build.yml").read_text()
        draft = (REPO / ".github/workflows/private-draft.yml").read_text()
        for action in re.findall(r"uses:\s+([^\s#]+)", build + draft):
            self.assertTrue(action.startswith("./") or re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", action), action)
        self.assertNotIn("contents: write", build)
        self.assertEqual(draft.count("contents: write"), 1)
        self.assertIn("default: false", draft)
        self.assertIn("draft: true, prerelease: true", draft)
        self.assertIn("needs: [preflight, build, verify-all]", draft)
        self.assertNotRegex(draft, r"(?m)^  (push|pull_request|release|schedule):")
        self.assertNotIn("zig build test\n", build + draft)
        self.assertNotIn("git push", build + draft)


if __name__ == "__main__":
    unittest.main()
