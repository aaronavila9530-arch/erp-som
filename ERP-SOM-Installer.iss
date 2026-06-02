; =========================================================
; ERP-SOM — INSTALADOR PRODUCCIÓN (PyInstaller onedir)
; Enfocado en copiar el árbol de dist tal cual y evitar
; efectos de compresión/mezcla que rompan módulos como Informes
; =========================================================

#define MyAppName "ERP-SOM"
#define MyAppVersion "1.5.5"
#define MyAppPublisher "InnovaCore SRL"
#define MyAppExeName "ERP-SOM.exe"

[Setup]
AppId={{ERP-SOM-INNOVACORE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}

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

DisableProgramGroupPage=yes
ChangesAssociations=no
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no

[Files]
; Copia todo el árbol exactamente como sale de dist
Source: "dist\ERP-SOM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ERP-SOM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\ERP-SOM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Dirs]
; Asegura que la carpeta exista antes de copiar
Name: "{app}"

[InstallDelete]
; Limpiar SOLO el contenido, no el directorio raíz
Type: files; Name: "{app}\*"
Type: filesandordirs; Name: "{app}\*"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent unchecked
