"""
app/api/reports.py
--------------------------------------------------------------------
REST API for downloadable reports:
  GET /api/v1/reports/csv    - daily vehicle counts as CSV
  GET /api/v1/reports/excel  - multi-sheet Excel workbook
  GET /api/v1/reports/pdf    - formatted PDF summary report
--------------------------------------------------------------------
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.services.analytics_service import build_summary
from app.services.report_generator import generate_csv, generate_excel, generate_pdf

router = APIRouter(prefix="/reports", tags=["Reports"])


def _timestamped_filename(prefix: str, ext: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}.{ext}"


@router.get("/csv")
async def download_csv_report(
    camera_id: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> StreamingResponse:
    summary = await build_summary(db, camera_id=camera_id, days=days)
    csv_bytes = generate_csv(summary)
    filename = _timestamped_filename("traffic_report", "csv")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/excel")
async def download_excel_report(
    camera_id: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> StreamingResponse:
    summary = await build_summary(db, camera_id=camera_id, days=days)
    excel_bytes = generate_excel(summary)
    filename = _timestamped_filename("traffic_report", "xlsx")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
async def download_pdf_report(
    camera_id: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> StreamingResponse:
    summary = await build_summary(db, camera_id=camera_id, days=days)
    pdf_bytes = generate_pdf(summary)
    filename = _timestamped_filename("traffic_report", "pdf")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
