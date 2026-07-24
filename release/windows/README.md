# Windows release artifacts

Place the Inno Setup output here:

```
ProjectX-Setup.exe
SHA256SUMS
```

**Version:** `0.3.1-beta`  
**Script:** `installer/windows/projectx.iss` (`MyAppVersion` / `MyAppVersionNumeric`)  
**Icon:** `src/resources/branding/projectx.ico`

Build on native Windows (after PyInstaller):

```bat
scripts\build_windows.bat
```

or:

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\windows\projectx.iss
```

Website copy: `website/downloads/windows/ProjectX-Setup.exe` (synced by `scripts/prepare_release.sh`).

SAVE-205: installer script and metadata prepared; binary not produced on Linux CI.
