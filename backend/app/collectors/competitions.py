from dataclasses import dataclass


@dataclass(frozen=True)
class Competition:
    """Une compétition et ce que chaque source en connaît. Un champ à None = la source l'ignore.

    Deux régimes coexistent, et c'est le champ `odds_api_key` qui les sépare :

    - **cotes live** : The Odds API est interrogée à chaque relevé (3 crédits par compétition,
      500 crédits gratuits par mois). Top 5, coupes d'Europe, Ligue des Nations.
    - **gratuit** (`odds_api_key=None`) : football-data.co.uk seul — calendrier de la semaine et
      cotes moyennes hebdomadaires, sans mouvement de cotes entre deux relevés. Zéro crédit.
      C'est le régime des championnats secondaires tant qu'ils ne financent pas leur relevé.
    """
    code: str                  # clé interne = code football-data.co.uk (E0, E1, SP1…) ; CL/EL/NL n'existent pas chez fd_uk
    name: str
    country: str
    odds_api_key: str | None   # The Odds API sport key ; None = pas de cotes live (mode gratuit)
    fd_org_code: str | None    # football-data.org competition code ; None = pas de calendrier fd_org
    fd_uk_code: str | None
    fd_org_free: bool = True   # False si le calendrier n'est pas dans le plan gratuit de football-data.org


COMPETITIONS: dict[str, Competition] = {
    "E0": Competition("E0", "Premier League", "Angleterre", "soccer_epl", "PL", "E0"),
    "F1": Competition("F1", "Ligue 1", "France", "soccer_france_ligue_one", "FL1", "F1"),
    "SP1": Competition("SP1", "La Liga", "Espagne", "soccer_spain_la_liga", "PD", "SP1"),
    "D1": Competition("D1", "Bundesliga", "Allemagne", "soccer_germany_bundesliga", "BL1", "D1"),
    "I1": Competition("I1", "Serie A", "Italie", "soccer_italy_serie_a", "SA", "I1"),
    "CL": Competition("CL", "Ligue des Champions", "Europe", "soccer_uefa_champs_league", "CL", None),
    # football-data.org ne donne le calendrier de la Ligue Europa que sur son plan payant (fd_org_free=False) :
    # fd_org.run doit sauter cette compétition. Les matchs EL sont créés par le collecteur de cotes
    # (odds_api.store_events crée des matchs SCHEDULED à partir des événements) et n'ont pas de résultat pour l'instant.
    "EL": Competition("EL", "Ligue Europa", "Europe", "soccer_uefa_europa_league", "EL", None, fd_org_free=False),
    # Même régime que la Ligue Europa : cotes live, aucun calendrier gratuit. Les sélections nationales
    # sont des équipes comme les autres pour les alias (pays « Sélections »).
    "NL": Competition("NL", "Ligue des Nations", "Europe", "soccer_uefa_nations_league", None, None, fd_org_free=False),

    # ---- Championnats secondaires, mode gratuit : fd_uk seul (odds_api_key=None, zéro crédit). ----
    # Le calendrier football-data.org n'est gratuit que pour ELC, DED et PPL ; ailleurs fd_uk fixtures.csv
    # fait seul le calendrier (quotidien) et les cotes moyennes.
    "E1": Competition("E1", "Championship", "Angleterre", None, "ELC", "E1"),
    "F2": Competition("F2", "Ligue 2", "France", None, None, "F2", fd_org_free=False),
    "SP2": Competition("SP2", "Liga 2", "Espagne", None, None, "SP2", fd_org_free=False),
    "D2": Competition("D2", "2. Bundesliga", "Allemagne", None, None, "D2", fd_org_free=False),
    "I2": Competition("I2", "Serie B", "Italie", None, None, "I2", fd_org_free=False),
    "N1": Competition("N1", "Eredivisie", "Pays-Bas", None, "DED", "N1"),
    "P1": Competition("P1", "Liga Portugal", "Portugal", None, "PPL", "P1"),
    "B1": Competition("B1", "Pro League", "Belgique", None, None, "B1", fd_org_free=False),
    "T1": Competition("T1", "Süper Lig", "Turquie", None, None, "T1", fd_org_free=False),
    "G1": Competition("G1", "Super League", "Grèce", None, None, "G1", fd_org_free=False),
    "SC0": Competition("SC0", "Premiership", "Écosse", None, None, "SC0", fd_org_free=False),
}

FRENCH_BOOKMAKERS = ("betclic_fr", "winamax_fr", "unibet_fr", "pmu_fr", "netbet_fr")
REFERENCE_BOOKMAKER = "pinnacle"

# Pattern de validation du paramètre `competition` des routes API, dérivé de COMPETITIONS (jamais codé en dur
# ailleurs) : toute compétition ajoutée ici devient automatiquement acceptée par les routes.
COMPETITION_PATTERN = "^(" + "|".join(COMPETITIONS) + ")$"


def by_odds_api_key(key: str) -> Competition | None:
    return next((c for c in COMPETITIONS.values() if c.odds_api_key == key), None)


def by_fd_org_code(code: str) -> Competition | None:
    return next((c for c in COMPETITIONS.values() if c.fd_org_code == code), None)
