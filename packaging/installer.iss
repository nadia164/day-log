; Inno Setup script for Daylog. build.py runs this; you don't need to open it.
; Values in {#...} are passed in by build.py (defaults below are for manual builds).

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\Daylog"
#endif
#ifndef IconFile
  #define IconFile "..\assets\daylog.ico"
#endif
#ifndef OutputDir
  #define OutputDir "..\installer_output"
#endif

[Setup]
; Never change AppId: Windows uses it to recognize upgrades of the same app.
AppId={{8F3C2A51-6B0E-4C7D-9A12-5E4F1B7D2C90}
AppName=Daylog
AppVersion={#AppVersion}
AppVerName=Daylog {#AppVersion}
AppPublisher=Daylog
; Per-user install, no admin needed: %LOCALAPPDATA%\Programs\Daylog
PrivilegesRequired=lowest
DefaultDirName={autopf}\Daylog
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir={#OutputDir}
OutputBaseFilename=Daylog-Setup-{#AppVersion}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\Daylog.exe
UninstallDisplayName=Daylog
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Daylog holds this mutex while running, so setup/uninstall asks you to quit it first.
AppMutex=DaylogAppMutex
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "Start Daylog when I sign in to Windows"; GroupDescription: "Startup:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Clear the previous version's files on upgrade (your data lives elsewhere and is kept).
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\Daylog"; Filename: "{app}\Daylog.exe"
Name: "{autodesktop}\Daylog"; Filename: "{app}\Daylog.exe"; Tasks: desktopicon

[Registry]
; Optional "start at sign-in" (the same entry the tray's Launch at startup toggle uses).
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Daylog"; ValueData: """{app}\Daylog.exe"" --minimized"; Tasks: startup
; Always remove that entry on uninstall, even if it was turned on from the tray menu.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Daylog"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Daylog.exe"; Description: "{cm:LaunchProgram,Daylog}"; Flags: nowait postinstall skipifsilent
