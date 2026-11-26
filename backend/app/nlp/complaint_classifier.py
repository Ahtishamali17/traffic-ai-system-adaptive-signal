"""
app/nlp/complaint_classifier.py
--------------------------------------------------------------------
Classifies a citizen's traffic complaint (plain English text) into:
  - a CATEGORY  (traffic_congestion, accident, signal_fault,
                 illegal_parking, rash_driving, road_damage)
  - a PRIORITY  (urgent / normal)

Approach (classic, lightweight NLP -- trains in about a second on a
CPU, needs no GPU, no internet and no API key):
  * CATEGORY: TF-IDF features (word 1-2 grams + character 3-5 grams)
    feeding a Logistic Regression classifier.
  * PRIORITY: a hybrid. A small, explainable SAFETY-KEYWORD RULE marks a
    complaint urgent when it mentions things like injuries, bleeding,
    ambulance, fire, trapped people or an open manhole (negations such as
    "no injuries" / "nobody is hurt" are ignored). Otherwise a second
    Logistic Regression model decides. Priority from text alone is hard
    to learn from a small dataset, so the rule stops the model from
    ever downgrading an obvious emergency.

Honest limitations:
  - Trained on a small hand-written English demo set (complaint_data.py);
    it only knows these 6 topics and only English.
  - Text outside these topics still gets a label; `needs_review` marks
    low-confidence predictions so a human can check them.
  - cv_accuracy is measured on the same small demo set, and the safety
    keywords were chosen while looking at it, so the numbers are
    optimistic indicators, not real-world accuracy.
--------------------------------------------------------------------
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline

from app.nlp.complaint_data import CATEGORIES, get_training_rows

# Below this top-category probability the result is flagged for human review.
REVIEW_THRESHOLD = 0.35

# Words that signal danger to people. Checked after removing negated phrases.
_URGENT_PATTERN = re.compile(
    r"\b(injur\w*|hurt|bleed\w*|blood|unconscious|trapped|fatal|ambulance|emergency|fire|"
    r"overturned|drunk|manhole|sinkhole|child|children|danger\w*|wires?)\b"
)
# "no injuries", "nobody is hurt", "not dangerous" ... must NOT trigger the rule.
_NEGATION_PATTERN = re.compile(r"\b(no|nobody|not|without)\s+(\w+\s+){0,2}(injur\w*|hurt|bleed\w*|danger\w*)\b")


def find_safety_keyword(text: str) -> str | None:
    """Return the first safety keyword found (ignoring negated mentions), else None."""
    cleaned = _NEGATION_PATTERN.sub(" ", text.lower())
    match = _URGENT_PATTERN.search(cleaned)
    return match.group(0) if match else None


def _build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
    ])
    # liblinear: small, deterministic, and avoids scipy/lbfgs version warnings.
    clf = LogisticRegression(solver="liblinear", C=10.0, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


@dataclass
class ComplaintPrediction:
    text: str
    category: str
    category_confidence: float
    priority: str
    priority_reason: str
    top_categories: list[tuple[str, float]]
    needs_review: bool


class ComplaintClassifier:
    """Trains on construction (about a second) and predicts category + priority for new text."""

    def __init__(self) -> None:
        rows = get_training_rows()
        self._texts = [r[0] for r in rows]
        self._categories = [r[1] for r in rows]
        self._priorities = [r[2] for r in rows]

        self._category_model = _build_pipeline().fit(self._texts, self._categories)
        self._priority_model = _build_pipeline().fit(self._texts, self._priorities)
        self.n_train = len(rows)
        self.cv_accuracy = self._cross_validate()

    def _cross_validate(self) -> dict[str, float]:
        """5-fold stratified CV on the demo set (optimistic -- see module docstring)."""
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        n = len(self._texts)

        cat_pred = cross_val_predict(_build_pipeline(), self._texts, self._categories, cv=skf)
        pri_pred = cross_val_predict(_build_pipeline(), self._texts, self._priorities, cv=skf)
        hybrid = ["urgent" if find_safety_keyword(t) else p for t, p in zip(self._texts, pri_pred)]

        def acc(pred, truth):
            return round(sum(a == b for a, b in zip(pred, truth)) / n, 3)

        majority = max(self._priorities.count("normal"), self._priorities.count("urgent")) / n
        return {
            "category": acc(cat_pred, self._categories),
            "priority_model_only": acc(pri_pred, self._priorities),
            "priority_with_safety_rule": acc(hybrid, self._priorities),
            "priority_majority_baseline": round(majority, 3),
        }

    @staticmethod
    def _proba_dict(model: Pipeline, text: str) -> dict[str, float]:
        probs = model.predict_proba([text])[0]
        return {label: float(p) for label, p in zip(model.classes_, probs)}

    def predict(self, text: str) -> ComplaintPrediction:
        text = text.strip()

        cat_probs = self._proba_dict(self._category_model, text)
        ranked = sorted(cat_probs.items(), key=lambda kv: kv[1], reverse=True)
        category, category_conf = ranked[0]

        keyword = find_safety_keyword(text)
        if keyword:
            priority, reason = "urgent", f"safety keyword: '{keyword}'"
        else:
            pri_probs = self._proba_dict(self._priority_model, text)
            priority = max(pri_probs.items(), key=lambda kv: kv[1])[0]
            reason = "model prediction"

        return ComplaintPrediction(
            text=text,
            category=category,
            category_confidence=round(category_conf, 3),
            priority=priority,
            priority_reason=reason,
            top_categories=[(c, round(p, 3)) for c, p in ranked[:3]],
            needs_review=category_conf < REVIEW_THRESHOLD,
        )

    def info(self) -> dict:
        return {
            "model": "TF-IDF (word + character n-grams) + Logistic Regression; priority adds a safety-keyword rule",
            "language": "English",
            "categories": CATEGORIES,
            "priorities": ["urgent", "normal"],
            "n_train": self.n_train,
            "cv_accuracy": self.cv_accuracy,
            "review_threshold": REVIEW_THRESHOLD,
            "note": (
                "Measured on a small hand-written demo dataset; safety keywords were chosen while "
                "looking at it, so these numbers are optimistic."
            ),
        }


@lru_cache
def get_classifier() -> ComplaintClassifier:
    """Train once per process and reuse."""
    return ComplaintClassifier()
