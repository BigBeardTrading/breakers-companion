#define MyAppName "Breakers Companion"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Big Beard Trading"
#define MyAppExeName "Breakers Companion.exe"

[Setup]
AppId={{1D4A3E14-4E56-4A8F-8B9F-6D9A6F6DB7B6}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=build\installer
OutputBaseFilename=BreakersCompanion-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes

[Files]
; everything built by PyInstaller
Source: "dist\Breakers Companion\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; seed the default checklist (pick the one you actually have)
Source: "data\2025 Donruss Football Master Checklist.xlsx"; DestDir: "{localappdata}\BreakersCompanion\sets"; Flags: ignoreversion
; If your file is in sets\ instead of data\, delete the line above and use this line instead:
; Source: "sets\2025 Donruss Football Master Checklist.xlsx"; DestDir: "{localappdata}\BreakersCompanion\sets"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\BreakersCompanion\logs"

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if MsgBox('Also remove saved sets and preferences?'#13#10 +
            '(Deletes %LOCALAPPDATA%\BreakersCompanion)', mbConfirmation, MB_YESNO) = IDYES then
    DelTree(ExpandConstant('{localappdata}\BreakersCompanion'), True, True, True);
end;
