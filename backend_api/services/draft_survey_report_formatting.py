"""Presentation dates and field-safe replacements for Draft Survey reports."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def refresh_draft_difference(data):
    result = dict(data or {})
    def number(value):
        text = str(value or '').strip().replace(' ', '').replace('\u00a0', '')
        if ',' in text and '.' in text:
            text = text.replace('.', '').replace(',', '.') if text.rfind(',') > text.rfind('.') else text.replace(',', '')
        else:
            text = text.replace(',', '.')
        return Decimal(text)
    try:
        draft = number(result.get('word_draft_figures'))
        bl = number(result.get('word_bl_figures'))
        if draft.is_finite() and bl.is_finite():
            diff = draft - bl
            result['word_difference'] = f'{diff:,.2f}'
            result['word_percentage'] = f'{(diff / bl * 100) if bl else Decimal(0):.4f}'
    except (InvalidOperation, ValueError):
        pass
    return result


def report_date(data):
    for key in ('word_final_draft_date', 'word_final_draft',
                'word_completed_date', 'word_completed'):
        value = data.get(key)
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = re.sub(r'\s+LT\.?$', '', str(value or '').strip(), flags=re.I)
        if not text:
            continue
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00')).date()
        except ValueError:
            pass
        for fmt in ('%d/%m/%Y', '%d/%m/%Y %H:%M', '%d-%m-%Y',
                    '%d-%m-%Y %H:%M', '%b %d %Y', '%b %d %Y %H:%M',
                    '%B %d, %Y', '%B %d, %Y %H:%M'):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def report_place_line(data):
    port = str(data.get('word_port') or '').strip()
    country = str(data.get('word_country') or '').strip()
    value = report_date(data)
    place = ' - '.join(part for part in (port, country) if part)
    if value:
        months = ('January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December')
        formatted = f'{months[value.month - 1]} {value.day:02d}, {value.year}'
        return f'{place}, {formatted}' if place else formatted
    return place


def replace_placeholders(paragraph, values):
    """Replace only placeholder runs; never redistribute cached PAGE field text."""
    runs = paragraph.runs
    text = ''.join(run.text for run in runs)
    for match in reversed(list(re.finditer(r'\{[^{}]+\}', text))):
        start, end = match.span()
        value = str(values.get(match.group(), '') or '')
        offset = 0
        inserted = False
        for run in runs:
            original = run.text
            right = offset + len(original)
            if right > start and offset < end:
                left_part = original[:max(0, start - offset)]
                right_part = original[max(0, end - offset):]
                run.text = left_part + (value if not inserted else '') + right_part
                inserted = True
            offset = right
