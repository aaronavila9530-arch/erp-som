from psycopg2.extras import Json, RealDictCursor


DEFAULT_POSTING_RULES = [
    {
        "rule_code": "COLLECTIONS_INVOICE_POSTING",
        "origin": "Collections",
        "event_type": "Invoice issued",
        "description": "Customer invoice posting from Collections.",
        "debit_account_code": "1.1.04.01",
        "credit_account_code": "4.1.01",
        "third_party_policy": "CLIENT_REQUIRED",
        "currency_policy": "SOURCE_DOCUMENT",
        "bank_policy": "NOT_APPLICABLE",
        "iva_policy": "CREDIT_IVA_PAYABLE_WHEN_TAXED",
        "retention_policy": "APPLY_IF_SOURCE_WITHHOLDING",
        "line_description_template": "From Collections {invoice_number} - {client}",
        "priority": 10,
    },
    {
        "rule_code": "COLLECTIONS_PAYMENT_RECEIVED",
        "origin": "Collections",
        "event_type": "Payment received",
        "description": "Cash application against customer receivable.",
        "debit_account_code": "BANK_BY_CLIENT_RULE",
        "credit_account_code": "1.1.04.01",
        "third_party_policy": "CLIENT_REQUIRED",
        "currency_policy": "PAYMENT_CURRENCY",
        "bank_policy": "BCR_FOR_NORDEN_THEMECO_MASTER_MARINE__BAC_FOR_PANDI_EL_SURCO__USER_OVERRIDE",
        "iva_policy": "NO_NEW_IVA_PAYMENT_AGAINST_RECEIVABLE",
        "retention_policy": "REGISTER_RETENTION_IF_PAYMENT_NET_OF_WITHHOLDING",
        "line_description_template": "From Collections payment {payment_id} - {client}",
        "priority": 20,
    },
    {
        "rule_code": "ITP_PURCHASE_DOCUMENT",
        "origin": "ITP",
        "event_type": "Purchase document",
        "description": "Supplier purchase or service obligation from ITP/XML.",
        "debit_account_code": "EXPENSE_OR_ASSET_BY_CABYS_SUPPLIER",
        "credit_account_code": "2.1.01.01",
        "third_party_policy": "SUPPLIER_REQUIRED",
        "currency_policy": "SOURCE_DOCUMENT",
        "bank_policy": "NOT_APPLICABLE",
        "iva_policy": "DEBIT_IVA_CREDIT_FISCAL_WHEN_DEDUCTIBLE",
        "retention_policy": "CREDIT_RETENTION_PAYABLE_IF_APPLIES",
        "line_description_template": "From ITP {supplier} {document_number}",
        "priority": 30,
    },
    {
        "rule_code": "ITP_PAYMENT_DONE",
        "origin": "ITP",
        "event_type": "Payment done",
        "description": "Payment of supplier obligation.",
        "debit_account_code": "2.1.01.01",
        "credit_account_code": "BANK_BY_SUPPLIER_RULE",
        "third_party_policy": "SUPPLIER_REQUIRED",
        "currency_policy": "PAYMENT_CURRENCY",
        "bank_policy": "BAC_FOR_COSTA_RICA_MAGALLY_MANFRED_ERASMO_JAFETH__USER_OVERRIDE",
        "iva_policy": "NO_NEW_IVA_PAYMENT_AGAINST_PAYABLE",
        "retention_policy": "REGISTER_WITHHOLDING_PAYMENT_IF_APPLIES",
        "line_description_template": "From ITP payment {supplier}",
        "priority": 40,
    },
    {
        "rule_code": "PAYROLL_ACCRUAL",
        "origin": "Payroll",
        "event_type": "Payroll accrual",
        "description": "Payroll accrual with employer and employee statutory charges.",
        "debit_account_code": "500-001-001-001",
        "credit_account_code": "2105",
        "third_party_policy": "EMPLOYEE_REQUIRED",
        "currency_policy": "CRC",
        "bank_policy": "NOT_APPLICABLE",
        "iva_policy": "NOT_APPLICABLE",
        "retention_policy": "CREDIT_EMPLOYEE_WITHHOLDINGS_AND_SOCIAL_SECURITY",
        "line_description_template": "Payroll {employee} {period}",
        "priority": 50,
    },
    {
        "rule_code": "PAYROLL_PAYMENT",
        "origin": "Payroll",
        "event_type": "Payroll payment",
        "description": "Payroll disbursement through selected bank.",
        "debit_account_code": "2105",
        "credit_account_code": "BANK_SELECTED",
        "third_party_policy": "EMPLOYEE_REQUIRED",
        "currency_policy": "CRC",
        "bank_policy": "USER_SELECTED_BANK_REQUIRED",
        "iva_policy": "NOT_APPLICABLE",
        "retention_policy": "NOT_APPLICABLE_ON_PAYMENT",
        "line_description_template": "Pago salarios Payroll {employee} {period}",
        "priority": 60,
    },
    {
        "rule_code": "BANK_RECONCILIATION_FEE",
        "origin": "Bank Reconciliation",
        "event_type": "Bank fee",
        "description": "Bank fee identified in reconciliation.",
        "debit_account_code": "5.2.03",
        "credit_account_code": "BANK_STATEMENT_ACCOUNT",
        "third_party_policy": "BANK_OPTIONAL",
        "currency_policy": "BANK_STATEMENT_CURRENCY",
        "bank_policy": "STATEMENT_BANK_REQUIRED",
        "iva_policy": "NOT_APPLICABLE_UNLESS_BANK_TAX_LINE",
        "retention_policy": "NOT_APPLICABLE",
        "line_description_template": "Bank fee {bank} {reference}",
        "priority": 70,
    },
    {
        "rule_code": "BANK_RECONCILIATION_TRANSFER",
        "origin": "Bank Reconciliation",
        "event_type": "Bank transfer",
        "description": "Transfer between ERP bank accounts.",
        "debit_account_code": "BANK_DESTINATION",
        "credit_account_code": "BANK_SOURCE",
        "third_party_policy": "BANK_REQUIRED",
        "currency_policy": "BANK_STATEMENT_CURRENCY",
        "bank_policy": "SOURCE_AND_DESTINATION_BANK_REQUIRED",
        "iva_policy": "NOT_APPLICABLE",
        "retention_policy": "NOT_APPLICABLE",
        "line_description_template": "Bank transfer {source_bank} to {destination_bank}",
        "priority": 80,
    },
    {
        "rule_code": "INVOICING_SERVICE_INVOICE",
        "origin": "Invoicing",
        "event_type": "Service invoice",
        "description": "Formal service invoice issued from ERP.",
        "debit_account_code": "1.1.04.01",
        "credit_account_code": "4.1.01",
        "third_party_policy": "CLIENT_REQUIRED",
        "currency_policy": "INVOICE_CURRENCY",
        "bank_policy": "NOT_APPLICABLE",
        "iva_policy": "CREDIT_IVA_PAYABLE_WHEN_TAXED",
        "retention_policy": "REGISTER_IF_CUSTOMER_WITHHOLDS",
        "line_description_template": "Invoice {invoice_number} - {client}",
        "priority": 90,
    },
    {
        "rule_code": "XML_PURCHASE_ACCEPTED",
        "origin": "XML",
        "event_type": "Purchase XML accepted",
        "description": "Accepted supplier XML imported from fiscal inbox.",
        "debit_account_code": "EXPENSE_OR_ASSET_BY_CABYS_SUPPLIER",
        "credit_account_code": "2.1.01.01",
        "third_party_policy": "SUPPLIER_REQUIRED",
        "currency_policy": "XML_CURRENCY",
        "bank_policy": "NOT_APPLICABLE",
        "iva_policy": "DEBIT_IVA_CREDIT_FISCAL_FROM_XML",
        "retention_policy": "CREDIT_RETENTION_IF_XML_INDICATES",
        "line_description_template": "XML compra {supplier} {key}",
        "priority": 100,
    },
    {
        "rule_code": "XML_SALE_ACCEPTED",
        "origin": "XML",
        "event_type": "Sale XML accepted",
        "description": "Accepted customer sale XML imported from fiscal inbox.",
        "debit_account_code": "1.1.04.01",
        "credit_account_code": "4.1.01",
        "third_party_policy": "CLIENT_REQUIRED",
        "currency_policy": "XML_CURRENCY",
        "bank_policy": "NOT_APPLICABLE",
        "iva_policy": "CREDIT_IVA_PAYABLE_FROM_XML",
        "retention_policy": "REGISTER_IF_XML_WITHHOLDING",
        "line_description_template": "XML venta {client} {key}",
        "priority": 110,
    },
    {
        "rule_code": "MANUAL_ADJUSTMENT",
        "origin": "Manual",
        "event_type": "Manual adjustment",
        "description": "User-entered accounting adjustment with balanced debit and credit lines.",
        "debit_account_code": "USER_SELECTED",
        "credit_account_code": "USER_SELECTED",
        "third_party_policy": "ACCORDING_TO_ACCOUNT_REQUIREMENT",
        "currency_policy": "USER_SELECTED",
        "bank_policy": "REQUIRED_IF_BANK_ACCOUNT_IS_SELECTED",
        "iva_policy": "USER_SELECTED_AND_VALIDATED",
        "retention_policy": "USER_SELECTED_AND_VALIDATED",
        "line_description_template": "Manual adjustment {reason}",
        "priority": 120,
    },
]


def ensure_posting_rule_schema(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounting_posting_rules (
            id BIGSERIAL PRIMARY KEY,
            rule_code VARCHAR(100) NOT NULL UNIQUE,
            origin VARCHAR(50) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            debit_account_code VARCHAR(80) NOT NULL,
            debit_account_name TEXT,
            credit_account_code VARCHAR(80) NOT NULL,
            credit_account_name TEXT,
            third_party_policy VARCHAR(80) NOT NULL DEFAULT 'OPTIONAL',
            currency_policy VARCHAR(80) NOT NULL DEFAULT 'SOURCE_DOCUMENT',
            bank_policy VARCHAR(160) NOT NULL DEFAULT 'NOT_APPLICABLE',
            iva_policy VARCHAR(160) NOT NULL DEFAULT 'NOT_APPLICABLE',
            retention_policy VARCHAR(160) NOT NULL DEFAULT 'NOT_APPLICABLE',
            line_description_template TEXT,
            priority INTEGER NOT NULL DEFAULT 100,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            locked BOOLEAN NOT NULL DEFAULT TRUE,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_by TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_posting_rules_origin ON accounting_posting_rules(origin, active, priority)")


def _account_name(cur, account_code):
    if not account_code or account_code.startswith(("BANK_", "EXPENSE_", "USER_")):
        return None
    cur.execute("SELECT account_name FROM accounting_accounts WHERE account_code = %s", (account_code,))
    row = cur.fetchone()
    if isinstance(row, dict):
        return row.get("account_name")
    if row:
        return row[0]
    return None


def seed_default_posting_rules(cur, user="system"):
    ensure_posting_rule_schema(cur)
    inserted = 0
    updated = 0
    for rule in DEFAULT_POSTING_RULES:
        debit_name = _account_name(cur, rule["debit_account_code"])
        credit_name = _account_name(cur, rule["credit_account_code"])
        payload = {**rule, "debit_account_name": debit_name, "credit_account_name": credit_name}
        cur.execute("""
            INSERT INTO accounting_posting_rules (
                rule_code, origin, event_type, description,
                debit_account_code, debit_account_name,
                credit_account_code, credit_account_name,
                third_party_policy, currency_policy, bank_policy,
                iva_policy, retention_policy, line_description_template,
                priority, active, locked, metadata, created_by, updated_by
            ) VALUES (
                %(rule_code)s, %(origin)s, %(event_type)s, %(description)s,
                %(debit_account_code)s, %(debit_account_name)s,
                %(credit_account_code)s, %(credit_account_name)s,
                %(third_party_policy)s, %(currency_policy)s, %(bank_policy)s,
                %(iva_policy)s, %(retention_policy)s, %(line_description_template)s,
                %(priority)s, TRUE, TRUE, %(metadata)s, %(user)s, %(user)s
            )
            ON CONFLICT (rule_code) DO UPDATE SET
                origin = EXCLUDED.origin,
                event_type = EXCLUDED.event_type,
                description = EXCLUDED.description,
                debit_account_code = EXCLUDED.debit_account_code,
                debit_account_name = EXCLUDED.debit_account_name,
                credit_account_code = EXCLUDED.credit_account_code,
                credit_account_name = EXCLUDED.credit_account_name,
                third_party_policy = EXCLUDED.third_party_policy,
                currency_policy = EXCLUDED.currency_policy,
                bank_policy = EXCLUDED.bank_policy,
                iva_policy = EXCLUDED.iva_policy,
                retention_policy = EXCLUDED.retention_policy,
                line_description_template = EXCLUDED.line_description_template,
                priority = EXCLUDED.priority,
                active = TRUE,
                locked = TRUE,
                metadata = EXCLUDED.metadata,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            RETURNING (xmax = 0) AS inserted
        """, {**payload, "metadata": Json({"seed": "default_formal_engine"}), "user": user})
        if cur.fetchone()["inserted"]:
            inserted += 1
        else:
            updated += 1
    return {"inserted": inserted, "updated": updated, "total": len(DEFAULT_POSTING_RULES)}


def list_posting_rules(conn, origin=None, include_inactive=False):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_posting_rule_schema(cur)
        params = []
        where = []
        if origin:
            where.append("origin = %s")
            params.append(origin)
        if not include_inactive:
            where.append("active = TRUE")
        sql = """
            SELECT *
            FROM accounting_posting_rules
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY priority, origin, event_type"
        cur.execute(sql, params)
        return cur.fetchall()


def resolve_posting_rule(cur, origin, event_type=None):
    ensure_posting_rule_schema(cur)
    if event_type:
        cur.execute("""
            SELECT *
            FROM accounting_posting_rules
            WHERE active = TRUE
              AND origin = %s
              AND event_type = %s
            ORDER BY priority
            LIMIT 1
        """, (origin, event_type))
    else:
        cur.execute("""
            SELECT *
            FROM accounting_posting_rules
            WHERE active = TRUE
              AND origin = %s
            ORDER BY priority
            LIMIT 1
        """, (origin,))
    return cur.fetchone()
