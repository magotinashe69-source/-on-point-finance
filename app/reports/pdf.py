"""Branded PDF report (ReportLab — pure Python, no system libraries)."""

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)

from app.money import cents_to_str

NAVY = colors.HexColor("#16264d")
GOLD = colors.HexColor("#c9a227")
INCOME_GREEN = colors.HexColor("#1b7e3c")
EXPENSE_RED = colors.HexColor("#b3261e")
ROW_ALT = colors.HexColor("#f4f6fa")


def build_pdf(start_day: date, end_day: date, entries, totals: dict, breakdown: dict) -> bytes:
    """Render the report to PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title="On Point Finance Report", author="On Point Educational Centre",
    )
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, leading=11)
    title = ParagraphStyle("title", parent=styles["Title"], textColor=colors.white,
                           fontSize=16, leading=19, alignment=0, spaceAfter=0)
    motto = ParagraphStyle("motto", textColor=GOLD, fontSize=10, leading=12)

    elems = []

    # --- Navy header bar with gold accent line ---
    header = Table(
        [[Paragraph("On Point Educational Centre", title)],
         [Paragraph("Quality Beyond Measure", motto)]],
        colWidths=[doc.width],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, 1), (0, 1), 12),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 0),
    ]))
    elems.append(header)
    elems.append(HRFlowable(width="100%", thickness=3, color=GOLD, spaceBefore=0, spaceAfter=12))

    # --- Range heading ---
    elems.append(Paragraph(
        f"Financial record: {start_day.strftime('%d %b %Y')} &ndash; {end_day.strftime('%d %b %Y')}",
        styles["Heading2"],
    ))
    elems.append(Spacer(1, 6))

    # --- Entries table ---
    data = [["Type", "Description", "Category", "Method", "Amount"]]
    for e in entries:
        data.append([
            e.type.capitalize(),
            Paragraph(e.description or "", cell),
            e.category.name,
            e.payment_method,
            cents_to_str(e.amount_cents),
        ])
    if not entries:
        data.append([Paragraph("No entries in this range.", cell), "", "", "", ""])

    widths = [w * doc.width for w in (0.12, 0.36, 0.20, 0.16, 0.16)]
    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6deec")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Green/red type cell + zebra striping for the data rows.
    for i, e in enumerate(entries, start=1):
        style.append(("TEXTCOLOR", (0, i), (0, i), INCOME_GREEN if e.type == "income" else EXPENSE_RED))
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    table.setStyle(TableStyle(style))
    elems.append(table)
    elems.append(Spacer(1, 12))

    # --- Totals ---
    totals_tbl = Table(
        [["Income", cents_to_str(totals["income_cents"])],
         ["Expenses", cents_to_str(totals["expense_cents"])],
         ["Balance", cents_to_str(totals["balance_cents"])]],
        colWidths=[doc.width * 0.30, doc.width * 0.25],
        hAlign="RIGHT",
    )
    totals_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (0, 0), INCOME_GREEN),
        ("TEXTCOLOR", (0, 1), (0, 1), EXPENSE_RED),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEABOVE", (0, 2), (-1, 2), 0.6, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(totals_tbl)
    elems.append(Spacer(1, 16))

    # --- Summary by category ---
    elems.append(Paragraph("Summary by category", styles["Heading3"]))
    elems.append(_breakdown_table("Income", breakdown["income"], breakdown["income_subtotal_cents"],
                                  INCOME_GREEN, doc.width))
    elems.append(Spacer(1, 8))
    elems.append(_breakdown_table("Expenses", breakdown["expense"], breakdown["expense_subtotal_cents"],
                                  EXPENSE_RED, doc.width))

    doc.build(elems)
    return buf.getvalue()


def _breakdown_table(heading: str, rows, subtotal_cents: int, accent, width) -> Table:
    data = [[heading, ""]]
    if rows:
        for name, cents in rows:
            data.append([name, cents_to_str(cents)])
    else:
        data.append(["(none)", cents_to_str(0)])
    data.append(["Subtotal", cents_to_str(subtotal_cents)])

    tbl = Table(data, colWidths=[width * 0.55, width * 0.25], hAlign="LEFT")
    last = len(data) - 1
    tbl.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
        ("LINEABOVE", (0, last), (-1, last), 0.5, colors.HexColor("#d6deec")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e3e7ef")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl
