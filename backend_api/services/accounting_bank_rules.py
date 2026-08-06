import unicodedata


BCR_PREFERRED_CODES = ("1.1.02.04", "110-002-002-001")
BAC_PREFERRED_CODES = ("1.1.02.02",)

COLLECTIONS_BCR_CLIENTS = ("NORDEN", "THEMECO", "MASTER MARINE")
COLLECTIONS_BAC_CLIENTS = ("PANDI", "EL SURCO")
ITP_BAC_PAYEES = (
    "MAGALLY",
    "MANFRED",
    "ERASMO",
    "JAFETH",
    "CARD PROCESSOR",
    "PABEL",
    "SIN DEFINIR",
)
BCR_COLLECTION_FEE_USD = 25.0
SURVEYOR_EXTERNAL_DEDUCTION_USD = 25.0
SURVEYOR_EXTERNAL_WITHHOLDING_RATE = 0.25


def normalize_text(value):
    text = str(value or "").strip().lower()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return " ".join(text.split())


def is_costa_rica_country(value):
    text = normalize_text(value)
    return text in {"costa rica", "cr", "c.r.", "c r", "costarricense", "costaricense"}


def _account_by_code(cur, code):
    if not code:
        return None
    for table in ("accounting_accounts", "accounting_ledger"):
        cur.execute(
            f"""
            SELECT account_code, account_name
            FROM {table}
            WHERE account_code = %s
              AND COALESCE(active, TRUE) = TRUE
            LIMIT 1
            """,
            (code,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)
    return None


def _account_by_name(cur, tokens):
    for table in ("accounting_accounts", "accounting_ledger"):
        cur.execute(
            f"""
            SELECT account_code, account_name
            FROM {table}
            WHERE COALESCE(active, TRUE) = TRUE
              AND (
                    account_code LIKE '1.1.02.%%'
                 OR account_code LIKE '1.1.01.%%'
                 OR LOWER(account_name) LIKE '%%banco%%'
                 OR LOWER(account_name) LIKE '%%bac%%'
              )
            ORDER BY
              CASE WHEN account_code LIKE '1.1.02.%%' THEN 0 ELSE 1 END,
              account_code
            """,
        )
        for row in cur.fetchall() or []:
            name = normalize_text(row.get("account_name"))
            if all(token in name for token in tokens):
                return dict(row)
    return None


def _preferred(cur, codes, tokens):
    for code in codes:
        row = _account_by_code(cur, code)
        if row:
            return row
    return _account_by_name(cur, tokens)


def canonical_bcr_account(cur):
    return _preferred(cur, BCR_PREFERRED_CODES, ("banco", "costa", "rica"))


def canonical_bac_account(cur):
    return _preferred(cur, BAC_PREFERRED_CODES, ("bac",))


def canonicalize_bank_account(cur, code=None, name=None):
    code = str(code or "").strip()
    name = str(name or "").strip()
    search = normalize_text(f"{code} {name}")
    if "banco de costa rica" in search or search == "bcr" or " bcr " in f" {search} ":
        return canonical_bcr_account(cur)
    if "bac" in search:
        return canonical_bac_account(cur)
    return _account_by_code(cur, code)


def infer_collections_bank(cur, client_name, raw_bank=None):
    bank_text = normalize_text(raw_bank).upper()
    if "BCR" in bank_text or "BANCO DE COSTA RICA" in bank_text:
        return canonical_bcr_account(cur)
    if "BAC" in bank_text:
        return canonical_bac_account(cur)
    text = normalize_text(client_name).upper()
    if any(token in text for token in COLLECTIONS_BCR_CLIENTS):
        return canonical_bcr_account(cur)
    if any(token in text for token in COLLECTIONS_BAC_CLIENTS):
        return canonical_bac_account(cur)
    return None


def infer_itp_bank(cur, payee_name=None, country=None, reference=None, notes=None, payee_type=None, obligation_type=None):
    text = normalize_text(" ".join(str(x or "") for x in (payee_name, reference, notes))).upper()
    country_text = normalize_text(country)
    payee_kind = normalize_text(payee_type).upper()
    obligation_kind = normalize_text(obligation_type).upper()
    if (
        country_text == "costa rica"
        or payee_kind == "SURVEYOR"
        or obligation_kind == "SURVEYOR_FEE"
        or any(token in text for token in ITP_BAC_PAYEES)
    ):
        return canonical_bac_account(cur)
    return None


def resolve_collections_bank(cur, code=None, name=None, client_name=None, raw_bank=None):
    return canonicalize_bank_account(cur, code, name) or infer_collections_bank(cur, client_name, raw_bank)


def is_bcr_account(code=None, name=None, raw_bank=None):
    text = normalize_text(" ".join(str(x or "") for x in (code, name, raw_bank))).upper()
    return (
        str(code or "").strip() in BCR_PREFERRED_CODES
        or "BANCO DE COSTA RICA" in text
        or " BCR " in f" {text} "
        or text == "BCR"
    )


def _table_has_columns(cur, table_name, columns):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = ANY (current_schemas(FALSE))
          AND table_name = %s
          AND column_name = ANY(%s)
    """, (table_name, list(columns)))
    found = {row.get("column_name") for row in (cur.fetchall() or [])}
    return all(column in found for column in columns)


def collections_invoice_country(cur, numero_documento=None, codigo_cliente=None, nombre_cliente=None):
    numero = str(numero_documento or "").strip().lstrip("0")
    codigo = str(codigo_cliente or "").strip()
    nombre = str(nombre_cliente or "").strip()
    if not numero and not codigo and not nombre:
        return ""

    collection = None
    if numero or codigo:
        cur.execute("""
            SELECT num_informe, codigo_cliente, nombre_cliente
            FROM collections c
            WHERE (%s = '' OR LTRIM(c.numero_documento, '0') = %s)
              AND (%s = '' OR c.codigo_cliente = %s)
              AND c.tipo_documento = 'FACTURA'
            ORDER BY c.id DESC
            LIMIT 1
        """, (numero, numero, codigo, codigo))
        collection = cur.fetchone()

    if collection:
        codigo = codigo or str(collection.get("codigo_cliente") or "").strip()
        nombre = nombre or str(collection.get("nombre_cliente") or "").strip()
        num_informe = str(collection.get("num_informe") or "").strip()

    if (codigo or nombre) and _table_has_columns(cur, "cliente", ("codigo", "nombrecomercial", "pais")):
        cur.execute("""
            SELECT pais AS country
            FROM cliente
            WHERE (%s <> '' AND codigo = %s)
               OR (%s <> '' AND LOWER(nombrecomercial) = LOWER(%s))
            ORDER BY CASE WHEN %s <> '' AND codigo = %s THEN 0 ELSE 1 END
            LIMIT 1
        """, (codigo, codigo, nombre, nombre, codigo, codigo))
        row = cur.fetchone()
        if row and row.get("country"):
            return str(row.get("country") or "").strip()

    if collection:
        num_informe = str(collection.get("num_informe") or "").strip()
        if num_informe and _table_has_columns(cur, "servicios", ("num_informe", "pais")):
            cur.execute("""
                SELECT pais AS country
                FROM servicios
                WHERE num_informe::text = %s
                  AND NULLIF(BTRIM(pais), '') IS NOT NULL
                LIMIT 1
            """, (num_informe,))
            row = cur.fetchone()
            if row and row.get("country"):
                return str(row.get("country") or "").strip()

    return ""


def should_apply_bcr_collection_fee(cur, code=None, name=None, raw_bank=None, numero_documento=None, codigo_cliente=None, nombre_cliente=None):
    if not is_bcr_account(code, name, raw_bank):
        return False
    country = collections_invoice_country(
        cur,
        numero_documento=numero_documento,
        codigo_cliente=codigo_cliente,
        nombre_cliente=nombre_cliente,
    )
    return bool(country) and not is_costa_rica_country(country)


def surveyor_country(cur, payee_name=None, fallback_country=None):
    name = str(payee_name or "").strip()
    if name and _table_has_columns(cur, "surveyor", ("codigo", "nombre", "apellidos", "nacionalidad", "provincia", "canton", "distrito")):
        cur.execute("""
            SELECT nacionalidad, provincia, canton, distrito
            FROM surveyor
            WHERE LOWER(BTRIM(CONCAT_WS(' ', nombre, apellidos))) = LOWER(BTRIM(%s))
               OR LOWER(BTRIM(nombre)) = LOWER(BTRIM(%s))
            ORDER BY codigo ASC
            LIMIT 1
        """, (name, name))
        row = cur.fetchone()
        if row:
            nacionalidad = str(row.get("nacionalidad") or "").strip()
            if nacionalidad:
                return nacionalidad
            if any(str(row.get(field) or "").strip() for field in ("provincia", "canton", "distrito")):
                return "Costa Rica"
    return str(fallback_country or "").strip()


def is_external_surveyor(cur, payee_name=None, fallback_country=None, payee_type=None, obligation_type=None):
    if normalize_text(payee_type).upper() != "SURVEYOR" and normalize_text(obligation_type).upper() != "SURVEYOR_FEE":
        return False
    country = surveyor_country(cur, payee_name=payee_name, fallback_country=fallback_country)
    return bool(country) and not is_costa_rica_country(country)


def external_surveyor_settlement(cur, gross_amount, payee_name=None, fallback_country=None, payee_type=None, obligation_type=None):
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    try:
        gross = Decimal(str(gross_amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        gross = Decimal("0.00")

    if gross <= 0 or not is_external_surveyor(
        cur,
        payee_name=payee_name,
        fallback_country=fallback_country,
        payee_type=payee_type,
        obligation_type=obligation_type,
    ):
        return {
            "applies": False,
            "gross": gross,
            "deduction": Decimal("0.00"),
            "withholding": Decimal("0.00"),
            "net_payment": gross,
        }

    deduction = Decimal(str(SURVEYOR_EXTERNAL_DEDUCTION_USD)).quantize(Decimal("0.01"))
    withholding = (gross * Decimal(str(SURVEYOR_EXTERNAL_WITHHOLDING_RATE))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    deduction = min(deduction, max(gross - withholding, Decimal("0.00")))
    net_payment = gross - deduction - withholding
    if net_payment < 0:
        net_payment = Decimal("0.00")
    return {
        "applies": True,
        "gross": gross,
        "deduction": deduction,
        "withholding": withholding,
        "net_payment": net_payment,
    }


def resolve_itp_bank(cur, code=None, name=None, payee_name=None, country=None, reference=None, notes=None, payee_type=None, obligation_type=None):
    return (
        canonicalize_bank_account(cur, code, name)
        or infer_itp_bank(
            cur,
            payee_name=payee_name,
            country=country,
            reference=reference,
            notes=notes,
            payee_type=payee_type,
            obligation_type=obligation_type,
        )
    )


def backfill_missing_bank_accounts(cur):
    """Apply deterministic bank rules to old records so alerts do not stay noisy."""
    cur.execute("""
        ALTER TABLE cash_app ADD COLUMN IF NOT EXISTS bank_account_code TEXT
    """)
    cur.execute("""
        ALTER TABLE cash_app ADD COLUMN IF NOT EXISTS bank_account_name TEXT
    """)
    cur.execute("""
        ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS payment_bank TEXT
    """)
    cur.execute("""
        ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS payment_bank_account_code TEXT
    """)
    cur.execute("""
        ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS payment_bank_account_name TEXT
    """)

    changed = {"collections": 0, "itp": 0}
    cur.execute("""
        SELECT id, nombre_cliente, banco, bank_account_code, bank_account_name
        FROM cash_app
        WHERE tipo_aplicacion = 'PAGO'
          AND (
                bank_account_code IS NULL OR BTRIM(bank_account_code) = ''
             OR bank_account_code = ANY(%s)
          )
        ORDER BY id
    """, (list(BCR_PREFERRED_CODES[1:]),))
    for row in cur.fetchall() or []:
        account = resolve_collections_bank(
            cur,
            row.get("bank_account_code"),
            row.get("bank_account_name"),
            row.get("nombre_cliente"),
            row.get("banco"),
        )
        if not account:
            continue
        cur.execute("""
            UPDATE cash_app
            SET bank_account_code = %s,
                bank_account_name = %s
            WHERE id = %s
              AND (
                    bank_account_code IS DISTINCT FROM %s
                 OR bank_account_name IS DISTINCT FROM %s
              )
        """, (
            account["account_code"],
            account["account_name"],
            row["id"],
            account["account_code"],
            account["account_name"],
        ))
        changed["collections"] += cur.rowcount

    cur.execute("""
        SELECT id, payee_name, payee_type, obligation_type, country, reference, notes, payment_bank_account_code, payment_bank_account_name
        FROM payment_obligations
        WHERE active = TRUE
          AND status IN ('PAID', 'PARTIAL')
          AND last_payment_date IS NOT NULL
          AND (
                payment_bank_account_code IS NULL OR BTRIM(payment_bank_account_code) = ''
             OR payment_bank_account_code = ANY(%s)
          )
        ORDER BY id
    """, (list(BCR_PREFERRED_CODES[1:]),))
    for row in cur.fetchall() or []:
        account = resolve_itp_bank(
            cur,
            row.get("payment_bank_account_code"),
            row.get("payment_bank_account_name"),
            payee_name=row.get("payee_name"),
            payee_type=row.get("payee_type"),
            obligation_type=row.get("obligation_type"),
            country=row.get("country"),
            reference=row.get("reference"),
            notes=row.get("notes"),
        )
        if not account:
            continue
        cur.execute("""
            UPDATE payment_obligations
            SET payment_bank = %s,
                payment_bank_account_code = %s,
                payment_bank_account_name = %s,
                updated_at = NOW()
            WHERE id = %s
              AND (
                    payment_bank_account_code IS DISTINCT FROM %s
                 OR payment_bank_account_name IS DISTINCT FROM %s
              )
        """, (
            account["account_name"],
            account["account_code"],
            account["account_name"],
            row["id"],
            account["account_code"],
            account["account_name"],
        ))
        changed["itp"] += cur.rowcount
    return changed
