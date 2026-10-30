# Third-party notices and distribution boundaries

## Original application: MIT

The original Local Shazam application code remains under the existing [MIT
license](LICENSE). Its original `Copyright (c) 2026` notice is preserved verbatim;
this document does not invent or assign a copyright holder. The MIT declaration
in the application manifests is **not** a license for every component in this
repository or a conclusion about the licensing of a combined distribution.

## Modified Olaf runtime: AGPL-3.0-or-later

The separately distributed modified Olaf runtime and Olaf-derived source are
licensed under the **GNU Affero General Public License, version 3 or, at your
option, any later version**, not MIT. Original file-level notices remain intact.
Olaf credits Joren Six (see the years in individual source files).

- Public source: [JorenSix/Olaf](https://github.com/JorenSix/Olaf), base revision
  `f6f7cbefb50485953f71100c9d08c625f01780ba`.
- Modified source, precise provenance and source inventory:
  [vendor/olaf](vendor/olaf), [PROVENANCE.json](vendor/olaf/PROVENANCE.json),
  [BUILDING.md](vendor/olaf/BUILDING.md), and [ordered patches](patches/olaf/series).
- Full AGPL text: [licenses/olaf/AGPL-3.0.txt](licenses/olaf/AGPL-3.0.txt)
  (also retained as `vendor/olaf/LICENSE`). Original runtime notices:
  [vendor/olaf/NOTICES.txt](vendor/olaf/NOTICES.txt).

**Distribution obligation:** binaries require the exact matching modified runtime
source, all applicable patches, dependency source, configuration, and build/install
instructions needed to reproduce and modify that runtime, made available to
recipients in a license-compliant manner. Include any required installation
information. A link to a private repository alone is not an adequate source
delivery plan. A source snapshot or patch against a different revision is not a
substitute for corresponding source. Preserve the upstream notices and identify
modifications and their dates. See AGPL sections 1, 5, 6 and 13 in the supplied text
and the [FSF license](https://www.gnu.org/licenses/agpl-3.0.html).

Launching Olaf as a subprocess does **not** automatically exempt the application
or combined distribution from AGPL obligations. The combined-work/aggregation
question and any remote-network source-offer obligations require review of the
actual integration and deployment. No exemption is asserted here. The upstream
patent warning is also not resolved by including license texts.

## Embedded Olaf components (not relicensed by this notice)

The exact source-file terms control. These notices were compared to the supplied
pinned source, including both implementations and relevant headers; do not replace
them with a generic MIT/BSD label.

| Component | Attribution and terms | Included texts |
| --- | --- | --- |
| LMDB, `mdb.c`, `midl.c`, `lmdb.h`, `midl.h` | Howard Chu / Symas Corp.; The OpenLDAP Foundation, with years as written in the originals. OpenLDAP Public License 2.8. `mdb.c` additionally retains Martin Hedenfalk's 2009–2010 btree permission/disclaimer. | [OpenLDAP full text](licenses/olaf/OpenLDAP-LICENSE.txt), [mdb notice](licenses/olaf/LMDB-mdb-NOTICE.txt), [midl notice](licenses/olaf/LMDB-midl-NOTICE.txt) |
| PFFFT / FFTPACK | Julien Pommier (2013); FFTPACKv4 by Paul Swarztrauber / NCAR (1985); UCAR (2004). The embedded FFTPACK terms apply to Pommier's changes too. Retain the non-endorsement, source/binary notice and disclaimer provisions. | [C notice](licenses/olaf/PFFFT-NOTICE.txt), [header notice](licenses/olaf/PFFFT-header-NOTICE.txt) |
| c-algorithms hash table and queue | Simon Howard, 2005–2008. ISC permission/disclaimer, in both `.c` and `.h` files. | [Full notice](licenses/olaf/c-algorithms-NOTICE.txt) |
| Zigzag 0.1.2 | Matthew Meszaros, 2026. MIT. Pinned revision `e16e2523972d174d7ca9783631cc90e2609fa55e`, Zig package hash `zigzag-0.1.2-YXwYS9_qEQDBkc3k9-gNIC3mcONlH4N_RxxgcxM7Bhxt`. Its manifest declares no package dependencies. | [Full MIT notice](licenses/olaf/Zigzag-LICENSE.txt); [vendored source](vendor/zigzag); [upstream](https://github.com/meszmate/zigzag) |

The OpenLDAP license is verified against the [OpenLDAP Foundation's license
publication](https://www.openldap.org/software/release/license.html); retaining the
AGPL text alone would not meet LMDB's notice requirements. The PFFFT/FFTPACK and
Simon Howard texts are copied from the actual source headers, rather than an
unrelated current package's license. Copy provenance is in
[olaf-inventory.json](licenses/olaf-inventory.json).

## Locked Rust dependency inventory, including other targets

[RUST_DEPENDENCIES.md](licenses/RUST_DEPENDENCIES.md) lists **all 115 registry
packages** in the current `rust-app/Cargo.lock`, not only Windows dependencies.
[rust-inventory.json](licenses/rust-inventory.json) records the normalized lockfile
SHA-256, each exact version and archive checksum, primary source URL, manifest
license declaration, published VCS revision, copied-notice hashes and review
status. The application package itself is covered by the unchanged root MIT text.

All 115 published archives were checksum-verified against Cargo.lock and inspected
without compiling. Complete distributed license/notice files are retained in
`licenses/rust/<name>-<version>/`. Additional attribution/license comment blocks
are retained as `EMBEDDED-NOTICES.txt`, with source-file headings. Where archives
omitted licensing documents, the document was fetched from the exact VCS revision
recorded inside that archive, not from a moving main branch.

Inventory coverage is **not** a complete binary license audit. There are **seven
explicitly unresolved Apple-family attribution/SDK reviews** in that inventory;
108 packages have supplied license-text evidence (107 in their archives, one from
pinned upstream). A separate `sqlite-wasm-rs` embedded-musl provenance/notice
blocker also remains. Do not convert these evidence counts into a compliance claim.

Important non-generic and embedded terms include:

- `libsqlite3-sys 0.39.1` is an MIT-licensed Rust binding, but its bundled SQLite
  amalgamation is **SQLite 3.54.1**, with the authors' public-domain dedication,
  not a new MIT license for SQLite. The exact SQLite notice is retained in that
  crate's embedded notices. `rusqlite` enables `bundled` in the application.
  SQLite's [primary copyright statement](https://www.sqlite.org/copyright.html)
  distinguishes deliverable SQLite code from separately licensed build scripts.
- The target-specific `sqlite-wasm-rs 0.6.2` archive contains **SQLite 3.53.4**,
  MIT-licensed printf code with Eyal Rozenberg / Marco Paland attribution and
  musl qsort code with Valentin Ochs / Rich Felker notices. Those notices are
  included independently of the crate's root MIT license. However, many other
  files under `shim/musl/` have no file-level license, and this crate archive has
  no musl-wide COPYRIGHT or precise import revision. Its build script includes
  those sources. Confirm their provenance and complete notices before shipping
  this dependency source or a binary incorporating the shim. The Olaf toolchain's
  separate musl notice is not proof of coverage for these files.
- `unicode-ident`: `(MIT OR Apache-2.0) AND Unicode-3.0`; the Unicode license is
  included, not lost by selecting MIT for the Rust portions.
- `foldhash`: Zlib; `libloading`: ISC; `rustix` / `linux-raw-sys`: their actual
  MIT, Apache and Apache-with-LLVM-exception texts and COPYRIGHT are included.
- `crossbeam-channel`: the full `LICENSE-THIRD-PARTY` (including the separate
  example/test licensing) and attribution comments are retained. A source bundle
  containing dependency examples/tests must not discard these as “not runtime.”
- Wayland client/protocol XML copyright and permission blocks, `rfd`'s nested
  window-identifier license, and `serde_json`'s Alexander Huszagh lexical
  attribution are included. Windows bindings, wasm, Apple, Linux and UEFI packages
  are inventoried even when not selected by a particular build.
- `r-efi` offers MIT / Apache-2.0 / LGPL-2.1-or-later alternatives. Its `AUTHORS`
  contains complete MIT terms and explicit copyright notices; the MIT alternative
  is selected here. LGPL obligations are not inferred just from the package name
  or the presence of an unselected alternative.

For optional alternative terms, this notice selects MIT where offered and otherwise
the supplied ISC or Zlib terms, without excluding additional embedded/conjunctive
terms. Full alternative texts present in the archives are also preserved. Crate
`authors` fields are recorded as metadata, **not** invented copyright notices.

## Toolchains, system libraries and external tools

Olaf's Zig 0.16.0 toolchain notice copies are included as
[Zig MIT](licenses/olaf/Zig-LICENSE.txt),
[mingw-w64 COPYING](licenses/olaf/mingw-w64-COPYING.txt), and
[musl COPYRIGHT](licenses/olaf/musl-COPYRIGHT.txt). Applicability depends on the
actual target and linked output. These copies do not certify every CRT/compiler
runtime subcomponent emitted by Zig or Rust, or satisfy every SDK agreement.
The Rust standard library/compiler runtime and platform link inputs are not
described comprehensively by Cargo.lock. Audit each final binary and exact
toolchain before distribution; record any additional notices and source duties.

**FFmpeg and FFprobe are external, user-installed tools and are not redistributed.**
No FFmpeg license/source coverage is claimed for a hypothetical bundled build.
Changing that packaging decision requires a new build-specific audit.

The Python reference application's `click`, `numpy`, `scipy`, `tqdm` and build
dependencies, and Olaf's optional Python wrapper dependencies, are declared with
version ranges rather than an exact resolved distribution inventory. They are
not included as Python wheels/interpreters in this source license inventory.
If Python environments, wheels, native numerical libraries, or optional wrappers
are bundled, first pin and audit the actual artifacts and transitive licenses.
No comprehensive Python-binary compliance claim is made from package names.

## Release blockers and source-hygiene gate

See [RELEASE_REVIEW.md](licenses/RELEASE_REVIEW.md) for the open blockers,
manual review requirements, and the exact source-checker interface. A passing
privacy test does not close licensing blockers or establish release readiness.
