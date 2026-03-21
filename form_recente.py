"""
Module pour récupérer la forme récente des équipes depuis l'API
"""

import requests
from datetime import datetime, timedelta
from config import KEY_API_FOOTBALL

def get_recent_fixtures(team_id, league_id, season, max_matches=5):
    """Récupère les derniers matchs d'une équipe"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    
    # Récupérer tous les matchs terminés de l'équipe dans la ligue
    params = {
        "team": team_id,
        "league": league_id,
        "season": season,
        "status": "FT"  # Seulement les matchs terminés
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors'):
            return []
        
        fixtures = data.get('response', [])
        
        # Trier par date (plus récent d'abord) et prendre les N derniers
        fixtures.sort(key=lambda x: x.get('fixture', {}).get('date', ''), reverse=True)
        return fixtures[:max_matches]
    except Exception as e:
        return []

def get_team_id(team_name, league_id, season):
    """Récupère l'ID d'une équipe depuis son nom"""
    url = "https://v3.football.api-sports.io/teams"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    params = {
        "league": league_id,
        "season": season,
        "search": team_name
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors') or not data.get('response'):
            return None
        
        # Prendre la première équipe trouvée
        team = data['response'][0]
        return team['team']['id']
    except:
        return None

def calculate_form_from_fixtures(fixtures, team_name):
    """Calcule la forme récente depuis les fixtures"""
    wins = 0
    draws = 0
    losses = 0
    
    for fixture in fixtures:
        home_team = fixture.get('teams', {}).get('home', {}).get('name', '')
        away_team = fixture.get('teams', {}).get('away', {}).get('name', '')
        
        # Le score peut être dans fixture['score'] directement
        score = fixture.get('score', {}) or fixture.get('fixture', {}).get('score', {})
        
        # Extraire les scores
        home_goals = None
        away_goals = None
        
        if score.get('fulltime'):
            home_goals = score['fulltime'].get('home')
            away_goals = score['fulltime'].get('away')
        
        if home_goals is None and 'home' in score:
            home_goals = score.get('home')
            away_goals = score.get('away')
        
        if home_goals is None or away_goals is None:
            continue
        
        # Déterminer le résultat pour l'équipe
        if home_team == team_name:
            if home_goals > away_goals:
                wins += 1
            elif home_goals == away_goals:
                draws += 1
            else:
                losses += 1
        elif away_team == team_name:
            if away_goals > home_goals:
                wins += 1
            elif away_goals == home_goals:
                draws += 1
            else:
                losses += 1
    
    return {'wins': wins, 'draws': draws, 'losses': losses}

def get_form_recente_api(home_team, away_team, league_id, season, max_matches=5):
    """
    Récupère la forme récente des deux équipes depuis l'API
    
    Retourne: (home_form, away_form)
    """
    # Récupérer les IDs des équipes
    home_team_id = get_team_id(home_team, league_id, season)
    away_team_id = get_team_id(away_team, league_id, season)
    
    home_form = {'wins': 0, 'draws': 0, 'losses': 0}
    away_form = {'wins': 0, 'draws': 0, 'losses': 0}
    
    # Récupérer les matchs récents de l'équipe à domicile
    if home_team_id:
        home_fixtures = get_recent_fixtures(home_team_id, league_id, season, max_matches)
        home_form = calculate_form_from_fixtures(home_fixtures, home_team)
    
    # Récupérer les matchs récents de l'équipe à l'extérieur
    if away_team_id:
        away_fixtures = get_recent_fixtures(away_team_id, league_id, season, max_matches)
        away_form = calculate_form_from_fixtures(away_fixtures, away_team)
    
    return home_form, away_form
