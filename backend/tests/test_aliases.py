import pytest

from app.collectors.aliases import KNOWN_TEAMS, TeamAliasError, resolve_team, seed_aliases
from app.models.team import Team


def test_seed_creates_150_teams(db):
    created = seed_aliases(db)
    assert db.query(Team).count() == 150
    assert created > 150            # chaque équipe a au moins un alias par source


def test_seed_is_idempotent(db):
    seed_aliases(db)
    n = db.query(Team).count()
    assert seed_aliases(db) == 0
    assert db.query(Team).count() == n


def test_resolve_known_alias_from_each_source(db):
    seed_aliases(db)
    assert resolve_team(db, "fd_uk", "Man United").name == "Manchester United"
    assert resolve_team(db, "odds_api", "Manchester United").name == "Manchester United"
    assert resolve_team(db, "fd_org", "Manchester United FC").name == "Manchester United"
    assert resolve_team(db, "fd_uk", "Paris SG").name == "Paris Saint-Germain"
    assert resolve_team(db, "fd_uk", "Ath Bilbao").name == "Athletic Bilbao"
    assert resolve_team(db, "fd_uk", "M'gladbach").name == "Borussia Mönchengladbach"


def test_resolve_promoted_and_european_clubs_2026_27(db):
    seed_aliases(db)
    assert resolve_team(db, "fd_uk", "Schalke 04").name == "Schalke 04"
    assert resolve_team(db, "odds_api", "PSV Eindhoven").name == "PSV Eindhoven"


def test_resolve_is_accent_and_case_insensitive(db):
    seed_aliases(db)
    assert resolve_team(db, "odds_api", "  bayern MUNICH ").name == "Bayern Munich"


def test_unknown_alias_raises(db):
    seed_aliases(db)
    with pytest.raises(TeamAliasError) as e:
        resolve_team(db, "fd_uk", "FC Nulle Part")
    assert e.value.source == "fd_uk" and e.value.alias == "FC Nulle Part"


def test_known_teams_cover_five_leagues():
    countries = {country for _, country, _ in KNOWN_TEAMS}
    assert {"Angleterre", "France", "Espagne", "Allemagne", "Italie"} <= countries
    # 98 (saison 2025/26 + 2 relégués 2024/25) + 12 promus 2026/27 + 14 clubs LdC + 9 clubs LE hors des cinq championnats
    assert len(KNOWN_TEAMS) == 150


def test_resolve_team_fallback_other_source(db):
    """Un nom connu pour une autre source (et une seule équipe) est accepté, puis mémorisé pour la source."""
    from app.collectors.aliases import resolve_team, seed_aliases, normalize
    from app.models.team import TeamAlias
    from sqlalchemy import select
    seed_aliases(db)
    team = resolve_team(db, "odds_api", "Sporting Clube de Portugal")   # alias fd_org seulement
    assert team.name == "Sporting CP"
    assert db.scalar(select(TeamAlias).where(TeamAlias.source == "odds_api", TeamAlias.alias == normalize("Sporting Clube de Portugal"))) is not None
