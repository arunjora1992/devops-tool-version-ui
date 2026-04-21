import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def _row_data(tools: list[dict]) -> list[list[str]]:
    rows = []
    for t in tools:
        latest = t.get("latest") or {}
        prev = t.get("previous") or {}
        rows.append([
            t.get("name", ""),
            t.get("category", ""),
            latest.get("version", "N/A"),
            latest.get("date", ""),
            prev.get("version", "N/A"),
            prev.get("date", ""),
            t.get("status", ""),
        ])
    return rows


def generate_csv(data: dict) -> bytes:
    tools = data.get("tools", [])
    fetched_at = data.get("fetched_at", "")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# DevOps Tools Version Dashboard"])
    writer.writerow([f"# Generated: {fetched_at}"])
    writer.writerow([])
    writer.writerow(["Tool", "Category", "Latest Version", "Latest Release Date",
                     "N-1 Version", "N-1 Release Date", "Status"])
    for row in _row_data(tools):
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def generate_pdf(data: dict) -> bytes:
    tools = data.get("tools", [])
    fetched_at = data.get("fetched_at", "")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="DevOps Tools Version Dashboard",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1e293b"),
        alignment=TA_LEFT,
    )
    sub_style = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#64748b"),
    )
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )

    HEADER_BG = colors.HexColor("#1e293b")
    ALT_ROW = colors.HexColor("#f8fafc")
    OK_COLOR = colors.HexColor("#dcfce7")
    ERR_COLOR = colors.HexColor("#fee2e2")

    header = ["Tool", "Category", "Latest Version", "Latest Date", "N-1 Version", "N-1 Date", "Status"]
    table_data = [header]
    row_colors = []

    for i, row in enumerate(_row_data(tools), start=1):
        table_data.append([Paragraph(str(c), cell_style) for c in row])
        if row[6] == "error":
            row_colors.append(("BACKGROUND", (0, i), (-1, i), ERR_COLOR))
        elif i % 2 == 0:
            row_colors.append(("BACKGROUND", (0, i), (-1, i), ALT_ROW))

    col_widths = [55 * mm, 42 * mm, 38 * mm, 28 * mm, 38 * mm, 28 * mm, 20 * mm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    base_style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [colors.white, ALT_ROW]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    table.setStyle(TableStyle(base_style + row_colors))

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    elements = [
        Paragraph("DevOps Tools Version Dashboard", title_style),
        Paragraph(f"Generated: {now_str}  |  Data fetched: {fetched_at}", sub_style),
        Spacer(1, 6 * mm),
        table,
    ]
    doc.build(elements)
    return buffer.getvalue()
