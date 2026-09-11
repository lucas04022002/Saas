from dataclasses import dataclass


@dataclass(frozen=True)
class Competition:
    code: str          # clé interne et football-data.co.uk (E0, F1, SP1, D1, I1) ; CL/EL n'existent pas chez fd_uk
    name: str
    country: str
    odds_api_key: str  # The Odds API sport key
    fd_org_code: str   # football-data.org competition code
    fd_uk_code: str | None
    fd_org_free: bool = True   # False si le calendrier de la compétition n'est pas dans le plan gratuit de football-data.org


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
