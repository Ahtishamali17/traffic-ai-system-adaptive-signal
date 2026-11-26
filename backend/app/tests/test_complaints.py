"""
Tests for the NLP complaint classifier (app/nlp) and its API.
No database, GPU or internet needed.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.nlp.complaint_classifier import find_safety_keyword, get_classifier
from app.nlp.complaint_data import CATEGORIES, DEMO_COMPLAINTS, get_training_rows

# Expected category for each unseen DEMO_COMPLAINT, in the same order.
DEMO_EXPECTED = [
    "traffic_congestion", "accident", "signal_fault", "illegal_parking", "rash_driving",
    "road_damage", "signal_fault", "traffic_congestion", "road_damage", "illegal_parking",
]


# ---------------- data ----------------

def test_training_data_is_balanced_and_unique():
    rows = get_training_rows()
    assert len({r[0] for r in rows}) == len(rows)  # no duplicate sentences
    for category in CATEGORIES:
        assert sum(1 for r in rows if r[1] == category) == 22


def test_demo_complaints_are_not_in_training_data():
    training_texts = {r[0] for r in get_training_rows()}
    assert not training_texts.intersection(DEMO_COMPLAINTS)


# ---------------- safety rule ----------------

@pytest.mark.parametrize("text,expected", [
    ("The rider is bleeding badly", "bleeding"),
    ("Please send an ambulance", "ambulance"),
    ("An open manhole on the road", "manhole"),
    ("Children are crying after the crash", "children"),
])
def test_safety_keyword_detected(text, expected):
    assert find_safety_keyword(text) == expected


@pytest.mark.parametrize("text", [
    "Minor collision, nobody is hurt",
    "Rear end crash, there are no injuries",
    "Heavy traffic jam near the mall",
])
def test_safety_keyword_ignores_negations_and_normal_text(text):
    assert find_safety_keyword(text) is None


# ---------------- classifier ----------------

def test_classifier_gets_most_unseen_demo_complaints_right():
    classifier = get_classifier()
    predicted = [classifier.predict(t).category for t in DEMO_COMPLAINTS]
    correct = sum(p == e for p, e in zip(predicted, DEMO_EXPECTED))
    assert correct >= 8, f"only {correct}/10 correct: {predicted}"


def test_injury_complaint_is_urgent_via_rule():
    result = get_classifier().predict("A bike hit a car and the rider is bleeding on the road.")
    assert result.priority == "urgent"
    assert "safety keyword" in result.priority_reason


def test_nobody_hurt_is_not_forced_urgent_by_rule():
    result = get_classifier().predict("Minor collision between two cars, nobody is hurt.")
    assert "safety keyword" not in result.priority_reason


def test_unrelated_text_is_flagged_for_review():
    assert get_classifier().predict("I love eating pizza on sunday").needs_review is True


def test_prediction_fields_are_consistent():
    p = get_classifier().predict("The traffic light at the crossing is not working.")
    assert p.category in CATEGORIES
    assert p.priority in ("urgent", "normal")
    assert len(p.top_categories) == 3
    assert p.top_categories[0][0] == p.category
    assert 0.0 <= p.category_confidence <= 1.0


def test_model_info_reports_accuracy_and_baseline():
    info = get_classifier().info()
    assert info["n_train"] == 132
    assert 0.0 < info["cv_accuracy"]["category"] <= 1.0
    # the safety rule should not make priority worse than the model alone
    assert info["cv_accuracy"]["priority_with_safety_rule"] >= info["cv_accuracy"]["priority_model_only"]


# ---------------- API ----------------

@pytest.mark.asyncio
async def test_api_classify_single():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/complaints/classify",
                                 json={"text": "Cars are parked on the footpath near the market."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "illegal_parking"
    assert len(body["top_categories"]) == 3


@pytest.mark.asyncio
async def test_api_rejects_blank_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/complaints/classify", json={"text": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_api_batch_and_samples_and_info():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        samples = (await client.get("/api/v1/complaints/samples")).json()
        assert len(samples) == len(DEMO_COMPLAINTS)

        batch = await client.post("/api/v1/complaints/classify-batch", json={"texts": samples})
        assert batch.status_code == 200
        body = batch.json()
        assert len(body["results"]) == len(samples)
        assert sum(body["counts_by_category"].values()) == len(samples)

        info = await client.get("/api/v1/complaints/model-info")
        assert info.status_code == 200
        assert info.json()["language"] == "English"
