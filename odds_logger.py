"""
Module pour logger les cotes bookmakers afin de les réutiliser lors de l'entraînement.
Sauvegarde dans historical_odds.json : {date_team1_team2: {home_avg, draw_avg, away_avg}}
"""
import json
import os
from datetime import datetime

ODDS_FILE = "historical_odds.json"


def save_odds(date_str, home_team, away_team, stats):
    """
    Sauvegarde les cotes moyennes pour un match.
    
    Args:
        date_str: Date au format YYYY-MM-DD
        home_team: Nom équipe domicile
        away_team: Nom équipe extérieur
        stats: Dict avec 'home', 'draw', 'away' contenant 'moyenne'
    """
    if not stats or not stats.get('home', {}).get('moyenne'):
        return
    
    # Charger les cotes existantes
    if os.path.exists(ODDS_FILE):
        try:
            with open(ODDS_FILE, 'r') as f:
                all_odds = json.load(f)
        except:
            all_odds = {}
    else:
        all_odds = {}
    
    # Clé : date_home_away (normalisée)
    key = f"{date_str}_{home_team}_{away_team}"
    
    all_odds[key] = {
        'date': date_str,
        'home_team': home_team,
        'away_team': away_team,
        'home_avg': stats['home']['moyenne'],
        'draw_avg': stats['draw']['moyenne'],
        'away_avg': stats['away']['moyenne'],
        'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Sauvegarder
    with open(ODDS_FILE, 'w') as f:
        json.dump(all_odds, f, indent=2)


def load_odds(date_str, home_team, away_team):
    """
    Charge les cotes pour un match historique.
    
    Returns:
        Dict avec 'home_avg', 'draw_avg', 'away_avg' ou None si pas trouvé
    """
    if not os.path.exists(ODDS_FILE):
        return None
    
    try:
        with open(ODDS_FILE, 'r') as f:
            all_odds = json.load(f)
    except:
        return None
    
    # Chercher avec plusieurs variantes de clé (normalisation des noms)
    key_variants = [
        f"{date_str}_{home_team}_{away_team}",
        f"{date_str}_{away_team}_{home_team}",  # Inversé
    ]
    
    for key in key_variants:
        if key in all_odds:
            odds_data = all_odds[key]
            return {
                'home_avg': odds_data.get('home_avg', 0),
                'draw_avg': odds_data.get('draw_avg', 0),
                'away_avg': odds_data.get('away_avg', 0)
            }
    
    return None
