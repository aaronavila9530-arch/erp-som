# ERP SOM Android

Cliente móvil inicial para Android basado en Expo/React Native.

## Qué incluye

- Pantalla de ingreso por usuario y contraseña.
- Flujo TOTP compatible con el login desktop: registro con QR y verificación por código.
- Sesión persistida en el dispositivo.
- Navegación por módulos con el mismo RBAC visual del desktop.
- Mapa inicial de secciones para Dashboard, Master Data, Servicios, Finanzas, HHRR, Comercial e Informes.
- Cliente API que envía `X-User`, `X-Role` y `X-User-Role` igual que el desktop.

## Ejecutar en Android

```powershell
cd android_app
npm install
npm run start
```

Luego abrir en Android con Expo Go o generar build con EAS/Gradle.

## Crear APK instalable

```powershell
cd android_app
npm install
npm install -g eas-cli
eas login
eas build -p android --profile preview
```

Cuando termine, EAS muestra un link para descargar el `.apk`. Abre ese link desde el celular o descarga el archivo y pásalo al teléfono.

Para instalarlo por cable USB:

```powershell
adb install ruta\al\archivo.apk
```

## Backend requerido

La app usa:

- `POST /auth/mobile/login`
- `POST /auth/mobile/totp/confirm`
- `POST /auth/mobile/totp/verify`

Estos endpoints deben estar desplegados en Railway junto con el backend FastAPI.

## Próximos pasos

Esta base no intenta portar Tkinter. Cada pantalla compleja del desktop debe migrarse como vista móvil nativa usando los routers FastAPI existentes. El mapa de secciones ya está creado para que la migración sea incremental sin perder módulos ni permisos.
