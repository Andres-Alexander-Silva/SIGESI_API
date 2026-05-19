"""Helper to build single-sheet xlsx HttpResponses with openpyxl."""
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from django.http import HttpResponse
from openpyxl import Workbook


XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def render_xlsx(resource_name: str, columns: list[str], rows: Iterable[Iterable]) -> HttpResponse:
    """Build a single-sheet xlsx and return it as a download response.

    The filename is `<resource_name>_<YYYY-MM-DD>.xlsx`.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = resource_name[:31]  # Excel sheet name limit

    ws.append(columns)
    for row in rows:
        ws.append([_coerce_cell(v) for v in row])

    response = HttpResponse(content_type=XLSX_MIME)
    response['Content-Disposition'] = (
        f'attachment; filename="{resource_name}_{date.today().isoformat()}.xlsx"'
    )
    wb.save(response)
    return response


def _coerce_cell(value):
    """openpyxl handles str/int/float/datetime/date/Decimal natively.

    Datetimes must be tz-naive — Excel has no concept of timezones, and
    openpyxl raises on aware datetimes. We convert to UTC-naive on the fly.
    Anything else (model instances, querysets, lists) is stringified so the
    workbook write never fails on an unexpected type.
    """
    if value is None:
        return ''
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return value
    if isinstance(value, (str, int, float, Decimal, date, bool)):
        return value
    return str(value)
