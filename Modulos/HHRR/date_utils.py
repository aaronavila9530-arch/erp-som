from datetime import date, datetime


LONG_DATE_FORMAT = "%b %d %Y"
DB_DATE_FORMAT = "%Y-%m-%d"


def parse_hhrr_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text or text in ("None", "-"):
        return None

    normalized = " ".join(text.replace(",", " ").split())

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%b %d %Y",
        "%B %d %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(normalized, fmt).date()
        except Exception:
            continue

    try:
        return datetime.fromisoformat(text[:19].replace(" ", "T")).date()
    except Exception:
        return None


def to_long_english_date(value):
    parsed = parse_hhrr_date(value)
    if not parsed:
        return "" if value in (None, "") else str(value)
    return parsed.strftime(LONG_DATE_FORMAT)


def to_db_date(value):
    parsed = parse_hhrr_date(value)
    if not parsed:
        return ""
    return parsed.strftime(DB_DATE_FORMAT)


def parse_hhrr_datetime(value):
    if isinstance(value, datetime):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    normalized = " ".join(text.replace(",", " ").split())

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%b %d %Y %H:%M",
        "%B %d %Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
    ):
        try:
            return datetime.strptime(normalized, fmt)
        except Exception:
            continue

    try:
        return datetime.fromisoformat(text[:19].replace(" ", "T"))
    except Exception:
        return None


def is_date_column(column):
    key = str(column or "").lower()
    return (
        key == "event_date"
        or key.startswith("fecha_")
        or key.endswith("_date")
        or key.endswith("_at")
    )
