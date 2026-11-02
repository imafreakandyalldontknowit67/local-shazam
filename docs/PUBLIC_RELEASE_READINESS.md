# Release status: Windows 0.2.2

[Local Shazam v0.2.2](https://github.com/imafreakandyalldontknowit67/local-shazam/releases/tag/v0.2.2)
is published as the latest regular release. The repository is public.

- x64 and x86 executables report version `0.2.2`; download filenames have no prerelease suffix.
- Both builds passed release gates and independent verification of binaries,
  matching source archives, notices, architecture and checksums.
- All seven uploaded assets were downloaded anonymously and byte-compared.
- Generated-audio tests passed on both builds: index two tracks, identify a correct
  seven-second excerpt, reject unrelated audio, reopen and skip unchanged files.
- Cross-architecture index reuse was rejected without changing the index marker.
- Original app copyright names **badger**; third-party notices remain intact.

The exact packaged commit is `25ac6feafa961b51ac6574dd2d9860a1607b59df`.
Recognition code and settings are unchanged from 0.2.1.

See the [release receipt](release-0.2.2-verification.json),
[smoke results](release-smoke-0.2.2.json),
[history review](public-history-review.json), and
[Windows distribution review](../licenses/WINDOWS_DISTRIBUTION.md).
Historical verification records describe their original releases, not current status.

## Remaining verification

Clean-PC setup and native 32-bit Windows testing remain unverified. x86 was tested
through WOW64 on Windows 10 x64. The smoke tests are functional checks, not an
accuracy benchmark. Follow the [clean Windows checklist](CLEAN_WINDOWS_TEST.md)
on a separate PC or fresh VM. Downloads are unsigned.

## Local cleanup

Disposable staging remains locally because earlier deletion commands were rejected
by execution policy. No local cleanup is claimed. Staging is ignored by Git and
not included in the release. Verified recovery archives and audit evidence are retained.
