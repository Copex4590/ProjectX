@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem Project X — Verify Windows installer (SAVE-076)
rem ============================================================================
rem Run on Windows after ProjectX-Setup.exe is built.
rem Performs silent install to a temp directory, checks shortcuts logic, uninstalls.

cd /d "%~dp0.."
set "ROOT=%CD%"
set "INSTALLER=%ROOT%\release\windows\ProjectX-Setup.exe"
set "WEBSITE_COPY=%ROOT%\website\downloads\windows\ProjectX-Setup.exe"
set "TEST_DIR=%TEMP%\ProjectXInstallerTest"
set "TEST_EXE=%TEST_DIR%\projectx.exe"

if not exist "%INSTALLER%" (
    echo [FAIL] Installer not found: %INSTALLER%
    echo        Run scripts\build_windows.bat or scripts\build_installer.bat first.
    exit /b 1
)

if not exist "%ROOT%\website\downloads\windows" (
    mkdir "%ROOT%\website\downloads\windows"
)
copy /Y "%INSTALLER%" "%WEBSITE_COPY%" >nul
if errorlevel 1 (
    echo [FAIL] Could not sync installer to website\downloads\windows\
    exit /b 1
)
echo [OK] Canonical installer: %INSTALLER%
echo [OK] Website copy: %WEBSITE_COPY%

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
    echo [FAIL] Bundled translation missing: en.json
    exit /b 1
)
if not exist "%TEST_DIR%\resources\translations\hu.json" (
    echo [FAIL] Bundled translation missing: hu.json
    exit /b 1
)
if not exist "%TEST_DIR%\resources\map\leaflet\leaflet.js" (
    echo [FAIL] Bundled map resource missing: leaflet.js
    exit /b 1
)
if not exist "%TEST_DIR%\resources\branding\projectx-logo.png" (
    echo [FAIL] Bundled branding missing: projectx-logo.png
    exit /b 1
)
if not exist "%TEST_DIR%\config\playback.json" (
    echo [FAIL] Bundled config missing: playback.json
    exit /b 1
)
echo [OK] Bundled resources present (translations, map, branding, config).

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

set "RETRIES=30"
:wait_uninstall
if not exist "%TEST_DIR%" goto :uninstall_done
set /a RETRIES-=1
if !RETRIES! LEQ 0 goto :uninstall_check_fail
ping 127.0.0.1 -n 2 >nul
goto :wait_uninstall

:uninstall_check_fail
if not exist "%TEST_DIR%" goto :uninstall_done
echo [FAIL] Install directory still exists after uninstall.
exit /b 1

:uninstall_done
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
