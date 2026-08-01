import re
import unicodedata


def normalize_person_name(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    return re.sub(r"[^A-Z0-9]", "", text)


def normalize_person_tokens(value) -> tuple[str, ...]:
    text = str(value or "").strip()
    if not text:
        return tuple()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return tuple(re.findall(r"[A-Z0-9]+", text.upper()))


def load_employee_name_keys(cur) -> set[tuple[str, ...]]:
    cur.execute("""
        SELECT nombre, apellidos
        FROM empleados
        WHERE COALESCE(nombre, '') <> ''
    """)
    keys = set()
    for row in cur.fetchall() or []:
        if isinstance(row, dict):
            nombre = row.get("nombre")
            apellidos = row.get("apellidos")
        else:
            nombre = row[0] if len(row) > 0 else ""
            apellidos = row[1] if len(row) > 1 else ""
        tokens = normalize_person_tokens(f"{nombre or ''} {apellidos or ''}")
        if len(tokens) >= 2:
            keys.add(tokens)
    return keys


def is_employee_payee(cur, payee_name, employee_keys: set[tuple[str, ...]] | None = None) -> bool:
    payee_tokens = set(normalize_person_tokens(payee_name))
    if not payee_tokens:
        return False
    keys = employee_keys if employee_keys is not None else load_employee_name_keys(cur)
    for employee_tokens in keys:
        employee_token_set = set(employee_tokens)
        if employee_token_set.issubset(payee_tokens):
            return True
        if len(payee_tokens) >= 2 and payee_tokens.issubset(employee_token_set):
            return True
        if employee_tokens and employee_tokens[0] in payee_tokens:
            surnames = set(employee_tokens[1:])
            if surnames and surnames.intersection(payee_tokens):
                return True
    return False


def employee_obligation_ids(cur) -> list[int]:
    keys = load_employee_name_keys(cur)
    if not keys:
        return []
    cur.execute("""
        SELECT id, payee_name
        FROM payment_obligations
        WHERE record_type = 'OBLIGATION'
          AND COALESCE(payee_name, '') <> ''
    """)
    ids = []
    for row in cur.fetchall() or []:
        row_id = row.get("id") if isinstance(row, dict) else row[0]
        payee_name = row.get("payee_name") if isinstance(row, dict) else row[1]
        if is_employee_payee(cur, payee_name, keys):
            ids.append(row_id)
    return ids


def deactivate_employee_itp_obligations(cur) -> list[int]:
    ids = employee_obligation_ids(cur)
    if ids:
        cur.execute("""
            UPDATE payment_obligations
            SET active = FALSE,
                updated_at = NOW(),
                notes = TRIM(COALESCE(notes, '') || ' | Excluido de ITP: beneficiario existe en Master Data Empleados.')
            WHERE id = ANY(%s)
              AND COALESCE(active, TRUE) = TRUE
        """, (ids,))
    return ids
