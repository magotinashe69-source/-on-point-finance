"""Reports routes: on-screen range summary + PDF/Excel downloads."""

from datetime import date, datetime

from flask import render_template, request, Response
from flask_login import login_required

from app.main.services import compute_totals
from app.reports import bp
from app.reports.services import (
    transactions_in_range, category_breakdown, month_range,
)
from app.reports.pdf import build_pdf
from app.reports.excel import build_excel

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _parse_day(raw: str | None, default: date) -> date:
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    return default


def _range_from_args() -> tuple[date, date]:
    """Resolve the start/end range from query args, defaulting to this month."""
    default_start, default_end = month_range(date.today())
    start = _parse_day(request.args.get("start"), default_start)
    end = _parse_day(request.args.get("end"), default_end)
    if end < start:
        start, end = end, start
    return start, end


def _gather(start: date, end: date):
    entries = transactions_in_range(start, end)
    totals = compute_totals(entries)
    breakdown = category_breakdown(start, end)
    return entries, totals, breakdown


@bp.route("/")
@login_required
def index():
    start, end = _range_from_args()
    entries, totals, breakdown = _gather(start, end)
    return render_template(
        "reports/index.html",
        start=start, end=end, entries=entries, totals=totals, breakdown=breakdown,
    )


@bp.route("/pdf")
@login_required
def pdf():
    start, end = _range_from_args()
    entries, totals, breakdown = _gather(start, end)
    data = build_pdf(start, end, entries, totals, breakdown)
    filename = f"on-point-record-{start.isoformat()}_to_{end.isoformat()}.pdf"
    return Response(
        data, mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.route("/excel")
@login_required
def excel():
    start, end = _range_from_args()
    entries, totals, breakdown = _gather(start, end)
    data = build_excel(start, end, entries, totals, breakdown)
    filename = f"on-point-record-{start.isoformat()}_to_{end.isoformat()}.xlsx"
    return Response(
        data, mimetype=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
