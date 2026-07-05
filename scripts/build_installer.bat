@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem Project X — Compile Windows Inno Setup installer (SAVE-076)
rem ============================================================================
rem Requires: dist\projectx\projectx.exe from PyInstaller
rem Produces: website\downloads\windows\ProjectX-Setup.exe

cd /d "%~dp0.."
set "ROOT=%CD%"
set "INSTALLER=%ROOT%\website\downloads\windows\ProjectX-Setup.exe"
set "ISCC="

if not exist "%ROOT%\dist\projectx\projectx.exe" (
    echo [FAIL] PyInstaller bundle missing: dist\projectx\projectx.exe
    echo        Run scripts\build_windows.bat first.
    exit /b 1
)

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not defined ISCC if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not defined ISCC (
    echo [FAIL] Inno Setup 6 not found.
    echo        Install from https://jrsoftware.org/isinfo.php
    exit /b 1
)

echo Compiling installer with: !ISCC!
"!ISCC!" "%ROOT%\installer\windows\projectx.iss"
if errorlevel 1 (
    echo [FAIL] Inno Setup compilation failed.
    exit /b 1
)

if not exist "%INSTALLER%" (
    echo [FAIL] Expected installer not found: %INSTALLER%
    exit /b 1
)

echo [OK] Windows installer created:
echo   %INSTALLER%
exit /b 0
