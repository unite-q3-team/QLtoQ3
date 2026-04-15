#define MyAppName "QLtoQ3"

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef SourceDir
  #define SourceDir "..\..\..\dist\windows\portable\QLtoQ3"
#endif

#ifndef OutputDir
  #define OutputDir "..\..\..\dist\windows\installer"
#endif

#ifndef InstallerIconFile
  #define InstallerIconFile ""
#endif

[Setup]
AppId={{6D7E0C37-A3EB-4305-B2F3-F2FC12753E0F}
AppName={#MyAppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\QLtoQ3
DefaultGroupName=QLtoQ3
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=QLtoQ3-setup-{#AppVersion}-win64
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\qltoq3-gui.exe
#if InstallerIconFile != ""
SetupIconFile={#InstallerIconFile}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QLtoQ3"; Filename: "{app}\qltoq3-gui.exe"
Name: "{group}\QLtoQ3 CLI"; Filename: "{app}\qltoq3-cli.exe"
Name: "{autodesktop}\QLtoQ3"; Filename: "{app}\qltoq3-gui.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\qltoq3-gui.exe"; Description: "Launch QLtoQ3"; Flags: nowait postinstall skipifsilent
