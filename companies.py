COMPANIES = [
    {
        "code": "MSL-CR",
        "name": "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL",
    },
    {
        "code": "MMS-CR",
        "name": "MMS MARITIME MASTER SURVEYORS SRL",
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
