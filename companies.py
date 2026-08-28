COMPANIES = [
    {
        "code": "MSL-CR",
        "name": "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL",
        "legal_name": "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL",
        "trade_name": "MSL",
        "tax_id": "",
        "economic_activity": "",
        "phone": "",
        "billing_email": "",
        "email": "",
        "country": "Costa Rica",
        "province": "",
        "canton": "",
        "district": "",
        "address": "",
        "notes": "",
    },
    {
        "code": "MCI-CR",
        "name": "MSL MARINE CLAIMS RISK & INTELLIGENCE",
        "legal_name": "MSL MARINE CLAIMS RISK & INTELLIGENCE",
        "trade_name": "MSL MARINE CLAIMS",
        "tax_id": "3 101 969 147",
        "economic_activity": "7020.0",
        "phone": "",
        "billing_email": "facturacion.fe@xtravon.com",
        "email": "facturacion.fe@xtravon.com",
        "country": "Costa Rica",
        "province": "Alajuela",
        "canton": "Alajuela",
        "district": "Rio Segundo",
        "address": "Alajuela, Alajuela, Rio Segundo. Oficentro Plaza Aeropuerto local G-14",
        "notes": "",
    },
]

DEFAULT_COMPANY_CODE = "MSL-CR"


def company_by_code(code):
    normalized = str(code or "").strip().upper()
    for company in COMPANIES:
        if company["code"] == normalized:
            return dict(company)
    return dict(COMPANIES[0])


def company_by_label(label):
    text = str(label or "").strip()
    for company in COMPANIES:
        if text == company_label(company):
            return dict(company)
    return dict(COMPANIES[0])


def company_label(company):
    return f"{company['code']} | {company['name']}"


def company_labels():
    return [company_label(company) for company in COMPANIES]
