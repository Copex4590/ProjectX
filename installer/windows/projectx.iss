; ============================================================================
; Project X — Windows Installer (Inno Setup)
; ============================================================================

#define MyAppName "Project X"
#define MyAppVersion "0.3.0-alpha"
#define MyAppPublisher "Project X"
#define MyAppExeName "projectx.exe"

[Setup]
AppId={{A4F8B2C1-9D3E-4F5A-8B7C-1E2D3C4B5A6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Project X
DefaultGroupName={#MyAppName}
OutputBaseFilename=ProjectX-Setup
SetupIconFile=..\..\src\resources\branding\projectx.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "launch"; Description: "Launch Project X after installation"; Flags: unchecked

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
