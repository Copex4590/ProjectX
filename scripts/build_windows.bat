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

call :install_dependencies
if errorlevel 1 goto :report_failure

call :run_pyinstaller
if errorlevel 1 goto :report_failure

call :verify_output
if errorlevel 1 goto :report_failure

call :offer_inno_setup
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
if exist "%ROOT%\dist\projectx\projectx.exe" (
    echo [OK] Verified: dist\projectx\projectx.exe
    echo.
    exit /b 0
)
echo [FAIL] Expected output not found: dist\projectx\projectx.exe
exit /b 1

:offer_inno_setup
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not defined ISCC if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not defined ISCC (
    echo Inno Setup 6 was not detected.
    echo Optional next step: install Inno Setup from https://jrsoftware.org/isinfo.php
    echo Then compile: installer\windows\projectx.iss
    echo.
    exit /b 0
)

echo Inno Setup found: !ISCC!
set "BUILD_INSTALLER="
set /p BUILD_INSTALLER="Compile Windows installer now? [Y/N]: "
if /I "!BUILD_INSTALLER!"=="Y" (
    echo Compiling installer\windows\projectx.iss ...
    "!ISCC!" "%ROOT%\installer\windows\projectx.iss"
    if errorlevel 1 (
        echo [WARN] Inno Setup compilation failed.
    ) else (
        echo [OK] Installer compiled. Check installer\windows\Output\
    )
) else (
    echo Skipped installer compilation.
    echo You can compile later with:
    echo   "!ISCC!" "%ROOT%\installer\windows\projectx.iss"
)
echo.
exit /b 0

:report_success
call :banner "BUILD SUCCESSFUL"
echo Output directory:
echo   %ROOT%\dist\projectx\
echo Executable:
echo   %ROOT%\dist\projectx\projectx.exe
echo.
echo Next steps:
echo   1. Run projectx.exe and smoke-test maps, language, first-run wizard
echo   2. Optionally compile the Inno Setup installer
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
