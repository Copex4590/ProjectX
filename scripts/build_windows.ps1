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

    $exePath = Join-Path $Root "dist\projectx\projectx.exe"
    if (-not (Test-Path $exePath)) {
        throw "Expected output not found: dist\projectx\projectx.exe"
    }
    Write-Host "[OK] Verified: dist\projectx\projectx.exe`n"

    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($iscc) {
        Write-Host "Inno Setup found: $iscc"
        $answer = Read-Host "Compile Windows installer now? [Y/N]"
        if ($answer -match '^[Yy]$') {
            & $iscc (Join-Path $Root "installer\windows\projectx.iss")
            Write-Host "[OK] Installer compiled. Check installer\windows\Output\"
        } else {
            Write-Host "Skipped installer compilation."
        }
    } else {
        Write-Host "Inno Setup 6 was not detected."
        Write-Host "Optional next step: install Inno Setup from https://jrsoftware.org/isinfo.php"
        Write-Host "Then compile: installer\windows\projectx.iss"
    }

    Write-Host ""
    Write-Banner "BUILD SUCCESSFUL"
    Write-Host "Output directory:`n  $(Join-Path $Root 'dist\projectx\')"
    Write-Host "Executable:`n  $exePath`n"
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
