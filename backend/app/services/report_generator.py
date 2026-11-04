"""
app/services/report_generator.py
--------------------------------------------------------------------
Generates downloadable reports from analytics data: CSV, Excel
(via pandas/openpyxl), and PDF (via reportlab). Each function
returns raw bytes so the API layer can stream them directly without
touching the filesystem.
--------------------------------------------------------------------
"""

from __future__ import annotations

import io

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.analytics import AnalyticsSummary


def _summary_to_dataframe(summary: AnalyticsSummary) -> pd.DataFrame:
    """Flattens the daily-count series into a DataFrame -- the most useful
    single table for a spreadsheet export."""
    return pd.DataFrame([{"date": d.date, "vehicle_count": d.count} for d in summary.daily_counts])


def generate_csv(summary: AnalyticsSummary) -> bytes:
    """CSV export of the daily vehicle counts."""
    df = _summary_to_dataframe(summary)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def generate_excel(summary: AnalyticsSummary) -> bytes:
    """
    Excel export with four sheets: Daily Counts, Hourly Counts,
    Class Breakdown, Violations -- gives a fuller picture than the
    single-table CSV.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _summary_to_dataframe(summary).to_excel(writer, sheet_name="Daily Counts", index=False)

        pd.DataFrame([{"hour": h.hour, "count": h.count} for h in summary.hourly_counts]).to_excel(
            writer, sheet_name="Hourly Counts", index=False
        )

        pd.DataFrame([
            {"class": c.class_name, "count": c.count, "percentage": c.percentage}
            for c in summary.class_breakdown
        ]).to_excel(writer, sheet_name="Class Breakdown", index=False)

        pd.DataFrame([
            {"violation_type": k, "count": v} for k, v in summary.violations_by_type.items()
        ]).to_excel(writer, sheet_name="Violations", index=False)

    return buffer.getvalue()


def generate_pdf(summary: AnalyticsSummary) -> bytes:
    """A formatted PDF report summarizing the analytics period."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Traffic Monitoring Report", styles["Title"]))
    elements.append(Paragraph(
        f"Camera: {summary.camera_id or 'All Cameras'} | "
        f"Period: {summary.period_start} to {summary.period_end}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 16))

    elements.append(Paragraph(f"<b>Total Vehicles:</b> {summary.total_vehicles}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Total Violations:</b> {summary.total_violations}", styles["Normal"]))
    if summary.peak_hour:
        elements.append(Paragraph(
            f"<b>Peak Hour:</b> {summary.peak_hour.hour} ({summary.peak_hour.count} vehicles)",
            styles["Normal"],
        ))
    elements.append(Spacer(1, 16))

    if summary.class_breakdown:
        elements.append(Paragraph("Vehicle Class Distribution", styles["Heading2"]))
        table_data = [["Class", "Count", "Percentage"]] + [
            [c.class_name.replace("_", " ").title(), str(c.count), f"{c.percentage}%"]
            for c in summary.class_breakdown
        ]
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 16))

    if summary.violations_by_type:
        elements.append(Paragraph("Violations by Type", styles["Heading2"]))
        v_data = [["Violation Type", "Count"]] + [
            [k.replace("_", " ").title(), str(v)] for k, v in summary.violations_by_type.items()
        ]
        v_table = Table(v_data, hAlign="LEFT")
        v_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(v_table)

    doc.build(elements)
    return buffer.getvalue()
