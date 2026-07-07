@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem Project X — Native Windows release build (dual-boot workflow)
rem ============================================================================
rem Run from the repository root or from anywhere:
rem   scripts\build_windows.bat
rem
rem Requires: Git, Python 3.10+ (python.org or py launcher)
rem Produces: dist\projectx\projectx.exe

cd /d "%~dp0.."
set "ROOT=%CD%"
set "FAILED=0"

call :banner "Project X — Windows Release Build"
echo Repository: %ROOT%
echo.

call :find_python
if errorlevel 1 goto :report_failure

call :ensure_venv
if errorlevel 1 goto :report_failure

call :check_bundled_assets
if errorlevel 1 goto :report_failure

call :verify_data_tree
if errorlevel 1 goto :report_failure

call :install_dependencies
if errorlevel 1 goto :report_failure

call :run_pyinstaller
if errorlevel 1 goto :report_failure

call :verify_output
if errorlevel 1 goto :report_failure

call :build_installer
if errorlevel 1 goto :report_failure

if not exist "%ROOT%\release\windows\ProjectX-Setup.exe" (
    echo [FAIL] Expected installer not found: release\windows\ProjectX-Setup.exe
    goto :report_failure
)
echo [OK] Verified: release\windows\ProjectX-Setup.exe
echo.

call :sync_website_installer
if errorlevel 1 goto :report_failure

goto :report_success

:find_python
set "PY="
where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
    goto :find_python_ok
)
where python >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    goto :find_python_ok
)
echo [FAIL] Python 3 was not found.
echo        Install Python 3.10+ from https://www.python.org/downloads/
echo        Enable "Add python.exe to PATH" during installation.
exit /b 1

:find_python_ok
echo [OK] Using Python launcher: %PY%
%PY% --version
if errorlevel 1 exit /b 1
echo.
exit /b 0

:ensure_venv
if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"
    echo [OK] Using existing virtual environment: .venv
    echo.
    exit /b 0
)

echo Creating virtual environment at .venv ...
%PY% -m venv "%ROOT%\.venv"
if errorlevel 1 (
    echo [FAIL] Could not create .venv
    exit /b 1
)
set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"
echo [OK] Virtual environment created.
echo.
exit /b 0

:check_bundled_assets
set "MISSING="
if not exist "%ROOT%\src\resources\map\leaflet\leaflet.js" set "MISSING=!MISSING! leaflet"
if not exist "%ROOT%\src\resources\translations\en.json" set "MISSING=!MISSING! translations"
if not exist "%ROOT%\src\resources\branding\projectx.ico" set "MISSING=!MISSING! branding"
if not defined MISSING (
    echo [OK] Bundled assets present in repository.
    echo.
    exit /b 0
)
echo [FAIL] Missing bundled assets:!MISSING!
echo        Pull the latest repository on Linux, commit bundled assets, then try again.
echo        Leaflet fetch (Linux): scripts/fetch_leaflet.sh
exit /b 1

:verify_data_tree
echo Verifying data/ tree contains no runtime artifacts ...
"%VENV_PY%" "%ROOT%\scripts\verify_data_tree_clean.py"
if errorlevel 1 exit /b 1
echo [OK] data/ tree is clean.
echo.
exit /b 0

:install_dependencies
echo Upgrading pip ...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo Installing requirements.txt ...
"%VENV_PY%" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 exit /b 1

echo Installing PyInstaller ...
"%VENV_PY%" -m pip install pyinstaller
if errorlevel 1 exit /b 1

echo [OK] Build dependencies installed.
echo.
exit /b 0

:run_pyinstaller
echo Running PyInstaller ...
"%VENV_PY%" -m PyInstaller --noconfirm "%ROOT%\installer\projectx.spec"
if errorlevel 1 (
    echo [FAIL] PyInstaller build failed.
    exit /b 1
)
echo.
exit /b 0

:verify_output
set "BUNDLE=%ROOT%\dist\projectx"
set "MISSING="

if not exist "%BUNDLE%\projectx.exe" set "MISSING=!MISSING! projectx.exe"
if not exist "%BUNDLE%\resources\translations\en.json" set "MISSING=!MISSING! resources\translations\en.json"
if not exist "%BUNDLE%\resources\translations\hu.json" set "MISSING=!MISSING! resources\translations\hu.json"
if not exist "%BUNDLE%\resources\map\leaflet\leaflet.js" set "MISSING=!MISSING! resources\map\leaflet\leaflet.js"
if not exist "%BUNDLE%\resources\branding\projectx-logo.png" set "MISSING=!MISSING! resources\branding\projectx-logo.png"
if not exist "%BUNDLE%\projectx.ico" set "MISSING=!MISSING! projectx.ico"
if not exist "%BUNDLE%\config\playback.json" set "MISSING=!MISSING! config\playback.json"

if defined MISSING (
    echo [FAIL] PyInstaller bundle incomplete under dist\projectx\:
    echo        !MISSING!
    exit /b 1
)

if exist "%BUNDLE%\data" (
    echo [FAIL] dist\projectx\data\ must not exist in release bundles.
    exit /b 1
)

echo [OK] PyInstaller bundle verified:
echo        executable, translations, map, branding, icon, config
echo.
exit /b 0

:build_installer
if /I "%SKIP_INSTALLER%"=="1" (
    echo [SKIP] Installer build skipped ^(SKIP_INSTALLER=1^).
    echo.
    exit /b 0
)

call "%ROOT%\scripts\build_installer.bat"
if errorlevel 1 exit /b 1

echo [OK] Verified: release\windows\ProjectX-Setup.exe
echo.
exit /b 0

:sync_website_installer
set "CANONICAL=%ROOT%\release\windows\ProjectX-Setup.exe"
set "WEBSITE_COPY=%ROOT%\website\downloads\windows\ProjectX-Setup.exe"

if not exist "%CANONICAL%" (
    echo [FAIL] Canonical installer not found: %CANONICAL%
    exit /b 1
)

if not exist "%ROOT%\website\downloads\windows" (
    mkdir "%ROOT%\website\downloads\windows"
)

copy /Y "%CANONICAL%" "%WEBSITE_COPY%" >nul
if errorlevel 1 (
    echo [FAIL] Could not sync installer to website\downloads\windows\
    exit /b 1
)

echo [OK] Synced website\downloads\windows\ProjectX-Setup.exe
echo.
exit /b 0

:report_success
call :banner "BUILD SUCCESSFUL"
echo Application bundle:
echo   %ROOT%\dist\projectx\projectx.exe
if exist "%ROOT%\release\windows\ProjectX-Setup.exe" (
    echo Windows installer:
    echo   %ROOT%\release\windows\ProjectX-Setup.exe
    echo.
    echo Next steps:
    echo   1. Run scripts\verify_windows_installer.bat
    echo   2. Run ./scripts/prepare_release.sh on Linux to refresh checksums
    echo   3. On a clean VM: install, confirm First Run Wizard, smoke-test map
) else (
    echo.
    echo Next steps:
    echo   1. Install Inno Setup 6 and run scripts\build_installer.bat
    echo   2. Run projectx.exe and smoke-test maps, language, first-run wizard
)
echo.
endlocal
exit /b 0

:report_failure
call :banner "BUILD FAILED"
echo Review the messages above, fix the reported issue, and run:
echo   scripts\build_windows.bat
echo.
echo Documentation: BUILD_WINDOWS.md
echo.
endlocal
exit /b 1

:banner
echo ============================================================
echo %~1
echo ============================================================
exit /b 0
