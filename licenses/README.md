# License evidence layout

- `../LICENSE`: original app MIT license, unchanged.
- `../THIRD_PARTY_NOTICES.md`: component boundaries and attribution summary.
- `olaf/`: full Olaf AGPL, embedded C licenses and source notices, Zigzag MIT,
  and the vendor-provided Zig/mingw-w64/musl toolchain notices.
- `olaf-inventory.json`: hashes and source paths for those copies.
- `rust/`: exact per-version license/notice texts from checksum-verified published
  crates; `UPSTREAM-*` identifies exact-revision upstream supplements.
  `EMBEDDED-NOTICES.txt` preserves full attribution/license comment blocks from
  named source files (and copyright elements from Wayland protocol XML).
- `rust-inventory.json`: machine-readable 115-package evidence and explicit review
  statuses, tied to the LF-normalized Cargo.lock SHA-256.
- `RUST_DEPENDENCIES.md`: human-readable version/license/evidence index.
- `terms/MIT-template.txt`: unfilled standard terms linked by upstream documents;
  not an invented grant or copyright holder for crates missing notices.
- `RELEASE_REVIEW.md`: unresolved blockers and source-hygiene interface.

Retain these texts, the root notices, and original file-level notices together in
any applicable distribution. Copies preserve original bytes; do not run automatic
line-ending normalization or substitute generic licenses for attributed texts.
Authors and copyright holders are not interchangeable. The original spelling,
years, email addresses and public attribution URLs in notices are intentional.

These are license documents and audit evidence, **not dependency source archives**.
Binary corresponding-source obligations require the actual exact dependency source
and build instructions as well. No license file alone establishes that obligation
has been met. See RELEASE_REVIEW.md before distribution.
