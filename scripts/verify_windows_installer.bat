@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem Project X — Verify Windows installer (SAVE-076)
rem ============================================================================
rem Run on Windows after ProjectX-Setup.exe is built.
rem Performs silent install to a temp directory, checks shortcuts logic, uninstalls.

cd /d "%~dp0.."
set "ROOT=%CD%"
set "INSTALLER=%ROOT%\website\downloads\windows\ProjectX-Setup.exe"
set "TEST_DIR=%TEMP%\ProjectXInstallerTest"
set "TEST_EXE=%TEST_DIR%\projectx.exe"

if not exist "%INSTALLER%" (
    echo [FAIL] Installer not found: %INSTALLER%
    echo        Run scripts\build_installer.bat first.
    exit /b 1
)

echo ============================================================
echo Project X — Windows Installer Verification
echo ============================================================
echo Installer: %INSTALLER%
echo Test directory: %TEST_DIR%
echo.

if exist "%TEST_DIR%" rmdir /S /Q "%TEST_DIR%" 2>nul

echo [1/4] Silent install ...
"%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="%TEST_DIR%" /TASKS=""
if errorlevel 1 (
    echo [FAIL] Silent install returned an error.
    exit /b 1
)

if not exist "%TEST_EXE%" (
    echo [FAIL] Installed executable not found: %TEST_EXE%
    exit /b 1
)
echo [OK] Silent install completed.

echo [2/4] Application files present ...
if not exist "%TEST_DIR%\projectx.ico" (
    echo [WARN] projectx.ico not found in install directory.
) else (
    echo [OK] Application icon present.
)
if not exist "%TEST_DIR%\resources\translations\en.json" (
    echo [FAIL] Bundled resources missing under install directory.
    exit /b 1
)
echo [OK] Bundled resources present.

echo [3/4] Executable present ...
if not exist "%TEST_EXE%" (
    echo [FAIL] projectx.exe missing after install.
    exit /b 1
)
echo [OK] projectx.exe present. Launch manually to confirm First Run Wizard.

echo [4/4] Silent uninstall ...
set "UNINSTALLER=%TEST_DIR%\unins000.exe"
if not exist "%UNINSTALLER%" (
    echo [FAIL] Uninstaller not found: %UNINSTALLER%
    exit /b 1
)
"%UNINSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
if errorlevel 1 (
    echo [FAIL] Silent uninstall returned an error.
    exit /b 1
)
if exist "%TEST_DIR%" (
    echo [FAIL] Install directory still exists after uninstall.
    exit /b 1
)
echo [OK] Silent uninstall completed and install directory removed.

echo.
echo ============================================================
echo INSTALLER VERIFICATION SUCCESSFUL
echo ============================================================
echo Manual checks still recommended on a clean VM:
echo   - Install to Program Files via interactive setup
echo   - Confirm Start Menu shortcut
echo   - Optional desktop shortcut task
echo   - First Run Wizard on first launch
echo.
exit /b 0
