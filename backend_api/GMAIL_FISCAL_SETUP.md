# Activación de la bandeja fiscal Gmail/BAC

La integración usa OAuth 2.0 y corre en el backend. No utiliza ni almacena la contraseña normal de Google. El buzón configurado en `GMAIL_ACCOUNT` debe ser el que recibe los XML fiscales, Notificaciones BAC y estados de cuenta BAC que se quieran automatizar, por ejemplo `contabilidad@mslogisticsgroup.com` si ahí está la carpeta `Notificaciones BAC`.

## Google Cloud

1. Crear o seleccionar un proyecto de `mslogisticsgroup.com`.
2. Habilitar Gmail API.
3. Configurar la pantalla de consentimiento como aplicación interna.
4. Crear un cliente OAuth 2.0 de tipo aplicación web.
5. Registrar exactamente esta URI autorizada:

   `https://api-som-fastapi-production-e66d.up.railway.app/accounting/tax/gmail/oauth/callback`

## Variables protegidas en Railway

```text
GMAIL_ACCOUNT=contabilidad@mslogisticsgroup.com
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

## Automatización en backend

Con la automatización activa, Railway revisa el buzón aunque la computadora del usuario, Outlook y el ERP de escritorio estén cerrados. El scheduler procesa:

- XML/ZIP fiscales adjuntos.
- PDFs de estados de cuenta BAC de tarjetas corporativas.
- Notificaciones BAC de compras con tarjeta para cruzar/aplicar pagos.
- Notificaciones BAC de transferencias a socios como Diana/Pabel.

La consulta por defecto cubre adjuntos `xml`, `zip`, `pdf`, remitentes `baccredomatic.com` y asuntos BAC de los últimos 730 días.

## Alternativa local con Outlook

Cuando el buzón ya está configurado en Outlook clásico de Windows, ERP-SOM puede importar sin OAuth adicional desde:

`gastos@mslogisticsgroup.com > xml gastos electrónicos`

Esta modalidad no almacena contraseñas. Outlook debe estar configurado en la misma sesión de Windows y el ERP debe permanecer abierto para ejecutar la revisión programada. Es solo respaldo/manual; la automatización que no depende de la computadora es la de OAuth en backend.
