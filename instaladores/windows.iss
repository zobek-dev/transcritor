; Instalador de Windows (Inno Setup 6). Se compila desde la raíz del proyecto con:
;   iscc /DVersion=0.1.0 instaladores\windows.iss
; Requiere haber generado antes dist\Transcriptor.exe con PyInstaller.

#ifndef Version
  #define Version "0.1.0"
#endif

[Setup]
AppId={{6E2B1C4A-3F5D-4B8E-9A71-2C0D8F4E5B93}
AppName=Transcriptor de audios
AppVersion={#Version}
AppPublisher=Mediahuella
DefaultDirName={autopf}\Transcriptor
DefaultGroupName=Transcriptor de audios
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=Transcriptor-{#Version}-windows-instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Transcriptor.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "..\dist\Transcriptor.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Transcriptor de audios"; Filename: "{app}\Transcriptor.exe"
Name: "{autodesktop}\Transcriptor de audios"; Filename: "{app}\Transcriptor.exe"; Tasks: escritorio

[Run]
Filename: "{app}\Transcriptor.exe"; Description: "Abrir Transcriptor de audios"; Flags: nowait postinstall skipifsilent
