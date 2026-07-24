@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem Project X — SAVE-234 Windows release + verification (native Windows)
rem ============================================================================
rem Run from repository root on Windows 10/11 x64 after dual-boot / VM:
rem   scripts\save234_windows_release.bat
rem
rem Steps: build stamp → PyInstaller → Inno Setup → silent install tests
rem         → upgrade → uninstall → resource inventory → checklist log

cd /d "%~dp0.."
set "ROOT=%CD%"
set "LOG=%ROOT%\docs\reports\SAVE-234_windows_verify_log.txt"
set "INSTALLER=%ROOT%\release\windows\ProjectX-Setup.exe"
set "FAILED=0"

if exist "%LOG%" del /f /q "%LOG%" >nul 2>&1

call :log "============================================================"
call :log "SAVE-234 — Windows installer completion"
call :log "Repo: %ROOT%"
call :log "============================================================"

if not defined PROJECTX_BUILD (
    for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"`) do set "PROJECTX_BUILD=0.3.1-beta-%%D"
)
call :log "PROJECTX_BUILD=%PROJECTX_BUILD%"

call :log ""
call :log "[1/5] Building Windows release (scripts\build_windows.bat) ..."
call "%ROOT%\scripts\build_windows.bat"
if errorlevel 1 (
    call :fail "build_windows.bat failed"
    goto :done
)
if not exist "%INSTALLER%" (
    call :fail "ProjectX-Setup.exe missing after build"
    goto :done
)
for %%A in ("%INSTALLER%") do call :log "[OK] Installer size: %%~zA bytes"

call :log ""
call :log "[2/5] Static installer metadata (ISS) ..."
findstr /C:"MyAppVersion \"0.3.1-beta\"" "%ROOT%\installer\windows\projectx.iss" >nul
if errorlevel 1 (call :fail "ISS MyAppVersion not 0.3.1-beta") else (call :log "[OK] ISS version 0.3.1-beta")
findstr /C:"SetupIconFile=" "%ROOT%\installer\windows\projectx.iss" >nul
if errorlevel 1 (call :fail "ISS SetupIconFile missing") else (call :log "[OK] ISS SetupIconFile present")
findstr /C:"desktopicon" "%ROOT%\installer\windows\projectx.iss" >nul
if errorlevel 1 (call :fail "ISS desktop shortcut task missing") else (call :log "[OK] Desktop shortcut task")
findstr /C:"DefaultGroupName" "%ROOT%\installer\windows\projectx.iss" >nul
if errorlevel 1 (call :fail "ISS Start Menu group missing") else (call :log "[OK] Start Menu group")
findstr /C:"Name: \"launch\"" "%ROOT%\installer\windows\projectx.iss" >nul
if errorlevel 1 (call :fail "ISS launch-after-install task missing") else (call :log "[OK] Launch after install task")
findstr /C:"UninstallDisplayName" "%ROOT%\installer\windows\projectx.iss" >nul
if errorlevel 1 (call :fail "ISS uninstall display missing") else (call :log "[OK] Uninstall entry metadata")
findstr /I /C:"[Registry]" "%ROOT%\installer\windows\projectx.iss" >nul
if not errorlevel 1 (
    call :log "[WARN] ISS has Registry section — review file associations"
) else (
    call :log "[OK] File associations: none declared (not used)"
)

call :log ""
call :log "[3/5] Fresh silent install + resource inventory ..."
set "TEST_DIR=%TEMP%\ProjectX-SAVE234-Fresh"
if exist "%TEST_DIR%" rmdir /S /Q "%TEST_DIR%" 2>nul
"%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="%TEST_DIR%" /TASKS="desktopicon"
if errorlevel 1 (
    call :fail "Fresh silent install failed"
    goto :done
)
call :check_file "%TEST_DIR%\projectx.exe" "projectx.exe"
call :check_file "%TEST_DIR%\projectx.ico" "projectx.ico"
call :check_file "%TEST_DIR%\resources\build_stamp" "build_stamp"
call :check_file "%TEST_DIR%\resources\translations\en.json" "en.json"
call :check_file "%TEST_DIR%\resources\translations\hu.json" "hu.json"
call :check_file "%TEST_DIR%\resources\map\leaflet\leaflet.js" "leaflet.js"
call :check_file "%TEST_DIR%\resources\map\map.html" "map.html"
call :check_file "%TEST_DIR%\resources\theme\colors.css" "theme colors.css"
call :check_file "%TEST_DIR%\resources\branding\projectx-logo.png" "branding logo"
call :check_file "%TEST_DIR%\config\playback.json" "playback.json"
call :check_dir "%TEST_DIR%\config\camera_packs" "camera_packs"
call :check_dir "%TEST_DIR%\config\cameras" "cameras"
if exist "%TEST_DIR%\data" (
    call :fail "Bundled data\ must not exist"
) else (
    call :log "[OK] No bundled data\ tree"
)

rem GUI PE check (subsystem Windows, not console)
powershell -NoProfile -Command "$b=[IO.File]::ReadAllBytes('%TEST_DIR%\projectx.exe'); $pe=BitConverter.ToInt32($b,0x3C); $sub=BitConverter.ToUInt16($b,$pe+0x5C); if($sub -eq 2){'GUI'} elseif($sub -eq 3){'CONSOLE'} else {$sub}" > "%TEMP%\px_subsys.txt"
set /p SUBSYS=<"%TEMP%\px_subsys.txt"
if /I "%SUBSYS%"=="GUI" (
    call :log "[OK] projectx.exe is GUI subsystem (no console window)"
) else (
    call :fail "projectx.exe subsystem is %SUBSYS% (expected GUI)"
)

call :log ""
call :log "[4/5] Upgrade install (re-run Setup over same dir) ..."
"%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="%TEST_DIR%" /TASKS=""
if errorlevel 1 (
    call :fail "Upgrade silent install failed"
) else (
    call :log "[OK] Upgrade install completed"
)
if not exist "%TEST_DIR%\projectx.exe" (
    call :fail "projectx.exe missing after upgrade"
) else (
    call :log "[OK] projectx.exe present after upgrade"
)

call :log ""
call :log "[5/5] Clean uninstall ..."
set "UNINS=%TEST_DIR%\unins000.exe"
if not exist "%UNINS%" (
    call :fail "unins000.exe missing"
    goto :done
)
"%UNINS%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
set "RETRIES=45"
:wait_unins
if not exist "%TEST_DIR%" goto :unins_ok
set /a RETRIES-=1
if !RETRIES! LEQ 0 (
    call :fail "Install directory remains after uninstall: %TEST_DIR%"
    goto :done
)
ping 127.0.0.1 -n 2 >nul
goto :wait_unins
:unins_ok
call :log "[OK] Clean uninstall removed install directory"

call :log ""
call :log "Manual smoke (required for full SAVE-234 PASS):"
call :log "  - Launch installed app once: First Run Wizard, settings under %%APPDATA%%\Project X"
call :log "  - Confirm DB files created under %%APPDATA%%\Project X\data"
call :log "  - Map / cameras / AIS / theme / language switch"
call :log "  - No startup exceptions; no missing DLL dialogs"

:done
call :log ""
if "%FAILED%"=="0" (
    call :log "SAVE-234 automated installer checks: PASS"
    call :log "Full application smoke still required for overall PASS."
    echo.
    echo Log: %LOG%
    endlocal & exit /b 0
)
call :log "SAVE-234 automated installer checks: FAIL"
echo.
echo Log: %LOG%
endlocal & exit /b 1

:check_file
if exist "%~1" (call :log "[OK] %~2") else (call :fail "Missing %~2 (%~1)")
exit /b 0

:check_dir
if exist "%~1" (call :log "[OK] %~2") else (call :fail "Missing dir %~2 (%~1)")
exit /b 0

:fail
set "FAILED=1"
call :log "[FAIL] %~1"
exit /b 0

:log
echo %~1
>>"%LOG%" echo %~1
exit /b 0
