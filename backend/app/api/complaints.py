"""
app/api/complaints.py
--------------------------------------------------------------------
REST API for the NLP complaint classifier (English text only):
  POST /api/v1/complaints/classify        - classify one complaint
  POST /api/v1/complaints/classify-batch  - classify up to 100 complaints
  GET  /api/v1/complaints/samples         - unseen demo complaints for the UI
  GET  /api/v1/complaints/model-info      - model description + accuracy

These endpoints are plain `def` (not async) on purpose: the first call
trains the small model (about a second), and FastAPI runs sync endpoints
in a worker thread so that never blocks the event loop.
--------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter

from app.nlp.complaint_classifier import ComplaintPrediction, get_classifier
from app.nlp.complaint_data import DEMO_COMPLAINTS
from app.schemas.complaints import (
    BatchComplaintRequest,
    BatchComplaintResponse,
    CategoryScore,
    ComplaintModelInfo,
    ComplaintRequest,
    ComplaintResult,
)

router = APIRouter(prefix="/complaints", tags=["Complaints (NLP)"])


def _to_result(p: ComplaintPrediction) -> ComplaintResult:
    return ComplaintResult(
        text=p.text,
        category=p.category,
        category_confidence=p.category_confidence,
        priority=p.priority,
        priority_reason=p.priority_reason,
        top_categories=[CategoryScore(category=c, probability=prob) for c, prob in p.top_categories],
        needs_review=p.needs_review,
    )


@router.post("/classify", response_model=ComplaintResult)
def classify_complaint(payload: ComplaintRequest) -> ComplaintResult:
    """Classify one complaint into a category and a priority."""
    return _to_result(get_classifier().predict(payload.text))


@router.post("/classify-batch", response_model=BatchComplaintResponse)
def classify_complaints(payload: BatchComplaintRequest) -> BatchComplaintResponse:
    """Classify many complaints at once and return per-category totals."""
    classifier = get_classifier()
    results = [_to_result(classifier.predict(t)) for t in payload.texts]
    return BatchComplaintResponse(
        results=results,
        counts_by_category=dict(Counter(r.category for r in results)),
        urgent_count=sum(r.priority == "urgent" for r in results),
        needs_review_count=sum(r.needs_review for r in results),
    )


@router.get("/samples", response_model=list[str])
def get_sample_complaints() -> list[str]:
    """Demo complaints that are NOT part of the training data."""
    return DEMO_COMPLAINTS


@router.get("/model-info", response_model=ComplaintModelInfo)
def get_model_info() -> ComplaintModelInfo:
    return ComplaintModelInfo(**get_classifier().info())
