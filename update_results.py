"""
Script de mise à jour des résultats réels des prédictions loggées.
À lancer manuellement (ou en cron) après les matchs.

Pour chaque prédiction sans résultat dans predictions_log.json,
récupère le score final via API-Football et met à jour le log.
"""
import json
import os
import time
import requests
from datetime import datetime, timedelta
from prediction_tracker import update_result, print_stats, _load_log
from config import KEY_API_FOOTBALL

HEADERS = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': KEY_API_FOOTBALL
}


def _fetch_result_by_fixture_id(fixture_id):
    """Récupère le résultat d'un match via son fixture_id."""
    try:
        r = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=HEADERS,
            params={"id": fixture_id},
            timeout=10
        )
        r.raise_for_status()
        data = r.json().get('response', [])
        if not data:
            return None
        fixture = data[0]
        status = fixture.get('fixture', {}).get('status', {}).get('short', '')
        if status != 'FT':
            return None  # Pas encore terminé
        goals = fixture.get('goals', {})
        home_g = goals.get('home')
        away_g = goals.get('away')
        if home_g is None or away_g is None:
            return None
        if home_g > away_g:
            return 'home'
        elif home_g < away_g:
            return 'away'
        return 'draw'
    except Exception:
        return None


def _fetch_result_by_date_teams(date, league_name, home_team, away_team):
    """
    Cherche le résultat en cherchant les matchs du jour dans toutes les ligues connues.
    Utilisé en fallback si fixture_id absent.
    """
    LEAGUE_IDS = {
        "Premier League (Ang)": 39,
        "Ligue 1 (Fra)": 61,
        "La Liga (Esp)": 140,
        "Bundesliga (All)": 78,
        "Serie A (Ita)": 135,
        "Ligue des Champions": 2,
        "Europa League": 3,
        "Conference League": 848,
    }
    league_id = LEAGUE_IDS.get(league_name)
    if not league_id:
        return None

    try:
        r = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=HEADERS,
            params={"date": date, "league": league_id},
            timeout=10
        )
        r.raise_for_status()
        fixtures = r.json().get('response', [])
    except Exception:
        return None

    home_lower = home_team.lower()
    away_lower = away_team.lower()
    for f in fixtures:
        status = f.get('fixture', {}).get('status', {}).get('short', '')
        if status != 'FT':
            continue
        h = (f.get('teams', {}).get('home', {}).get('name') or '').lower()
        a = (f.get('teams', {}).get('away', {}).get('name') or '').lower()
        if home_lower in h or h in home_lower:
            if away_lower in a or a in away_lower:
                goals = f.get('goals', {})
                hg = goals.get('home')
                ag = goals.get('away')
                if hg is None or ag is None:
                    return None
                if hg > ag:
                    return 'home'
                elif hg < ag:
                    return 'away'
                return 'draw'
    return None


def update_all_pending():
    """
    Récupère les résultats de toutes les prédictions non résolues
    dont la date est passée d'au moins 2 heures.
    """
    log = _load_log()
    pending = [
        e for e in log
        if e.get('actual_result') is None
        and e.get('date', '') <= (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d')
    ]

    if not pending:
        print("   [UPDATE] Aucune prédiction en attente de résultat.")
        return

    print(f"   [UPDATE] {len(pending)} prédiction(s) à mettre à jour...")
    updated_count = 0
    not_found = 0

    for entry in pending:
        date       = entry.get('date', '')
        home_team  = entry.get('home_team', '')
        away_team  = entry.get('away_team', '')
        league     = entry.get('league', '')
        fixture_id = entry.get('fixture_id')

        result = None
        if fixture_id:
            result = _fetch_result_by_fixture_id(fixture_id)

        if result is None:
            result = _fetch_result_by_date_teams(date, league, home_team, away_team)

        if result:
            ok = update_result(date, home_team, away_team, result)
            if ok:
                correct = (entry.get('predicted_outcome') == result)
                icon = "OK" if correct else "KO"
                print(f"   [{icon}] {home_team} vs {away_team} ({date}) : predit={entry.get('predicted_outcome')} reel={result}")
                updated_count += 1
        else:
            not_found += 1

        time.sleep(0.5)  # Respecter les limites de l'API

    print(f"\n   [UPDATE] Terminé : {updated_count} mis à jour, {not_found} non trouvés.")


if __name__ == "__main__":
    print("=" * 50)
    print("  MISE À JOUR DES RÉSULTATS")
    print("=" * 50)
    update_all_pending()
    print()
    print_stats()
