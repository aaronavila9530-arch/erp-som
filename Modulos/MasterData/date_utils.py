from datetime import date, datetime


LONG_DATE_FORMAT = "%b %d %Y"
DB_DATE_FORMAT = "%Y-%m-%d"


def parse_master_date(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    normalized = " ".join(text.replace(",", " ").split())
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt.replace(",", "")).date()
        except Exception:
            continue

    try:
        return datetime.fromisoformat(text[:10]).date()
    except Exception:
        return None


def to_long_english_date(value):
    parsed = parse_master_date(value)
    return parsed.strftime(LONG_DATE_FORMAT) if parsed else ("" if value is None else str(value).strip())


def to_db_date(value):
    parsed = parse_master_date(value)
    return parsed.strftime(DB_DATE_FORMAT) if parsed else None
