"""
Module pour récupérer les features avancées depuis l'API-Football
- Blessures (injuries)
- Suspensions (sidelined)
- Confrontations directes (head to head)
"""

import requests
from config import KEY_API_FOOTBALL

# ==========================================
# 1. BLESSURES ET SUSPENSIONS
# ==========================================

def get_injuries_suspensions(fixture_id=None, team_id=None, league_id=None, season=None):
    """
    Récupère les blessures et suspensions pour un match ou une équipe
    
    Args:
        fixture_id: ID du match (optionnel)
        team_id: ID de l'équipe (optionnel)
        league_id: ID de la ligue (optionnel, nécessite season)
        season: Saison (optionnel, nécessite league_id ou team_id)
    
    Returns:
        dict avec 'home_injuries', 'away_injuries', 'home_suspensions', 'away_suspensions'
        ou None en cas d'erreur
    """
    url = "https://v3.football.api-sports.io/injuries"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    
    params = {}
    if fixture_id:
        params['fixture'] = fixture_id
    elif team_id and season:
        params['team'] = team_id
        params['season'] = season
    elif league_id and season:
        params['league'] = league_id
        params['season'] = season
    else:
        return None
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors') or not data.get('response'):
            return None
        
        injuries = data.get('response', [])
        
        # Séparer par équipe et type
        result = {
            'home_injuries': 0,
            'away_injuries': 0,
            'home_suspensions': 0,
            'away_suspensions': 0,
            'home_questionable': 0,
            'away_questionable': 0
        }
        
        for injury in injuries:
            team_id_injury = injury.get('team', {}).get('id')
            player_type = injury.get('player', {}).get('type', '')
            reason = injury.get('player', {}).get('reason', '').lower()
            
            # Déterminer si c'est home ou away (nécessite fixture_id pour savoir)
            # Pour l'instant, on compte le total par équipe
            if 'suspended' in reason or 'suspension' in reason:
                if team_id_injury:
                    # On ne peut pas distinguer home/away sans fixture_id
                    # On retournera le total pour l'équipe
                    result['home_suspensions'] += 1  # Temporaire, sera ajusté
            elif player_type == 'Missing Fixture':
                if team_id_injury:
                    result['home_injuries'] += 1  # Temporaire
            elif player_type == 'Questionable':
                if team_id_injury:
                    result['home_questionable'] += 1  # Temporaire
        
        return result
    except Exception as e:
        return None

def get_injuries_for_match(fixture_id, home_team_id, away_team_id):
    """
    Récupère les blessures et suspensions pour un match spécifique
    
    Args:
        fixture_id: ID du match
        home_team_id: ID de l'équipe à domicile
        away_team_id: ID de l'équipe à l'extérieur
    
    Returns:
        dict avec les compteurs par équipe
    """
    url = "https://v3.football.api-sports.io/injuries"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    
    params = {'fixture': fixture_id}
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors') or not data.get('response'):
            return {
                'home_injuries': 0,
                'away_injuries': 0,
                'home_suspensions': 0,
                'away_suspensions': 0,
                'home_questionable': 0,
                'away_questionable': 0
            }
        
        injuries = data.get('response', [])
        
        result = {
            'home_injuries': 0,
            'away_injuries': 0,
            'home_suspensions': 0,
            'away_suspensions': 0,
            'home_questionable': 0,
            'away_questionable': 0
        }
        
        for injury in injuries:
            team_id_injury = injury.get('team', {}).get('id')
            player_type = injury.get('player', {}).get('type', '')
            reason = injury.get('player', {}).get('reason', '').lower()
            
            is_suspended = 'suspended' in reason or 'suspension' in reason
            is_missing = player_type == 'Missing Fixture'
            is_questionable = player_type == 'Questionable'
            
            if team_id_injury == home_team_id:
                if is_suspended:
                    result['home_suspensions'] += 1
                elif is_missing:
                    result['home_injuries'] += 1
                elif is_questionable:
                    result['home_questionable'] += 1
            elif team_id_injury == away_team_id:
                if is_suspended:
                    result['away_suspensions'] += 1
                elif is_missing:
                    result['away_injuries'] += 1
                elif is_questionable:
                    result['away_questionable'] += 1
        
        return result
    except Exception as e:
        return {
            'home_injuries': 0,
            'away_injuries': 0,
            'home_suspensions': 0,
            'away_suspensions': 0,
            'home_questionable': 0,
            'away_questionable': 0
        }

# ==========================================
# 2. CONFRONTATIONS DIRECTES (HEAD TO HEAD)
# ==========================================

def get_head_to_head(home_team_id, away_team_id, league_id=None, season=None, last=5):
    """
    Récupère l'historique des confrontations directes entre deux équipes
    
    Args:
        home_team_id: ID de l'équipe à domicile
        away_team_id: ID de l'équipe à l'extérieur
        league_id: ID de la ligue (optionnel)
        season: Saison (optionnel)
        last: Nombre de matchs à récupérer (défaut: 5)
    
    Returns:
        dict avec les statistiques H2H:
        - home_wins: Victoires équipe home
        - away_wins: Victoires équipe away
        - draws: Matchs nuls
        - total_matches: Total de matchs
        - home_goals_avg: Moyenne de buts marqués par home
        - away_goals_avg: Moyenne de buts marqués par away
    """
    url = "https://v3.football.api-sports.io/fixtures/headtohead"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    
    params = {
        'h2h': f"{home_team_id}-{away_team_id}",
        'last': last
    }
    
    if league_id:
        params['league'] = league_id
    if season:
        params['season'] = season
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors') or not data.get('response'):
            return {
                'home_wins': 0,
                'away_wins': 0,
                'draws': 0,
                'total_matches': 0,
                'home_goals_avg': 0.0,
                'away_goals_avg': 0.0,
                'home_goals_total': 0,
                'away_goals_total': 0
            }
        
        fixtures = data.get('response', [])
        
        home_wins = 0
        away_wins = 0
        draws = 0
        home_goals_total = 0
        away_goals_total = 0
        
        for fixture in fixtures:
            fixture_data = fixture.get('fixture', {})
            if fixture_data.get('status', {}).get('short') != 'FT':
                continue
            
            home_team = fixture.get('teams', {}).get('home', {})
            away_team = fixture.get('teams', {}).get('away', {})
            goals = fixture.get('goals', {})
            
            home_goals = goals.get('home', 0) or 0
            away_goals = goals.get('away', 0) or 0
            
            home_goals_total += home_goals
            away_goals_total += away_goals
            
            # Déterminer le résultat selon l'équipe qui était "home" dans ce match
            # On compare avec les IDs pour savoir qui a gagné
            home_id_in_fixture = home_team.get('id')
            away_id_in_fixture = away_team.get('id')
            
            if home_id_in_fixture == home_team_id:
                # L'équipe home actuelle était home dans ce match
                if home_goals > away_goals:
                    home_wins += 1
                elif away_goals > home_goals:
                    away_wins += 1
                else:
                    draws += 1
            elif home_id_in_fixture == away_team_id:
                # L'équipe home actuelle était away dans ce match
                if away_goals > home_goals:
                    home_wins += 1
                elif home_goals > away_goals:
                    away_wins += 1
                else:
                    draws += 1
        
        total_matches = home_wins + away_wins + draws
        
        return {
            'home_wins': home_wins,
            'away_wins': away_wins,
            'draws': draws,
            'total_matches': total_matches,
            'home_goals_avg': home_goals_total / total_matches if total_matches > 0 else 0.0,
            'away_goals_avg': away_goals_total / total_matches if total_matches > 0 else 0.0,
            'home_goals_total': home_goals_total,
            'away_goals_total': away_goals_total
        }
    except Exception as e:
        return {
            'home_wins': 0,
            'away_wins': 0,
            'draws': 0,
            'total_matches': 0,
            'home_goals_avg': 0.0,
            'away_goals_avg': 0.0,
            'home_goals_total': 0,
            'away_goals_total': 0
        }

def get_team_id_from_name(team_name, league_id, season):
    """
    Récupère l'ID d'une équipe à partir de son nom
    
    Args:
        team_name: Nom de l'équipe
        league_id: ID de la ligue
        season: Saison
    
    Returns:
        ID de l'équipe ou None
    """
    url = "https://v3.football.api-sports.io/teams"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    
    params = {
        'league': league_id,
        'season': season,
        'search': team_name[:3]  # Recherche avec les 3 premiers caractères
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors') or not data.get('response'):
            return None
        
        teams = data.get('response', [])
        
        # Chercher la meilleure correspondance
        from fuzz_fallback import fuzz
        
        best_match = None
        best_score = 0
        
        for team in teams:
            team_name_api = team.get('team', {}).get('name', '')
            score = fuzz.token_sort_ratio(team_name.lower(), team_name_api.lower())
            if score > best_score:
                best_score = score
                best_match = team
        
        if best_match and best_score >= 70:
            return best_match.get('team', {}).get('id')
        
        return None
    except Exception as e:
        return None
