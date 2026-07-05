from datetime import date, datetime


LONG_DATE_FORMAT = "%b %d %Y"
DB_DATE_FORMAT = "%Y-%m-%d"
DATETIME_DB_FORMAT = "%Y-%m-%d %H:%M"


def parse_informe_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = " ".join(text.replace(",", " ").split())
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%b %d %Y",
        "%B %d %Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )

    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text[:19].replace(" ", "T")).date()
    except ValueError:
        return None


def to_long_english_date(value):
    parsed = parse_informe_date(value)
    if parsed:
        return parsed.strftime(LONG_DATE_FORMAT)
    return "" if value in (None, "") else str(value)


def to_db_date(value):
    parsed = parse_informe_date(value)
    if parsed:
        return parsed.strftime(DB_DATE_FORMAT)
    return "" if value in (None, "") else str(value)


def to_db_datetime(date_value, hour_value="00", minute_value="00"):
    parsed = parse_informe_date(date_value)
    if not parsed:
        return ""

    try:
        hour = int(str(hour_value or "0").strip())
        minute = int(str(minute_value or "0").strip())
    except ValueError:
        return ""

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return ""

    return f"{parsed.strftime(DB_DATE_FORMAT)} {hour:02d}:{minute:02d}"


def format_informe_row_dates(row, columns):
    formatted = dict(row or {})
    for column in columns:
        key = str(column).lower()
        if (
            key == "date"
            or key.endswith("_date")
            or key.startswith("date_")
            or key.startswith("fecha_")
            or key in ("created_at", "updated_at", "place_date", "report_date")
        ):
            formatted[column] = to_long_english_date(formatted.get(column))
    return formatted
