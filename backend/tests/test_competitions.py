"""Le catalogue des compétitions : ce que chaque source doit ou ne doit pas y trouver.

Deux régimes coexistent, et le code des collecteurs les distingue par les champs
à None :

- **cotes live** (The Odds API, 3 crédits par relevé) : top 5, coupes d'Europe,
  Ligue des Nations ;
- **gratuit** (football-data.co.uk seulement : calendrier et cotes hebdomadaires) :
  les championnats secondaires, `odds_api_key=None`. Ils coûtent zéro crédit.
"""
import re

from app.collectors.competitions import COMPETITIONS, COMPETITION_PATTERN
from app.collectors.fd_uk import FIXTURE_DIVS
from app.engine.score import LEAGUE_GOALS

# Les codes fd_uk sont les codes internes : `import_fixtures` retrouve la compétition par `COMPETITIONS.get(r.div)`.
LIGUES_GRATUITES = ["E1", "D2", "I2", "SP2", "F2", "N1", "P1", "B1", "T1", "G1", "SC0"]


def test_la_ligue_des_nations_est_en_cotes_live_sans_calendrier_gratuit():
    nl = COMPETITIONS["NL"]
    assert nl.odds_api_key == "soccer_uefa_nations_league"
    # Ni football-data.co.uk ni le plan gratuit de football-data.org ne la couvrent :
    # comme la Ligue Europa, ses matchs naissent du collecteur de cotes.
    assert nl.fd_uk_code is None
    assert nl.fd_org_free is False


def test_les_championnats_secondaires_sont_en_mode_gratuit():
    """Zéro crédit The Odds API : le calendrier et les cotes viennent de fd_uk."""
    for code in LIGUES_GRATUITES:
        comp = COMPETITIONS[code]
        assert comp.fd_uk_code == code, code
        assert comp.odds_api_key is None, code


def test_les_calendriers_gratuits_de_football_data_org_sont_declares():
    """Championship, Eredivisie et Liga Portugal sont dans le plan gratuit ; les autres non."""
    assert COMPETITIONS["E1"].fd_org_code == "ELC" and COMPETITIONS["E1"].fd_org_free
    assert COMPETITIONS["N1"].fd_org_code == "DED" and COMPETITIONS["N1"].fd_org_free
    assert COMPETITIONS["P1"].fd_org_code == "PPL" and COMPETITIONS["P1"].fd_org_free
    for code in ("D2", "I2", "SP2", "F2", "B1", "T1", "G1", "SC0"):
        assert COMPETITIONS[code].fd_org_free is False, code


def test_les_routes_acceptent_toutes_les_nouvelles_competitions():
    for code in ["NL", *LIGUES_GRATUITES]:
        assert re.match(COMPETITION_PATTERN, code), code
    assert not re.match(COMPETITION_PATTERN, "E2")


def test_fixtures_csv_garde_les_divisions_gratuites():
    """`FIXTURE_DIVS` filtre fixtures.csv : une division absente y est silencieusement ignorée."""
    assert set(LIGUES_GRATUITES) <= FIXTURE_DIVS
    assert "E2" not in FIXTURE_DIVS


def test_chaque_championnat_fd_uk_a_sa_moyenne_de_buts():
    """Sans entrée, le moteur retombe sur DEFAULT_GOALS (2,75) : l'Eredivisie (3,08)
    et la Serie B (2,51) auraient le même score le plus probable. La constante
    est mesurée sur deux saisons complètes, pas devinée."""
    for comp in COMPETITIONS.values():
        if comp.fd_uk_code:
            assert comp.code in LEAGUE_GOALS, comp.code
    assert LEAGUE_GOALS["N1"] == 3.08
    assert LEAGUE_GOALS["I2"] == 2.51
