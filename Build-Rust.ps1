param(
    [ValidateSet('windows-x64', 'windows-x86', 'linux-x64', 'macos-arm64', 'macos-x64')]
    [string]$Target = 'windows-x64',
    [string]$OutDir = '',
    [switch]$Package
)
# All compiler flags and archive privacy gates are enforced by release.py.
# Windows native dependencies require clang-cl on PATH; there is no cl.exe fallback.
$ErrorActionPreference = 'Stop'
if (-not $OutDir) { $OutDir = "build/release/$Target" }
Push-Location -LiteralPath $PSScriptRoot
try {
    python scripts/release.py build --target $Target --out-dir $OutDir
    if ($LASTEXITCODE -ne 0) { throw 'Staged build failed; no root executables were replaced.' }
    if ($Package) {
        python scripts/release.py test --target $Target --out-dir $OutDir
        if ($LASTEXITCODE -ne 0) { throw 'Dataset-free release gates failed.' }
        python scripts/release.py package --target $Target --out-dir $OutDir
        if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
        python scripts/release.py verify --out-dir $OutDir
        if ($LASTEXITCODE -ne 0) { throw 'Archive verification failed.' }
    }
} finally {
    Pop-Location
}
