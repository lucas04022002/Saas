from datetime import datetime, timedelta, timezone

import pytest

from app.engine.market import favourite, gaps, movement, read
from app.engine.probabilities import implied, reference
from app.engine.types import BookQuote

FR = ("betclic_fr", "winamax_fr", "unibet_fr", "pmu_fr", "netbet_fr")
T0 = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def test_favourite_is_argmax():
    assert favourite((0.58, 0.24, 0.18)) == ("home", 0.58)
    assert favourite((0.30, 0.25, 0.45)) == ("away", 0.45)


def test_gaps_positive_when_book_pays_more_than_reference():
    ref = implied((2.0, 3.5, 4.0))              # ≈ (0.4706, 0.2689, 0.2353)
    g = gaps({"betclic_fr": (2.2, 3.5, 4.0)}, ref)
    assert g["betclic_fr"][0] == pytest.approx(2.2 * ref[0] - 1, abs=1e-9)
    assert g["betclic_fr"][0] > 0 and g["betclic_fr"][1] < 0


def test_movement_in_percentage_points():
    assert movement((0.50, 0.25, 0.25), (0.53, 0.24, 0.23)) == pytest.approx((3.0, -1.0, -2.0), abs=1e-9)


def test_read_assembles_everything_from_raw_quotes():
    quotes = [
        BookQuote("pinnacle", T0, (2.10, 3.60, 3.80)),
        BookQuote("betclic_fr", T0, (2.00, 3.50, 3.70)),
        BookQuote("pinnacle", T1, (1.95, 3.70, 4.10)),
        BookQuote("betclic_fr", T1, (1.90, 3.55, 3.90)),
        BookQuote("winamax_fr", T1, (2.05, 3.50, 3.80)),
        BookQuote("williamhill", T1, (2.50, 3.50, 3.80)),   # ignoré : ni FR ni référence
    ]
    r = read(quotes, FR)
    assert r.reference_source == "pinnacle" and r.reference == implied((1.95, 3.70, 4.10))
    assert r.favourite == "home" and r.favourite_prob == pytest.approx(r.reference[0])
    assert set(r.latest_by_book) == {"pinnacle", "betclic_fr", "winamax_fr"}
    assert set(r.gaps) == {"betclic_fr", "winamax_fr"}                 # écarts calculés pour les FR seulement
    assert r.gaps["winamax_fr"][0] == pytest.approx(2.05 * r.reference[0] - 1, abs=1e-9)
    assert r.movement[0] == pytest.approx((implied((1.95, 3.70, 4.10))[0] - implied((2.10, 3.60, 3.80))[0]) * 100, abs=1e-9)
    assert (r.first_taken_at, r.last_taken_at) == (T0, T1)
    assert 0 < r.margin_by_book["betclic_fr"] < 0.1


def test_read_single_snapshot_has_no_movement():
    r = read([BookQuote("betclic_fr", T0, (2.0, 3.5, 4.0))], FR)
    assert r.movement is None and r.reference_source == "moyenne"


def test_read_uses_latest_snapshot_per_book_even_if_books_differ_in_timing():
    quotes = [BookQuote("betclic_fr", T0, (2.0, 3.5, 4.0)), BookQuote("pinnacle", T1, (2.1, 3.6, 3.8))]
    r = read(quotes, FR)
    assert r.latest_by_book["betclic_fr"] == (2.0, 3.5, 4.0)
    assert r.last_taken_at == T1


def test_read_uses_fd_uk_pinnacle_as_reference():
    quotes = [BookQuote("fd_uk_pinnacle", T0, (2.10, 3.60, 3.80)), BookQuote("fd_uk_avg", T0, (2.05, 3.55, 3.70))]
    r = read(quotes, FR)
    assert r.reference_source == "fd_uk_pinnacle" and r.reference == implied((2.10, 3.60, 3.80))
    assert r.gaps == {}


def test_read_falls_back_to_fd_uk_avg_alone_as_moyenne_reference():
    """Un match couvert uniquement par l'archive fixtures fd_uk (pas de Pinnacle, pas de FR) doit rester lisible :
    fallback_books suffit, la référence retombe sur la moyenne (ici l'unique bookmaker disponible)."""
    r = read([BookQuote("fd_uk_avg", T0, (2.0, 3.2, 3.5))], FR)
    assert r.reference_source == "moyenne"
    assert r.reference == implied((2.0, 3.2, 3.5))
    assert r.favourite == "home"
    assert r.latest_by_book == {"fd_uk_avg": (2.0, 3.2, 3.5)}


def test_read_empty_raises():
    with pytest.raises(ValueError):
        read([], FR)
    with pytest.raises(ValueError):
        read([BookQuote("williamhill", T0, (2.0, 3.5, 4.0))], FR)


def test_read_mixed_live_and_archive_uses_live_timeline():
    kickoff = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)
    t_archive_open = kickoff - timedelta(days=7)
    t_archive_close = kickoff - timedelta(hours=1)
    t_fr = kickoff - timedelta(hours=6)
    t_live_pinnacle = kickoff - timedelta(hours=2)
    quotes = [
        BookQuote("fd_uk_pinnacle", t_archive_open, (2.10, 3.60, 3.80)),
        BookQuote("fd_uk_pinnacle", t_archive_close, (2.00, 3.55, 3.90)),
        BookQuote("betclic_fr", t_fr, (2.05, 3.50, 3.80)),
        BookQuote("winamax_fr", t_fr, (2.02, 3.55, 3.85)),
        BookQuote("pinnacle", t_live_pinnacle, (1.95, 3.70, 4.10)),
    ]
    r = read(quotes, FR)
    assert r.reference_source == "pinnacle"
    assert r.first_taken_at == t_fr
    assert r.last_taken_at == t_live_pinnacle
    assert len(r.timeline) == 2
    assert set(r.gaps) == {"betclic_fr", "winamax_fr"}
    fr_ref, _ = reference({"betclic_fr": (2.05, 3.50, 3.80), "winamax_fr": (2.02, 3.55, 3.85)})
    pinnacle_ref, _ = reference({"pinnacle": (1.95, 3.70, 4.10)})
    assert r.movement == pytest.approx(movement(fr_ref, pinnacle_ref), abs=1e-9)
    assert [t for t, _ in r.timeline] == [t_fr, t_live_pinnacle]
