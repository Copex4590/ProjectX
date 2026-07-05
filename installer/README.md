# Project X Installer

Packaging assets and scripts for distributing Project X as a desktop application.

## Branding assets

| File | Purpose |
|------|---------|
| `src/resources/branding/projectx-logo.svg` | Master vector logo |
| `src/resources/branding/projectx-logo.png` | Application / About / splash |
| `src/resources/branding/projectx.ico` | Windows icon |
| `src/resources/branding/projectx.icns` | macOS icon (future) |

Regenerate PNG and ICO from the master artwork:

```bash
python3 scripts/generate_branding_assets.py
```

## Linux installer

Installs Project X to `~/.local/share/projectx`, creates a launcher, desktop shortcut, and applications menu entry.

```bash
chmod +x installer/linux/install.sh
installer/linux/install.sh --launch
```

Options:

- `--prefix DIR` — custom install directory
- `--no-desktop` — skip desktop shortcut
- `--no-start-menu` — skip applications menu entry
- `--launch` — start Project X after installation

Uninstall:

```bash
installer/linux/uninstall.sh
```

## Windows installer

1. Build the PyInstaller bundle:

```bash
pip install pyinstaller
pyinstaller installer/projectx.spec
```

2. Compile the Inno Setup script `installer/windows/projectx.iss` using [Inno Setup](https://jrsoftware.org/isinfo.php).

The installer provides:

- Desktop shortcut (optional task)
- Start Menu shortcut
- Launch after installation (optional task)
- Official Project X icon

## macOS (future)

- Bundle with `projectx.icns`
- `.app` packaging

## Build metadata

Set at package time:

```bash
export PROJECTX_BUILD="2026.07.05"
export PROJECTX_GITHUB_URL="https://github.com/Copex4590/ProjectX"
```
