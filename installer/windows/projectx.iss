; ============================================================================
; Project X — Windows Installer (Inno Setup 6)
; SAVE-076 — First installable Windows release
; ============================================================================
;
; Build (after PyInstaller):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\windows\projectx.iss
;
; Output:
;   release\windows\ProjectX-Setup.exe
;   (sync to website via scripts/prepare_release.sh)
;
; Silent install:
;   ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
;
; Silent install with desktop shortcut:
;   ProjectX-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="desktopicon"
;
; Silent uninstall:
;   "%ProgramFiles%\Project X\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

#define MyAppName "Project X"
#define MyAppVersion "0.3.0-alpha"
#define MyAppVersionNumeric "0.3.0.0"
#define MyAppPublisher "Project X"
#define MyAppExeName "projectx.exe"
#define MyAppOutput "ProjectX-Setup"

[Setup]
AppId={{A4F8B2C1-9D3E-4F5A-8B7C-1E2D3C4B5A6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Project X
DefaultGroupName={#MyAppName}
DisableDirPage=auto
DisableProgramGroupPage=no
OutputDir=..\..\release\windows
OutputBaseFilename={#MyAppOutput}
SetupIconFile=..\..\src\resources\branding\projectx.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=force
RestartIfNeededByRun=no
VersionInfoVersion={#MyAppVersionNumeric}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersionNumeric}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Optional:"; Flags: unchecked
Name: "launch"; Description: "Run Project X"; GroupDescription: "Optional:"; Flags: unchecked

[Files]
Source: "..\..\dist\projectx\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\projectx.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\projectx.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent; Tasks: launch

[Messages]
SetupAppTitle=Project X Setup
WelcomeLabel2=This will install [name/ver] on your computer.%n%nProject X is a Danube vessel monitoring platform with live AIS maps, cameras, and alerts.
