from datetime import datetime, timezone

from app.engine.context import Form, PastMatch
from app.engine.narrative import MatchContext, describe, label
from app.engine.types import Reading

T0 = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def reading(ref=(0.58, 0.24, 0.18), fav="home", mov=None, src="pinnacle"):
    return Reading(reference=ref, reference_source=src, favourite=fav, favourite_prob=max(ref),
                   latest_by_book={"betclic_fr": (1.78, 3.9, 4.8), "pinnacle": (1.72, 4.0, 5.0)},
                   margin_by_book={"betclic_fr": 0.07}, gaps={"betclic_fr": (0.032, -0.06, -0.14)},
                   movement=mov, first_taken_at=T0, last_taken_at=T1)


def ctx(**kw):
    base = dict(home="Lyon", away="Nice", reading=reading(), home_form=Form(5, 3, 1, 1, 7, 4, "VVNDV"),
                away_form=Form(5, 1, 2, 2, 4, 6, "DNVDN"), h2h=[], best_gap=("betclic_fr", "home", 0.032))
    base.update(kw)
    return MatchContext(**base)


def test_label():
    assert label("home", "Lyon", "Nice") == "Lyon" and label("away", "Lyon", "Nice") == "Nice" and label("draw", "Lyon", "Nice") == "le nul"


def test_clear_favourite_with_gap_and_form():
    t = describe(ctx())
    assert t == ("Lyon est favori à 58 %. Betclic paie 1,78 sur Lyon, soit 3,2 % au-dessus de la référence. "
                 "Lyon reste sur trois victoires lors des cinq derniers matchs ; Nice sur une seule.")


def test_movement_sentence_when_reference_moved_more_than_three_points():
    t = describe(ctx(reading=reading(mov=(4.2, -1.5, -2.7))))
    assert "La probabilité de Lyon a gagné 4,2 points depuis le premier relevé." in t


def test_tight_match_wording():
    t = describe(ctx(reading=reading(ref=(0.41, 0.30, 0.29), fav="home"), best_gap=None))
    assert t.startswith("Match serré : Lyon favori de peu à 41 %.")
    assert "au-dessus de la référence" not in t


def test_draw_favourite_and_h2h():
    h2h = [PastMatch(T0, "Lyon", "Nice", 1, 1), PastMatch(T0, "Nice", "Lyon", 0, 0)]
    t = describe(ctx(reading=reading(ref=(0.33, 0.36, 0.31), fav="draw"), h2h=h2h, best_gap=None))
    assert "le nul est l'issue la plus probable à 36 %" in t
    assert "Les deux dernières confrontations se sont soldées par un nul." in t


def test_describe_is_deterministic():
    assert describe(ctx()) == describe(ctx())
