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

#ifndef WizardSmallImageFile
  #define WizardSmallImageFile ""
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
#if WizardSmallImageFile != ""
WizardSmallImageFile={#WizardSmallImageFile}
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

[Code]
var
  AppLangPage: TInputOptionWizardPage;

function UiText(const EnText, RuText: string): string;
begin
  if ActiveLanguage = 'russian' then
    Result := RuText
  else
    Result := EnText;
end;

function DefaultAppLangCode(): string;
begin
  if ActiveLanguage = 'russian' then
    Result := 'ru'
  else
    Result := 'en';
end;

procedure InitializeWizard();
begin
  AppLangPage := CreateInputOptionPage(
    wpSelectTasks,
    UiText('Program language', 'Язык программы'),
    UiText('Choose preferred interface language', 'Выберите предпочитаемый язык интерфейса'),
    UiText('This language will be saved to QLtoQ3 config.', 'Этот язык будет сохранен в конфиг QLtoQ3.'),
    True,
    False
  );
  AppLangPage.Add('English');
  AppLangPage.Add('Русский');
  if DefaultAppLangCode() = 'ru' then
    AppLangPage.SelectedValueIndex := 1
  else
    AppLangPage.SelectedValueIndex := 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppLang: string;
  PrefDir: string;
  PrefFile: string;
  PrefBody: string;
begin
  if CurStep <> ssPostInstall then
    exit;

  if AppLangPage.SelectedValueIndex = 1 then
    AppLang := 'ru'
  else
    AppLang := 'en';

  PrefDir := ExpandConstant('{userappdata}\qltoq3');
  if not DirExists(PrefDir) then
    ForceDirectories(PrefDir);
  PrefFile := AddBackslash(PrefDir) + 'prefs.json';
  PrefBody := '{'#13#10'  "lang": "' + AppLang + '"'#13#10'}'#13#10;
  SaveStringToFile(PrefFile, PrefBody, False);
end;
