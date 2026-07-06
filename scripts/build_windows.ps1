# ============================================================================
# Project X — Native Windows release build (PowerShell)
# ============================================================================
# Optional alternative to build_windows.bat with the same workflow.

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Failed = $false

function Write-Banner {
    param([string]$Title)
    Write-Host "============================================================"
    Write-Host $Title
    Write-Host "============================================================"
}

function Find-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Command = "py"; Args = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Args = @() }
    }
    throw "Python 3 was not found. Install from https://www.python.org/downloads/"
}

try {
    Write-Banner "Project X — Windows Release Build"
    Write-Host "Repository: $Root`n"

    $launcher = Find-PythonLauncher
    $launchCmd = $launcher.Command
    $launchArgs = $launcher.Args
    Write-Host "[OK] Using Python launcher: $launchCmd $($launchArgs -join ' ')"
    & $launchCmd @launchArgs --version
    Write-Host ""

    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating virtual environment at .venv ..."
        & $launchCmd @launchArgs -m venv (Join-Path $Root ".venv")
        Write-Host "[OK] Virtual environment created.`n"
    } else {
        Write-Host "[OK] Using existing virtual environment: .venv`n"
    }

    $requiredAssets = @(
        (Join-Path $Root "src\resources\map\leaflet\leaflet.js"),
        (Join-Path $Root "src\resources\translations\en.json"),
        (Join-Path $Root "src\resources\branding\projectx.ico")
    )
    foreach ($asset in $requiredAssets) {
        if (-not (Test-Path $asset)) {
            throw "Missing bundled asset: $asset. Pull the latest repository and try again."
        }
    }
    Write-Host "[OK] Bundled assets present in repository.`n"

    Write-Host "Upgrading pip ..."
    & $venvPython -m pip install --upgrade pip
    Write-Host "Installing requirements.txt ..."
    & $venvPython -m pip install -r (Join-Path $Root "requirements.txt")
    Write-Host "Installing PyInstaller ..."
    & $venvPython -m pip install pyinstaller
    Write-Host "[OK] Build dependencies installed.`n"

    Write-Host "Running PyInstaller ..."
    & $venvPython -m PyInstaller --noconfirm (Join-Path $Root "installer\projectx.spec")

    $bundleRoot = Join-Path $Root "dist\projectx"
    $bundleRequired = @(
        (Join-Path $bundleRoot "projectx.exe"),
        (Join-Path $bundleRoot "resources\translations\en.json"),
        (Join-Path $bundleRoot "resources\translations\hu.json"),
        (Join-Path $bundleRoot "resources\map\leaflet\leaflet.js"),
        (Join-Path $bundleRoot "resources\branding\projectx-logo.png"),
        (Join-Path $bundleRoot "projectx.ico"),
        (Join-Path $bundleRoot "config\playback.json")
    )
    foreach ($path in $bundleRequired) {
        if (-not (Test-Path $path)) {
            throw "PyInstaller bundle incomplete, missing: $path"
        }
    }
    Write-Host "[OK] PyInstaller bundle verified: executable, translations, map, branding, icon, config`n"

    $exePath = Join-Path $Root "dist\projectx\projectx.exe"
    if ($env:SKIP_INSTALLER -ne "1") {
        & (Join-Path $Root "scripts\build_installer.bat")
        if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }
        $installerPath = Join-Path $Root "release\windows\ProjectX-Setup.exe"
        if (-not (Test-Path $installerPath)) {
            throw "Expected installer not found: release\windows\ProjectX-Setup.exe"
        }
    }

    Write-Host ""
    Write-Banner "BUILD SUCCESSFUL"
    Write-Host "Application bundle:`n  $exePath"
    $installerPath = Join-Path $Root "release\windows\ProjectX-Setup.exe"
    if (Test-Path $installerPath) {
        Write-Host "Windows installer:`n  $installerPath`n"
        Write-Host "Next steps:"
        Write-Host "  1. Run scripts\verify_windows_installer.bat"
        Write-Host "  2. Run ./scripts/prepare_release.sh on Linux"
    }
    exit 0
}
catch {
    Write-Host ""
    Write-Banner "BUILD FAILED"
    Write-Host $_.Exception.Message
    Write-Host "`nRun scripts\build_windows.bat or scripts\build_windows.ps1 after fixing the issue."
    Write-Host "Documentation: BUILD_WINDOWS.md`n"
    exit 1
}
