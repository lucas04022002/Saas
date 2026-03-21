"""
Module pour récupérer et mettre à jour les données nécessaires au modèle
- Stats de saison pour Poisson
- Historique pour initialiser Elo
- Données pour entraîner XGBoost
"""

import requests
import json
import os
from datetime import datetime
from prediction_engine import EloRating, PoissonPredictor
from config import KEY_API_FOOTBALL

# Configuration API
# Les clés API sont maintenant dans config.py
# Modifiez config.py pour ajouter vos clés API

# Fichiers de sauvegarde
STATS_FILE = "team_stats.json"
ELO_HISTORY_FILE = "elo_history.json"

# ==========================================
# 1. RÉCUPÉRATION DES STATS DE SAISON
# ==========================================

def get_team_statistics(team_id, league_id, season):
    """Récupère les statistiques d'une équipe pour une saison"""
    url = "https://v3.football.api-sports.io/teams/statistics"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    params = {
        "team": team_id,
        "league": league_id,
        "season": season
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors'):
            print(f"   [ERREUR] {data.get('errors')}")
            return None
        
        response = data.get('response', {})
        if not response:
            return None
        
        # Extraire les stats importantes
        fixtures = response.get('fixtures', {})
        goals = response.get('goals', {})
        
        matches_played = fixtures.get('played', {}).get('total', 0)
        goals_for = goals.get('for', {}).get('total', {}).get('total', 0)
        goals_against = goals.get('against', {}).get('total', {}).get('total', 0)
        
        return {
            'matches_played': matches_played,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'avg_goals_for': goals_for / matches_played if matches_played > 0 else 0,
            'avg_goals_against': goals_against / matches_played if matches_played > 0 else 0
        }
    except Exception as e:
        print(f"   [ERREUR] Problème lors de la récupération des stats: {e}")
        return None

def get_all_teams_stats(league_id, season):
    """Récupère les stats de toutes les équipes d'une ligue"""
    # D'abord, récupérer la liste des équipes
    url = "https://v3.football.api-sports.io/teams"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    params = {"league": league_id, "season": season}
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors'):
            return {}
        
        teams = data.get('response', [])
        stats_dict = {}
        
        print(f"   Récupération des stats pour {len(teams)} équipes...")
        
        for team in teams:
            team_id = team['team']['id']
            team_name = team['team']['name']
            
            print(f"   → {team_name}...", end=" ")
            stats = get_team_statistics(team_id, league_id, season)
            
            if stats:
                stats_dict[team_name] = stats
                print(f"✓ ({stats['matches_played']} matchs)")
            else:
                print("✗")
            
            # Pause pour respecter les quotas API
            import time
            time.sleep(0.5)
        
        return stats_dict
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return {}

def save_team_stats(stats_dict, league_name):
    """Sauvegarde les stats dans un fichier"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            all_stats = json.load(f)
    else:
        all_stats = {}
    
    all_stats[league_name] = {
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stats': stats_dict
    }
    
    with open(STATS_FILE, 'w') as f:
        json.dump(all_stats, f, indent=2)
    
    print(f"   ✓ Stats sauvegardées dans {STATS_FILE}")

def load_team_stats(league_name):
    """Charge les stats depuis un fichier"""
    if not os.path.exists(STATS_FILE):
        return {}
    
    try:
        with open(STATS_FILE, 'r') as f:
            all_stats = json.load(f)
        return all_stats.get(league_name, {}).get('stats', {})
    except Exception:
        return {}


# Ligues europeennes : on ne remplit que les equipes absentes (pour ne pas ecraser les stats domestiques)
FILL_ONLY_LEAGUES = {"Ligue des Champions", "UEFA Europa League", "UEFA Europa Conference League"}


def load_team_stats_into_poisson(poisson_predictor):
    """
    Charge toutes les stats du fichier team_stats.json dans le Poisson.
    Les ligues domestiques sont chargees en premier ; pour les ligues UEFA (LDC, etc.),
    on n'ajoute que les equipes pas deja presentes (stats domestiques prioritaires).
    """
    if not os.path.exists(STATS_FILE):
        return
    try:
        with open(STATS_FILE, 'r') as f:
            all_stats = json.load(f)
    except Exception:
        return
    # D'abord les ligues non-UEFA (domestiques)
    for league_name, data in all_stats.items():
        if league_name in FILL_ONLY_LEAGUES:
            continue
        stats_dict = data.get('stats', {})
        for team_name, stats in stats_dict.items():
            poisson_predictor.update_stats(
                team_name,
                stats['goals_for'],
                stats['goals_against'],
                stats['matches_played']
            )
    # Puis UEFA : seulement les equipes manquantes
    for league_name in FILL_ONLY_LEAGUES:
        if league_name not in all_stats:
            continue
        stats_dict = all_stats[league_name].get('stats', {})
        for team_name, stats in stats_dict.items():
            if team_name not in poisson_predictor.team_stats:
                poisson_predictor.update_stats(
                    team_name,
                    stats['goals_for'],
                    stats['goals_against'],
                    stats['matches_played']
                )
    return


def update_poisson_with_stats(poisson_predictor, league_name, league_id, season):
    """Met à jour le prédicteur Poisson avec les stats réelles.
    Pour les ligues UEFA (LDC, etc.), n'ajoute que les équipes pas déjà présentes."""
    # Charger les stats existantes
    stats_dict = load_team_stats(league_name)
    
    # Si pas de stats ou stats anciennes, les récupérer
    if not stats_dict:
        print(f"   Récupération des stats pour {league_name}...")
        stats_dict = get_all_teams_stats(league_id, season)
        save_team_stats(stats_dict, league_name)
    
    fill_only = league_name in FILL_ONLY_LEAGUES
    added = 0
    for team_name, stats in stats_dict.items():
        if fill_only and team_name in poisson_predictor.team_stats:
            continue
        poisson_predictor.update_stats(
            team_name,
            stats['goals_for'],
            stats['goals_against'],
            stats['matches_played']
        )
        added += 1
    
    print(f"   ✓ Poisson mis à jour avec {added} équipes ({league_name})")
    return added

# ==========================================
# 2. INITIALISATION ELO AVEC HISTORIQUE
# ==========================================

def get_historical_fixtures(league_id, season):
    """Récupère tous les matchs d'une saison"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    params = {
        "league": league_id,
        "season": season
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors'):
            return []
        
        fixtures = data.get('response', [])
        return fixtures
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return []

def initialize_elo_from_history(elo_rating, league_id, league_name, seasons=[2023, 2024]):
    """Initialise les ratings Elo avec l'historique"""
    print(f"\n   Initialisation Elo pour {league_name}...")
    
    all_fixtures = []
    
    # Récupérer les matchs de toutes les saisons
    for season in seasons:
        print(f"   → Récupération saison {season}...", end=" ")
        fixtures = get_historical_fixtures(league_id, season)
        all_fixtures.extend(fixtures)
        print(f"✓ ({len(fixtures)} matchs)")
        
        import time
        time.sleep(1)  # Pause pour API
    
    print(f"   Total: {len(all_fixtures)} matchs historiques")
    
    # Trier par date (plus ancien d'abord)
    all_fixtures.sort(key=lambda x: x.get('fixture', {}).get('date', ''))
    
    # Rejouer chaque match pour mettre à jour les ratings
    processed = 0
    for fixture in all_fixtures:
        fixture_data = fixture.get('fixture', {})
        # Score peut être dans fixture['score'] ou fixture['fixture']['score']
        score = fixture.get('score', {}) or fixture_data.get('score', {})
        home_team_data = fixture.get('teams', {}).get('home', {})
        away_team_data = fixture.get('teams', {}).get('away', {})
        
        home_team = home_team_data.get('name', '')
        away_team = away_team_data.get('name', '')
        
        # Vérifier si le match est terminé
        if fixture_data.get('status', {}).get('short') != 'FT':
            continue
        
        # Récupérer les scores (plusieurs formats possibles selon l'API)
        home_goals = None
        away_goals = None
        if score.get('fulltime'):
            home_goals = score['fulltime'].get('home')
            away_goals = score['fulltime'].get('away')
        if home_goals is None and 'home' in score:
            home_goals = score.get('home')
            away_goals = score.get('away')
        if home_goals is None and 'goals' in fixture:
            goals = fixture.get('goals', {})
            home_goals = goals.get('home')
            away_goals = goals.get('away')
        
        if home_goals is None or away_goals is None:
            continue
        
        # Mettre à jour les ratings Elo
        elo_rating.update_ratings(home_team, away_team, home_goals, away_goals)
        processed += 1
        
        if processed % 50 == 0:
            print(f"   → {processed}/{len(all_fixtures)} matchs traités...")
    
    print(f"   ✓ Elo initialisé avec {processed} matchs")
    elo_rating.save_ratings()
    
    return processed

# ==========================================
# 3. FONCTION PRINCIPALE
# ==========================================

def update_all_data(leagues_config, seasons=[2023, 2024]):
    """
    Met à jour toutes les données nécessaires
    
    leagues_config: Liste de dicts avec 'nom', 'id_foot', 'key_odds'
    """
    print("=" * 50)
    print("MISE À JOUR DES DONNÉES")
    print("=" * 50)
    
    poisson = PoissonPredictor()
    elo = EloRating()
    
    now = datetime.now()
    for league in leagues_config:
        league_name = league['nom']
        league_id = league['id_foot']
        # Ligue des Champions (2) : saison = année de début (ex. jan 2026 -> 2025)
        if league_id == 2:
            season = now.year - 1 if now.month < 7 else now.year
        else:
            season = seasons[-1]
        
        print(f"\n[LIGUE] {league_name} (saison {season})")
        print("-" * 50)
        
        # 1. Mettre à jour Poisson avec stats réelles
        print("1. Mise à jour Poisson...")
        update_poisson_with_stats(poisson, league_name, league_id, season)
        
        # 2. Initialiser Elo avec historique
        print("\n2. Initialisation Elo...")
        initialize_elo_from_history(elo, league_id, league_name, seasons)
        
        print(f"\n✓ {league_name} terminé\n")
    
    print("=" * 50)
    print("✓ Mise à jour terminée !")
    print("=" * 50)
    
    return poisson, elo

# ==========================================
# EXEMPLE D'UTILISATION
# ==========================================

def _current_season_year():
    """Année de début de la saison en cours (ex: janv 2026 -> 2025 pour 2025-26)."""
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1

if __name__ == "__main__":
    # Configuration des ligues
    LIGUES = [
        {"nom": "Premier League (Ang)", "id_foot": 39, "key_odds": "soccer_epl"},
        {"nom": "Ligue 1 (Fra)", "id_foot": 61, "key_odds": "soccer_france_ligue_one"},
        {"nom": "La Liga (Esp)", "id_foot": 140, "key_odds": "soccer_spain_la_liga"},
        {"nom": "Bundesliga (All)", "id_foot": 78, "key_odds": "soccer_germany_bundesliga"},
        {"nom": "Serie A (Ita)", "id_foot": 135, "key_odds": "soccer_italy_serie_a"},
        {"nom": "Ligue des Champions", "id_foot": 2, "key_odds": "soccer_uefa_champs_league"}
    ]
    
    # Inclure la saison en cours pour avoir les matchs récents (dont cette semaine)
    current = _current_season_year()
    seasons = [current - 2, current - 1, current]  # ex: [2023, 2024, 2025] en 2025-26
    print(f"Saisons utilisées: {seasons} (saison en cours: {current})")
    
    # Mettre à jour les données
    poisson, elo = update_all_data(LIGUES, seasons=seasons)
