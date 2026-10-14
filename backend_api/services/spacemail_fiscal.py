"""Read-only Spacemail ingestion, using the existing fiscal import and audit trail."""
import email
from email import policy
from email.utils import parsedate_to_datetime
import imaplib
import re
import ssl

from psycopg2.extras import RealDictCursor, Json

ACCOUNT = "operations@xtravon.com"
HOST = "mail.spacemail.com"
MAX_BYTES = 20 * 1024 * 1024


class ConnectionFailure(ValueError):
    """Only fixed, credential-free messages may cross the API boundary."""


def logout_safely(mail):
    try:
        mail.logout()
    except Exception:
        pass


def select_received(mail):
    status, folders = mail.list()
    if status != "OK":
        raise ConnectionFailure("IMAP_FOLDER_LIST: Se conecto al buzon, pero no se pudieron consultar sus carpetas.")
    matches = []
    for line in folders or []:
        if not isinstance(line, bytes):
            continue
        match = re.match(rb'\([^)]*\) (?:"([^"]*)"|NIL) (.+)$', line)
        if not match:
            continue
        delimiter = (match[1] or b"/").decode("ascii", errors="replace")
        name = match[2].decode("ascii", errors="replace").strip('"')
        if name.lower() in {"fe recibidas", "inbox" + delimiter + "fe recibidas"}:
            matches.append(name)
    if len(matches) != 1:
        raise ConnectionFailure("IMAP_FOLDER: La clave fue aceptada, pero no se encontro una carpeta unica Inbox / FE recibidas en el servidor.")
    folder = matches[0]
    status, _ = mail.select('"' + folder + '"', readonly=True)
    if status != "OK":
        raise ConnectionFailure("IMAP_FOLDER_ACCESS: La clave fue aceptada, pero el servidor no permite leer FE recibidas.")
    _, values = mail.response("UIDVALIDITY")
    if not values or not values[0] or not values[0].isdigit():
        raise ConnectionFailure("IMAP_UID: El servidor no devolvio el identificador de la carpeta. No se importo ningun mensaje.")
    return folder, values[0].decode("ascii")


def connect(password):
    try:
        mail = imaplib.IMAP4_SSL(HOST, 993, ssl_context=ssl.create_default_context(), timeout=20)
    except ssl.SSLError:
        raise ConnectionFailure("IMAP_TLS: No se pudo verificar la conexion cifrada con Spacemail.") from None
    except (OSError, imaplib.IMAP4.error):
        raise ConnectionFailure("IMAP_NETWORK: Railway no pudo conectar con mail.spacemail.com:993. No se llego a validar la contrasena.") from None
    try:
        try:
            mail.login(ACCOUNT, password)
        except imaplib.IMAP4.abort:
            raise ConnectionFailure("IMAP_DISCONNECTED: Spacemail interrumpio la conexion durante la autenticacion.") from None
        except imaplib.IMAP4.error:
            raise ConnectionFailure("IMAP_AUTH: Spacemail rechazo el acceso de operations@xtravon.com. Use la clave de ese buzon, no la de SOM, y compruebe que IMAP este habilitado.") from None
        except UnicodeError:
            raise ConnectionFailure("IMAP_ENCODING: El inicio de sesion IMAP no pudo codificar la clave. Requiere revisar el metodo de autenticacion.") from None
        try:
            folder, validity = select_received(mail)
        except imaplib.IMAP4.error:
            raise ConnectionFailure("IMAP_FOLDER_ACCESS: La clave fue aceptada, pero fallo la consulta de FE recibidas.") from None
        return mail, folder, validity
    except OSError:
        logout_safely(mail)
        raise ConnectionFailure("IMAP_TIMEOUT: Spacemail dejo de responder durante la conexion. Vuelva a intentar.") from None
    except Exception:
        logout_safely(mail)
        raise


def configure(conn, password, user):
    from services.gmail_fiscal_service import ensure_schema, encrypt_token
    ensure_schema(conn)
    try:
        encrypted = encrypt_token(password)
    except Exception:
        raise ConnectionFailure("IMAP_ENCRYPTION: Falta configurar correctamente el cifrado de credenciales en SOM. No es un error de su clave.") from None
    mail, folder, _ = connect(password)
    logout_safely(mail)
    with conn.cursor() as cur:
        cur.execute("""UPDATE gmail_fiscal_connections SET encrypted_imap_password=%s,
            encrypted_refresh_token=NULL, status='CONNECTED', auto_enabled=TRUE,
            interval_minutes=10, next_sync_at=NOW(), last_error=NULL,
            connected_by=%s, connected_at=NOW(), updated_at=NOW() WHERE account_email=%s""",
                    (encrypted, user, ACCOUNT))
        cur.execute("""INSERT INTO gmail_fiscal_audit(account_email,action,performed_by)
            VALUES(%s,'IMAP_CONNECTED',%s)""", (ACCOUNT, user))
    conn.commit()
    return {"account_email": ACCOUNT, "folder": folder, "auto_enabled": True}


def fetch_message(mail, uid):
    status, sizes = mail.uid("fetch", uid, "(RFC822.SIZE)")
    size = next((re.search(rb'RFC822.SIZE (\d+)', item) for item in sizes or []
                 if isinstance(item, bytes) and b"RFC822.SIZE" in item), None)
    if status != "OK" or not size or int(size[1]) > MAX_BYTES:
        raise ValueError("Mensaje no disponible o mayor a 20 MB")
    status, data = mail.uid("fetch", uid, "(BODY.PEEK[])")
    raw = next((item[1] for item in data or [] if isinstance(item, tuple)), None)
    if status != "OK" or not raw or len(raw) > MAX_BYTES:
        raise ValueError("No se pudo leer el mensaje")
    return email.message_from_bytes(raw, policy=policy.default)


def import_message(cur, message_id, msg):
    from services.gmail_fiscal_service import _xml_members, _process_xml, _response_data
    members = []
    for part in msg.walk():
        filename = part.get_filename() or ""
        if filename.lower().endswith((".xml", ".zip")):
            members.extend(_xml_members(filename, part.get_payload(decode=True) or b""))
    # Process invoice XML before Hacienda acknowledgments, regardless of MIME order.
    members.sort(key=lambda item: bool(_response_data(item[1])))
    imported = duplicates = reviews = 0
    for filename, content in members:
        status, _ = _process_xml(cur, message_id, filename, content, None, "MCI-CR")
        imported += status == "IMPORTED"
        duplicates += status == "DUPLICATE"
        reviews += status not in {"IMPORTED", "DUPLICATE"}
    return len(members), imported, duplicates, reviews


def sync(conn, triggered_by="SCHEDULER", max_messages=50):
    from services.gmail_fiscal_service import ensure_schema, decrypt_token
    ensure_schema(conn)
    mail = None
    summary = {"messages": 0, "imported": 0, "duplicates": 0, "review": 0}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT pg_try_advisory_lock(hashtext(%s)) locked", ("gmail-fiscal:" + ACCOUNT,))
        if not cur.fetchone()["locked"]:
            return {"status": "busy"}
        try:
            cur.execute("SELECT encrypted_imap_password FROM gmail_fiscal_connections WHERE account_email=%s", (ACCOUNT,))
            config = cur.fetchone()
            if not config or not config["encrypted_imap_password"]:
                raise ValueError("Spacemail requiere autorizacion")
            mail, folder, validity = connect(decrypt_token(config["encrypted_imap_password"]))
            if triggered_by != "SCHEDULER":
                cur.execute("""UPDATE gmail_fiscal_messages SET status='NEW'
                    WHERE account_email=%s AND status='REVIEW' AND gmail_message_id LIKE 'imap:%%'""", (ACCOUNT,))
            prefix = f"imap:{folder}:{validity}:"
            status, data = mail.uid("search", None, "ALL")
            if status != "OK":
                raise ValueError("No se pudo consultar FE recibidas")
            cur.execute("""SELECT gmail_message_id FROM gmail_fiscal_messages
                WHERE account_email=%s AND status IN ('PROCESSED','DUPLICATE','REVIEW')""", (ACCOUNT,))
            done = {row["gmail_message_id"] for row in cur.fetchall()}
            pending = [uid for uid in (data[0] or b"").split()
                       if prefix + uid.decode("ascii") not in done]
            for uid in pending[-max_messages:][::-1]:
                key = prefix + uid.decode("ascii")
                cur.execute("""INSERT INTO gmail_fiscal_messages(account_email,gmail_message_id)
                    VALUES(%s,%s) ON CONFLICT(account_email,gmail_message_id)
                    DO UPDATE SET updated_at=NOW() RETURNING id""", (ACCOUNT, key))
                message_id = cur.fetchone()["id"]
                conn.commit()
                try:
                    msg = fetch_message(mail, uid)
                    try:
                        received = parsedate_to_datetime(str(msg.get("Date", "")))
                    except (ValueError, TypeError):
                        received = None
                    count, imported, duplicates, reviews = import_message(cur, message_id, msg)
                    state = "REVIEW" if reviews else ("DUPLICATE" if duplicates and not imported else "PROCESSED")
                    cur.execute("""UPDATE gmail_fiscal_messages SET sender=%s,subject=%s,status=%s,received_at=%s,
                        xml_count=%s,imported_count=%s,duplicate_count=%s,error_count=%s,
                        error_detail=NULL,processed_at=NOW(),updated_at=NOW() WHERE id=%s""",
                        (str(msg.get("From", "")), str(msg.get("Subject", "")), state, received,
                         count, imported, duplicates, reviews, message_id))
                    conn.commit()
                    summary["imported"] += imported
                    summary["duplicates"] += duplicates
                    summary["review"] += reviews
                except Exception:
                    conn.rollback()
                    # Keep processing other messages, without leaking server/credential details.
                    cur.execute("""UPDATE gmail_fiscal_messages SET status='REVIEW',error_count=1,
                        error_detail='No se pudo importar el XML. Requiere revision.',updated_at=NOW()
                        WHERE id=%s""", (message_id,))
                    conn.commit()
                    summary["review"] += 1
                summary["messages"] += 1
            cur.execute("""UPDATE gmail_fiscal_connections SET last_sync_at=NOW(),
                next_sync_at=NOW()+INTERVAL '10 minutes',last_error=%s,updated_at=NOW()
                WHERE account_email=%s""",
                ("Hay mensajes pendientes de revision" if summary["review"] else None, ACCOUNT))
            cur.execute("""INSERT INTO gmail_fiscal_audit(account_email,action,detail,performed_by)
                VALUES(%s,'IMAP_SYNC',%s,%s)""", (ACCOUNT, Json(summary), triggered_by))
            conn.commit()
            return {"status": "ok", "account_email": ACCOUNT, "company_code": "MCI-CR", **summary}
        except Exception:
            conn.rollback()
            cur.execute("""UPDATE gmail_fiscal_connections SET
                last_error='No se pudo conectar o leer Spacemail; revise acceso IMAP y credenciales.',
                next_sync_at=NOW()+INTERVAL '10 minutes',updated_at=NOW() WHERE account_email=%s""", (ACCOUNT,))
            conn.commit()
            raise RuntimeError("No se pudo sincronizar Spacemail") from None
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass
            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", ("gmail-fiscal:" + ACCOUNT,))
            conn.commit()
