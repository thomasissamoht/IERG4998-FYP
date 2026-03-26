; Inno Setup script for BibTeX Manager
; Build output: installer\output\BibTeXManagerSetup.exe

#define MyAppName "BibTeX Manager"
#ifndef MyAppVersion
	#define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Thomas"
#define MyAppExeName "BibTeXManager.exe"
#ifexist "..\installer\app.ico"
	#define MySetupIconFile "..\installer\app.ico"
#endif

[Setup]
AppId={{E2E7D4FD-3E16-4B58-84F0-40E3D09A9EA9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=BibTeXManagerSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
#ifdef MySetupIconFile
SetupIconFile={#MySetupIconFile}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\BibTeXManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\test_data.zip"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
