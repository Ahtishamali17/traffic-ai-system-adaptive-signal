"""
Unit tests for app/services/report_generator.py using synthetic
AnalyticsSummary data (no live MongoDB needed).
"""

from app.schemas.analytics import AnalyticsSummary, ClassBreakdown, DailyCount, HourlyCount, PeakHour
from app.services.report_generator import generate_csv, generate_excel, generate_pdf

_SAMPLE_SUMMARY = AnalyticsSummary(
    camera_id="gate-1",
    period_start="2026-08-15 00:00",
    period_end="2026-08-22 00:00",
    total_vehicles=452,
    hourly_counts=[HourlyCount(hour="2026-08-22 08:00", count=40), HourlyCount(hour="2026-08-22 09:00", count=65)],
    daily_counts=[DailyCount(date="2026-08-21", count=210), DailyCount(date="2026-08-22", count=242)],
    class_breakdown=[
        ClassBreakdown(class_name="car", count=300, percentage=66.4),
        ClassBreakdown(class_name="truck", count=90, percentage=19.9),
        ClassBreakdown(class_name="motorcycle", count=62, percentage=13.7),
    ],
    peak_hour=PeakHour(hour="2026-08-22 09:00", count=65),
    total_violations=12,
    violations_by_type={"overspeed": 7, "wrong_direction": 5},
)


def test_generate_csv_produces_valid_bytes_with_header():
    data = generate_csv(_SAMPLE_SUMMARY)
    assert isinstance(data, bytes)
    text = data.decode("utf-8")
    assert "date" in text and "vehicle_count" in text
    assert "2026-08-22" in text


def test_generate_excel_produces_nonempty_xlsx_bytes():
    data = generate_excel(_SAMPLE_SUMMARY)
    assert isinstance(data, bytes)
    assert len(data) > 0
    # XLSX files are zip archives; magic number check
    assert data[:2] == b"PK"


def test_generate_pdf_produces_nonempty_pdf_bytes():
    data = generate_pdf(_SAMPLE_SUMMARY)
    assert isinstance(data, bytes)
    assert len(data) > 0
    assert data[:4] == b"%PDF"


def test_generate_pdf_handles_empty_summary_gracefully():
    empty_summary = AnalyticsSummary(
        camera_id=None, period_start="2026-08-01", period_end="2026-08-02",
        total_vehicles=0, hourly_counts=[], daily_counts=[], class_breakdown=[],
        peak_hour=None, total_violations=0, violations_by_type={},
    )
    data = generate_pdf(empty_summary)
    assert data[:4] == b"%PDF"
