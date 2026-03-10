; =========================================================
; ERP-SOM — INSTALADOR DEFINITIVO PRODUCCIÓN
; Limpia carpeta completa antes de instalar
; =========================================================

#define MyAppName "ERP-SOM"
#define MyAppVersion "1.2.9"
#define MyAppPublisher "InnovaCore SRL"
#define MyAppExeName "ERP-SOM.exe"

[Setup]
AppId={{ERP-SOM-INNOVACORE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={commonpf64}\{#MyAppName}
DefaultGroupName={#MyAppName}

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

OutputDir=installer
OutputBaseFilename=ERP-SOM-Setup

Compression=lzma
SolidCompression=yes
WizardStyle=modern

SetupIconFile=assets\logo_menu_tareas.ico

UninstallDisplayIcon={app}\{#MyAppExeName}

; =========================================================
; 🔥 CERRAR APP SI ESTÁ ABIERTA
; =========================================================
[Run]
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden

; =========================================================
; 🔥 LIMPIAR COMPLETAMENTE CARPETA ANTES DE COPIAR
; =========================================================
[InstallDelete]
Type: filesandordirs; Name: "{app}"

; =========================================================
; ARCHIVOS
; =========================================================
[Files]
Source: "dist\ERP-SOM\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

; =========================================================
; ICONOS
; =========================================================
[Icons]
Name: "{group}\ERP-SOM"; Filename: "{app}\ERP-SOM.exe"
Name: "{commondesktop}\ERP-SOM"; Filename: "{app}\ERP-SOM.exe"

; =========================================================
; EJECUCIÓN FINAL
; =========================================================
[Run]
Filename: "{app}\ERP-SOM.exe"; Flags: nowait postinstall skipifsilent unchecked
