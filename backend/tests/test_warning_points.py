import pytest

from app.services.analysis_runner import build_warning_points


def _make_prediction(**overrides):
    base = {
        "confidence_score": 65.0,
        "value_percent": 5.0,
        "risk_level": "LOW",
        "probabilities": {"home": 0.65, "draw": 0.20, "away": 0.15},
        "expected_home_goals": 1.8,
        "expected_away_goals": 1.2,
    }
    base.update(overrides)
    return base


def test_no_warnings_on_clean_prediction():
    warnings = build_warning_points(_make_prediction())
    assert warnings == ["Aucun signal critique detecte par les regles de risque."]


def test_high_risk_triggers_warning():
    warnings = build_warning_points(_make_prediction(risk_level="HIGH"))
    assert any("HIGH" in w for w in warnings)


def test_low_confidence_triggers_warning():
    warnings = build_warning_points(_make_prediction(confidence_score=45.0))
    assert any("50%" in w for w in warnings)


def test_negative_value_triggers_warning():
    warnings = build_warning_points(_make_prediction(value_percent=-3.0))
    assert any("Value negative" in w for w in warnings)


def test_balanced_match_triggers_warning():
    probs = {"home": 0.35, "draw": 0.30, "away": 0.35}
    warnings = build_warning_points(_make_prediction(probabilities=probs))
    assert any("equilibre" in w for w in warnings)


def test_high_draw_prob_triggers_warning():
    probs = {"home": 0.35, "draw": 0.35, "away": 0.30}
    warnings = build_warning_points(_make_prediction(probabilities=probs))
    assert any("nul" in w for w in warnings)


def test_low_xg_triggers_warning():
    warnings = build_warning_points(_make_prediction(
        expected_home_goals=0.7, expected_away_goals=0.9
    ))
    assert any("xG" in w for w in warnings)


def test_multiple_warnings_accumulated():
    prediction = _make_prediction(
        confidence_score=45.0,
        risk_level="HIGH",
        value_percent=-2.0,
    )
    warnings = build_warning_points(prediction)
    assert len(warnings) >= 3
