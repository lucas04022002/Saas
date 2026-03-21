"""
Script pour récupérer toutes les cotes d'une saison complète et les sauvegarder.
Par défaut : récupère toutes les ligues (dont LDC) pour la saison 2025-2026.
Usage: python collect_odds_season.py [saison]
Exemple: python collect_odds_season.py 2025  (toutes les ligues saison 2025)
"""
import requests
import json
import time
from datetime import datetime, timedelta
from config import KEY_API_FOOTBALL, KEY_THE_ODDS
from odds_logger import save_odds
from fuzz_fallback import fuzz

def get_fixtures_for_season(league_id, season):
    """Récupère tous les matchs d'une saison"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': KEY_API_FOOTBALL}
    params = {"league": league_id, "season": season}
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get('errors'):
            print(f"   [ERREUR API] {data.get('errors')}")
            return []
        return data.get('response', [])
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return []


def get_odds_for_match(home_team, away_team, ligue_key):
    """Récupère les cotes pour un match via The-Odds-API"""
    url = f'https://api.the-odds-api.com/v4/sports/{ligue_key}/odds'
    params = {'apiKey': KEY_THE_ODDS, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            # Chercher le match avec fuzzy matching
            for match_odds in data:
                home_odds = match_odds.get('home_team', '')
                away_odds = match_odds.get('away_team', '')
                score_home = fuzz.token_sort_ratio(home_team.lower(), home_odds.lower())
                score_away = fuzz.token_sort_ratio(away_team.lower(), away_odds.lower())
                if score_home >= 85 and score_away >= 85:
                    return match_odds, home_odds, away_odds
            # Essayer inversé
            for match_odds in data:
                home_odds = match_odds.get('home_team', '')
                away_odds = match_odds.get('away_team', '')
                score_home_inv = fuzz.token_sort_ratio(home_team.lower(), away_odds.lower())
                score_away_inv = fuzz.token_sort_ratio(away_team.lower(), home_odds.lower())
                if score_home_inv >= 85 and score_away_inv >= 85:
                    return match_odds, away_odds, home_odds  # Inversé
        return None, None, None
    except Exception as e:
        return None, None, None


def analyser_cotes_match(match_data, home_odds_name, away_odds_name):
    """Analyse les cotes d'un match et retourne les stats"""
    if not match_data or not match_data.get('bookmakers'):
        return None
    
    stats = {
        'home': {'cotes': [], 'moyenne': 0},
        'away': {'cotes': [], 'moyenne': 0},
        'draw': {'cotes': [], 'moyenne': 0}
    }
    
    home_odds_lower = home_odds_name.lower() if home_odds_name else ''
    away_odds_lower = away_odds_name.lower() if away_odds_name else ''
    
    for bookie in match_data['bookmakers']:
        for market in bookie['markets']:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    team_name = outcome['name']
                    price = outcome['price']
                    team_name_lower = team_name.lower()
                    
                    # Identifier quel équipe correspond avec matching flou
                    score_home = fuzz.token_sort_ratio(team_name_lower, home_odds_lower)
                    score_away = fuzz.token_sort_ratio(team_name_lower, away_odds_lower)
                    
                    if 'draw' in team_name_lower or 'nul' in team_name_lower or 'tie' in team_name_lower:
                        stats['draw']['cotes'].append(price)
                    elif score_home >= 90 or (score_home >= 80 and score_home > score_away):
                        stats['home']['cotes'].append(price)
                    elif score_away >= 90 or (score_away >= 80 and score_away > score_home):
                        stats['away']['cotes'].append(price)
    
    for key in ['home', 'away', 'draw']:
        if stats[key]['cotes']:
            stats[key]['moyenne'] = sum(stats[key]['cotes']) / len(stats[key]['cotes'])
    
    return stats


def collect_odds_for_season(league_id, league_name, ligue_key, season):
    """Récupère toutes les cotes d'une saison"""
    print(f"\n📊 Collecte des cotes pour {league_name} (saison {season})")
    print("-" * 50)
    
    fixtures = get_fixtures_for_season(league_id, season)
    if not fixtures:
        print(f"   Aucun match trouvé pour la saison {season}")
        return 0
    
    print(f"   {len(fixtures)} matchs trouvés")
    
    saved = 0
    skipped = 0
    
    for i, fixture in enumerate(fixtures):
        fixture_data = fixture.get('fixture', {})
        match_date = fixture_data.get('date', '')[:10] if fixture_data.get('date') else None
        
        if not match_date:
            skipped += 1
            continue
        
        home_team = fixture.get('teams', {}).get('home', {}).get('name', '')
        away_team = fixture.get('teams', {}).get('away', {}).get('name', '')
        
        if not home_team or not away_team:
            skipped += 1
            continue
        
        # Récupérer les cotes
        match_odds, home_odds_name, away_odds_name = get_odds_for_match(home_team, away_team, ligue_key)
        
        if match_odds:
            stats = analyser_cotes_match(match_odds, home_odds_name, away_odds_name)
            if stats and stats['home']['moyenne'] > 0:
                save_odds(match_date, home_team, away_team, stats)
                saved += 1
            else:
                skipped += 1
        else:
            skipped += 1
        
        if (i + 1) % 50 == 0:
            print(f"   → {i + 1}/{len(fixtures)} matchs traités ({saved} cotes sauvegardées)")
        
        time.sleep(0.5)  # Pause pour respecter les quotas API
    
    print(f"   ✓ Terminé: {saved} cotes sauvegardées, {skipped} matchs sans cotes")
    return saved


if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    LIGUES = [
        {"id": 39, "nom": "Premier League", "key": "soccer_epl"},
        {"id": 61, "nom": "Ligue 1", "key": "soccer_france_ligue_one"},
        {"id": 140, "nom": "La Liga", "key": "soccer_spain_la_liga"},
        {"id": 78, "nom": "Bundesliga", "key": "soccer_germany_bundesliga"},
        {"id": 135, "nom": "Serie A", "key": "soccer_italy_serie_a"},
        {"id": 2, "nom": "Ligue des Champions", "key": "soccer_uefa_champs_league"}
    ]
    
    # Saison par défaut : 2025 (2025-2026)
    now = datetime.now()
    default_season = now.year - 1 if now.month < 7 else now.year
    
    if len(sys.argv) > 1:
        season = int(sys.argv[1])
    else:
        season = default_season
    
    print("=" * 50)
    print(f"COLLECTE DES COTES - SAISON {season} ({season}-{season+1})")
    print("=" * 50)
    print(f"Ligues à traiter: {len(LIGUES)}")
    for ligue in LIGUES:
        print(f"  - {ligue['nom']} (id: {ligue['id']})")
    print()
    
    total_saved = 0
    for ligue in LIGUES:
        # Pour la LDC, ajuster la saison si nécessaire (janvier = saison précédente)
        ligue_season = season
        if ligue['id'] == 2 and now.month < 7:
            ligue_season = season - 1
        
        saved = collect_odds_for_season(ligue['id'], ligue['nom'], ligue['key'], ligue_season)
        total_saved += saved
        print()  # Ligne vide entre ligues
    
    print("=" * 50)
    print(f"✓ Collecte terminée ! Total: {total_saved} cotes sauvegardées")
    print("=" * 50)
