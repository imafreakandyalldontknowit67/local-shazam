# Clean Windows release check

Status: **not yet run on a clean PC or VM**. Existing-machine generated-audio
checks passed for v0.2.1 x64 and x86; see [the scoped results](release-smoke-0.2.1.json).
A restricted PATH on a development PC does not remove installed system DLLs.
The current test host is Windows 10 Home x64 without Windows Sandbox available.
No VM, OS feature, system configuration or runtime installer was added.

## Run on another PC or an existing fresh Windows VM

1. Record Windows edition/version/build and CPU architecture. Use a normal user,
   with no Rust, Zig, Visual Studio or Python installed. Do not disable security.
2. Download the v0.2.2-beta.1 ZIP and `SHA256SUMS.txt` from the same release. Compare
   `Get-FileHash -Algorithm SHA256` with the ZIP entry before extracting.
3. Extract the entire ZIP into a writable directory. Keep notices and
   `olaf-runtime` next to `local-shazam.exe`. Do not run inside the ZIP.
4. Try opening the menu before adding prerequisites. Record any missing-DLL
   message. If needed, install the matching **x64 or x86 Microsoft Visual C++
   v14 Redistributable** from [Microsoft's official page](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170).
   Match the app architecture, even for an x86 app on x64 Windows. Never fetch
   individual DLLs from third-party sites. Record the installed runtime version.
5. Install FFmpeg and FFprobe appropriate to the OS; verify both `-version`
   commands work in a newly opened terminal. Record their versions.
6. Open the app normally; exercise the real folder/file picker dialogs. Add a
   dedicated folder containing two short audio files you own or generated, with
   **two workers**. Use a fresh index, not a production library.
7. Identify a seven-second excerpt from one indexed file. Check the first result
   is the expected file. Try an unrelated clip and record whether the app declines
   to match; a suggestion is not proof of identity.
8. Close and reopen. Check library stats still show both files; adding the unchanged
   folder again should skip those files. Keep the originals available.
9. Repeat in a separate extraction/index for x86. A WOW64 pass is not native
   32-bit Windows validation. Do not claim native 32-bit support was tested unless
   it was actually run there. Never reuse an x64 index with x86 or vice versa.
10. Record exit/errors, prerequisites and observations without usernames or music
    paths. Mark each architecture independently; failures remain open until fixed.

## Evidence to retain

Release/tag and ZIP hash, OS/build/architecture, native versus WOW64 execution,
prerequisite versions, menu/dialog behavior, indexed/failed/skipped counts, known
and unrelated clip outcomes, reopen/incremental results, and any required setup
fix. A tiny functional check is not a recognition-accuracy benchmark or stress test.
