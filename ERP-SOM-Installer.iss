; =========================================================
; ERP-SOM â€” INSTALADOR PRODUCCIÃ“N (PyInstaller onedir)
; Enfocado en copiar el Ã¡rbol de dist tal cual y evitar
; efectos de compresiÃ³n/mezcla que rompan mÃ³dulos como Informes
; =========================================================

#define MyAppName "ERP-SOM"
#define MyAppVersion "1.7.16"
#define MyAppPublisher "InnovaCore SRL"
#define MyAppExeName "ERP-SOM.exe"

[Setup]
AppId={{ERP-SOM-INNOVACORE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}

DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
UsePreviousAppDir=yes

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

OutputDir=installer
OutputBaseFilename=ERP-SOM-Setup

; IMPORTANTE: para builds PyInstaller onedir, evitar solid compression
Compression=lzma2
SolidCompression=no
InternalCompressLevel=normal
WizardStyle=modern

SetupIconFile=assets\logo_menu_tareas.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=EULA.rtf
SetupLogging=yes

DisableProgramGroupPage=yes
ChangesAssociations=no
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
DisableFinishedPage=no

[Files]
; Copia todo el Ã¡rbol exactamente como sale de dist
Source: "dist\ERP-SOM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ERP-SOM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\ERP-SOM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Dirs]
; Asegura que la carpeta exista antes de copiar
Name: "{app}"

[InstallDelete]
; Limpiar SOLO el contenido, no el directorio raÃ­z
Type: files; Name: "{app}\*"
Type: filesandordirs; Name: "{app}\*"

[Messages]
FinishedHeadingLabel=Instalacion de {#MyAppName} completada
FinishedLabelNoIcons={#MyAppName} {#MyAppVersion} se instalo correctamente. La aplicacion se abrira automaticamente.
FinishedLabel={#MyAppName} {#MyAppVersion} se instalo correctamente. La aplicacion se abrira automaticamente.

[Code]
procedure StopRunningERP();
var
  ResultCode: Integer;
begin
  Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/F /T /IM "{#MyAppExeName}"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  );
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopRunningERP();
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    StopRunningERP();
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait runascurrentuser
