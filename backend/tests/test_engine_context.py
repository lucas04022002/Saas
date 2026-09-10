from datetime import datetime, timedelta, timezone

from app.engine.context import PastMatch, form, head_to_head

T = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)


def pm(days_ago, home, away, hg, ag):
    return PastMatch(T - timedelta(days=days_ago), home, away, hg, ag)


HIST = [
    pm(1, "Lyon", "Nice", 2, 0),        # Lyon V
    pm(8, "Lens", "Lyon", 1, 1),        # Lyon N
    pm(15, "Lyon", "Marseille", 0, 3),  # Lyon D
    pm(22, "Metz", "Lyon", 0, 1),       # Lyon V
    pm(29, "Lyon", "Brest", 1, 0),      # Lyon V
    pm(36, "Nantes", "Lyon", 2, 2),     # 6e match : hors fenêtre de 5
    pm(400, "Marseille", "Lyon", 1, 0),
    pm(800, "Lyon", "Marseille", 2, 2),
]


def test_form_last_five_most_recent_first():
    f = form("Lyon", HIST)
    assert (f.played, f.wins, f.draws, f.losses) == (5, 3, 1, 1)
    assert (f.goals_for, f.goals_against) == (5, 4)
    assert f.sequence == "VNDVV"


def test_form_with_fewer_matches_than_window():
    f = form("Nice", HIST)
    assert f.played == 1 and f.losses == 1 and f.sequence == "D"


def test_form_unknown_team_is_empty():
    f = form("Inconnu", HIST)
    assert f.played == 0 and f.sequence == ""


def test_head_to_head_both_venues_most_recent_first():
    h2h = head_to_head("Lyon", "Marseille", HIST)
    assert [(m.home, m.away) for m in h2h] == [("Lyon", "Marseille"), ("Marseille", "Lyon"), ("Lyon", "Marseille")]
