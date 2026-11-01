"""Small synthetic headers/files only. Never compiles or runs an app/runtime."""
import importlib.util
import contextlib
import io
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
    data = bytearray(2048)
    if target in release.WINDOWS_TARGETS:
        x86 = target == "windows-x86"
        opt_size = 224 if x86 else 240
        base = 96 if x86 else 112
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<HH", data, 132, 0x14C if x86 else 0x8664, 1)
        struct.pack_into("<HH", data, 148, opt_size, 2)
        struct.pack_into("<H", data, 152, 0x10B if x86 else 0x20B)
        struct.pack_into("<I", data, 152 + 60, 512)
        struct.pack_into("<I", data, 152 + base - 4, 16)
        # One file-backed section, no imports by default.
        struct.pack_into("<IIII", data, 152 + opt_size + 8, 1536, 4096, 1536, 512)
    elif target == "linux-x64":
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 62)
    else:
        data[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", data, 4, 0x0100000C if target == "macos-arm64" else 0x01000007)
    return bytes(data)


def imported_pe(target):
    data = bytearray(binary(target))
    base = 96 if target == "windows-x86" else 112
    width = 4 if target == "windows-x86" else 8
    fmt = "<I" if width == 4 else "<Q"
    struct.pack_into("<II", data, 152 + base + 8, 4096, 40)
    struct.pack_into("<5I", data, 512, 4480, 0, 0, 4352, 4512)
    struct.pack_into("<II", data, 152 + base + 13 * 8, 4160, 64)
    struct.pack_into("<8I", data, 576, 1, 4384, 4656, 4576, 4544, 0, 0, 0)
    data[768:781] = b"KERNEL32.dll\0"
    data[800:814] = b"VCRUNTIME.dll\0"
    for offset in (896, 928):
        struct.pack_into(fmt, data, offset, (1 << (8 * width - 1)) | 1)
    for offset in (960, 992):
        struct.pack_into(fmt, data, offset, 4608)
    data[1024:1031] = b"\0\0Func\0"
    return bytes(data)


class PEInspectionTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(release.subprocess, "run", side_effect=AssertionError("No executable inspection by execution")).start()
        patch.object(release.urllib.request, "urlopen", side_effect=AssertionError("No network")).start()

    def test_both_formats_normal_and_delay_imports(self):
        for target in release.WINDOWS_TARGETS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                data = imported_pe(target)
                self.assertEqual(release.architecture(data), target)
                self.assertEqual(release.pe_imports(data), ["kernel32.dll", "vcruntime.dll"])
                # A filename is not architecture evidence.
                path = Path(tmp) / "misleading-x64.exe"
                path.write_bytes(data)
                self.assertEqual(release.inspect_binary(path, target)["architecture"], target)
                other = next(t for t in release.WINDOWS_TARGETS if t != target)
                with self.assertRaisesRegex(release.ReleaseError, "Architecture mismatch"):
                    release.inspect_binary(path, other)

    def test_truncation_machine_magic_and_section_bounds_fail_closed(self):
        for target in release.WINDOWS_TARGETS:
            data = imported_pe(target)
            for length in (1, 2, 63, 130, 151, 155, 247, 375, 430, 511, len(data) - 1):
                with self.subTest(target=target, length=length), self.assertRaises(release.ReleaseError):
                    release.architecture(data[:length])
            base = 96 if target == "windows-x86" else 112
            section = 152 + (224 if target == "windows-x86" else 240) + 8
            changes = [(60, "I", 0), (132, "H", 0xAA64), (134, "H", 0), (134, "H", 97),
                       (148, "H", base - 1), (150, "H", 0), (152, "H", 0x20B if base == 96 else 0x10B),
                       (212, "I", 200), (152 + base - 4, "I", 17), (152 + base - 4, "I", 1),
                       (section + 4, "I", 0xFFFFFFF0), (section + 8, "I", 4096), (section + 12, "I", 0)]
            for offset, fmt, value in changes:
                bad = bytearray(data)
                struct.pack_into("<" + fmt, bad, offset, value)
                with self.subTest(target=target, offset=offset, value=value), self.assertRaises(release.ReleaseError):
                    release.pe_imports(bad)

    def test_invalid_directories_descriptors_names_and_thunks(self):
        for target in release.WINDOWS_TARGETS:
            base = 96 if target == "windows-x86" else 112
            directory = 152 + base + 8
            # Invalid range, missing descriptor terminator, missing file backing,
            # invalid thunk RVA/name/ordinal and unsupported VA delay form.
            changes = [(directory, 0), (directory, 9999), (directory + 4, 0),
                       (directory + 4, 20), (directory + 4, 1600), (512, 0xFFFFFFF0),
                       (524, 0), (524, 5631), (528, 0), (532, 1), (576, 0), (576, 3),
                       (592, 0), (608, 1), (896, 65536), (960, 9999)]
            for offset, value in changes:
                bad = bytearray(imported_pe(target))
                struct.pack_into("<I", bad, offset, value)
                with self.subTest(target=target, offset=offset, value=value), self.assertRaises(release.ReleaseError):
                    release.pe_imports(bad)
            for name in (b"../bad.dll\0", b"not-a-dll\0", b"bad\xff.dll\0", b"\0"):
                bad = bytearray(imported_pe(target))
                bad[768:768 + len(name)] = name
                with self.subTest(target=target, name=name), self.assertRaises(release.ReleaseError):
                    release.pe_imports(bad)
            # Name terminators must be inside their mapped raw section, not an overlay.
            bad = bytearray(imported_pe(target))
            struct.pack_into("<I", bad, 524, 5624)
            bad[2040:] = b"LONG.dll" + b"\0"
            with self.assertRaises(release.ReleaseError):
                release.pe_imports(bad)
            bad = bytearray(imported_pe(target))
            struct.pack_into("<I", bad, 512, 5628)
            bad[2044:] = b"\xff" * 4
            with self.assertRaises(release.ReleaseError):
                release.pe_imports(bad)

    def test_overlapping_sections_and_unbacked_imports(self):
        for target in release.WINDOWS_TARGETS:
            data = bytearray(imported_pe(target))
            section = 152 + (224 if target == "windows-x86" else 240)
            struct.pack_into("<H", data, 134, 2)
            data[section + 40:section + 80] = data[section:section + 40]
            with self.assertRaisesRegex(release.ReleaseError, "Overlapping"):
                release.pe_imports(data)
            data = bytearray(imported_pe(target))
            struct.pack_into("<I", data, section + 16, 64)
            with self.assertRaisesRegex(release.ReleaseError, "file-backed"):
                release.pe_imports(data)


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
        self.write("rust-app/Cargo.toml", b'[package]\nname = "local-shazam"\nversion = "7.8.9"\n')
        self.write("vendor/olaf/PROVENANCE.json", b'{"schema_version": 1, "fixture": true}\n')
        self.write("vendor/olaf/NOTICES.txt", b"dependency notices fixture")
        self.write("rust-app/src/olaf.rs", b"// no runtime execution\n")
        self.addCleanup(patch.stopall)
        patch.object(release, "tracked", side_effect=lambda root: sorted(self.names)).start()
        patch.object(release, "clean_commit", return_value="a" * 40).start()
        patch.object(release, "run", side_effect=AssertionError("Tests must not execute a subprocess")).start()
        patch.object(release.subprocess, "run", side_effect=AssertionError("No subprocesses")).start()
        patch.object(release.urllib.request, "urlopen", side_effect=AssertionError("No network")).start()
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
        suffix = ".exe" if target in release.WINDOWS_TARGETS else ""
        source = release.inventory(self.root, self.cfg)
        files = {"local-shazam" + suffix: binary(target), "olaf-runtime/olaf" + suffix: binary(target),
                 "olaf-runtime/OLAF-LICENSE": (self.root / "vendor/olaf/LICENSE").read_bytes(),
                 "olaf-runtime/OLAF-NOTICES.txt": (self.root / "vendor/olaf/NOTICES.txt").read_bytes(),
                 "olaf-runtime/PROVENANCE.json": (self.root / "vendor/olaf/PROVENANCE.json").read_bytes(),
                 "olaf-runtime/BUILD-INFO.json": release.encoded({
                     "zig_version": self.cfg["zig"],
                     "build_arguments": ["build", "install", "-Dtarget=" + release.TARGET_DETAILS[target][3],
                                         "-Dcpu=baseline", "-Doptimize=ReleaseFast", "-j1"],
                     "target": target, "zig_target": release.TARGET_DETAILS[target][3], "executable": "olaf" + suffix,
                     "executable_sha256": release.digest(binary(target)),
                     "source_provenance_sha256": release.digest((self.root / "vendor/olaf/PROVENANCE.json").read_bytes()),
                     "cpu": "baseline", "optimize": "ReleaseFast", "jobs": 1, "privacy_policy": release.PRIVACY_POLICY}),
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
        host_target = "windows-x64" if target == "windows-x86" else target
        host = self.cfg["targets"][host_target]
        execution = release.execution_policy(target, host["os"], host["arch"])
        manifest = {"schema": 1, "target": target, "commit": "a" * 40,
                    "source_inventory": source, "source_inventory_sha256": release.digest(release.encoded(source)),
                    "binary_inspections": inspections, "payload": release.tree_records(payload),
                    "olaf_source_version": "0.0.0-fixture", "app_version": "7.8.9",
                    "rust_target": self.cfg["targets"][target]["rust"],
                    "toolchains": {"rustc": "release: " + self.cfg["rust"] + "\nhost: " + host["rust"],
                                   "rustup": self.cfg["rustup"], "zig": self.cfg["zig"],
                                   "downloads": json.loads((self.root / "release/targets.json").read_bytes())["targets"][host_target]},
                    "host": {"system": host["os"], "machine": host["arch"], "arch": host["arch"]},
                    "support_status": release.gate_status(execution),
                    "build": {"cargo_locked": True, "jobs": 1, **execution,
                              "regression_target": release.TARGET_DETAILS[target][3], "regression_cpu": "baseline",
                              "privacy_policy": release.PRIVACY_POLICY},
                    "gates": {"dataset_free_tests": "passed", "completed": completed,
                              "target": target, "execution_mode": execution["execution_mode"]}}
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
        checksum = "SHA256SUMS.txt" if (dist / "SHA256SUMS.txt").exists() else "SHA256SUMS"
        sums = "".join(f"{release.file_hash(p)}  {p.name}\n" for p in sorted(dist.iterdir())
                       if p.name not in ("SHA256SUMS", "SHA256SUMS.txt"))
        (dist / checksum).write_text(sums, encoding="ascii")

    def test_all_target_formats_and_matching_source_archives(self):
        for target in release.TARGETS:
            with self.subTest(target=target):
                out = self.packaged(target)
                self.assertEqual(release.verify(out)["target"], target)
                for archive in (out / "dist").iterdir():
                    if archive.name not in ("SHA256SUMS", "SHA256SUMS.txt"):
                        entries = release.read_archive(archive)
                        self.assertIn(release.PROVENANCE, entries)
                        self.assertFalse(any(release.private_name(n) for n in entries))

    def rewrite_set(self, out, mutate):
        dist = out / "dist"
        paths = [path for path in dist.iterdir() if path.name.endswith((".zip", ".tar.gz"))]
        archives = {path.name: release.read_archive(path) for path in paths}
        p = json.loads(next(iter(archives.values()))[release.PROVENANCE][0])
        names = release.archive_names(p, clean=(dist / "SHA256SUMS.txt").exists())
        mutate(p, archives, names)
        for path in paths:
            entries = archives[path.name]
            entries[release.PROVENANCE] = (release.encoded(p), 0o644)
            path.unlink()  # Only this test's newly-created temporary fixture.
            release.write_archive(path, entries)
        self.reseal(out)

    def legacy_packaged(self, target):
        # Model the actual old writer contract, not just new packages renamed:
        # four-target config without new target fields and native-only provenance.
        old_cfg = json.loads(release.encoded(self.cfg))
        old_cfg["targets"].pop("windows-x86")
        for row in old_cfg["targets"].values():
            row.pop("olaf")
        self.write("release/targets.json", release.encoded(old_cfg))
        out = self.fixture(target)
        p = release.read_manifest(out)
        p.pop("app_version")
        p["host"].pop("arch")
        for key in ("host_target", "output_target", "cross_target", "execution_mode", "regression_target", "regression_cpu"):
            p["build"].pop(key)
        for key in ("target", "execution_mode"):
            p["gates"].pop(key)
        names = release.archive_names(p, clean=False)
        dist = out / "dist"
        dist.mkdir()
        common = {release.PROVENANCE: (release.encoded(p), 0o644)}
        for group in ("app", "olaf"):
            entries = {name: ((self.root / name).read_bytes(), 0o644) for name in p["source_inventory"][group]}
            release.write_archive(dist / names[group], entries | common)
        entries = {name: ((out / "payload" / name).read_bytes(), row["mode"]) for name, row in p["payload"].items()}
        release.write_archive(dist / names["binary"], entries | common)
        self.reseal(out)
        return out

    def test_authentic_legacy_conventions_remain_checkout_independent(self):
        for target in ("windows-x64", "linux-x64", "macos-arm64", "macos-x64"):
            with self.subTest(target=target):
                out = self.legacy_packaged(target)
                with patch.object(release, "config", side_effect=AssertionError("No checkout dependency")), \
                        patch.object(release, "inventory", side_effect=AssertionError("No checkout dependency")), \
                        patch.object(release.subprocess, "run", side_effect=AssertionError("No compiler/execution")):
                    p = release.verify(out / "dist")
                self.assertNotIn("app_version", p)
                self.assertNotIn("execution_mode", p["build"])
                self.assertTrue(p["build"]["native"])

    def test_windows_clean_names_use_application_version_not_commit_or_olaf(self):
        for target in release.WINDOWS_TARGETS:
            out = self.packaged(target)
            arch = target.removeprefix("windows-")
            self.assertEqual({path.name for path in (out / "dist").iterdir()}, {
                f"Local-Shazam_7.8.9_{arch}.zip", f"Local-Shazam_7.8.9_{arch}_app-source.tar.gz",
                f"Local-Shazam_7.8.9_{arch}_olaf-source.tar.gz", "SHA256SUMS.txt"})
            p = release.verify(out)
            self.assertEqual(p["commit"], "a" * 40)
            self.assertEqual(p["app_version"], "7.8.9")
            self.assertEqual(p["build"]["native"], target == "windows-x64")
            self.assertEqual(p["gates"]["execution_mode"], "wow64" if target == "windows-x86" else "native")

    def test_ambiguous_duplicate_missing_and_mixed_checksum_conventions(self):
        out = self.packaged("windows-x86")
        dist = out / "dist"
        sums = dist / "SHA256SUMS.txt"
        original = sums.read_bytes()
        (dist / "SHA256SUMS").write_bytes(original)
        with self.assertRaisesRegex(release.ReleaseError, "ambiguous checksum"):
            release.verify(out)
        (dist / "SHA256SUMS").unlink()
        sums.write_bytes(original + original.splitlines(keepends=True)[0])
        with self.assertRaisesRegex(release.ReleaseError, "Duplicate checksum"):
            release.verify(out)
        sums.write_bytes(original)
        sums.rename(dist / "SHA256SUMS")
        with self.assertRaisesRegex(release.ReleaseError, "naming/target"):
            release.verify(out)
        (dist / "SHA256SUMS").rename(sums)
        source = next(dist.glob("*_app-source.tar.gz"))
        source.rename(dist / "local-shazam-aaaaaaaaaaaa-windows-x86-app-source.tar.gz")
        self.reseal(out)
        with self.assertRaisesRegex(release.ReleaseError, "naming/target"):
            release.verify(out)

    def test_wrong_source_version_after_rehashing_all_sources(self):
        out = self.packaged("windows-x86")
        def mutate(p, archives, names):
            name = "rust-app/Cargo.toml"
            data = b'[package]\nname = "local-shazam"\nversion = "9.9.9"\n'
            archives[names["app"]][name] = (data, 0o644)
            p["source_inventory"]["app"][name] = release.digest(data)
            p["source_inventory_sha256"] = release.digest(release.encoded(p["source_inventory"]))
        self.rewrite_set(out, mutate)
        with self.assertRaisesRegex(release.ReleaseError, "Application source version mismatch"):
            release.verify(out)

    def test_mixed_target_sources_rejected_after_outer_reseal(self):
        x86, x64 = self.packaged("windows-x86"), self.packaged("windows-x64")
        src = next((x64 / "dist").glob("*_olaf-source.tar.gz"))
        dst = next((x86 / "dist").glob("*_olaf-source.tar.gz"))
        dst.write_bytes(src.read_bytes())
        self.reseal(x86)
        with self.assertRaisesRegex(release.ReleaseError, "provenance mismatch"):
            release.verify(x86)

    def test_false_execution_claims_and_target_metadata_fail_after_reseal(self):
        out = self.packaged("windows-x86")
        original = {path: path.read_bytes() for path in (out / "dist").iterdir()}
        changes = [("build", "native", True), ("build", "cross_target", False),
                   ("build", "execution_mode", "native"), ("build", "output_target", "windows-x64"),
                   ("build", "regression_target", "x86_64-windows-gnu"), ("build", "regression_cpu", "native"),
                   ("host", "arch", "x86"), ("host", "machine", "i686"),
                   ("gates", "execution_mode", "native"), ("gates", "target", "windows-x64")]
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                for path, data in original.items():
                    path.write_bytes(data)
                self.rewrite_set(out, lambda p, a, n: p[section].update({key: value}))
                with self.assertRaises(release.ReleaseError):
                    release.verify(out)
        for path, data in original.items():
            path.write_bytes(data)
        self.rewrite_set(out, lambda p, a, n: p.update({"support_status": "native gates passed; minimum OS and broader compatibility unverified"}))
        with self.assertRaisesRegex(release.ReleaseError, "support status"):
            release.verify(out)

    def test_wrong_binary_architectures_rejected_even_with_updated_inner_hashes(self):
        out = self.packaged("windows-x86")
        original = {path: path.read_bytes() for path in (out / "dist").iterdir()}
        for name, key in (("local-shazam.exe", "app"), ("olaf-runtime/olaf.exe", "olaf")):
            with self.subTest(binary=key):
                for path, data in original.items():
                    path.write_bytes(data)
                def mutate(p, archives, names):
                    data = binary("windows-x64")
                    archives[names["binary"]][name] = (data, 0o755)
                    p["payload"][name]["sha256"] = release.digest(data)
                    p["binary_inspections"][key]["sha256"] = release.digest(data)
                self.rewrite_set(out, mutate)
                with self.assertRaisesRegex(release.ReleaseError, "Wrong executable architecture"):
                    release.verify(out)

    def test_legacy_metadata_cannot_relabel_x86_or_bypass_privacy(self):
        out = self.legacy_packaged("windows-x64")
        def mutate(p, archives, names):
            name = "local-shazam.exe"
            data = binary("windows-x86")
            archives[names["binary"]][name] = (data, 0o755)
            p["payload"][name]["sha256"] = release.digest(data)
            p["binary_inspections"]["app"]["sha256"] = release.digest(data)
        self.rewrite_set(out, mutate)
        with self.assertRaisesRegex(release.ReleaseError, "Wrong executable architecture"):
            release.verify(out)
        self.rewrite_set(out, lambda p, a, n: p["build"].pop("privacy_policy"))
        with self.assertRaisesRegex(release.ReleaseError, "privacy policy"):
            release.verify(out)

    def test_runtime_relabeling_and_noncanonical_modes_fail_with_recomputed_hashes(self):
        out = self.packaged("windows-x86")
        original = {path: path.read_bytes() for path in (out / "dist").iterdir()}
        for key, value in (("target", "windows-x64"), ("zig_target", "x86_64-windows-gnu"),
                           ("source_provenance_sha256", "0" * 64), ("cpu", "native"),
                           ("privacy_policy", "unreviewed"), ("build_arguments", [])):
            with self.subTest(key=key):
                for path, data in original.items():
                    path.write_bytes(data)
                def mutate(p, archives, names):
                    name = "olaf-runtime/BUILD-INFO.json"
                    info = json.loads(archives[names["binary"]][name][0])
                    info[key] = value
                    data = release.encoded(info)
                    archives[names["binary"]][name] = (data, 0o644)
                    p["payload"][name]["sha256"] = release.digest(data)
                self.rewrite_set(out, mutate)
                with self.assertRaises(release.ReleaseError):
                    release.verify(out)
        for path, data in original.items():
            path.write_bytes(data)
        def mode(p, archives, names):
            name = "olaf-runtime/BUILD-INFO.json"
            archives[names["binary"]][name] = (archives[names["binary"]][name][0], 0o755)
            p["payload"][name]["mode"] = 0o755
        self.rewrite_set(out, mode)
        with self.assertRaisesRegex(release.ReleaseError, "Noncanonical payload mode"):
            release.verify(out)

    def test_application_version_parser_rejects_placeholder_and_unsafe_versions(self):
        for data in (b"placeholder", b'[package]\nname="other"\nversion="1.2.3"',
                     b'[package]\nname="local-shazam"\nversion="../1.2.3"',
                     b'[package]\nname="local-shazam"\nversion={workspace=true}'):
            with self.assertRaises(release.ReleaseError):
                release.app_source_version(data)
        self.assertEqual(release.app_source_version(b'[package]\nname="local-shazam"\nversion="1.2.3-rc.1+build"'),
                         "1.2.3-rc.1+build")

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
        self.write("vendor/olaf/src/credentials.json", b"marker")
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
        with self.assertRaisesRegex(release.ReleaseError, "Incomplete or unexpected target test gates"):
            release.package("linux-x64", out, self.root)

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
        with archive.open("wb") as raw, release.gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz, release.tarfile.open(fileobj=gz, mode="w") as tar:
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
        self.assertNotIn("github.event.repository.private == true", build)
        self.assertIn("if (!repo.private)", draft)
        self.assertEqual(draft.count("contents: write"), 1)
        self.assertIn("default: false", draft)
        self.assertIn("draft: true, prerelease: true", draft)
        self.assertIn("needs: [preflight, build, verify-all]", draft)
        self.assertNotRegex(draft, r"(?m)^  (push|pull_request|release|schedule):")
        self.assertNotIn("zig build test\n", build + draft)
        self.assertNotIn("git push", build + draft)

    def test_private_payloads_fail_even_with_consistent_source_and_payload_hashes(self):
        marker = ('gh' + 'p_' + 'P' * 36)
        for member, encoding in (('local-shazam', 'utf-16-le'), ('olaf-runtime/olaf', 'utf-16-be'),
                                 ('olaf-runtime/extra.json', 'utf-8'), ('rust-app/src/main.rs', 'utf-8'),
                                 ('licenses/dependency.txt', 'utf-8')):
            with self.subTest(member=member):
                # Deliberately bypass only the writer gate to produce a hostile
                # fully resealed fixture. The independent reader must reject it.
                with patch.object(release, 'check_privacy'):
                    if member.startswith(('rust-app/', 'licenses/')):
                        self.write(member, marker.encode(encoding))
                    out = self.fixture()
                    if not member.startswith(('rust-app/', 'licenses/')):
                        path = out / 'payload' / member
                        data = path.read_bytes() if path.exists() else b"{}"
                        if member.endswith('.json'):
                            data = release.encoded({'target': 'linux-x64', 'leak': marker})
                        else:
                            data += b'X' + marker.encode(encoding) + b'\0\0'
                        path.write_bytes(data)
                        if member == 'olaf-runtime/olaf':
                            info_path = out / 'payload/olaf-runtime/BUILD-INFO.json'
                            info = json.loads(info_path.read_bytes())
                            info['executable_sha256'] = release.digest(data)
                            info_path.write_bytes(release.encoded(info))
                        p = release.read_manifest(out)
                        p['payload'] = release.tree_records(out / 'payload')
                        if member in ('local-shazam', 'olaf-runtime/olaf'):
                            p['binary_inspections']['app' if member == 'local-shazam' else 'olaf']['sha256'] = release.digest(data)
                        (out / 'build-manifest.json').write_bytes(release.encoded(p))
                    release.package('linux-x64', out, self.root)
                with self.assertRaisesRegex(release.ReleaseError, 'Privacy gate') as error:
                    release.verify(out)
                self.assertNotIn(marker, str(error.exception))
                # Scoped temporary fixture cleanup, not a checkout/artifact repair.
                release.shutil.rmtree(out)
                if member.startswith(('rust-app/', 'licenses/')):
                    self.write(member, b'Synthetic reviewed source/license fixture.\n')

    def test_zip_metadata_tampering_survives_checksums_but_not_verification(self):
        out = self.packaged('windows-x64')
        archive = next((out / 'dist').glob('*.zip'))
        original = archive.read_bytes()
        for kind in ('archive-comment', 'member-comment', 'extra', 'local-extra', 'trailer'):
            with self.subTest(kind=kind):
                archive.write_bytes(original)
                if kind in ('local-extra', 'trailer'):
                    data = bytearray(original)
                    if kind == 'local-extra':
                        struct.pack_into('<H', data, 28, 1)
                    else:
                        data.extend(b'private metadata')
                    archive.write_bytes(data)
                else:
                    with release.zipfile.ZipFile(io.BytesIO(original)) as z:
                        members = [(info, z.read(info)) for info in z.infolist()]
                    with release.zipfile.ZipFile(archive, 'w') as z:
                        for i, (info, data) in enumerate(members):
                            if i == 0 and kind == 'member-comment':
                                info.comment = b'private metadata'
                            if i == 0 and kind == 'extra':
                                info.extra = b'\xfe\xca\x04\0data'
                            z.writestr(info, data)
                        if kind == 'archive-comment':
                            z.comment = b'private metadata'
                self.reseal(out)
                with self.assertRaises(release.ReleaseError):
                    release.verify(out)

    def test_tar_and_gzip_metadata_are_canonical_not_just_checksummed(self):
        out = self.packaged()
        archive = next(p for p in (out / 'dist').glob('*.tar.gz') if '-source' not in p.name)
        original = archive.read_bytes()
        for kind in ('uname', 'gname', 'uid', 'gid', 'mtime', 'linkname', 'pax', 'global-pax',
                     'gzip-name', 'gzip-comment', 'gzip-extra', 'gzip-concatenation'):
            with self.subTest(kind=kind):
                archive.write_bytes(original)
                if kind.startswith('gzip-'):
                    if kind == 'gzip-concatenation':
                        data = original + release.gzip.compress(b'', mtime=0)
                    else:
                        flags, metadata = {'gzip-name': (8, b'private-name\0'),
                                           'gzip-comment': (16, b'private-comment\0'),
                                           'gzip-extra': (4, b'\x04\0data')}[kind]
                        data = original[:3] + bytes([flags]) + original[4:10] + metadata + original[10:]
                    archive.write_bytes(data)
                else:
                    entries = release.read_archive(archive)
                    with archive.open('wb') as raw, release.gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
                        with release.tarfile.open(fileobj=gz, mode='w', format=release.tarfile.PAX_FORMAT,
                                                  pax_headers={'comment': 'private metadata'} if kind == 'global-pax' else {}) as tar:
                            for i, (name, (data, mode)) in enumerate(sorted(entries.items())):
                                info = release.tarfile.TarInfo(name)
                                info.size, info.mode = len(data), mode
                                if i == 0:
                                    if kind == 'pax':
                                        info.pax_headers = {'comment': 'private metadata'}
                                    elif kind != 'global-pax':
                                        setattr(info, kind, 123 if kind in ('uid', 'gid', 'mtime') else 'private metadata')
                                tar.addfile(info, io.BytesIO(data))
                self.reseal(out)
                with self.assertRaises(release.ReleaseError):
                    release.verify(out)

    def test_writer_rejects_private_binary_before_opening_archive(self):
        archive = self.root / 'new.zip'
        with self.assertRaisesRegex(release.ReleaseError, 'Privacy gate'):
            release.write_archive(archive, {'olaf.exe': (b'MZ' + ('gh' + 'p_' + 'R' * 36).encode(), 0o755)})
        self.assertFalse(archive.exists())


if __name__ == "__main__":
    unittest.main()
