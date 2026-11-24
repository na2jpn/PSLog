# Developer-only. No automatic dependency installation. Used for the Windows-tested PSLog build workflow.
param(
    [switch]$Sign,
    [switch]$NoSign,
    [string]$CertificateThumbprint = $env:PSLOG_SIGN_CERT_THUMBPRINT,
    [string]$SignToolPath = $env:PSLOG_SIGNTOOL,
    [string]$TimestampUrl = $env:PSLOG_TIMESTAMP_URL,
    [switch]$MachineCertificateStore
)
$ErrorActionPreference = 'Stop'
if ($Sign -and $NoSign) { throw '-Sign and -NoSign cannot be combined.' }
if ($Sign -and [string]::IsNullOrWhiteSpace($CertificateThumbprint)) {
    throw 'Specify -CertificateThumbprint or PSLOG_SIGN_CERT_THUMBPRINT to sign this build.'
}
$shouldSign = -not $NoSign -and ($Sign -or -not [string]::IsNullOrWhiteSpace($CertificateThumbprint))
Push-Location $PSScriptRoot
try {
    python -c "import sys, struct, PySide6, PyInstaller, serial; assert sys.platform == 'win32', 'Windows build required'; assert struct.calcsize('P') == 8, '64-bit Python required'; print(sys.version); print(PySide6.__version__); print(PyInstaller.__version__); print(serial.__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'Build dependencies are missing. Check the existing environment first.' }
    if (-not (Test-Path "assets/pslog.ico")) { throw 'Missing icon: assets/pslog.ico' }
    if (-not (Test-Path "assets/pslog_icon.png")) { throw 'Missing icon: assets/pslog_icon.png' }
    python tools/run_tests.py
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    python tools/windows_version_info.py build/version-pslog.txt
    if ($LASTEXITCODE -ne 0) { throw 'PSLog VERSIONINFO generation failed.' }
    python tools/windows_version_info.py build/version-updater.txt --updater
    if ($LASTEXITCODE -ne 0) { throw 'PSLogUpdater VERSIONINFO generation failed.' }

    # Updater is a tiny standalone helper. PSLog copies it to a temporary folder
    # before launching it, so the installed PSLogUpdater.exe itself can also be
    # replaced by a newer release.
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name PSLogUpdater --icon "assets/pslog.ico" --version-file "build/version-updater.txt" updater.py
    if ($LASTEXITCODE -ne 0) { throw 'PSLogUpdater build failed.' }

    python -m PyInstaller --noconfirm --clean --onedir --windowed --name pslog --icon "assets/pslog.ico" --version-file "build/version-pslog.txt" --hidden-import xlrd --add-data "LICENSE.md;licenses" --add-data "LICENSING.md;licenses" --add-data "AUTHOR_NOTICE.txt;licenses" --add-data "assets/pslog_icon.png;assets" --add-data "assets/sounds;assets/sounds" --add-data "config/db/locations.json;config/db" --add-data "config/db/aja_locations.json;config/db" --add-data "config/db/club_db.csv;config/db" --add-data "config/db/club_db_meta.json;config/db" --add-data "config/db/cty.dat;config/db" --add-data "config/db/cty_meta.json;config/db" --add-data "config/db/country_history.json;config/db" --add-data "config/db/cty_LICENSE.txt;config/db" --add-data "config/templates/pdf;config/templates/pdf" --add-data "config/rules;config/rules" --add-data "config/db/contest;config/db/contest" --add-data "config/templates/cabrillo;config/templates/cabrillo" main.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    New-Item -ItemType Directory -Force "dist/pslog/exec" | Out-Null
    New-Item -ItemType Directory -Force "dist/pslog/meta" | Out-Null
    New-Item -ItemType Directory -Force "dist/pslog/docs" | Out-Null
    Copy-Item -Force "dist/PSLogUpdater.exe" "dist/pslog/exec/PSLogUpdater.exe"

    # Before packaging, make the frozen pslog.exe force-load the update modules.
    # This catches a damaged/incomplete PyInstaller archive before a ZIP can be released.
    $selfCheck = Start-Process -FilePath (Join-Path $PSScriptRoot "dist/pslog/pslog.exe") -ArgumentList '--update-self-check' -WorkingDirectory (Join-Path $PSScriptRoot "dist/pslog") -Wait -PassThru
    if ($selfCheck.ExitCode -ne 0) { throw "Frozen PSLog self-check failed (exit $($selfCheck.ExitCode)); packaging stopped." }

    # Sign the exact executables that will be packaged. Hashes must be created
    # afterwards; signing an EXE inside an existing ZIP would invalidate them.
    if ($shouldSign) {
        $signArgs = @('-m', 'tools.windows_signing', '--certificate-thumbprint', $CertificateThumbprint)
        if ($SignToolPath) { $signArgs += @('--signtool', $SignToolPath) }
        if ($TimestampUrl) { $signArgs += @('--timestamp-url', $TimestampUrl) }
        if ($MachineCertificateStore) { $signArgs += '--machine-store' }
        $signArgs += @('dist/pslog/pslog.exe', 'dist/pslog/exec/PSLogUpdater.exe')
        python @signArgs
        if ($LASTEXITCODE -ne 0) { throw 'Code signing or verification failed; packaging stopped.' }
        Write-Host 'Code signing and verification succeeded.' -ForegroundColor Green
    } else {
        Write-Warning 'Unsigned development build. Use -Sign and a signing certificate for the public release.'
    }

    $versionOutput = python -c "from storage import VERSION; print(VERSION)"
    if ($LASTEXITCODE -ne 0) { throw 'Could not read PSLog VERSION from storage.py.' }
    $version = "$versionOutput".Trim()
    if (-not $version) { throw 'PSLog VERSION is empty.' }
    $releaseStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $releaseFile = Join-Path $PSScriptRoot "release/PSLog_${version}_Windows_$releaseStamp.zip"
    python tools/package_windows.py dist/pslog . $releaseFile
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }

    # Ver1.043以降は通常のWindows版ZIPを、そのままPSLogのバージョンアップ機能で使用します。

    Write-Host "Created: $releaseFile"
    Write-Host 'Windows runtime checks are still required. See WINDOWS_CHECKLIST.txt in the source tree.'
} finally { Pop-Location }
