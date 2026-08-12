from psycopg2.extras import RealDictCursor
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from services.accounting_bank_rules import (
    BCR_COLLECTION_FEE_USD,
    backfill_missing_bank_accounts,
    resolve_collections_bank,
    resolve_itp_bank,
    external_surveyor_settlement,
    should_apply_bcr_collection_fee,
)
from services.employee_payee_rules import employee_obligation_ids, is_employee_payee, load_employee_name_keys
from services.tenanting import DEFAULT_COMPANY_CODE, company_code as normalize_company_code, ensure_company_column


def _apply_current_fiscal_classification(conn):
    try:
        from services.accounting_fiscal_rules import apply_fiscal_classification
        apply_fiscal_classification(conn, year=date.today().year, apply=True)
    except Exception:
        # Fiscal tags must not block balanced accounting syncs; validation alerts catch gaps.
        pass

def create_accounting_entry(
    conn,
    entry_date,
    period,
    description,
    origin,
    origin_id,
    lines,
    created_by="SYSTEM"
):
    """
    Crea un asiento contable con validación de partida doble
    """

    def money(value):
        try:
            return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Monto contable inválido")

    total_debit = sum((money(l.get("debit")) for l in lines), Decimal("0"))
    total_credit = sum((money(l.get("credit")) for l in lines), Decimal("0"))

    if total_debit != total_credit or total_debit == 0:
        raise ValueError("Partida no balanceada")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Las integraciones automáticas tampoco pueden escribir en un período cerrado.
    cur.execute("""
        SELECT status FROM accounting_period_controls
        WHERE company_code = 'MSL-CR' AND period = %s
    """, (period,))
    period_control = cur.fetchone()
    if period_control and period_control.get("status") == "CLOSED":
        raise ValueError(f"El período contable {period} está cerrado")
    fiscal_year, fiscal_month = (int(value) for value in period.split("-"))
    cur.execute("""
        SELECT period_closed FROM closing_status
        WHERE company_code='MSL-CR' AND fiscal_year=%s AND period=%s AND ledger='0L'
    """, (fiscal_year, fiscal_month))
    legacy_control = cur.fetchone()
    if legacy_control and legacy_control.get("period_closed"):
        raise ValueError(f"El período contable {period} está cerrado")

    # 1️⃣ Insert entry
    cur.execute("""
        INSERT INTO accounting_entries
            (entry_date, period, description, origin, origin_id, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        entry_date,
        period,
        description,
        origin,
        origin_id,
        created_by
    ))

    entry_id = cur.fetchone()["id"]

    # 2️⃣ Insert lines
    for line in lines:
        cur.execute("""
            INSERT INTO accounting_lines
                (entry_id, account_code, account_name, debit, credit, line_description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            entry_id,
            line["account_code"],
            line["account_name"],
            money(line.get("debit")),
            money(line.get("credit")),
            line.get("description") or line.get("line_description")
        ))

    # 🔥🔥🔥 ESTA ES LA LÍNEA QUE FALTABA 🔥🔥🔥
    _apply_current_fiscal_classification(conn)
    conn.commit()

    return entry_id


def sync_collections_to_accounting(conn, company_code_filter: str | None = None):

    from psycopg2.extras import RealDictCursor
    from datetime import date, datetime

    if not conn:
        raise Exception("DB connection is required")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    company = normalize_company_code(company_code_filter)

    try:
        ensure_company_column("collections")
        ensure_company_column("accounting_entries")
        # ============================================================
        # 1️⃣ TC DEL DÍA
        # ============================================================
        today = date.today()

        cur.execute("""
            SELECT rate, rate_date, source
            FROM exchange_rate
            WHERE rate_date <= %s
            ORDER BY rate_date DESC
            LIMIT 1
        """, (today,))

        row_tc = cur.fetchone()

        if not row_tc:
            raise Exception("No existe ningún tipo de cambio registrado.")

        tc = float(row_tc["rate"])


        # ============================================================
        # 2️⃣ COLLECTIONS
        # ============================================================
        cur.execute("""
            SELECT
                c.id,
                c.numero_documento,
                c.nombre_cliente,
                c.fecha_emision,
                c.created_at,
                c.moneda,
                c.total
            FROM collections c
            WHERE c.company_code = %s
            ORDER BY c.id ASC
        """, (company,))

        rows = cur.fetchall() or []

        for c in rows:

            collection_id = c.get("id")
            numero = (c.get("numero_documento") or "").strip()

            nombre_cliente = (c.get("nombre_cliente") or "").strip()
            moneda = (c.get("moneda") or "").upper()

            total_raw = float(c.get("total") or 0)

            if total_raw <= 0:
                continue


            # ========================================================
            # 3️⃣ FECHA CONTABLE
            # ========================================================
            fecha_emision = c.get("fecha_emision") or c.get("created_at") or today

            if isinstance(fecha_emision, datetime):
                fecha = fecha_emision.date()
            else:
                fecha = fecha_emision

            period = fecha.strftime("%Y-%m")

            cur.execute("""
                SELECT rate
                FROM exchange_rate
                WHERE rate_date <= %s
                ORDER BY rate_date DESC
                LIMIT 1
            """, (fecha,))
            row_tc_invoice = cur.fetchone()
            tc_invoice = float((row_tc_invoice or {}).get("rate") or tc)


            # ========================================================
            # 4️⃣ PAÍS DEL CLIENTE
            # ========================================================
            pais = ""

            if nombre_cliente:

                cur.execute("""
                    SELECT pais
                    FROM cliente
                    WHERE LOWER(nombrecomercial) = LOWER(%s)
                    LIMIT 1
                """, (nombre_cliente,))

                cli = cur.fetchone()

                if cli:
                    pais = (cli.get("pais") or "").strip().lower()


            # ========================================================
            # 5️⃣ CONVERSIÓN MONEDA
            # ========================================================
            if moneda == "USD":
                total_crc = round(total_raw * tc_invoice, 2)
            else:
                total_crc = round(total_raw, 2)


            # ========================================================
            # 6️⃣ IVA
            # ========================================================
            if pais == "costa rica":
                subtotal = round(total_crc / 1.13, 2)
                iva = round(total_crc - subtotal, 2)
            else:
                subtotal = total_crc
                iva = 0.0


            detail_text = f"From Collections {numero}"


            # ========================================================
            # 7️⃣ VALIDAR SI YA EXISTE ASIENTO
            # ========================================================
            cur.execute("""
                SELECT id
                FROM accounting_entries
                WHERE origin = 'COLLECTIONS'
                  AND origin_id = %s
                  AND company_code = %s
                  AND COALESCE(reversed, FALSE) = FALSE
                ORDER BY id DESC
                LIMIT 1
            """, (collection_id, company))

            row_entry = cur.fetchone()

            entry_id = row_entry["id"] if row_entry else None


            # ========================================================
            # 8️⃣ CREAR ASIENTO CONTABLE
            # ========================================================
            AR_ACCOUNT_CODE = "1.1.04.01"
            AR_ACCOUNT_NAME = "Cuentas por cobrar comerciales"
            REV_ACCOUNT_CODE = "4.1.01"
            REV_ACCOUNT_NAME = "Ingresos por servicios"
            IVA_ACCOUNT_CODE = "2.1.02.03"
            IVA_ACCOUNT_NAME = "Impuesto sobre valor agregado (IVA) por pagar"

            if entry_id:
                cur.execute("""
                    UPDATE accounting_entries
                    SET entry_date = %s,
                        period = %s,
                        description = %s
                    WHERE id = %s
                """, (fecha, period, detail_text, entry_id))
                cur.execute("DELETE FROM accounting_lines WHERE entry_id = %s", (entry_id,))

            else:

                cur.execute("""
                    INSERT INTO accounting_entries
                    (company_code, entry_date, period, description, origin, origin_id, created_by)
                    VALUES (%s, %s, %s, %s, 'COLLECTIONS', %s, 'SYSTEM')
                    RETURNING id
                """, (company, fecha, period, detail_text, collection_id))

                entry_id = cur.fetchone()["id"]


                # ----------------------------------------------------
                # CUENTAS CONTABLES (COA JERÁRQUICO ERP-SOM)
                # ----------------------------------------------------

                AR_ACCOUNT_CODE = "1.1.04.01"
                AR_ACCOUNT_NAME = "Cuentas por cobrar comerciales"

                REV_ACCOUNT_CODE = "4.1.01"
                REV_ACCOUNT_NAME = "Ingresos por servicios"

                IVA_ACCOUNT_CODE = "2.1.02.03"
                IVA_ACCOUNT_NAME = "Impuesto sobre valor agregado (IVA) por pagar"


                # ---------------- CxC ----------------
                cur.execute("""
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, %s, 0, %s)
                """, (
                    entry_id,
                    AR_ACCOUNT_CODE,
                    AR_ACCOUNT_NAME,
                    total_crc,
                    detail_text
                ))


                # ---------------- INGRESOS ----------------
                cur.execute("""
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, 0, %s, %s)
                """, (
                    entry_id,
                    REV_ACCOUNT_CODE,
                    REV_ACCOUNT_NAME,
                    subtotal,
                    detail_text
                ))


                # ---------------- IVA ----------------
                if iva > 0:

                    cur.execute("""
                        INSERT INTO accounting_lines
                        (entry_id, account_code, account_name, debit, credit, line_description)
                        VALUES (%s, %s, %s, 0, %s, %s)
                    """, (
                        entry_id,
                        IVA_ACCOUNT_CODE,
                        IVA_ACCOUNT_NAME,
                        iva,
                        detail_text
                    ))

            if row_entry:
                cur.execute("""
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, %s, 0, %s)
                """, (
                    entry_id,
                    AR_ACCOUNT_CODE,
                    AR_ACCOUNT_NAME,
                    total_crc,
                    detail_text
                ))
                cur.execute("""
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, 0, %s, %s)
                """, (
                    entry_id,
                    REV_ACCOUNT_CODE,
                    REV_ACCOUNT_NAME,
                    subtotal,
                    detail_text
                ))
                if iva > 0:
                    cur.execute("""
                        INSERT INTO accounting_lines
                        (entry_id, account_code, account_name, debit, credit, line_description)
                        VALUES (%s, %s, %s, 0, %s, %s)
                    """, (
                        entry_id,
                        IVA_ACCOUNT_CODE,
                        IVA_ACCOUNT_NAME,
                        iva,
                        detail_text
                    ))

        _apply_current_fiscal_classification(conn)
        _apply_current_fiscal_classification(conn)
        conn.commit()

    except Exception as e:

        conn.rollback()
        raise Exception(f"sync_collections_to_accounting error: {str(e)}")

    finally:
        cur.close()


def sync_payroll_to_accounting(conn):
    """
    Sincroniza payroll_runs con formato formal de planilla.
    Para empleados quincenales, un payroll_run mensual genera dos devengos
    y dos pagos: dia 15 y dia 30.
    """
    from datetime import date
    from decimal import Decimal
    from calendar import monthrange
    from psycopg2.extras import RealDictCursor

    if not conn:
        raise Exception("DB connection is required")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    def _money(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _is_half_run(gross, employee_salary):
        gross_d = Decimal(str(gross or 0))
        salary_d = Decimal(str(employee_salary or 0))
        return salary_d > 0 and gross_d <= (salary_d / Decimal("2") + Decimal("1.00"))

    def _entry_date(year, month, day):
        last_day = monthrange(int(year), int(month))[1]
        return date(int(year), int(month), min(int(day), last_day))

    def _monthly_income_tax(monthly_gross):
        brackets = [
            (Decimal("918000"), Decimal("0.00")),
            (Decimal("1347000"), Decimal("0.10")),
            (Decimal("2364000"), Decimal("0.15")),
            (Decimal("4727000"), Decimal("0.20")),
            (Decimal("999999999999"), Decimal("0.25")),
        ]
        amount = _money(monthly_gross)
        previous = Decimal("0.00")
        tax = Decimal("0.00")
        for limit, rate in brackets:
            if amount <= previous:
                break
            taxable_slice = min(amount, limit) - previous
            if taxable_slice > 0:
                tax += taxable_slice * rate
            previous = limit
        return _money(tax)

    def _ensure_account(code, name, level, account_type, parent=None):
        cur.execute("SELECT id FROM accounting_ledger WHERE account_code = %s LIMIT 1", (code,))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE accounting_ledger
                   SET account_name = %s,
                       active = TRUE
                 WHERE id = %s
            """, (name, row["id"]))
        else:
            cur.execute("""
                INSERT INTO accounting_ledger (
                    account_code, account_name, account_level, account_type, parent_account,
                    description, active, source_module
                )
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'PAYROLL')
            """, (code, name, level, account_type, parent, name))
        normal_balance = "DEBIT" if account_type == "EXPENSE" else "CREDIT"
        cur.execute("SELECT id FROM accounting_accounts WHERE account_code = %s LIMIT 1", (code,))
        account_row = cur.fetchone()
        if account_row:
            cur.execute("""
                UPDATE accounting_accounts
                   SET account_name = %s,
                       account_type = %s,
                       normal_balance = %s,
                       account_level = %s,
                       parent_account = %s,
                       active = TRUE,
                       accepts_posting = TRUE,
                       updated_by = 'PAYROLL',
                       updated_at = NOW()
                 WHERE id = %s
            """, (name, account_type, normal_balance, level, parent, account_row["id"]))
        else:
            cur.execute("""
                INSERT INTO accounting_accounts (
                    account_code, account_name, account_type, normal_balance, account_level,
                    parent_account, accepts_posting, active, created_by, updated_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, TRUE, 'PAYROLL', 'PAYROLL')
            """, (code, name, account_type, normal_balance, level, parent))

    accounts = {
        "salary_exp": ("500-001-001-001", "Sueldos"),
        "social_exp": ("500-001-001-002", "Cargas Sociales"),
        "bonus_exp": ("500-001-001-003", "Aguinaldos"),
        "vacation_exp": ("500-001-001-004", "Vacaciones"),
        "salary_payable": ("2.1.02.07", "Salarios por pagar"),
        "worker_payable": ("2.1.03.01", "Retenciones obreras por pagar-CCSS"),
        "income_tax_payable": ("2.1.02.04", "Impuesto de renta por pagar"),
        "employer_payable": ("2.1.05.01", "Obligaciones patronales por pagar-CCSS"),
        "bonus_payable": ("2.1.04.03", "Provisión aguinaldo"),
        "vacation_payable": ("2.1.04.01", "Provisión vacaciones"),
        "bank": ("1.1.02", "Bancos"),
    }

    def _line(key, debit, credit, detail):
        code, name = accounts[key]
        return {
            "account_code": code,
            "account_name": name,
            "debit": _money(debit),
            "credit": _money(credit),
            "line_description": detail,
        }

    def _payroll_lines(gross, detail, worker_rate, employer_rate, income_tax=0):
        gross = _money(gross)
        worker = _money(gross * Decimal(str(worker_rate)))
        employer = _money(gross * Decimal(str(employer_rate)))
        income_tax = _money(income_tax)
        bonus = _money(gross * Decimal("0.0833"))
        vacation = _money(gross * Decimal("0.0417"))
        net_salary = _money(gross - worker - income_tax)

        lines = [
            _line("salary_exp", gross, 0, f"{detail} - Sueldos"),
            _line("social_exp", employer, 0, f"{detail} - Cargas Sociales"),
            _line("bonus_exp", bonus, 0, f"{detail} - Aguinaldo"),
            _line("vacation_exp", vacation, 0, f"{detail} - Vacaciones"),
            _line("employer_payable", 0, employer, f"{detail} - CCSS Cuota Patronal"),
            _line("worker_payable", 0, worker, f"{detail} - CCSS Cuota Obrera"),
            _line("salary_payable", 0, net_salary, f"{detail} - Salario neto"),
            _line("bonus_payable", 0, bonus, f"{detail} - Reserva Aguinaldo"),
            _line("vacation_payable", 0, vacation, f"{detail} - Reserva Vacaciones"),
        ]
        if income_tax > 0:
            lines.insert(6, _line("income_tax_payable", 0, income_tax, f"{detail} - Impuesto de renta"))
        return lines, net_salary

    def _upsert_entry(origin, origin_id, period, entry_date, description, lines):
        cur.execute("""
            SELECT id
            FROM accounting_entries
            WHERE origin = %s
              AND origin_id = %s
              AND period = %s
            ORDER BY id
            LIMIT 1
        """, (origin, origin_id, period))
        entry = cur.fetchone()

        if entry:
            entry_id = entry["id"]
            cur.execute("""
                UPDATE accounting_entries
                   SET entry_date = %s,
                       description = %s,
                       workflow_status = COALESCE(workflow_status, 'POSTED'),
                       updated_at = NOW()
                 WHERE id = %s
            """, (entry_date, description, entry_id))
            cur.execute("DELETE FROM accounting_lines WHERE entry_id = %s", (entry_id,))
            for line in lines:
                cur.execute("""
                    INSERT INTO accounting_lines
                        (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    entry_id, line["account_code"], line["account_name"],
                    line["debit"], line["credit"], line["line_description"]
                ))
            return entry_id

        return create_accounting_entry(
            conn=conn,
            entry_date=entry_date,
            period=period,
            description=description,
            origin=origin,
            origin_id=origin_id,
            lines=lines,
        )

    try:
        _ensure_account("500-001-001-001", "Sueldos", 5, "EXPENSE", "500-001-001")
        _ensure_account("500-001-001-002", "Cargas Sociales", 5, "EXPENSE", "500-001-001")
        _ensure_account("500-001-001-003", "Aguinaldos", 5, "EXPENSE", "500-001-001")
        _ensure_account("500-001-001-004", "Vacaciones", 5, "EXPENSE", "500-001-001")
        _ensure_account("2.1.02.07", "Salarios por pagar", 4, "LIABILITY", "2.1.02")
        _ensure_account("2.1.02.04", "Impuesto de renta por pagar", 4, "LIABILITY", "2.1.02")
        _ensure_account("2.1.03.01", "Retenciones obreras por pagar-CCSS", 4, "LIABILITY", "2.1.03")
        _ensure_account("2.1.04.01", "Provisión vacaciones", 4, "LIABILITY", "2.1.04")
        _ensure_account("2.1.04.03", "Provisión aguinaldo", 4, "LIABILITY", "2.1.04")
        _ensure_account("2.1.05.01", "Obligaciones patronales por pagar-CCSS", 4, "LIABILITY", "2.1.05")

        cur.execute("""
            SELECT id, usuario, year, month, salario_bruto, creado_en
            FROM payroll_runs
            ORDER BY id
        """)
        runs = cur.fetchall() or []

        for payroll in runs:
            payroll_id = payroll.get("id")
            gross = _money(payroll.get("salario_bruto"))
            if gross <= 0:
                continue

            period = f"{payroll['year']}-{int(payroll['month']):02d}"
            detail = f"Payroll {payroll.get('usuario')} {period}"

            cur.execute("SELECT salario, pago FROM empleados WHERE usuario = %s LIMIT 1", (payroll.get("usuario"),))
            employee = cur.fetchone()
            employee_salary = employee.get("salario") if employee else 0
            is_quincenal = "QUINC" in ((employee.get("pago") if employee else "") or "").upper()

            if is_quincenal:
                monthly_gross = gross * Decimal("2") if _is_half_run(gross, employee_salary) else gross
                half_gross = _money(monthly_gross / Decimal("2"))
                half_tax = _money(_monthly_income_tax(monthly_gross) / Decimal("2"))
                total_net_salary = Decimal("0.00")

                for payroll_origin, payment_origin, day, label in (
                    ("PAYROLL", "PAYROLL_PAYMENT", 15, "Quincena 1"),
                    ("PAYROLL_Q2", "PAYROLL_PAYMENT_Q2", 30, "Quincena 2"),
                ):
                    piece_detail = f"{detail} - {label}"
                    entry_date = _entry_date(payroll["year"], payroll["month"], day)
                    lines, net_salary = _payroll_lines(
                        half_gross,
                        piece_detail,
                        Decimal("0.0517"),
                        Decimal("0.0850"),
                        half_tax,
                    )
                    total_net_salary += net_salary
                    _upsert_entry(payroll_origin, payroll_id, period, entry_date, piece_detail, lines)

                    payment_detail = f"Pago salarios {piece_detail}"
                    payment_lines = [
                        _line("salary_payable", net_salary, 0, payment_detail),
                        _line("bank", 0, net_salary, payment_detail),
                    ]
                    _upsert_entry(payment_origin, payroll_id, period, entry_date, payment_detail, payment_lines)

                cur.execute("""
                    UPDATE payroll_runs
                       SET salario_bruto = %s,
                           salario_neto = %s
                     WHERE id = %s
                """, (monthly_gross, total_net_salary, payroll_id))
            else:
                entry_date = _entry_date(
                    payroll["year"],
                    payroll["month"],
                    monthrange(int(payroll["year"]), int(payroll["month"]))[1],
                )
                income_tax = _monthly_income_tax(gross)
                lines, net_salary = _payroll_lines(
                    gross,
                    detail,
                    Decimal("0.1034"),
                    Decimal("0.1700"),
                    income_tax,
                )

                cur.execute("""
                    UPDATE payroll_runs
                       SET salario_neto = %s
                     WHERE id = %s
                """, (net_salary, payroll_id))

                _upsert_entry("PAYROLL", payroll_id, period, entry_date, detail, lines)

                payment_detail = f"Pago salarios {detail}"
                payment_lines = [
                    _line("salary_payable", net_salary, 0, payment_detail),
                    _line("bank", 0, net_salary, payment_detail),
                ]
                _upsert_entry("PAYROLL_PAYMENT", payroll_id, period, entry_date, payment_detail, payment_lines)

        _apply_current_fiscal_classification(conn)
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise Exception(f"sync_payroll_to_accounting error: {str(e)}")
    finally:
        cur.close()



def sync_cash_app_to_accounting(conn):

    from psycopg2.extras import RealDictCursor
    from datetime import date, datetime

    if not conn:
        raise Exception("DB connection is required")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            ALTER TABLE cash_app
            ADD COLUMN IF NOT EXISTS bank_account_code TEXT
        """)
        cur.execute("""
            ALTER TABLE cash_app
            ADD COLUMN IF NOT EXISTS bank_account_name TEXT
        """)
        backfill_missing_bank_accounts(cur)

        def _bank_account(code, name, fallback_code="1.1.01", fallback_name="Bancos"):
            account = resolve_collections_bank(cur, code, name, current_client_name, current_raw_bank)
            if account:
                return account["account_code"], account["account_name"]
            return fallback_code, fallback_name

        def _ensure_posting_account(code, name, account_type, normal_balance, parent_account=None):
            cur.execute("""
                UPDATE accounting_ledger
                   SET account_name = %s,
                       account_type = %s,
                       parent_account = COALESCE(parent_account, %s),
                       active = TRUE
                 WHERE account_code = %s
            """, (name, account_type, parent_account, code))
            cur.execute("""
                INSERT INTO accounting_ledger (
                    account_code, account_name, account_type, account_level,
                    parent_account, active, source_module
                )
                SELECT %s, %s, %s, %s, %s, TRUE, 'COLLECTIONS'
                WHERE NOT EXISTS (
                    SELECT 1 FROM accounting_ledger WHERE account_code = %s
                )
            """, (code, name, account_type, 4, parent_account, code))
            cur.execute("""
                UPDATE accounting_accounts
                   SET account_name = %s,
                       account_type = %s,
                       normal_balance = %s,
                       parent_account = COALESCE(parent_account, %s),
                       active = TRUE,
                       accepts_posting = TRUE,
                       updated_at = NOW()
                 WHERE account_code = %s
            """, (name, account_type, normal_balance, parent_account, code))
            cur.execute("""
                INSERT INTO accounting_accounts (
                    account_code, account_name, account_type, normal_balance,
                    account_level, parent_account, accepts_posting, active,
                    created_by, updated_by
                )
                SELECT %s, %s, %s, %s, %s, %s, TRUE, TRUE, 'COLLECTIONS', 'COLLECTIONS'
                WHERE NOT EXISTS (
                    SELECT 1 FROM accounting_accounts WHERE account_code = %s
                )
            """, (code, name, account_type, normal_balance, 4, parent_account, code))

        _ensure_posting_account("5.2.03", "Comisiones bancarias", "EXPENSE", "DEBIT", "5.2")

        # ============================================================
        # 0️⃣ TRAER TODOS LOS PAGOS CASH_APP
        # ============================================================
        cur.execute("""
            SELECT
                c.id,
                c.numero_documento,
                c.codigo_cliente,
                c.fecha_pago,
                c.nombre_cliente,
                c.banco,
                c.monto_pagado,
                c.comision,
                c.bank_account_code,
                c.bank_account_name,
                a.id AS entry_id
            FROM cash_app c
            LEFT JOIN accounting_entries a
              ON a.origin = 'CASH_APP'
             AND a.origin_id = c.id
            ORDER BY c.id
        """)

        pagos = cur.fetchall() or []

        for p in pagos:

            cash_id = p.get("id")
            numero = (p.get("numero_documento") or "").strip()
            current_client_code = (p.get("codigo_cliente") or "").strip()
            current_client_name = (p.get("nombre_cliente") or "").strip()
            current_raw_bank = (p.get("banco") or "").strip()
            fecha_pago = p.get("fecha_pago")

            if not fecha_pago:
                continue


            # ========================================================
            # NORMALIZAR FECHA
            # ========================================================
            if isinstance(fecha_pago, datetime):
                fecha = fecha_pago.date()
            else:
                fecha = fecha_pago


            monto = float(p.get("monto_pagado") or 0)
            comision = abs(float(p.get("comision") or 0))

            if monto <= 0:
                continue


            # ========================================================
            # 1️⃣ OBTENER TC POR FECHA
            # ========================================================
            cur.execute("""
                SELECT rate
                FROM exchange_rate
                WHERE rate_date = %s
                LIMIT 1
            """, (fecha,))

            row_tc = cur.fetchone()

            if not row_tc:

                cur.execute("""
                    SELECT rate
                    FROM exchange_rate
                    ORDER BY rate_date DESC
                    LIMIT 1
                """)

                row_tc = cur.fetchone()

                if not row_tc:
                    raise Exception(
                        "No existe ningún Tipo de Cambio registrado."
                    )

            tc = float(row_tc["rate"])


            # ========================================================
            # 2️⃣ CONVERSIÓN CRC
            # ========================================================
            monto_crc = round(monto * tc, 2)
            comision_crc = round(comision * tc, 2)
            banco_crc = monto_crc
            total_aplicado_crc = round((monto + comision) * tc, 2)

            if banco_crc < 0:
                raise Exception(
                    f"Comisión mayor al monto en cash_app id={cash_id}"
                )


            period = fecha.strftime("%Y-%m")
            detail = f"Pago factura {numero}"


            # ========================================================
            # 3️⃣ ¿EXISTE ASIENTO?
            # ========================================================
            entry_id = p.get("entry_id")


            # ========================================================
            # 4️⃣ CREAR / ACTUALIZAR CABECERA
            # ========================================================
            if not entry_id:

                cur.execute("""
                    INSERT INTO accounting_entries
                    (entry_date, period, description, origin, origin_id, created_by)
                    VALUES (%s, %s, %s, 'CASH_APP', %s, 'SYSTEM')
                    RETURNING id
                """, (fecha, period, detail, cash_id))

                entry_id = cur.fetchone()["id"]

            else:

                cur.execute("""
                    UPDATE accounting_entries
                    SET entry_date = %s,
                        period = %s,
                        description = %s
                    WHERE id = %s
                """, (fecha, period, detail, entry_id))


            # ========================================================
            # 5️⃣ LIMPIAR LÍNEAS EXISTENTES
            # ========================================================
            cur.execute("""
                DELETE FROM accounting_lines
                WHERE entry_id = %s
            """, (entry_id,))


            # ========================================================
            # 6️⃣ CUENTAS CONTABLES (COA ERP-SOM)
            # ========================================================

            BANK_ACCOUNT_CODE = "1.1.01"
            BANK_ACCOUNT_NAME = "Bancos"
            BANK_ACCOUNT_CODE, BANK_ACCOUNT_NAME = _bank_account(
                p.get("bank_account_code"),
                p.get("bank_account_name"),
                BANK_ACCOUNT_CODE,
                BANK_ACCOUNT_NAME
            )

            if should_apply_bcr_collection_fee(
                cur,
                BANK_ACCOUNT_CODE,
                BANK_ACCOUNT_NAME,
                current_raw_bank,
                numero,
                current_client_code,
                current_client_name,
            ):
                total_aplicado = round(monto + comision, 2)
                if total_aplicado <= BCR_COLLECTION_FEE_USD:
                    raise Exception(
                        f"Pago BCR menor o igual a comision de 25 USD en cash_app id={cash_id}"
                    )
                monto = round(total_aplicado - BCR_COLLECTION_FEE_USD, 2)
                comision = BCR_COLLECTION_FEE_USD
                cur.execute("""
                    UPDATE cash_app
                       SET monto_pagado = %s,
                           comision = %s,
                           bank_account_code = %s,
                           bank_account_name = %s
                     WHERE id = %s
                """, (monto, comision, BANK_ACCOUNT_CODE, BANK_ACCOUNT_NAME, cash_id))

                monto_crc = round(monto * tc, 2)
                comision_crc = round(comision * tc, 2)
                banco_crc = monto_crc
                total_aplicado_crc = round((monto + comision) * tc, 2)

            BANK_FEE_CODE = "5.2.03"
            BANK_FEE_NAME = "Comisiones bancarias"

            AR_ACCOUNT_CODE = "1.1.04.01"
            AR_ACCOUNT_NAME = "Cuentas por cobrar comerciales"


            # ========================================================
            # 7️⃣ BANCOS (NETO RECIBIDO)
            # ========================================================
            if banco_crc > 0:

                cur.execute("""
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, %s, 0, %s)
                """, (
                    entry_id,
                    BANK_ACCOUNT_CODE,
                    BANK_ACCOUNT_NAME,
                    banco_crc,
                    detail
                ))


            # ========================================================
            # 8️⃣ COMISIÓN BANCARIA
            # ========================================================
            if comision_crc > 0:

                cur.execute("""
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, %s, 0, %s)
                """, (
                    entry_id,
                    BANK_FEE_CODE,
                    BANK_FEE_NAME,
                    comision_crc,
                    f"Comisión - {detail}"
                ))


            # ========================================================
            # 9️⃣ CxC (CRÉDITO TOTAL FACTURA)
            # ========================================================
            cur.execute("""
                INSERT INTO accounting_lines
                (entry_id, account_code, account_name, debit, credit, line_description)
                VALUES (%s, %s, %s, 0, %s, %s)
            """, (
                entry_id,
                AR_ACCOUNT_CODE,
                AR_ACCOUNT_NAME,
                total_aplicado_crc,
                detail
            ))


        _apply_current_fiscal_classification(conn)
        conn.commit()

    except Exception as e:

        conn.rollback()
        raise Exception(f"sync_cash_app_to_accounting error: {str(e)}")

    finally:
        cur.close()



def sync_itp_to_accounting(conn):
    """
    Sincroniza payment_obligations → accounting
    (ERP-SOM BLINDADO - COA JERÁRQUICO)
    """

    from psycopg2.extras import RealDictCursor
    from datetime import date, datetime

    if not conn:
        raise Exception("DB connection is required")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # ============================================================
        # HELPERS
        # ============================================================
        def _to_date(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value.date()
            return value

        def _account_exists(code: str) -> bool:
            code = (code or "").strip()
            if not code:
                return False
            cur.execute("""
                SELECT 1
                FROM accounting_ledger
                WHERE account_code = %s
                  AND active = TRUE
                LIMIT 1
            """, (code,))
            return cur.fetchone() is not None

        def _ensure_account(code: str, name: str, account_type: str, normal_balance: str, parent_account=None):
            code = (code or "").strip()
            if not code:
                return
            cur.execute("""
                UPDATE accounting_ledger
                SET account_name = %s,
                    account_type = %s,
                    account_level = COALESCE(account_level, %s),
                    parent_account = COALESCE(parent_account, %s),
                    active = TRUE
                WHERE account_code = %s
            """, (name, account_type, 4, parent_account, code))
            cur.execute("""
                INSERT INTO accounting_ledger (
                    account_code, account_name, account_type, account_level,
                    parent_account, active
                )
                SELECT %s, %s, %s, %s, %s, TRUE
                WHERE NOT EXISTS (
                    SELECT 1 FROM accounting_ledger WHERE account_code = %s
                )
            """, (code, name, account_type, 4, parent_account, code))

        def _bank_account(code, name, fallback_code="1.1.02", fallback_name="Bancos"):
            account = resolve_itp_bank(
                cur,
                code,
                name,
                payee_name=current_payee_name,
                payee_type=current_payee_type,
                obligation_type=current_obligation_type,
                country=current_country,
                reference=current_reference,
                notes=current_notes,
            )
            if account:
                return account["account_code"], account["account_name"]
            return fallback_code, fallback_name

        def _insert_line(entry_id: int, code: str, name: str, debit: float, credit: float, desc: str):
            cur.execute("""
                INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (entry_id, code, name, float(debit or 0), float(credit or 0), desc))

        def _upsert_entry(origin: str, origin_id: int, entry_date: date, period: str, description: str) -> int:
            cur.execute("""
                SELECT id
                FROM accounting_entries
                WHERE origin = %s
                  AND origin_id = %s
                LIMIT 1
            """, (origin, origin_id))

            row = cur.fetchone()
            if row:
                eid = row["id"]
                cur.execute("""
                    UPDATE accounting_entries
                    SET entry_date = %s,
                        period = %s,
                        description = %s
                    WHERE id = %s
                """, (entry_date, period, description, eid))
                return eid

            cur.execute("""
                INSERT INTO accounting_entries
                    (entry_date, period, description, origin, origin_id, created_by)
                VALUES (%s, %s, %s, %s, %s, 'SYSTEM')
                RETURNING id
            """, (entry_date, period, description, origin, origin_id))

            return cur.fetchone()["id"]

        def _delete_future_system_entries(origin_id=None, origin=None):
            clauses = [
                "origin IN ('ITP', 'ITP_PAYMENT')",
                "entry_date > CURRENT_DATE",
                "COALESCE(created_by, 'SYSTEM') = 'SYSTEM'",
            ]
            params = []
            if origin_id is not None:
                clauses.append("origin_id = %s")
                params.append(origin_id)
            if origin:
                clauses.append("origin = %s")
                params.append(origin)
            where_clause = " AND ".join(clauses)
            cur.execute(f"""
                DELETE FROM accounting_lines
                WHERE entry_id IN (
                    SELECT id FROM accounting_entries WHERE {where_clause}
                )
            """, params)
            cur.execute(f"DELETE FROM accounting_entries WHERE {where_clause}", params)


        # ============================================================
        # 0️⃣ OBTENER TC DEL DÍA
        # ============================================================
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS payment_bank TEXT
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS payment_bank_account_code TEXT
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS payment_bank_account_name TEXT
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS paid_with_card BOOLEAN NOT NULL DEFAULT FALSE
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS card_transaction_id BIGINT
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS card_paid_at DATE
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS card_holder_name TEXT
        """)
        backfill_missing_bank_accounts(cur)
        employee_itp_ids = employee_obligation_ids(cur)
        if employee_itp_ids:
            cur.execute("""
                DELETE FROM accounting_lines
                WHERE entry_id IN (
                    SELECT id
                    FROM accounting_entries
                    WHERE origin IN ('ITP', 'ITP_PAYMENT')
                      AND origin_id = ANY(%s)
                )
            """, (employee_itp_ids,))
            cur.execute("""
                DELETE FROM accounting_entries
                WHERE origin IN ('ITP', 'ITP_PAYMENT')
                  AND origin_id = ANY(%s)
            """, (employee_itp_ids,))

        today = date.today()
        _delete_future_system_entries()

        cur.execute("""
            SELECT rate, rate_date, source
            FROM exchange_rate
            WHERE rate_date <= %s
            ORDER BY rate_date DESC
            LIMIT 1
        """, (today,))

        tc_row = cur.fetchone()
        if not tc_row:
            raise Exception("No existe ningún tipo de cambio registrado. No se puede contabilizar ITP.")

        tc = float(tc_row["rate"])


        # ============================================================
        # 1️⃣ Traer obligaciones activas
        # ============================================================
        cur.execute("""
            SELECT
                p.id,
                p.payee_name,
                p.payee_type,
                p.obligation_type,
                p.reference,
                p.country,
                p.issue_date,
                p.last_payment_date,
                p.currency,
                p.total,
                p.balance,
                p.status,
                p.active,
                p.notes,
                p.payment_bank_account_code,
                p.payment_bank_account_name,
                COALESCE(p.paid_with_card, FALSE) AS paid_with_card
            FROM payment_obligations p
            WHERE p.active = TRUE
            ORDER BY p.id ASC
        """)

        obligations = cur.fetchall() or []
        employee_name_keys = load_employee_name_keys(cur)


        # ============================================================
        # 2️⃣ Procesar una por una
        # ============================================================
        for ob in obligations:

            obligation_id = ob.get("id")
            payee_name = (ob.get("payee_name") or "").strip() or "N/A"
            if is_employee_payee(cur, payee_name, employee_name_keys):
                continue
            current_payee_name = payee_name
            current_country = (ob.get("country") or "").strip()
            current_reference = (ob.get("reference") or "").strip()
            current_notes = (ob.get("notes") or "").strip()
            payee_type = (ob.get("payee_type") or "").upper()
            obligation_type = (ob.get("obligation_type") or "").upper()
            current_payee_type = payee_type
            current_obligation_type = obligation_type
            currency = (ob.get("currency") or "").upper()

            total_raw = float(ob.get("total") or 0)
            balance_raw = float(ob.get("balance") or 0)

            if total_raw == 0:
                continue

            # ------------------------------------------------------------
            # Fechas + período
            # ------------------------------------------------------------
            issue_date = _to_date(ob.get("issue_date")) or today
            if issue_date > today:
                _delete_future_system_entries(obligation_id)
                continue
            period = issue_date.strftime("%Y-%m")

            status = (ob.get("status") or "").upper()

            # ------------------------------------------------------------
            # Conversión por moneda
            # ------------------------------------------------------------
            if currency == "USD":
                total_crc = round(total_raw * tc, 2)
                balance_crc = round(balance_raw * tc, 2)
            else:
                total_crc = round(total_raw, 2)
                balance_crc = round(balance_raw, 2)

            is_credit_note = (obligation_type == "SUPPLIER_CREDIT_NOTE")
            calc_total = abs(total_crc)

            def _purchase_xml_tax_crc(reference):
                if not reference:
                    return None
                cur.execute("""
                    SELECT currency_code, exchange_rate, tax_amount
                    FROM tax_electronic_documents
                    WHERE direction='PURCHASE'
                      AND (electronic_key=%s OR document_number=%s)
                      AND COALESCE(tax_amount,0) >= 0
                    ORDER BY
                      CASE WHEN COALESCE(tax_amount,0) > 0 THEN 0 ELSE 1 END,
                      updated_at DESC NULLS LAST,
                      id DESC
                    LIMIT 1
                """, (str(reference), str(reference)))
                row = cur.fetchone()
                if not row:
                    return None
                tax_raw = float(row.get("tax_amount") or 0)
                doc_currency = (row.get("currency_code") or "CRC").upper()
                rate = float(row.get("exchange_rate") or 1)
                if doc_currency == "USD":
                    return round(tax_raw * rate, 2)
                return round(tax_raw, 2)

            # ------------------------------------------------------------
            # IVA SOLO PARA SUPPLIER
            # ------------------------------------------------------------
            if payee_type == "SUPPLIER":
                xml_iva = _purchase_xml_tax_crc(ob.get("reference"))
                iva = min(round(abs(xml_iva or 0), 2), calc_total)
                subtotal = round(calc_total - iva, 2)
            else:
                subtotal = calc_total
                iva = 0.0


            # ============================================================
            # CUENTAS (COA JERÁRQUICO)
            # ============================================================

            # Gastos ITP. Salarios queda reservado exclusivamente para PAYROLL.
            EXP_PROF_CODE = "500-001-001-006"
            EXP_PROF_NAME = "Servicios Profesionales"

            EXP_ACCOUNTING_CODE = "500-001-001-007"
            EXP_ACCOUNTING_NAME = "Servicios Contables"

            EXP_SECURITY_CODE = "500-001-001-008"
            EXP_SECURITY_NAME = "Servicio de Vigilancia"

            EXP_CLEANING_CODE = "500-001-001-060"
            EXP_CLEANING_NAME = "Servicios de limpieza"

            EXP_SUPPLIES_CODE = "5.1.04"
            EXP_SUPPLIES_NAME = "Gastos por suministros de oficina"

            EXP_RENT_CODE = "5.1.05"
            EXP_RENT_NAME = "Gastos por alquiler"

            EXP_FUEL_CODE = "5.1.08"
            EXP_FUEL_NAME = "Gastos por combustible"

            EXP_OTHER_CODE = "5.4"
            EXP_OTHER_NAME = "Otros gastos"

            # Cuentas por pagar (tu COA sí trae 2.1.01.01/02/03)
            AP_CODE = "2.1.01.01"
            AP_NAME = "Cuentas por pagar-comerciales"

            # IVA crédito fiscal (NO lo veo en tu snippet; lo dejamos protegido)
            IVA_CF_CODE = "1.1.13.99"
            IVA_CF_NAME = "IVA crédito fiscal"

            # Bancos (grupo)
            BANK_CODE = "1.1.02"
            BANK_NAME = "Bancos"
            BANK_CODE, BANK_NAME = _bank_account(
                ob.get("payment_bank_account_code"),
                ob.get("payment_bank_account_name"),
                BANK_CODE,
                BANK_NAME
            )

            WITHHOLDING_CODE = "2.1.02.04"
            WITHHOLDING_NAME = "Impuesto de renta por pagar"
            SURVEYOR_DEDUCTION_CODE = "2.1.02.09"
            SURVEYOR_DEDUCTION_NAME = "Deducciones a surveyors del exterior por pagar"

            # El IVA de compras debe existir para que el asiento ITP balancee:
            # Debe gasto + IVA credito fiscal / Haber CxP.
            _ensure_account(IVA_CF_CODE, IVA_CF_NAME, "ASSET", "DEBIT", "1.1.13")
            _ensure_account(WITHHOLDING_CODE, WITHHOLDING_NAME, "LIABILITY", "CREDIT", "2.1.02")
            _ensure_account(SURVEYOR_DEDUCTION_CODE, SURVEYOR_DEDUCTION_NAME, "LIABILITY", "CREDIT", "2.1.02")

            def _first_existing(candidates):
                for code, name in candidates:
                    if _account_exists(code):
                        return code, name
                return EXP_PROF_CODE, EXP_PROF_NAME

            def _pick_itp_expense_account():
                text = " ".join([
                    payee_name,
                    payee_type,
                    obligation_type,
                    str(ob.get("reference") or ""),
                    str(ob.get("notes") or ""),
                ]).lower()

                if obligation_type == "SURVEYOR_FEE" or payee_type == "SURVEYOR":
                    return _first_existing([(EXP_PROF_CODE, EXP_PROF_NAME)])

                if "CARD_PROCESSING" in obligation_type:
                    return _first_existing([(EXP_OTHER_CODE, EXP_OTHER_NAME), (EXP_PROF_CODE, EXP_PROF_NAME)])

                if any(word in text for word in ("delta", "servicentro", "gasolin", "combustible", "petroleo", "petróleo", "estacion de servicio")):
                    return _first_existing([(EXP_FUEL_CODE, EXP_FUEL_NAME), (EXP_OTHER_CODE, EXP_OTHER_NAME)])

                if any(word in text for word in ("prime properties", "alquiler", "rent", "arrend")):
                    return _first_existing([(EXP_RENT_CODE, EXP_RENT_NAME), (EXP_OTHER_CODE, EXP_OTHER_NAME)])

                if any(word in text for word in ("limpieza", "clean")):
                    return _first_existing([(EXP_CLEANING_CODE, EXP_CLEANING_NAME), (EXP_PROF_CODE, EXP_PROF_NAME)])

                if any(word in text for word in ("vigilancia", "security")):
                    return _first_existing([(EXP_SECURITY_CODE, EXP_SECURITY_NAME), (EXP_PROF_CODE, EXP_PROF_NAME)])

                if any(word in text for word in ("contador", "contable", "accounting")):
                    return _first_existing([(EXP_ACCOUNTING_CODE, EXP_ACCOUNTING_NAME), (EXP_PROF_CODE, EXP_PROF_NAME)])

                if any(word in text for word in ("ferreteria", "ferretería", "epa", "office", "suministro", "material")):
                    return _first_existing([(EXP_SUPPLIES_CODE, EXP_SUPPLIES_NAME), (EXP_OTHER_CODE, EXP_OTHER_NAME)])

                return _first_existing([(EXP_PROF_CODE, EXP_PROF_NAME), (EXP_OTHER_CODE, EXP_OTHER_NAME)])

            # Elegir gasto según tipo/proveedor sin tocar cuentas de salarios.
            expense_account, expense_name = _pick_itp_expense_account()


            # Validar cuentas críticas existentes (NO inventar)
            # - Gastos y AP deben existir sí o sí
            if not _account_exists(expense_account):
                raise Exception(f"Cuenta de gasto no existe en accounting_ledger: {expense_account}")

            if not _account_exists(AP_CODE):
                raise Exception(f"Cuenta AP no existe en accounting_ledger: {AP_CODE}")

            # IVA es opcional, pero solo si existe en COA
            iva_account_ok = (iva > 0 and _account_exists(IVA_CF_CODE))

            # Banco solo se usa en el asiento de pago
            bank_account_ok = _account_exists(BANK_CODE)


            # ============================================================
            # A) ASIENTO GASTO vs CxP  (origin='ITP')
            # ============================================================
            detail_text = f"From ITP {payee_name}"

            # Signos contables (credit note invierte)
            expense_debit = 0 if is_credit_note else subtotal
            expense_credit = subtotal if is_credit_note else 0

            iva_debit = 0 if is_credit_note else iva
            iva_credit = iva if is_credit_note else 0

            ap_debit = calc_total if is_credit_note else 0
            ap_credit = 0 if is_credit_note else calc_total

            itp_entry_id = _upsert_entry(
                origin="ITP",
                origin_id=obligation_id,
                entry_date=issue_date,
                period=period,
                description=detail_text
            )

            # 🔥 Blindado: siempre recrear líneas para evitar residuos
            cur.execute("""
                DELETE FROM accounting_lines
                WHERE entry_id = %s
            """, (itp_entry_id,))

            # Gasto
            _insert_line(
                entry_id=itp_entry_id,
                code=expense_account,
                name=expense_name,
                debit=expense_debit,
                credit=expense_credit,
                desc=detail_text
            )

            # IVA crédito fiscal (solo si aplica y existe en COA)
            if iva_account_ok:
                _insert_line(
                    entry_id=itp_entry_id,
                    code=IVA_CF_CODE,
                    name=IVA_CF_NAME,
                    debit=iva_debit,
                    credit=iva_credit,
                    desc=detail_text
                )

            # CxP
            _insert_line(
                entry_id=itp_entry_id,
                code=AP_CODE,
                name=AP_NAME,
                debit=ap_debit,
                credit=ap_credit,
                desc=detail_text
            )


            # ============================================================
            # B) ASIENTO DE PAGO (origin='ITP_PAYMENT')
            # NO aplica para CREDIT NOTES
            # ============================================================
            if status == "PAID" and balance_crc == 0 and not is_credit_note and not ob.get("paid_with_card"):

                payment_date = _to_date(ob.get("last_payment_date")) or issue_date
                if payment_date > today:
                    _delete_future_system_entries(obligation_id, "ITP_PAYMENT")
                    continue
                payment_period = payment_date.strftime("%Y-%m")
                payment_detail = f"From ITP Payment done to {payee_name}"

                if not bank_account_ok:
                    raise Exception(f"Cuenta bancaria no existe en accounting_ledger: {BANK_CODE}")

                pay_entry_id = _upsert_entry(
                    origin="ITP_PAYMENT",
                    origin_id=obligation_id,
                    entry_date=payment_date,
                    period=payment_period,
                    description=payment_detail
                )

                # 🔥 Blindado: siempre recrear líneas
                cur.execute("""
                    DELETE FROM accounting_lines
                    WHERE entry_id = %s
                """, (pay_entry_id,))

                # Dr AP
                _insert_line(
                    entry_id=pay_entry_id,
                    code=AP_CODE,
                    name=AP_NAME,
                    debit=calc_total,
                    credit=0,
                    desc=payment_detail
                )

                settlement = external_surveyor_settlement(
                    cur,
                    total_raw,
                    payee_name=payee_name,
                    fallback_country=current_country,
                    payee_type=payee_type,
                    obligation_type=obligation_type,
                )
                if settlement["applies"]:
                    if currency == "USD":
                        withholding_crc = round(float(settlement["withholding"]) * tc, 2)
                        deduction_crc = round(float(settlement["deduction"]) * tc, 2)
                        bank_payment_crc = max(round(calc_total - withholding_crc - deduction_crc, 2), 0)
                    else:
                        withholding_crc = round(calc_total * 0.25, 2)
                        deduction_crc = min(round(25.0 * tc, 2), max(round(calc_total - withholding_crc, 2), 0))
                        bank_payment_crc = max(round(calc_total - withholding_crc - deduction_crc, 2), 0)
                else:
                    withholding_crc = 0
                    deduction_crc = 0
                    bank_payment_crc = calc_total

                if withholding_crc > 0:
                    _insert_line(
                        entry_id=pay_entry_id,
                        code=WITHHOLDING_CODE,
                        name=WITHHOLDING_NAME,
                        debit=0,
                        credit=withholding_crc,
                        desc=f"Retencion 25% - {payment_detail}"
                    )

                if deduction_crc > 0:
                    _insert_line(
                        entry_id=pay_entry_id,
                        code=SURVEYOR_DEDUCTION_CODE,
                        name=SURVEYOR_DEDUCTION_NAME,
                        debit=0,
                        credit=deduction_crc,
                        desc=f"Deduccion transferencia exterior - {payment_detail}"
                    )

                # Cr Bancos
                _insert_line(
                    entry_id=pay_entry_id,
                    code=BANK_CODE,
                    name=BANK_NAME,
                    debit=0,
                    credit=bank_payment_crc,
                    desc=payment_detail
                )


        _apply_current_fiscal_classification(conn)
        conn.commit()

    except Exception as e:

        conn.rollback()
        raise Exception(f"sync_itp_to_accounting error: {str(e)}")

    finally:
        cur.close()


def _sync_payroll_to_accounting_legacy(conn):
    """
    Sincroniza payroll_runs → accounting_entries / accounting_lines
    Usa salario_bruto como gasto total de salarios
    ERP-SOM BLINDADO (COA JERÁRQUICO)
    """

    from psycopg2.extras import RealDictCursor
    from datetime import date, datetime

    if not conn:
        raise Exception("DB connection is required")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # ============================================================
        # HELPERS
        # ============================================================
        def _normalize_date(value):
            if not value:
                return date.today()
            if isinstance(value, datetime):
                return value.date()
            return value

        def _account_exists(code: str) -> bool:
            cur.execute("""
                SELECT 1
                FROM accounting_ledger
                WHERE account_code = %s
                  AND active = TRUE
                LIMIT 1
            """, (code,))
            return cur.fetchone() is not None


        # ============================================================
        # CUENTAS CONTABLES (COA JERÁRQUICO)
        # ============================================================
        SALARY_EXP_CODE = "5.1.01"
        SALARY_EXP_NAME = "Gastos por sueldos y salarios"

        SALARY_PAYABLE_CODE = "2.1.03.01"
        SALARY_PAYABLE_NAME = "Salarios por pagar"

        BANK_CODE = "1.1.02"
        BANK_NAME = "Bancos"


        # Validar cuentas críticas
        if not _account_exists(SALARY_EXP_CODE):
            raise Exception(f"Cuenta no existe en COA: {SALARY_EXP_CODE}")

        if not _account_exists(SALARY_PAYABLE_CODE):
            raise Exception(f"Cuenta no existe en COA: {SALARY_PAYABLE_CODE}")

        if not _account_exists(BANK_CODE):
            raise Exception(f"Cuenta no existe en COA: {BANK_CODE}")


        # ============================================================
        # TRAER RUNS
        # ============================================================
        cur.execute("""
            SELECT
                id,
                usuario,
                year,
                month,
                salario_bruto,
                creado_en
            FROM payroll_runs
            ORDER BY id
        """)

        runs = cur.fetchall() or []


        # ============================================================
        # PROCESAR
        # ============================================================
        for p in runs:

            payroll_id = p.get("id")
            salario = float(p.get("salario_bruto") or 0)

            if salario <= 0:
                continue

            fecha = _normalize_date(p.get("creado_en"))

            period = f"{p['year']}-{int(p['month']):02d}"

            detail = f"Payroll {p.get('usuario')} {period}"


            # ======================================================
            # 🔒 EVITAR DUPLICADO ASIENTO 1
            # ======================================================
            cur.execute("""
                SELECT id
                FROM accounting_entries
                WHERE origin = 'PAYROLL'
                  AND origin_id = %s
                  AND period = %s
                LIMIT 1
            """, (payroll_id, period))

            payroll_entry = cur.fetchone()


            # ======================================================
            # ASIENTO 1
            # GASTO SALARIOS vs SALARIOS POR PAGAR
            # ======================================================
            if not payroll_entry:

                from services.accounting_auto import create_accounting_entry

                lines = [
                    {
                        "account_code": SALARY_EXP_CODE,
                        "account_name": SALARY_EXP_NAME,
                        "debit": salario,
                        "credit": 0,
                        "line_description": detail
                    },
                    {
                        "account_code": SALARY_PAYABLE_CODE,
                        "account_name": SALARY_PAYABLE_NAME,
                        "debit": 0,
                        "credit": salario,
                        "line_description": detail
                    }
                ]

                create_accounting_entry(
                    conn=conn,
                    entry_date=fecha,
                    period=period,
                    description=detail,
                    origin="PAYROLL",
                    origin_id=payroll_id,
                    lines=lines
                )


            # ======================================================
            # 🔒 EVITAR DUPLICADO ASIENTO 2
            # ======================================================
            cur.execute("""
                SELECT id
                FROM accounting_entries
                WHERE origin = 'PAYROLL_PAYMENT'
                  AND origin_id = %s
                  AND period = %s
                LIMIT 1
            """, (payroll_id, period))

            payment_entry = cur.fetchone()


            # ======================================================
            # ASIENTO 2
            # SALARIOS POR PAGAR vs BANCOS
            # ======================================================
            if not payment_entry:

                from services.accounting_auto import create_accounting_entry

                pago_lines = [
                    {
                        "account_code": SALARY_PAYABLE_CODE,
                        "account_name": SALARY_PAYABLE_NAME,
                        "debit": salario,
                        "credit": 0,
                        "line_description": f"Pago salarios {detail}"
                    },
                    {
                        "account_code": BANK_CODE,
                        "account_name": BANK_NAME,
                        "debit": 0,
                        "credit": salario,
                        "line_description": f"Pago salarios {detail}"
                    }
                ]

                create_accounting_entry(
                    conn=conn,
                    entry_date=fecha,
                    period=period,
                    description=f"Pago salarios {detail}",
                    origin="PAYROLL_PAYMENT",
                    origin_id=payroll_id,
                    lines=pago_lines
                )


        conn.commit()

    except Exception as e:

        conn.rollback()
        raise Exception(f"sync_payroll_to_accounting error: {str(e)}")

    finally:
        cur.close()
