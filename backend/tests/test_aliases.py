import pytest

from app.collectors.aliases import KNOWN_TEAMS, TeamAliasError, resolve_team, seed_aliases
from app.models.team import Team


def test_seed_creates_every_known_team(db):
    created = seed_aliases(db)
    assert db.query(Team).count() == len(KNOWN_TEAMS)
    assert created > len(KNOWN_TEAMS)            # chaque équipe a au moins un alias par source


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
    # 150 (top 5 + coupes d'Europe) + 170 clubs des onze championnats secondaires + 52 sélections, le 22/09/2026
    assert len(KNOWN_TEAMS) == 372


def test_resolve_team_fallback_other_source(db):
    """Un nom connu pour une autre source (et une seule équipe) est accepté, puis mémorisé pour la source."""
    from app.collectors.aliases import resolve_team, seed_aliases, normalize
    from app.models.team import TeamAlias
    from sqlalchemy import select
    seed_aliases(db)
    team = resolve_team(db, "odds_api", "Sporting Clube de Portugal")   # alias fd_org seulement
    assert team.name == "Sporting CP"
    assert db.scalar(select(TeamAlias).where(TeamAlias.source == "odds_api", TeamAlias.alias == normalize("Sporting Clube de Portugal"))) is not None


# ---- Les noms RÉELS des sources, relevés le 22/09/2026, doivent tous se résoudre ----
#
# Les listes viennent des sources elles-mêmes (CSV 2026/27 de football-data.co.uk + fixtures.csv,
# /competitions/{ELC,DED,PPL}/teams de football-data.org, un relevé Ligue des Nations de The Odds API),
# jamais de Wikipédia : les listes recopiées de mémoire étaient fausses au premier passage.

import json
from pathlib import Path

from app.collectors.aliases import resolve_team

_FIX = Path(__file__).parent / "fixtures"
FD_UK_2627 = json.loads((_FIX / "fd_uk_teams_2627.json").read_text(encoding="utf-8"))
FD_ORG_2627 = json.loads((_FIX / "fd_org_teams_2627.json").read_text(encoding="utf-8"))
NATIONS_2026 = json.loads((_FIX / "odds_api_nations_league_2026.json").read_text(encoding="utf-8"))


def _introuvables(db, source, noms):
    out = []
    for n in noms:
        try:
            resolve_team(db, source, n)
        except TeamAliasError:
            out.append(n)
    return out


def test_toutes_les_equipes_fd_uk_des_onze_championnats_se_resolvent(db):
    """Un nom inconnu = un match en quarantaine, invisible sur le site. Sur 200 clubs, zéro toléré."""
    seed_aliases(db)
    manquants = {code: _introuvables(db, "fd_uk", noms) for code, noms in FD_UK_2627.items()}
    assert {c: m for c, m in manquants.items() if m} == {}


def test_toutes_les_equipes_fd_org_des_trois_calendriers_gratuits_se_resolvent(db):
    seed_aliases(db)
    manquants = {code: _introuvables(db, "fd_org", [n for n, _court in noms]) for code, noms in FD_ORG_2627.items()}
    assert {c: m for c, m in manquants.items() if m} == {}


def test_toutes_les_selections_de_la_ligue_des_nations_se_resolvent(db):
    seed_aliases(db)
    assert _introuvables(db, "odds_api", NATIONS_2026) == []


def test_les_noms_fd_uk_abreges_rejoignent_les_clubs_deja_connus(db):
    """« Sp Lisbon » est le Sporting CP des coupes d'Europe, pas un nouveau club : sinon le même club
    existerait deux fois, et son historique européen et son championnat ne se rejoindraient jamais."""
    seed_aliases(db)
    assert resolve_team(db, "fd_uk", "Sp Lisbon").name == "Sporting CP"
    assert resolve_team(db, "fd_uk", "Nijmegen").name == "NEC Nijmegen"
    assert resolve_team(db, "fd_uk", "St. Gilloise").name == "Union Saint-Gilloise"
    assert resolve_team(db, "fd_uk", "West Ham").name == "West Ham"   # relégué : même club, nouvelle division


# ---- aucun nom ne désigne deux équipes (23/09/2026, Andorre) ----

def test_aucun_alias_n_est_partage_par_deux_equipes():
    """Le club FC Andorra (Liga 2, fd_uk « Andorra ») et la sélection d'Andorre (odds_api « Andorra »)
    partageaient la clé odds_api `andorra` : le premier servi gagnait, et la sélection a été rattachée au
    club — ses matchs internationaux auraient pollué la forme et l'historique du club."""
    import collections
    from app.collectors.aliases import SOURCES, normalize
    proprietaires = collections.defaultdict(set)
    for nom, _pays, par_source in KNOWN_TEAMS:
        for source in SOURCES:
            for alias in [nom, *par_source.get(source, [])]:
                proprietaires[(source, normalize(alias))].add(nom)
    assert {k: sorted(v) for k, v in proprietaires.items() if len(v) > 1} == {}


def test_chaque_selection_de_la_ligue_des_nations_se_resout_vers_une_selection(db):
    """Résoudre ne suffit pas : il faut résoudre vers la BONNE équipe. Le test précédent sur ces noms
    passait alors qu'« Andorra » désignait le club espagnol."""
    seed_aliases(db)
    mauvais = {n: resolve_team(db, "odds_api", n).country for n in NATIONS_2026
               if resolve_team(db, "odds_api", n).country != "Sélections"}
    assert mauvais == {}


def test_le_club_fc_andorra_reste_joignable_par_fd_uk(db):
    seed_aliases(db)
    club = resolve_team(db, "fd_uk", "Andorra")
    assert club.name == "FC Andorra" and club.country == "Espagne"
