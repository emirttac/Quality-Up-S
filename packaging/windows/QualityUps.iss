; Quality Up'S — professional Windows installer (Inno Setup 6+)
; Developer: https://github.com/emirttac
;
; Prerequisites:
;   1. Build the PyInstaller onedir bundle first (see build.ps1 / build.bat)
;   2. Install Inno Setup 6: https://jrsoftware.org/isinfo.php
;   3. Compile this script with ISCC or the Inno Setup IDE
;
; Output: dist\installer\QualityUps-Setup-1.0.exe
;
; The repo folder is named Quality Up'S. Inno Setup quotes filesystem paths
; with Pascal strings, so an apostrophe in the absolute path would split
; Source on the [Files] line and surface as an unknown identifier "dist".
; Resolve the repo root through the Windows 8.3 short path (QUALIT~1).

#define MyAppName "Quality Up'S"
#define MyAppVersion "1.0"
#define MyAppPublisher "Emir Tuğra Ataç"
#define MyAppURL "https://github.com/emirttac"
#define MyAppRepo "https://github.com/emirttac/Quality-Up-S"
#define MyAppExeName "QualityUps.exe"
#define MyAppId "{{A7C3E9F1-2B4D-4E8A-9C1F-6D5B8A0E3F27}"

; SourcePath is packaging\windows\ (trailing backslash). Climb two levels.
#define RepoRootDir ExtractFileDir(ExtractFileDir(RemoveBackslashUnlessRoot(SourcePath)))
#define ShortRootFile GetEnv("TEMP") + "\qualityups_shortroot.txt"
#expr Exec('cmd.exe', '/c for %I in ("' + RepoRootDir + '") do @echo %~sI>"' + ShortRootFile + '"', '', 1, SW_HIDE)
#define ShortRootHandle FileOpen(ShortRootFile)
#if ShortRootHandle
  #define RepoRoot FileRead(ShortRootHandle)
  #expr FileClose(ShortRootHandle)
#else
  #define RepoRoot RepoRootDir
#endif
#expr DeleteFile(ShortRootFile)

#ifndef SourceDir
  #define SourceDir RepoRoot + "\dist\QualityUps"
#endif

#ifndef OutputDir
  #define OutputDir RepoRoot + "\dist\installer"
#endif

#ifndef IconFile
  #define IconFile RepoRoot + "\assets\icon\app.ico"
#endif

#define LicenseFilePath RepoRoot + "\LICENSE"

#if !FileExists(SourceDir + "\" + MyAppExeName)
  #error "dist\QualityUps is missing. Run packaging\windows\build.ps1 (or build.bat) before compiling this script."
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppRepo}
AppUpdatesURL={#MyAppRepo}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile={#LicenseFilePath}
OutputDir={#OutputDir}
OutputBaseFilename=QualityUps-Setup-{#MyAppVersion}
#if FileExists(IconFile)
SetupIconFile={#IconFile}
#endif
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=no
DisableReadyPage=no
DisableDirPage=no
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Entire PyInstaller onedir payload (created by build.ps1 / build.bat)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
