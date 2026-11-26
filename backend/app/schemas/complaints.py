"""
app/schemas/complaints.py
--------------------------------------------------------------------
Request/response models for the complaint-classification API.
--------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ComplaintRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=1000, description="Complaint text in English")

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v.strip()


class CategoryScore(BaseModel):
    category: str
    probability: float


class ComplaintResult(BaseModel):
    text: str
    category: str
    category_confidence: float
    priority: str  # "urgent" | "normal"
    priority_reason: str  # "model prediction" or "safety keyword: '...'"
    top_categories: list[CategoryScore]
    needs_review: bool = Field(..., description="True when confidence is low and a human should check")


class BatchComplaintRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("texts")
    @classmethod
    def no_blank_items(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip() for t in v]
        if any(len(t) < 3 for t in cleaned):
            raise ValueError("every complaint must have at least 3 characters")
        return cleaned


class BatchComplaintResponse(BaseModel):
    results: list[ComplaintResult]
    counts_by_category: dict[str, int]
    urgent_count: int
    needs_review_count: int


class ComplaintModelInfo(BaseModel):
    model: str
    language: str
    categories: list[str]
    priorities: list[str]
    n_train: int
    cv_accuracy: dict[str, float]
    review_threshold: float
    note: str
