import requests
from datetime import datetime, timedelta
from fuzz_fallback import fuzz
import time
import unicodedata
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    Fore = Style = type('Dummy', (), {'__getattr__': lambda self, x: ''})()
from prediction_engine import AdvancedPredictor, kelly_fraction
from data_collector import update_poisson_with_stats, load_team_stats_into_poisson
from draw_policy import load_thresholds_map, select_recommended_outcome
from form_recente import get_form_recente_api
from features_avancees import get_injuries_for_match, get_head_to_head
from config import KEY_API_FOOTBALL, KEY_THE_ODDS, SAISON, PROBA_FAVORI_MIN, JOUR_A_SCANNER, DATE_SCAN
from odds_logger import save_odds
from prediction_tracker import log_prediction

# Initialiser le prédicteur avancé (Elo + Poisson + XGBoost)
predictor = AdvancedPredictor()
# Charger les stats attaque/défense (dont LDC) depuis team_stats.json pour des xG par équipe
load_team_stats_into_poisson(predictor.poisson)

# Appliquer le decay saisonnier Elo (idempotent : sans effet si déjà appliqué cette saison)
_now = datetime.now()
_current_season = _now.year - 1 if _now.month < 7 else _now.year
_n_decayed = predictor.elo.apply_season_decay(_current_season)
if _n_decayed:
    predictor.elo.save_ratings()
    print(f"   [ELO] Decay saisonnier appliqué ({_n_decayed} équipes, saison {_current_season})")

# Mettre à jour Poisson avec les stats réelles si disponibles
# (Décommenter pour activer la mise à jour automatique)
# for ligue in LIGUES_A_SCANNER:
#     update_poisson_with_stats(predictor.poisson, ligue['nom'], ligue['id_foot'], SAISON)

# ==========================================
# 1. CONFIGURATION ET CLÉS
# ==========================================
# Les clés API sont maintenant dans config.py
# Modifiez config.py pour ajouter vos clés API

# LE TABLEAU DE CORRESPONDANCE (C'est ça le secret de l'automatisation)
# J'ai pré-rempli les 5 grands championnats majeurs + Ligue des Champions
LIGUES_A_SCANNER = [
    {"nom": "Premier League (Ang)", "id_foot": 39,  "key_odds": "soccer_epl"},
    {"nom": "Ligue 1 (Fra)",        "id_foot": 61,  "key_odds": "soccer_france_ligue_one"},
    {"nom": "La Liga (Esp)",        "id_foot": 140, "key_odds": "soccer_spain_la_liga"},
    {"nom": "Bundesliga (All)",     "id_foot": 78,  "key_odds": "soccer_germany_bundesliga"},
    {"nom": "Serie A (Ita)",        "id_foot": 135, "key_odds": "soccer_italy_serie_a"},
    {"nom": "Ligue des Champions",  "id_foot": 2,   "key_odds": "soccer_uefa_champs_league"},
    {"nom": "Europa League",        "id_foot": 3,   "key_odds": "soccer_uefa_europa_league"},
    {"nom": "Conference League",    "id_foot": 848, "key_odds": "soccer_uefa_europa_conference_league"},
]

_DRAW_THRESHOLDS = load_thresholds_map()

_POISSON_REFRESHED_LEAGUES = set()


def _season_for_date_and_league(ligue_id, date_jour):
    """Saison à utiliser pour une date donnée."""
    if ligue_id not in (2, 3, 848):
        return SAISON
    try:
        y, m = int(date_jour[:4]), int(date_jour[5:7])
        return y - 1 if m < 7 else y
    except Exception:
        now = datetime.now()
        return now.year - 1 if now.month < 7 else now.year


def _ensure_poisson_stats_for_match(ligue, date_jour, home_team, away_team):
    """Recharge les stats Poisson d'une ligue si les équipes du match sont absentes."""
    league_id = ligue['id_foot']
    home_stats = predictor.poisson.get_stats(home_team, league_id)
    away_stats = predictor.poisson.get_stats(away_team, league_id)
    if home_stats and away_stats:
        return
    if league_id in _POISSON_REFRESHED_LEAGUES:
        return

    season = _season_for_date_and_league(league_id, date_jour or datetime.today().strftime('%Y-%m-%d'))
    print(f"   -> Stats Poisson manquantes ({ligue['nom']}), tentative de bootstrap saison {season}...")
    try:
        update_poisson_with_stats(predictor.poisson, ligue['nom'], league_id, season)
    except Exception as e:
        print(f"   [WARN] Bootstrap Poisson impossible: {e}")
    finally:
        _POISSON_REFRESHED_LEAGUES.add(league_id)

# ==========================================
# 2. FONCTIONS TECHNIQUES
# ==========================================

def get_matchs_du_jour(ligue_id, date_jour_override=None):
    """Récupère les matchs pour une ligue précise via API-Football.
    date_jour_override : si fourni (YYYY-MM-DD), utilisé à la place de config."""
    if date_jour_override:
        date_jour = date_jour_override
    elif DATE_SCAN:
        date_jour = DATE_SCAN
    else:
        date_cible = datetime.today() + timedelta(days=JOUR_A_SCANNER)
        date_jour = date_cible.strftime('%Y-%m-%d')
    # Compétitions européennes (UCL=2, EL=3, UECL=848) : saison = année de début (ex. jan 2026 -> 2025)
    if ligue_id in (2, 3, 848):
        y, m = int(date_jour[:4]), int(date_jour[5:7])
        season = y - 1 if m < 7 else y
    else:
        season = SAISON
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': KEY_API_FOOTBALL}
    params = {"date": date_jour, "league": ligue_id, "season": season}
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()  # Lève une exception si erreur HTTP
        data = r.json()
        if data.get('errors'):
            print(f"   [ERREUR API] {data.get('errors')}")
            return []
        return data.get('response', [])
    except requests.exceptions.RequestException as e:
        print(f"   [ERREUR] Problème de connexion: {e}")
        return []
    except Exception as e:
        print(f"   [ERREUR] Erreur inattendue: {e}")
        return []

def get_cotes_du_marche(ligue_key):
    """Récupère les cotes pour une ligue précise via The-Odds-API"""
    url = f'https://api.the-odds-api.com/v4/sports/{ligue_key}/odds'
    params = {'apiKey': KEY_THE_ODDS, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        # L'API renvoie parfois un message d'erreur si la quota est dépassée
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'message' in data:
            print(f"   [ERREUR API] {data.get('message')}")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise  # Laisser remonter pour permettre le fallback "upcoming"
        print(f"   [ERREUR] Problème de connexion: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"   [ERREUR] Problème de connexion: {e}")
        return []
    except Exception as e:
        print(f"   [ERREUR] Erreur inattendue: {e}")
        return []


def get_cotes_upcoming():
    """Récupère les cotes des prochains matchs (tous sports) via The-Odds-API. Coûte 1 crédit."""
    url = 'https://api.the-odds-api.com/v4/sports/upcoming/odds'
    params = {'apiKey': KEY_THE_ODDS, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def filter_cotes_par_matchs(cotes, matchs, seuil=60):
    """Garde les événements dont (home_team, away_team) matchent une paire dans matchs (fuzzy + alias)."""
    if not cotes or not matchs:
        return []
    result = []
    for evt in cotes:
        home_odds = (evt.get('home_team') or '').strip()
        away_odds = (evt.get('away_team') or '').strip()
        for m in matchs:
            home_api = (m.get('teams', {}).get('home', {}).get('name') or '').strip()
            away_api = (m.get('teams', {}).get('away', {}).get('name') or '').strip()
            sh = _score_team(home_api, home_odds)
            sa = _score_team(away_api, away_odds)
            if sh >= seuil and sa >= seuil:
                result.append(evt)
                break
            sh_inv = _score_team(home_api, away_odds)
            sa_inv = _score_team(away_api, home_odds)
            if sh_inv >= seuil and sa_inv >= seuil:
                result.append(evt)
                break
    return result

def calculer_probabilite_implicite(cote):
    """Convertit une cote décimale en probabilité implicite"""
    if cote <= 0:
        return 0
    return (1 / cote) * 100

# Alias pour matcher les noms API-Football avec ceux de The-Odds-API
ALIASES_ODDS = {
    # Angleterre (Premier League)
    "Wolves": ["Wolverhampton Wanderers", "Wolverhampton"],
    "Manchester United": ["Man United", "Man Utd"],
    "Bournemouth": ["AFC Bournemouth"],
    "Aston Villa": ["Villa"],
    "West Ham": ["West Ham United"],
    "Newcastle United": ["Newcastle"],
    "Tottenham Hotspur": ["Tottenham", "Spurs"],
    "Brighton": ["Brighton and Hove Albion"],
    "Nottingham Forest": ["Nott'ham Forest", "Nottingham Forest"],
    "Sunderland": ["Sunderland AFC"],
    "Everton": ["Everton FC"],
    "Chelsea": ["Chelsea FC"],
    "Arsenal": ["Arsenal FC"],
    "Liverpool": ["Liverpool FC"],
    "Manchester City": ["Man City", "City"],
    "Leicester City": ["Leicester"],
    "Fulham": ["Fulham FC"],
    "Brentford": ["Brentford FC"],
    "Crystal Palace": ["Palace"],
    "Sheffield United": ["Sheffield Utd", "Sheffield United"],
    "Luton Town": ["Luton"],
    "Ipswich Town": ["Ipswich"],
    "Southampton": ["Southampton FC"],
    # Espagne (La Liga)
    "Barcelona": ["FC Barcelona", "Barca"],
    "Real Madrid": ["Madrid"],
    "Atlético Madrid": ["Atletico Madrid", "Atletico"],
    "Atletico Madrid": ["Atletico Madrid", "Atletico"],
    "Mallorca": ["RCD Mallorca", "Real Mallorca"],
    "Sevilla": ["Sevilla FC"],
    "Real Sociedad": ["Sociedad"],
    "Athletic Club": ["Athletic Bilbao", "Bilbao"],
    "Villarreal": ["Villarreal CF"],
    "Betis": ["Real Betis"],
    "Getafe": ["Getafe CF"],
    "Valencia": ["Valencia CF"],
    "Celta Vigo": ["Celta Vigo", "Celta"],
    "Osasuna": ["CA Osasuna"],
    "Girona": ["Girona FC"],
    # Allemagne (Bundesliga)
    "SC Freiburg": ["Freiburg"],
    "VfL Wolfsburg": ["Wolfsburg"],
    "Borussia Dortmund": ["Dortmund"],
    "FSV Mainz 05": ["Mainz", "1. FSV Mainz 05"],
    "FC Augsburg": ["Augsburg"],
    "FC St. Pauli": ["St. Pauli", "St Pauli"],
    "VfB Stuttgart": ["Stuttgart"],
    "Bayer Leverkusen": ["Leverkusen"],
    "Borussia Mönchengladbach": ["Mönchengladbach", "Gladbach", "M'gladbach"],
    "Werder Bremen": ["Bremen"],
    "1. FC Heidenheim": ["Heidenheim"],
    "Hamburger SV": ["Hamburg", "HSV"],
    "Eintracht Frankfurt": ["Frankfurt", "Eintracht"],
    "Union Berlin": ["Union Berlin"],
    "Bayern München": ["Bayern Munich", "Bayern"],
    "1899 Hoffenheim": ["Hoffenheim"],
    # Ligue 1
    "Stade Brestois 29": ["Brest", "Stade Brestois"],
    "Lorient": ["FC Lorient"],
    "Lens": ["RC Lens"],
    "Rennes": ["Stade Rennes", "Stade Rennais"],
    "Paris Saint Germain": ["PSG", "Paris SG"],
    "Olympique Marseille": ["Marseille", "OM"],
    "Olympique Lyonnais": ["Lyon", "OL"],
    "Monaco": ["AS Monaco"],
    "Lille": ["Lille OSC"],
    "Nice": ["OGC Nice"],
    "Strasbourg": ["RC Strasbourg"],
    "Montpellier": ["Montpellier HSC"],
    "Nantes": ["FC Nantes"],
    "Toulouse": ["Toulouse FC"],
    "Clermont Foot 63": ["Clermont", "Clermont Foot"],
    "Le Havre": ["HAC", "Le Havre AC"],
    "Metz": ["FC Metz"],
    "Angers": ["Angers SCO", "SCO Angers"],
    # Italie (Serie A)
    "Genoa": ["Genoa CFC", "Genoa"],
    "Napoli": ["SSC Napoli", "Napoli"],
    "Inter": ["Inter Milan", "Internazionale"],
    "AC Milan": ["Milan", "AC Milan"],
    "Juventus": ["Juventus FC", "Juve"],
    "Roma": ["AS Roma"],
    "Lazio": ["SS Lazio"],
    "Atalanta": ["Atalanta BC"],
    "Fiorentina": ["Fiorentina"],
    "Torino": ["Torino FC"],
    "Bologna": ["Bologna FC"],
    "Udinese": ["Udinese Calcio"],
    "Verona": ["Hellas Verona", "Verona"],
    "Pisa": ["AC Pisa"],
    "Sassuolo": ["Sassuolo Calcio", "US Sassuolo"],
    "Parma": ["Parma Calcio"],
    "Real Betis": ["Betis"],
}

def _normalize_accents(s):
    """Retire les accents pour faciliter le matching (Atlético vs Atletico)."""
    if not s:
        return s
    normalized = unicodedata.normalize('NFKD', s)
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch))

def _score_team(api_name, odds_name):
    """Score de similarité entre un nom API et un nom Odds (avec alias et sous-chaînes)."""
    if not api_name or not odds_name:
        return 0
    a = _normalize_accents(api_name.lower())
    b = _normalize_accents(odds_name.lower())
    s = fuzz.token_sort_ratio(a, b)
    # Aliases directs (clé = api_name)
    for alias in ALIASES_ODDS.get(api_name, []):
        s = max(s, fuzz.token_sort_ratio(_normalize_accents(alias.lower()), b))
    # Alias inversés : api_name est un alias d'une clé (ex. API renvoie "Arsenal FC", Odds "Arsenal")
    for key, aliases in ALIASES_ODDS.items():
        if api_name == key or api_name in aliases:
            s = max(s, fuzz.token_sort_ratio(_normalize_accents(key.lower()), b))
            for al in aliases:
                s = max(s, fuzz.token_sort_ratio(_normalize_accents(al.lower()), b))
            break
    if b in a or a in b:
        s = max(s, 88)
    # Un mot significatif en commun (ex: "Lens" dans "RC Lens", "Villa" dans "Aston Villa")
    words_a = [w for w in a.split() if len(w) >= 3]
    words_b = [w for w in b.split() if len(w) >= 3]
    if any(wa in b for wa in words_a) or any(wb in a for wb in words_b):
        s = max(s, 72)
    return s

def trouver_match_odds(home_team, away_team, cotes):
    """Trouve le match correspondant dans les cotes avec matching flou + alias"""
    meilleur_match = None
    meilleur_score = 0
    meilleur_home_odds_name = None
    meilleur_away_odds_name = None
    SEUIL = 48  # Seuil bas pour rattraper un max de matchs (alias + sous-chaînes aident)

    for match_odds in cotes:
        home_odds = match_odds.get('home_team', '')
        away_odds = match_odds.get('away_team', '')

        score_home = _score_team(home_team, home_odds)
        score_away = _score_team(away_team, away_odds)
        score_combine = (score_home + score_away) / 2

        score_home_inv = _score_team(home_team, away_odds)
        score_away_inv = _score_team(away_team, home_odds)
        score_combine_inv = (score_home_inv + score_away_inv) / 2

        is_inverted = score_combine_inv > score_combine
        if is_inverted:
            score_combine = score_combine_inv
            home_odds_name = away_odds
            away_odds_name = home_odds
        else:
            home_odds_name = home_odds
            away_odds_name = away_odds

        if score_combine >= SEUIL and score_combine > meilleur_score:
            meilleur_score = score_combine
            meilleur_match = match_odds
            meilleur_home_odds_name = home_odds_name
            meilleur_away_odds_name = away_odds_name

    if meilleur_match and meilleur_score >= SEUIL:
        return meilleur_match, meilleur_home_odds_name, meilleur_away_odds_name
    return None, None, None

def analyser_cotes_match(match_data, home_team_name, away_team_name):
    """Analyse les cotes d'un match et retourne les statistiques"""
    if not match_data or not match_data.get('bookmakers'):
        return None
    
    stats = {
        'home': {'cotes': [], 'moyenne': 0, 'meilleure': 0, 'bookie': ''},
        'away': {'cotes': [], 'moyenne': 0, 'meilleure': 0, 'bookie': ''},
        'draw': {'cotes': [], 'moyenne': 0, 'meilleure': 0, 'bookie': ''}
    }
    
    # Normaliser les noms pour la comparaison
    home_team_lower = home_team_name.lower() if home_team_name else ''
    away_team_lower = away_team_name.lower() if away_team_name else ''
    
    for bookie in match_data['bookmakers']:
        for market in bookie['markets']:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    team_name = outcome['name']
                    price = outcome['price']
                    team_name_lower = team_name.lower()
                    
                    # Identifier quel équipe correspond avec matching flou
                    # (au cas où les noms diffèrent légèrement)
                    score_home = fuzz.token_sort_ratio(team_name_lower, home_team_lower)
                    score_away = fuzz.token_sort_ratio(team_name_lower, away_team_lower)
                    
                    # Correspondance exacte ou très proche (>= 90)
                    if score_home >= 90 or (score_home >= 80 and score_home > score_away):
                        stats['home']['cotes'].append(price)
                        if price > stats['home']['meilleure']:
                            stats['home']['meilleure'] = price
                            stats['home']['bookie'] = bookie['title']
                    elif score_away >= 90 or (score_away >= 80 and score_away > score_home):
                        stats['away']['cotes'].append(price)
                        if price > stats['away']['meilleure']:
                            stats['away']['meilleure'] = price
                            stats['away']['bookie'] = bookie['title']
                    elif team_name_lower in ['draw', 'match nul', 'nul', 'tie']:
                        stats['draw']['cotes'].append(price)
                        if price > stats['draw']['meilleure']:
                            stats['draw']['meilleure'] = price
                            stats['draw']['bookie'] = bookie['title']
    
    # Calculer les moyennes
    for key in ['home', 'away', 'draw']:
        if stats[key]['cotes']:
            stats[key]['moyenne'] = sum(stats[key]['cotes']) / len(stats[key]['cotes'])
        else:
            stats[key]['moyenne'] = 0
    
    return stats

def identifier_favori(stats):
    """Identifie le favori basé sur les cotes les plus basses"""
    favoris = []
    
    if stats['home']['moyenne'] > 0:
        favoris.append(('home', stats['home']['moyenne']))
    if stats['away']['moyenne'] > 0:
        favoris.append(('away', stats['away']['moyenne']))
    if stats['draw']['moyenne'] > 0:
        favoris.append(('draw', stats['draw']['moyenne']))
    
    if not favoris:
        return None, None
    
    # Le favori est celui avec la cote moyenne la plus basse
    favori = min(favoris, key=lambda x: x[1])
    return favori[0], favori[1]

def analyse_ligue(ligue, date_jour=None, cotes_upcoming=None):
    """Fonction principale qui traite une ligue entière. date_jour : YYYY-MM-DD ou None pour config. cotes_upcoming : liste optionnelle (évite de rappeler l'API)."""
    print(f"\n{Fore.CYAN}=== SCAN DE : {ligue['nom']} ==={Style.RESET_ALL}")
    
    # 1. Calendrier
    matchs = get_matchs_du_jour(ligue['id_foot'], date_jour_override=date_jour)
    if not matchs:
        print("   -> Aucun match prévu aujourd'hui.")
        return

    print(f"   -> {len(matchs)} matchs trouvés. Récupération des cotes...")
    
    # 2. Cotes
    cotes = []
    try:
        cotes = get_cotes_du_marche(ligue['key_odds'])
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404 and ligue['id_foot'] == 2:
            cotes = (cotes_upcoming if cotes_upcoming is not None else get_cotes_upcoming())
            cotes = filter_cotes_par_matchs(cotes, matchs, seuil=50)
            if cotes:
                print(f"   -> Cotes LDC récupérées via upcoming ({len(cotes)} matchs).")
        else:
            print(f"   [ERREUR] {e}")
    
    # Fallback : si aucune cote pour cette ligue (ex. Serie A vide certains jours), essayer "upcoming"
    if not cotes:
        cotes = (cotes_upcoming if cotes_upcoming is not None else get_cotes_upcoming())
        cotes = filter_cotes_par_matchs(cotes, matchs, seuil=50)
        if cotes:
            print(f"   -> Cotes récupérées via upcoming ({len(cotes)} matchs).")
    
    # Toujours compléter avec "upcoming" pour maximiser les matchs trouvés (noms différents selon les sources)
    seen_keys = {(e.get('home_team', ''), e.get('away_team', '')) for e in cotes}
    upcoming = cotes_upcoming if cotes_upcoming is not None else get_cotes_upcoming()
    added = 0
    for evt in filter_cotes_par_matchs(upcoming, matchs, seuil=50):
        key = (evt.get('home_team', ''), evt.get('away_team', ''))
        if key not in seen_keys:
            seen_keys.add(key)
            cotes.append(evt)
            added += 1
    if added:
        print(f"   -> Cotes complétées via upcoming (+{added} événement(s)).")
    
    if not cotes:
        print("   -> Aucune cote trouvée pour ces matchs (API ou quota). Matchs concernés:")
        for m in matchs:
            print(f"      - {m['teams']['home']['name']} vs {m['teams']['away']['name']}")
        import sys
        sys.stdout.flush()
        return

    print(f"   -> {len(cotes)} événement(s) avec cotes disponibles pour matching.")

    # 3. Comparaison
    favoris_trouves = []
    skipped = []  # matchs sans cote au premier essai
    
    for match in matchs:
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        
        match_data, home_odds_name, away_odds_name = trouver_match_odds(home_team, away_team, cotes)
        
        if not match_data:
            skipped.append(match)
            continue
        
        # Analyser les cotes
        stats = analyser_cotes_match(match_data, home_odds_name, away_odds_name)
        
        if not stats:
            print(f"   [SKIP] Données de cotes incomplètes pour {home_team} vs {away_team}")
            continue
        
        # Sauvegarder les cotes pour l'entraînement futur
        match_date = match.get('fixture', {}).get('date', '')[:10] if match.get('fixture', {}).get('date') else (date_jour or datetime.today().strftime('%Y-%m-%d'))
        if match_date:
            save_odds(match_date, home_team, away_team, stats)
        
        # Récupérer les IDs des équipes depuis le match
        home_team_id = match['teams']['home']['id']
        away_team_id = match['teams']['away']['id']
        fixture_id = match['fixture']['id']
        
        # Récupérer la forme récente des équipes
        try:
            home_form, away_form = get_form_recente_api(
                home_team, away_team, ligue['id_foot'], SAISON, max_matches=5
            )
        except Exception as e:
            # Si erreur, continuer sans forme récente
            home_form, away_form = None, None
        
        # Récupérer blessures et suspensions
        injuries = None
        try:
            injuries = get_injuries_for_match(fixture_id, home_team_id, away_team_id)
        except Exception as e:
            # Si erreur, continuer sans données de blessures
            injuries = None
        
        # Récupérer confrontations directes (H2H)
        h2h = None
        try:
            h2h = get_head_to_head(
                home_team_id, away_team_id, 
                league_id=ligue['id_foot'], 
                season=SAISON, 
                last=5
            )
        except Exception as e:
            # Si erreur, continuer sans H2H
            h2h = None
        
        # CALCULER LES PROBABILITÉS AVEC LE MODÈLE (Elo + Poisson + XGBoost)
        # Préparer les cotes bookmakers comme feature
        bookmaker_odds = {
            'home_avg': stats['home']['moyenne'],
            'draw_avg': stats['draw']['moyenne'],
            'away_avg': stats['away']['moyenne']
        } if stats else None
        _ensure_poisson_stats_for_match(ligue, date_jour, home_team, away_team)
        
        try:
            prediction = predictor.predict_match(
                home_team, away_team, 
                home_form=home_form, away_form=away_form,
                injuries=injuries, h2h=h2h, bookmaker_odds=bookmaker_odds,
                league_id=ligue['id_foot']
            )
            prob_model = prediction['probabilities']
        except Exception as e:
            # En cas d'erreur, utiliser les cotes des bookmakers
            prob_model = None
            prediction = None
        
        # IDENTIFIER LE FAVORI SELON LE MODÈLE (pas selon les bookmakers !)
        if prob_model:
            favori_type, nom_favori, prob_model_favori = select_recommended_outcome(
                prob_model,
                home_team,
                away_team,
                league_id=ligue['id_foot'],
                league_name=ligue['nom'],
                thresholds_map=_DRAW_THRESHOLDS,
            )
        else:
            # Fallback : utiliser les cotes si le modèle échoue
            favori_type, cote_favori = identifier_favori(stats)
            if not favori_type:
                continue
            
            if favori_type == 'home':
                nom_favori = home_team
                prob_model_favori = calculer_probabilite_implicite(stats['home']['moyenne'])
            elif favori_type == 'away':
                nom_favori = away_team
                prob_model_favori = calculer_probabilite_implicite(stats['away']['moyenne'])
            else:
                nom_favori = "Match Nul"
                prob_model_favori = calculer_probabilite_implicite(stats['draw']['moyenne'])
        
        # Récupérer les cotes correspondantes pour le favori identifié
        if favori_type == 'home':
            best_odd = stats['home']['meilleure']
            avg_odd = stats['home']['moyenne']
            best_bookie = stats['home']['bookie']
            cote_favori = stats['home']['moyenne']
        elif favori_type == 'away':
            best_odd = stats['away']['meilleure']
            avg_odd = stats['away']['moyenne']
            best_bookie = stats['away']['bookie']
            cote_favori = stats['away']['moyenne']
        else:
            best_odd = stats['draw']['meilleure']
            avg_odd = stats['draw']['moyenne']
            best_bookie = stats['draw']['bookie']
            cote_favori = stats['draw']['moyenne']
        
        # Ne marquer favori que si le modèle donne au moins PROBA_FAVORI_MIN (ex. 55%)
        is_favori = prob_model_favori >= PROBA_FAVORI_MIN

        # Probabilité implicite des bookmakers (pour comparaison)
        prob_implicite = calculer_probabilite_implicite(cote_favori)

        # Value bet : notre modèle prédit une probabilité plus élevée que celle des bookmakers
        # Si notre proba > proba implicite + 5%, c'est un value bet
        is_value_bet_model = prob_model_favori > prob_implicite + 5 if prob_model else False

        # Value bet classique (meilleure cote > moyenne + 5%)
        is_value_bet = best_odd > avg_odd * 1.05 if avg_odd > 0 else False

        # Combiner les deux critères
        is_value_bet = is_value_bet or is_value_bet_model

        # Kelly Criterion : mise optimale (demi-Kelly, plafond 25% du bankroll)
        kelly = kelly_fraction(prob_model_favori / 100, best_odd) if best_odd > 0 else 0.0
        kelly_pct = round(kelly * 100, 1)

        # Afficher les résultats
        if is_favori:
            favoris_trouves.append({
                'match': f"{home_team} vs {away_team}",
                'favori': nom_favori,
                'cote': round(cote_favori, 2),
                'prob_model': round(prob_model_favori, 1),
                'prob_bookmakers': round(prob_implicite, 1),
                'best_odd': round(best_odd, 2),
                'avg_odd': round(avg_odd, 2),
                'bookie': best_bookie,
                'value': is_value_bet,
                'kelly': kelly_pct,
            })

            # Logger la prédiction pour le suivi de performance
            try:
                _pm = prob_model or {}
                if _pm:
                    prob_home_log = _pm.get('home', 0)
                    prob_draw_log = _pm.get('draw', 0)
                    prob_away_log = _pm.get('away', 0)
                else:
                    prob_home_log = prob_model_favori / 100 if favori_type == 'home' else 0
                    prob_draw_log = prob_model_favori / 100 if favori_type == 'draw' else 0
                    prob_away_log = prob_model_favori / 100 if favori_type == 'away' else 0
                log_prediction(
                    date=match_date,
                    league=ligue['nom'],
                    home_team=home_team,
                    away_team=away_team,
                    predicted_outcome=favori_type,
                    prob_home=prob_home_log,
                    prob_draw=prob_draw_log,
                    prob_away=prob_away_log,
                    odds_home=stats['home']['moyenne'] if stats else None,
                    odds_draw=stats['draw']['moyenne'] if stats else None,
                    odds_away=stats['away']['moyenne'] if stats else None,
                    is_value_bet=is_value_bet,
                    kelly_pct=kelly_pct,
                    fixture_id=fixture_id,
                )
            except Exception:
                pass  # Ne jamais bloquer le scan principal

            if is_value_bet:
                print(f"{Fore.GREEN}   [FAVORI + VALUE] {home_team} vs {away_team}")
                print(f"   Favori: {nom_favori} | Cote moyenne: {round(avg_odd, 2)} | Meilleure: {round(best_odd, 2)} ({best_bookie})")
                print(f"   Probabilité modèle (Elo+Poisson+XGBoost): {round(prob_model_favori, 1)}%")
                print(f"   Probabilité bookmakers: {round(prob_implicite, 1)}%")
                if kelly_pct > 0:
                    print(f"   Kelly (demi): {kelly_pct}% du bankroll")
                if prediction:
                    hxg, axg = prediction['expected_goals']['home'], prediction['expected_goals']['away']
                    default_note = " (defaut: equipes absentes du modele)" if abs(hxg - 0.69) < 0.02 and abs(axg - 0.56) < 0.02 else ""
                    print(f"   Expected Goals: {round(hxg, 2)} - {round(axg, 2)}{default_note}")
                    print(f"   Elo Ratings: {round(prediction['elo_ratings']['home'], 0)} vs {round(prediction['elo_ratings']['away'], 0)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}   [FAVORI] {home_team} vs {away_team}")
                print(f"   Favori: {nom_favori} | Cote: {round(cote_favori, 2)} | Prob modèle: {round(prob_model_favori, 1)}% | Prob bookmakers: {round(prob_implicite, 1)}%")
                kelly_str = f" | Kelly: {kelly_pct}%" if kelly_pct > 0 else ""
                print(f"   Meilleure cote: {round(best_odd, 2)} ({best_bookie}){kelly_str}{Style.RESET_ALL}")
        else:
            # Value bet sans être favori
            if is_value_bet:
                print(f"{Fore.CYAN}   [VALUE] {home_team} vs {away_team}")
                print(f"   {nom_favori} | Moyenne: {round(avg_odd, 2)} | Top: {round(best_odd, 2)} ({best_bookie}){Style.RESET_ALL}")
            else:
                # Afficher tous les autres matchs (avec cotes mais ni favori ni value)
                p1 = calculer_probabilite_implicite(stats['home']['moyenne']) if stats['home']['moyenne'] > 0 else 0
                pn = calculer_probabilite_implicite(stats['draw']['moyenne']) if stats['draw']['moyenne'] > 0 else 0
                p2 = calculer_probabilite_implicite(stats['away']['moyenne']) if stats['away']['moyenne'] > 0 else 0
                print(f"   [MATCH] {home_team} vs {away_team}")
                print(f"   Prédit: {nom_favori} ({round(prob_model_favori, 1)}%) | Cotes 1/N/2: {round(stats['home']['moyenne'], 2)} / {round(stats['draw']['moyenne'], 2)} / {round(stats['away']['moyenne'], 2)}")
                print(f"   Proba bookmakers 1/N/2: {round(p1, 1)}% / {round(pn, 1)}% / {round(p2, 1)}%{Style.RESET_ALL}")
    
    # Seconde chance : si tous les matchs sont en skip, refaire un appel "upcoming" (snapshot plus frais)
    if skipped and len(skipped) == len(matchs):
        fresh = get_cotes_upcoming()
        added = 0
        for evt in filter_cotes_par_matchs(fresh, matchs, seuil=50):
            key = (evt.get('home_team', ''), evt.get('away_team', ''))
            if key not in seen_keys:
                seen_keys.add(key)
                cotes.append(evt)
                added += 1
        if added:
            print(f"   -> 2e essai : +{added} événement(s) (appel API frais).")
            still_skipped = []
            for match in skipped:
                md, ho, ao = trouver_match_odds(match['teams']['home']['name'], match['teams']['away']['name'], cotes)
                if md:
                    match_data, home_odds_name, away_odds_name = md, ho, ao
                    home_team = match['teams']['home']['name']
                    away_team = match['teams']['away']['name']
                    stats = analyser_cotes_match(match_data, home_odds_name, away_odds_name)
                    if stats:
                        match_date = match.get('fixture', {}).get('date', '')[:10] if match.get('fixture', {}).get('date') else (date_jour or datetime.today().strftime('%Y-%m-%d'))
                        if match_date:
                            save_odds(match_date, home_team, away_team, stats)
                        try:
                            home_form, away_form = get_form_recente_api(home_team, away_team, ligue['id_foot'], SAISON, max_matches=5)
                        except Exception:
                            home_form, away_form = None, None
                        injuries = None
                        try:
                            injuries = get_injuries_for_match(match['fixture']['id'], match['teams']['home']['id'], match['teams']['away']['id'])
                        except Exception:
                            pass
                        h2h = None
                        try:
                            h2h = get_head_to_head(match['teams']['home']['id'], match['teams']['away']['id'], league_id=ligue['id_foot'], season=SAISON, last=5)
                        except Exception:
                            pass
                        bookmaker_odds = {'home_avg': stats['home']['moyenne'], 'draw_avg': stats['draw']['moyenne'], 'away_avg': stats['away']['moyenne']}
                        _ensure_poisson_stats_for_match(ligue, date_jour, home_team, away_team)
                        try:
                            prediction = predictor.predict_match(home_team, away_team, home_form=home_form, away_form=away_form, injuries=injuries, h2h=h2h, bookmaker_odds=bookmaker_odds, league_id=ligue['id_foot'])
                            prob_model = prediction['probabilities']
                        except Exception:
                            prob_model = None
                            prediction = None
                        if prob_model:
                            favori_type, nom_favori, prob_model_favori = select_recommended_outcome(
                                prob_model,
                                home_team,
                                away_team,
                                league_id=ligue['id_foot'],
                                league_name=ligue['nom'],
                                thresholds_map=_DRAW_THRESHOLDS,
                            )
                        else:
                            favori_type, cote_favori = identifier_favori(stats)
                            if not favori_type:
                                still_skipped.append(match)
                                continue
                            nom_favori = home_team if favori_type == 'home' else (away_team if favori_type == 'away' else "Match Nul")
                            prob_model_favori = calculer_probabilite_implicite(stats['home']['moyenne'] if favori_type == 'home' else (stats['away']['moyenne'] if favori_type == 'away' else stats['draw']['moyenne']))
                        best_odd = stats[favori_type]['meilleure']
                        avg_odd = stats[favori_type]['moyenne']
                        cote_favori = avg_odd
                        is_favori = prob_model_favori >= PROBA_FAVORI_MIN
                        prob_implicite = calculer_probabilite_implicite(cote_favori)
                        is_value_bet = prob_model_favori > prob_implicite + 5 or best_odd > avg_odd * 1.05
                        if is_favori:
                            favoris_trouves.append({'match': f"{home_team} vs {away_team}", 'favori': nom_favori, 'cote': round(cote_favori, 2), 'prob_model': round(prob_model_favori, 1), 'prob_bookmakers': round(prob_implicite, 1), 'best_odd': round(best_odd, 2), 'avg_odd': round(avg_odd, 2), 'bookie': stats.get('home',{}).get('bookie',''), 'value': is_value_bet})
                            print(f"{Fore.GREEN}   [FAVORI + VALUE] {home_team} vs {away_team}" if is_value_bet else f"{Fore.YELLOW}   [FAVORI] {home_team} vs {away_team}")
                            print(f"   Favori: {nom_favori} | Cote: {round(cote_favori, 2)} | Prob modèle: {round(prob_model_favori, 1)}% | Prob bookmakers: {round(prob_implicite, 1)}%{Style.RESET_ALL}")
                        elif is_value_bet:
                            print(f"{Fore.CYAN}   [VALUE] {home_team} vs {away_team}")
                            print(f"   {nom_favori} | Moyenne: {round(avg_odd, 2)} | Top: {round(best_odd, 2)}{Style.RESET_ALL}")
                    else:
                        still_skipped.append(match)
                else:
                    still_skipped.append(match)
            skipped = still_skipped
    
    if skipped:
        if len(skipped) == len(matchs):
            print(f"   -> Aucune cote affichée pour les {len(skipped)} match(s) de cette ligue (noms non trouvés dans l'API cotes):")
        for match in skipped:
            try:
                h = match.get('teams', {}).get('home', {}).get('name', '?')
                a = match.get('teams', {}).get('away', {}).get('name', '?')
                print(f"   [SKIP] {h} vs {a}")
            except Exception:
                print(f"   [SKIP] (match sans cote)")
        import sys
        sys.stdout.flush()
    
    # Résumé des favoris trouvés
    if favoris_trouves:
        print(f"\n{Fore.MAGENTA}   === RÉSUMÉ: {len(favoris_trouves)} favori(s) trouvé(s) ==={Style.RESET_ALL}")
        for f in favoris_trouves:
            value_tag = " [VALUE]" if f['value'] else ""
            kelly_tag = f" | Kelly: {f['kelly']}%" if f.get('kelly', 0) > 0 else ""
            print(f"   • {f['favori']} ({f['match']})")
            print(f"     Cote: {f['cote']} | Prob modèle: {f['prob_model']}% | Prob bookmakers: {f['prob_bookmakers']}%{value_tag}{kelly_tag}")

# ==========================================
# MAIN LOOP
# ==========================================
def _demander_date_scan():
    """Demande à l'utilisateur quel jour scanner. Retourne (date_scan, lib_jour)."""
    print(f"{Fore.CYAN}+========================================+")
    print(f"|  ALGORITHME D'ANALYSE DE COTES      |")
    print(f"|  Elo + Poisson + XGBoost            |")
    print(f"|  Detection des favoris + Value Bets |")
    print(f"+========================================+{Style.RESET_ALL}")
    print("   Quel jour scanner ?")
    print("   [Enter] = config (config.py) | 0 = aujourd'hui | 1 = demain | 2 = apres-demain | ou date YYYY-MM-DD")
    rep = input("   Votre choix : ").strip()
    if rep == "":
        if DATE_SCAN:
            return DATE_SCAN, "date fixe (config)"
        date_scan = (datetime.today() + timedelta(days=JOUR_A_SCANNER)).strftime('%Y-%m-%d')
        lib = "aujourd'hui" if JOUR_A_SCANNER == 0 else ("demain" if JOUR_A_SCANNER == 1 else f"J+{JOUR_A_SCANNER}")
        return date_scan, lib + " (config)"
    if rep == "0":
        d = datetime.today().strftime('%Y-%m-%d')
        return d, "aujourd'hui"
    if rep == "1":
        d = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        return d, "demain"
    if rep == "2":
        d = (datetime.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        return d, "apres-demain"
    # Tentative de parsing YYYY-MM-DD
    try:
        datetime.strptime(rep, '%Y-%m-%d')
        return rep, "date choisie"
    except ValueError:
        print(f"   {Fore.YELLOW}Format invalide, utilisation de la config.{Style.RESET_ALL}")
        if DATE_SCAN:
            return DATE_SCAN, "date fixe (config)"
        date_scan = (datetime.today() + timedelta(days=JOUR_A_SCANNER)).strftime('%Y-%m-%d')
        lib = "aujourd'hui" if JOUR_A_SCANNER == 0 else ("demain" if JOUR_A_SCANNER == 1 else f"J+{JOUR_A_SCANNER}")
        return date_scan, lib + " (config)"

if __name__ == "__main__":
    date_scan, lib_jour = _demander_date_scan()
    print(f"\n   Scan des matchs du {date_scan} ({lib_jour})\n")
    # Une seule requête "upcoming" pour toutes les ligues (1 crédit)
    _cotes_upcoming = get_cotes_upcoming()
    
    for ligue in LIGUES_A_SCANNER:
        analyse_ligue(ligue, date_jour=date_scan, cotes_upcoming=_cotes_upcoming)
        time.sleep(1) 
        
    print(f"\n{Fore.GREEN}OK Scan termine.{Style.RESET_ALL}")
