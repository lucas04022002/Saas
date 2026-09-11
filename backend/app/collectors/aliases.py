"""Résolution des noms d'équipes entre sources. Un nom inconnu lève TeamAliasError, jamais deviné."""
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team, TeamAlias

SOURCES = ("fd_uk", "fd_org", "odds_api")


class TeamAliasError(LookupError):
    def __init__(self, source: str, alias: str):
        super().__init__(f"nom d'équipe inconnu pour {source}: {alias!r}")
        self.source, self.alias = source, alias


def normalize(name: str) -> str:
    """minuscules, sans accents, espaces réduits — clé de comparaison des alias."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.lower().split())


# (nom canonique, pays, {source: [alias, ...]}) — le nom canonique est lui-même un alias implicite pour chaque source.
KNOWN_TEAMS: list[tuple[str, str, dict[str, list[str]]]] = [
    # ---- Angleterre (Premier League 2025/26)
    ("Arsenal", "Angleterre", {"fd_org": ["Arsenal FC"]}),
    ("Aston Villa", "Angleterre", {"fd_org": ["Aston Villa FC"]}),
    ("Bournemouth", "Angleterre", {"fd_org": ["AFC Bournemouth"]}),
    ("Brentford", "Angleterre", {"fd_org": ["Brentford FC"]}),
    ("Brighton", "Angleterre", {"fd_org": ["Brighton & Hove Albion FC"], "odds_api": ["Brighton and Hove Albion"]}),
    ("Burnley", "Angleterre", {"fd_org": ["Burnley FC"]}),
    ("Chelsea", "Angleterre", {"fd_org": ["Chelsea FC"]}),
    ("Crystal Palace", "Angleterre", {"fd_org": ["Crystal Palace FC"]}),
    ("Everton", "Angleterre", {"fd_org": ["Everton FC"]}),
    ("Fulham", "Angleterre", {"fd_org": ["Fulham FC"]}),
    ("Leeds", "Angleterre", {"fd_org": ["Leeds United FC"], "odds_api": ["Leeds United"]}),
    ("Liverpool", "Angleterre", {"fd_org": ["Liverpool FC"]}),
    ("Manchester City", "Angleterre", {"fd_uk": ["Man City"], "fd_org": ["Manchester City FC"]}),
    ("Manchester United", "Angleterre", {"fd_uk": ["Man United"], "fd_org": ["Manchester United FC"]}),
    ("Newcastle", "Angleterre", {"fd_org": ["Newcastle United FC"], "odds_api": ["Newcastle United"]}),
    ("Nottingham Forest", "Angleterre", {"fd_uk": ["Nott'm Forest"], "fd_org": ["Nottingham Forest FC"]}),
    ("Sunderland", "Angleterre", {"fd_org": ["Sunderland AFC"]}),
    ("Tottenham", "Angleterre", {"fd_org": ["Tottenham Hotspur FC"], "odds_api": ["Tottenham Hotspur"]}),
    ("West Ham", "Angleterre", {"fd_org": ["West Ham United FC"], "odds_api": ["West Ham United"]}),
    ("Wolves", "Angleterre", {"fd_org": ["Wolverhampton Wanderers FC"], "odds_api": ["Wolverhampton Wanderers"]}),
    # ---- France (Ligue 1 2025/26)
    ("Angers", "France", {"fd_org": ["Angers SCO"]}),
    ("Auxerre", "France", {"fd_org": ["AJ Auxerre"]}),
    ("Brest", "France", {"fd_org": ["Stade Brestois 29"], "odds_api": ["Stade Brestois 29"]}),
    ("Le Havre", "France", {"fd_org": ["Le Havre AC"]}),
    ("Lens", "France", {"fd_org": ["RC Lens"]}),
    ("Lille", "France", {"fd_org": ["Lille OSC"]}),
    ("Lorient", "France", {"fd_org": ["FC Lorient"]}),
    ("Lyon", "France", {"fd_org": ["Olympique Lyonnais"], "odds_api": ["Olympique Lyonnais"]}),
    ("Marseille", "France", {"fd_org": ["Olympique de Marseille"], "odds_api": ["Marseille", "Olympique Marseille"]}),
    ("Metz", "France", {"fd_org": ["FC Metz"]}),
    ("Monaco", "France", {"fd_org": ["AS Monaco FC"], "odds_api": ["AS Monaco"]}),
    ("Nantes", "France", {"fd_org": ["FC Nantes"]}),
    ("Nice", "France", {"fd_org": ["OGC Nice"]}),
    ("Paris FC", "France", {"fd_org": ["Paris FC"]}),
    ("Paris Saint-Germain", "France", {"fd_uk": ["Paris SG"], "fd_org": ["Paris Saint-Germain FC"], "odds_api": ["Paris Saint Germain", "Paris Saint-Germain"]}),
    ("Rennes", "France", {"fd_org": ["Stade Rennais FC 1901"], "odds_api": ["Stade Rennais"]}),
    ("Strasbourg", "France", {"fd_org": ["RC Strasbourg Alsace"]}),
    ("Toulouse", "France", {"fd_org": ["Toulouse FC"]}),
    # ---- Espagne (La Liga 2025/26)
    ("Alavés", "Espagne", {"fd_uk": ["Alaves"], "fd_org": ["Deportivo Alavés"], "odds_api": ["Alaves", "Deportivo Alaves"]}),
    ("Athletic Bilbao", "Espagne", {"fd_uk": ["Ath Bilbao"], "fd_org": ["Athletic Club"], "odds_api": ["Athletic Club", "Athletic Bilbao"]}),
    ("Atlético Madrid", "Espagne", {"fd_uk": ["Ath Madrid"], "fd_org": ["Club Atlético de Madrid"], "odds_api": ["Atletico Madrid", "Atlético Madrid"]}),
    ("Barcelona", "Espagne", {"fd_org": ["FC Barcelona"]}),
    ("Celta Vigo", "Espagne", {"fd_uk": ["Celta"], "fd_org": ["RC Celta de Vigo"]}),
    ("Elche", "Espagne", {"fd_org": ["Elche CF"]}),
    ("Espanyol", "Espagne", {"fd_uk": ["Espanol"], "fd_org": ["RCD Espanyol de Barcelona"]}),
    ("Getafe", "Espagne", {"fd_org": ["Getafe CF"]}),
    ("Girona", "Espagne", {"fd_org": ["Girona FC"]}),
    ("Levante", "Espagne", {"fd_org": ["Levante UD"]}),
    ("Mallorca", "Espagne", {"fd_org": ["RCD Mallorca"]}),
    ("Osasuna", "Espagne", {"fd_org": ["CA Osasuna"]}),
    ("Real Oviedo", "Espagne", {"fd_uk": ["Oviedo"], "fd_org": ["Real Oviedo"], "odds_api": ["Oviedo"]}),
    ("Rayo Vallecano", "Espagne", {"fd_uk": ["Vallecano"], "fd_org": ["Rayo Vallecano de Madrid"]}),
    ("Real Betis", "Espagne", {"fd_uk": ["Betis"], "fd_org": ["Real Betis Balompié"]}),
    ("Real Madrid", "Espagne", {"fd_org": ["Real Madrid CF"]}),
    ("Real Sociedad", "Espagne", {"fd_uk": ["Sociedad"], "fd_org": ["Real Sociedad de Fútbol"]}),
    ("Sevilla", "Espagne", {"fd_org": ["Sevilla FC"]}),
    ("Valencia", "Espagne", {"fd_org": ["Valencia CF"]}),
    ("Villarreal", "Espagne", {"fd_org": ["Villarreal CF"]}),
    # ---- Allemagne (Bundesliga 2025/26)
    ("Augsburg", "Allemagne", {"fd_org": ["FC Augsburg"], "odds_api": ["FC Augsburg"]}),
    ("Bayer Leverkusen", "Allemagne", {"fd_uk": ["Leverkusen"], "fd_org": ["Bayer 04 Leverkusen"]}),
    ("Bayern Munich", "Allemagne", {"fd_org": ["FC Bayern München"], "odds_api": ["Bayern München", "FC Bayern Munich"]}),
    ("Borussia Dortmund", "Allemagne", {"fd_uk": ["Dortmund"], "fd_org": ["Borussia Dortmund"]}),
    ("Borussia Mönchengladbach", "Allemagne", {"fd_uk": ["M'gladbach"], "fd_org": ["Borussia Mönchengladbach"], "odds_api": ["Borussia Monchengladbach"]}),
    ("Eintracht Frankfurt", "Allemagne", {"fd_uk": ["Ein Frankfurt"], "fd_org": ["Eintracht Frankfurt"]}),
    ("Freiburg", "Allemagne", {"fd_org": ["SC Freiburg"], "odds_api": ["SC Freiburg"]}),
    ("Hamburg", "Allemagne", {"fd_org": ["Hamburger SV"], "odds_api": ["Hamburger SV"]}),
    ("Heidenheim", "Allemagne", {"fd_org": ["1. FC Heidenheim 1846"], "odds_api": ["1. FC Heidenheim"]}),
    ("Hoffenheim", "Allemagne", {"fd_org": ["TSG 1899 Hoffenheim"], "odds_api": ["TSG Hoffenheim"]}),
    ("Köln", "Allemagne", {"fd_uk": ["FC Koln"], "fd_org": ["1. FC Köln"], "odds_api": ["FC Cologne", "1. FC Köln"]}),
    ("Mainz", "Allemagne", {"fd_org": ["1. FSV Mainz 05"], "odds_api": ["1. FSV Mainz 05"]}),
    ("RB Leipzig", "Allemagne", {"fd_org": ["RB Leipzig"]}),
    ("St. Pauli", "Allemagne", {"fd_uk": ["St Pauli"], "fd_org": ["FC St. Pauli 1910"], "odds_api": ["FC St. Pauli"]}),
    ("Stuttgart", "Allemagne", {"fd_org": ["VfB Stuttgart"], "odds_api": ["VfB Stuttgart"]}),
    ("Union Berlin", "Allemagne", {"fd_org": ["1. FC Union Berlin"]}),
    ("Werder Bremen", "Allemagne", {"fd_org": ["SV Werder Bremen"]}),
    ("Wolfsburg", "Allemagne", {"fd_org": ["VfL Wolfsburg"], "odds_api": ["VfL Wolfsburg"]}),
    # ---- Italie (Serie A 2025/26)
    ("Atalanta", "Italie", {"fd_org": ["Atalanta BC"]}),
    ("Bologna", "Italie", {"fd_org": ["Bologna FC 1909"]}),
    ("Cagliari", "Italie", {"fd_org": ["Cagliari Calcio"]}),
    ("Como", "Italie", {"fd_org": ["Como 1907"]}),
    ("Cremonese", "Italie", {"fd_org": ["US Cremonese"]}),
    ("Fiorentina", "Italie", {"fd_org": ["ACF Fiorentina"]}),
    ("Genoa", "Italie", {"fd_org": ["Genoa CFC"]}),
    ("Inter", "Italie", {"fd_org": ["FC Internazionale Milano"], "odds_api": ["Inter Milan"]}),
    ("Juventus", "Italie", {"fd_org": ["Juventus FC"]}),
    ("Lazio", "Italie", {"fd_org": ["SS Lazio"]}),
    ("Lecce", "Italie", {"fd_org": ["US Lecce"]}),
    ("Milan", "Italie", {"fd_org": ["AC Milan"], "odds_api": ["AC Milan"]}),
    ("Napoli", "Italie", {"fd_org": ["SSC Napoli"]}),
    ("Parma", "Italie", {"fd_org": ["Parma Calcio 1913"]}),
    ("Pisa", "Italie", {"fd_org": ["Pisa SC"]}),
    ("Roma", "Italie", {"fd_org": ["AS Roma"], "odds_api": ["AS Roma"]}),
    ("Sassuolo", "Italie", {"fd_org": ["US Sassuolo Calcio"]}),
    ("Torino", "Italie", {"fd_org": ["Torino FC"]}),
    ("Udinese", "Italie", {"fd_org": ["Udinese Calcio"]}),
    ("Verona", "Italie", {"fd_org": ["Hellas Verona FC"], "odds_api": ["Hellas Verona"]}),
    # ---- relégués 2024/25 présents dans l'historique fd_uk (utile à la forme et aux face-à-face)
    ("Leicester", "Angleterre", {"fd_org": ["Leicester City FC"], "odds_api": ["Leicester City"]}),
    ("Ipswich", "Angleterre", {"fd_org": ["Ipswich Town FC"], "odds_api": ["Ipswich Town"]}),
    # ---- promus 2026/27 dans les cinq championnats domestiques (orthographes observées dans fixtures.csv)
    ("Schalke 04", "Allemagne", {"fd_org": ["FC Schalke 04"]}),
    ("SC Paderborn 07", "Allemagne", {"fd_uk": ["Paderborn"]}),
    ("SV Elversberg", "Allemagne", {"fd_uk": ["Elversberg"]}),
    ("Hull City", "Angleterre", {"fd_uk": ["Hull"], "fd_org": ["Hull City AFC"]}),
    ("Coventry City", "Angleterre", {"fd_uk": ["Coventry"], "fd_org": ["Coventry City FC"]}),
    ("ESTAC Troyes", "France", {"fd_uk": ["Troyes"], "odds_api": ["Troyes"]}),
    ("Le Mans FC", "France", {"fd_uk": ["Le Mans"], "odds_api": ["Le Mans"]}),
    ("Venezia FC", "Italie", {"fd_uk": ["Venezia"], "odds_api": ["Venezia"]}),
    ("Frosinone Calcio", "Italie", {"fd_uk": ["Frosinone"], "odds_api": ["Frosinone"]}),
    ("AC Monza", "Italie", {"fd_uk": ["Monza"], "odds_api": ["Monza"]}),
    ("Racing Santander", "Espagne", {"fd_uk": ["Santander"], "fd_org": ["Real Racing Club de Santander"]}),
    ("Málaga CF", "Espagne", {"fd_uk": ["Malaga"], "odds_api": ["Malaga"]}),
    # ---- Ligue des Champions 2026/27, clubs hors des cinq championnats domestiques (pas de calendrier fd_uk)
    ("PSV Eindhoven", "Pays-Bas", {"fd_org": ["PSV"]}),
    ("Feyenoord", "Pays-Bas", {"fd_org": ["Feyenoord Rotterdam"]}),
    ("NEC Nijmegen", "Pays-Bas", {"fd_org": ["NEC"]}),
    ("Porto", "Portugal", {"fd_org": ["FC Porto"], "odds_api": ["FC Porto"]}),
    ("Sporting CP", "Portugal", {"fd_org": ["Sporting Clube de Portugal"], "odds_api": ["Sporting Lisbon"]}),
    ("Club Brugge", "Belgique", {"fd_org": ["Club Brugge KV"]}),
    ("Union Saint-Gilloise", "Belgique", {"fd_org": ["Royale Union Saint-Gilloise"], "odds_api": ["Union Saint Gilloise", "Union St. Gilloise"]}),
    ("Slavia Prague", "Tchéquie", {"fd_org": ["SK Slavia Praha"], "odds_api": ["Slavia Praha"]}),
    ("Galatasaray", "Turquie", {"fd_org": ["Galatasaray SK"]}),
    ("Shakhtar Donetsk", "Ukraine", {"fd_org": ["FC Shakhtar Donetsk"]}),
    ("Viking", "Norvège", {"fd_org": ["Viking FK"], "odds_api": ["Viking FK"]}),
    ("AEK Athens", "Grèce", {"fd_org": ["AEK Athens FC"]}),
    ("LASK", "Autriche", {"fd_org": ["LASK Linz"], "odds_api": ["LASK Linz"]}),
    ("Celtic", "Écosse", {"fd_org": ["Celtic FC"]}),
    # ---- Ligue Europa 2026/27, clubs hors des cinq championnats domestiques (liste partielle, à compléter via
    # l'outil quarantine quand des orthographes inconnues apparaissent)
    ("AZ Alkmaar", "Pays-Bas", {"fd_org": ["AZ"]}),
    ("Torreense", "Portugal", {"fd_org": ["CD Torreense"]}),
    ("Hapoel Be'er Sheva", "Israël", {"fd_org": ["Hapoel Be'er Sheva FC"], "odds_api": ["Hapoel Beer Sheva"]}),
    ("Dinamo Zagreb", "Croatie", {"fd_org": ["GNK Dinamo Zagreb"]}),
    ("Celje", "Slovénie", {"fd_org": ["NK Celje"]}),
    ("Levski Sofia", "Bulgarie", {"fd_org": ["PFC Levski Sofia"]}),
    ("Sparta Prague", "Tchéquie", {"fd_org": ["AC Sparta Praha"], "odds_api": ["Sparta Praha"]}),
    ("Olympiacos", "Grèce", {"fd_org": ["Olympiacos FC"], "odds_api": ["Olympiakos"]}),
    ("Sturm Graz", "Autriche", {"fd_org": ["SK Sturm Graz"]}),
]


def seed_aliases(db: Session) -> int:
    """Crée les équipes et leurs alias manquants. Idempotent. Retourne le nombre d'alias créés."""
    created = 0
    existing_teams = {t.name: t for t in db.scalars(select(Team)).all()}
    existing_aliases = {(a.source, normalize(a.alias)) for a in db.scalars(select(TeamAlias)).all()}
    for name, country, per_source in KNOWN_TEAMS:
        team = existing_teams.get(name)
        if team is None:
            team = Team(name=name, country=country)
            db.add(team); db.flush()
            existing_teams[name] = team
        for source in SOURCES:
            for alias in [name, *per_source.get(source, [])]:
                key = (source, normalize(alias))
                if key in existing_aliases:
                    continue
                db.add(TeamAlias(source=source, alias=normalize(alias), team_id=team.id))
                existing_aliases.add(key); created += 1
    db.commit()
    return created


def resolve_team(db: Session, source: str, alias: str) -> Team:
    if source not in SOURCES:
        raise ValueError(f"source inconnue : {source}")
    row = db.scalar(select(TeamAlias).where(TeamAlias.source == source, TeamAlias.alias == normalize(alias)))
    if row is None:
        raise TeamAliasError(source, alias)
    return row.team
