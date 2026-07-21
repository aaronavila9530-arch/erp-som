# Activación de la bandeja fiscal Gmail

La integración está limitada al buzón `gastos@mslogisticsgroup.com` y usa OAuth 2.0. No utiliza ni almacena la contraseña normal de Google.

## Google Cloud

1. Crear o seleccionar un proyecto de `mslogisticsgroup.com`.
2. Habilitar Gmail API.
3. Configurar la pantalla de consentimiento como aplicación interna.
4. Crear un cliente OAuth 2.0 de tipo aplicación web.
5. Registrar exactamente esta URI autorizada:

   `https://api-som-fastapi-production-e66d.up.railway.app/accounting/tax/gmail/oauth/callback`

## Variables protegidas en Railway

```text
GMAIL_ACCOUNT=gastos@mslogisticsgroup.com
GOOGLE_CLIENT_ID=<cliente OAuth>
GOOGLE_CLIENT_SECRET=<secreto OAuth>
GOOGLE_REDIRECT_URI=https://api-som-fastapi-production-e66d.up.railway.app/accounting/tax/gmail/oauth/callback
CREDENTIAL_ENCRYPTION_KEY=<llave Fernet>
```

La llave Fernet puede generarse localmente con:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

No guardar estos valores en Git, capturas, documentos compartidos ni conversaciones.

## Activación en ERP-SOM

1. Accounting > Centro fiscal Costa Rica > Correo fiscal.
2. Seleccionar `Autorizar con Google`.
3. Iniciar sesión exclusivamente con `gastos@mslogisticsgroup.com`.
4. Confirmar que el estado cambie a `CONNECTED`.
5. Ejecutar `Revisar correo ahora`.
6. Revisar resultados antes de activar la programación automática.

El backend valida que Google haya autorizado exactamente la cuenta configurada. Una cuenta diferente será rechazada.
