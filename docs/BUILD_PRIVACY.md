# Release compiler and artifact privacy

Implemented policy: `compiler-paths-and-artifacts-v1`. This is a build-policy
change, not a pipeline migration or a claim that previous binaries were cleaned.
Both engines, application algorithms, copyright and license bytes are unchanged.
Never edit strings in an executable or retrofit old archives. Rebuild from the
reviewed commit on each matching host, then run the existing test/package/verify
commands. Existing artifacts without this policy record are rejected.

## Rust and native dependencies

`scripts/release.py` constructs ordered `--remap-path-prefix` arguments covering
the reviewed source snapshot, Cargo registry/home and target/build outputs,
Rustup/toolchains, Zig tools/caches, temporary roots, host home/cache/SDK roots,
the checkout and relevant enclosing directories. Filesystem roots are not mapped.
Mappings include original/resolved paths, Windows forward/backslash, drive-case,
extended drive and UNC spellings. Enclosing prefixes precede more specific ones:
Rust uses the **last matching** rule. Logical destinations are `/source`,
`/build` and `/toolchain`, not operator account names. No claim is made about
arbitrary hard-coded application strings, compressed strings or obfuscated data.

Flags use `CARGO_ENCODED_RUSTFLAGS` and `CARGO_ENCODED_RUSTDOCFLAGS`, not whitespace
concatenation. On Windows a UTF-8 rustc response file contains one argument per
line to avoid the command-line length limit. Spaces and backslashes are literal
arguments. Control characters and `=` in build roots are rejected (C prefix-map
syntax cannot safely represent every such name). See the official
[Rust remapping rules](https://doc.rust-lang.org/rustc/remap-source-paths.html) and
[rustc response-file syntax](https://doc.rust-lang.org/rustc/command-line-arguments.html#path-load-command-line-flags-from-a-path).

The environment drops inherited Rust/Cargo flags, wrappers, target/profile
overrides, Zig settings, native compiler/archiver/linker flags, SQLite overrides,
CMake settings and related injection variables. Fresh tool homes remain isolated.
Ancestor and Cargo-home configuration files are rejected, including on later
test invocations. This is not a sandbox against a malicious compiler, SDK,
dependency build script or hostile executable already on the trusted PATH.

Native C/C++ uses file, macro and debug prefix maps, including bundled SQLite
(`libsqlite3-sys 0.39.1`, `cc 1.10.0` in Cargo.lock). `CC_SHELL_ESCAPED_FLAGS=1`
preserves the response-file argument through cc's parser. Native response files
use GNU quoting for GCC/Clang, Windows quoting for clang-cl; Rust response files
use neither shell quoting nor whitespace splitting. Windows requires
**clang-cl on PATH**, in addition to the existing MSVC linker/SDK prerequisites;
there is no fallback to cl.exe without equivalent path controls. Missing tools
fail closed. See [cc's pinned environment interface](https://docs.rs/cc/1.10.0/cc/)
and [Clang's prefix maps](https://clang.llvm.org/docs/ClangCommandLineReference.html).

Rust debug information is disabled at compilation, and debug stripping is an
additional layer. The MSVC linker gets `/DEBUG:NONE`, `/INCREMENTAL:NO` and a
basename-only `/PDBALTPATH`; remapping alone cannot control linker-generated PDB
paths. See Microsoft's [debug control](https://learn.microsoft.com/en-us/cpp/build/reference/debug-generate-debug-info)
and [alternate PDB path](https://learn.microsoft.com/en-us/cpp/build/reference/pdbaltpath-use-alternate-pdb-path).
The same policy is reconstructed for hosted release tests, not just the initial
binary. Actual PE, ELF and Mach-O output still must pass the content gate.

## Olaf: exact Zig 0.16.0 support

The reviewed official [Zig 0.16.0 source archive](https://ziglang.org/download/0.16.0/zig-0.16.0.tar.xz)
has SHA-256 `43186959edc87d5c7a1be7b7d2a25efffd22ce5807c7af99067f86f99641bfdf`,
checked against the [official download manifest](https://ziglang.org/download/index.json).
This source review did not install or execute Zig. Evidence within that archive:

| Source | SHA-256 | Relevant interface |
| --- | --- | --- |
| `lib/std/Build/Module.zig` | `0d5d2a468c99bea020bd8b8ca13c32e64abd66686d1821c9737ffc1a9292729f` | `strip`, module graph, C source flag lists |
| `src/clang_options.zon` | `2d589a35c427aa3f83d0d11855cfed6f92d6a25b80a856852298c7ac209656ee` | file/macro/debug prefix-map options |
| `src/zig_clang_driver.cpp` | `26a8152eeab677f091455e802d6c5ea1dbb6168167abcffb847287ec16a19141` | Clang response expansion, GNU mode outside clang-cl |
| `src/Sema.zig` | `0095af1a464cab07473b0097508a698194f323f5b2ea0c66be7a426fc06bb7ca` | `@src().file` uses `sub_file_path` |
| `src/Zcu/PerThread.zig` | `ac4c0ed51f6b97bea7fb6af9258fb3e32ab5257a6d70c70af5e7a21e91e06e30` | module-relative source paths |
| `src/main.zig` | `dd931f83eb6c4747b185185dc8c76e0bc07f7b14361b435c1f1bec212539551b` | build/Clang argument dispatch; no general Zig-source prefix-map option |

Patch `0004-release-build-privacy.patch` changes only `build.zig`. The custom
build options `-Drelease-privacy=true` and `-Dprivacy-cflags=RESPONSE_FILE` are
implemented there, **not invented Zig compiler switches**. Module-relative Zig
source identities are retained; `strip = true` prevents Zig debug-path emission.
Every registered artifact's module graph (including Zigzag/REST imports and
dataset-free regression artifacts) gets the policy. Every C input receives an
immutable Clang response file containing file/macro/debug maps and `-g0`.
This avoids multiplying a large flag list across dozens of C files in one Zig
command. It does not rely on stripping to remove `__FILE__` macro strings.

The helper's install, local/global cache, response and package directories are
all beneath its output staging directory. Response files contain private host
paths and are **never shipped**. They are generated solely by inventoried scripts,
checked for unchanged bytes on reuse, and used only with fresh/isolated caches.
Their generating scripts and this document belong to both source archives and
Olaf's explicit provenance inventory. Original patches and upstream/captured
hashes remain intact; patch replay verifies the fourth patch and final hashes.

## Fail-closed content and metadata checks

The shared hygiene policy checks both executables, metadata/provenance, notices,
licenses and all source members before writing packages and independently when
reading downloaded archives. Artifact strings are decoded as UTF-8 and as both
UTF-16 byte orders at both byte offsets, without requiring a BOM. Overlapping
bounded windows catch boundary-crossing matches. Current build-root spellings
are also checked directly against newly compiled executables. The downloaded
verifier needs neither the original checkout paths nor any native tools.

Source-only hygiene remains strict UTF-8 text: binary scanning is not a source
exception. No blanket vendor, license, executable or hosted-runner exemption
exists. The one existing hash-and-path-scoped removed public fixture line remains
allowed **only in its exact source patch context**. Attribution URLs and ordinary
generic examples are not operator paths. Findings report rule names, not matched
strings or credentials; compiler failures withhold raw stdout/stderr. Inspection
output embedded in provenance is also scanned before it can be packaged.

ZIP comments and extras are forbidden at archive, central-member and local-header
levels; headers/modes/timestamps/layout are checked for canonical metadata.
Compressed member trailers and trailing archive data are rejected. Tar must have
zero IDs/time, empty owner/group/link names, and only canonical generated PAX
path records. Regenerating the uncompressed canonical tar structure detects hidden
or overridden PAX/global headers, link fields, padding and metadata. Gzip requires
the canonical nameless/commentless header and one stream without extra/trailing
data. These checks still fail after an attacker recomputes outer checksums.
Checksums prove correspondence, **not authentication** of a publisher or build.

## Validation and remaining gates

Local validation uses only standard-library Python/static checks: four-target
command construction, hostile inherited flags/config, spaces/overlapping paths,
encoded binary strings, redaction, recomputed-checksum metadata tampering,
source/payload correspondence and strict patch/hash replay. Run:

```sh
python -B -m unittest discover -s tests/release -v
python -B scripts/check_release_hygiene.py --root .
python -B scripts/check_release_hygiene.py --root . --staged
git diff --check
```

No Cargo/rustc/Zig/MSVC compilation, application/audio/index execution, hosted CI
dispatch, installer or artifact repair was performed for this change. Symlink
tests can skip when Windows denies symlink creation. The parent must rebuild all
four targets, verify actual native response-file handling (especially clang-cl
and Zig's Clang subprocess), inspect binaries/linker outputs, run the selected
dataset-free tests and independently verify the downloaded archives. All target
statuses remain unverified. Privacy heuristics cannot certify absence of all
private data; review remaining findings without erasing legitimate attribution
or widening exemptions. Licensing/source-offer and clean-host portability review
remain separate gates. Historical audit inputs and old artifacts were not read,
modified, relabeled sanitized or committed.

## Windows install-step ordering fix (2026-10-31)

Patch `0005-release-install-debug-policy.patch` sets the artifact strip flag before
registering its install step. Zig 0.16.0 InstallArtifact snapshots whether a PDB
is expected when the step is created; setting strip only in the deferred privacy
pass disabled PDB generation but left installation requesting that missing file.
The deferred graph-wide prefix maps and debug suppression remain unchanged.
A static regression checks every install registration; native verification is
required independently. No engine code or matching policy changes.

Binary heuristics ignore an adjacent drive-prefix fragment with exactly one
character and no further path component: packed instruction bytes produced this
false positive in the native app. Standalone drive paths, multi-character or
multi-component paths, strict source checks and exact known-root byte checks
remain enforced. This narrow heuristic is not a proof of zero private data.
