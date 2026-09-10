import pytest

from app.engine.probabilities import implied, margin, reference


def test_implied_sums_to_one_and_removes_margin():
    p = implied((2.0, 3.5, 4.0))
    assert pytest.approx(sum(p), abs=1e-12) == 1.0
    assert p[0] > p[1] > p[2]
    assert pytest.approx(p[0], abs=1e-9) == (1 / 2.0) / (1 / 2.0 + 1 / 3.5 + 1 / 4.0)


def test_margin_of_fair_odds_is_zero_and_typical_book_is_positive():
    assert pytest.approx(margin((3.0, 3.0, 3.0)), abs=1e-12) == 0.0
    assert 0.05 < margin((1.9, 3.5, 3.9)) < 0.10


def test_reference_prefers_pinnacle():
    latest = {"betclic_fr": (1.9, 3.5, 3.9), "pinnacle": (2.02, 3.7, 3.95)}
    p, src = reference(latest)
    assert src == "pinnacle" and p == implied((2.02, 3.7, 3.95))


def test_reference_falls_back_to_mean_of_books():
    latest = {"betclic_fr": (2.0, 3.5, 4.0), "winamax_fr": (2.2, 3.5, 3.6)}
    p, src = reference(latest)
    a, b = implied((2.0, 3.5, 4.0)), implied((2.2, 3.5, 3.6))
    assert src == "moyenne"
    assert pytest.approx(p[0], abs=1e-9) == (a[0] + b[0]) / 2
    assert pytest.approx(sum(p), abs=1e-9) == 1.0


def test_reference_rejects_empty():
    with pytest.raises(ValueError):
        reference({})
