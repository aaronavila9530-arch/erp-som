import unicodedata


BCR_PREFERRED_CODES = ("1.1.02.04", "110-002-002-001")
BAC_PREFERRED_CODES = ("1.1.02.02",)

COLLECTIONS_BCR_CLIENTS = ("NORDEN", "THEMECO", "MASTER MARINE")
COLLECTIONS_BAC_CLIENTS = ("PANDI", "EL SURCO")
ITP_BAC_PAYEES = ("MAGALLY", "MANFRED", "ERASMO", "JAFETH")


def normalize_text(value):
    text = str(value or "").strip().lower()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return " ".join(text.split())


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


def infer_itp_bank(cur, payee_name=None, country=None, reference=None, notes=None):
    text = normalize_text(" ".join(str(x or "") for x in (payee_name, reference, notes))).upper()
    country_text = normalize_text(country)
    if country_text == "costa rica" or any(token in text for token in ITP_BAC_PAYEES):
        return canonical_bac_account(cur)
    return None


def resolve_collections_bank(cur, code=None, name=None, client_name=None, raw_bank=None):
    return canonicalize_bank_account(cur, code, name) or infer_collections_bank(cur, client_name, raw_bank)


def resolve_itp_bank(cur, code=None, name=None, payee_name=None, country=None, reference=None, notes=None):
    return (
        canonicalize_bank_account(cur, code, name)
        or infer_itp_bank(cur, payee_name=payee_name, country=country, reference=reference, notes=notes)
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
        SELECT id, payee_name, country, reference, notes, payment_bank_account_code, payment_bank_account_name
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
