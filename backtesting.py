"""
Système de backtesting : Teste les prédictions sur données historiques
Évalue les performances du modèle sur des matchs passés
"""

import requests
import json
from datetime import datetime, timedelta
from prediction_engine import AdvancedPredictor, EloRating, PoissonPredictor
from data_collector import load_team_stats
from draw_policy import load_thresholds_map, select_recommended_outcome
from form_recente import get_form_recente_api
from odds_logger import load_odds
from features_avancees import get_injuries_for_match, get_head_to_head
from config import KEY_API_FOOTBALL, SAISON

_DRAW_THRESHOLDS = load_thresholds_map()

# ==========================================
# 1. RÉCUPÉRATION DES MATCHS DE TEST
# ==========================================

def get_test_fixtures(league_id, season, start_date, end_date):
    """Récupère les matchs terminés dans une période pour le backtesting (une saison)"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': KEY_API_FOOTBALL
    }
    params = {
        "league": league_id,
        "season": season,
        "from": start_date,
        "to": end_date
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors'):
            return []
        
        fixtures = data.get('response', [])
        fixtures_terminated = [f for f in fixtures if f.get('fixture', {}).get('status', {}).get('short') == 'FT']
        return fixtures_terminated
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return []


def get_season_from_fixture_date(date_str):
    """Déduit la saison (année de début) à partir de la date du match. Ex: 2025-06-01 -> 2024 (2024-25), 2025-08-01 -> 2025 (2025-26)."""
    if not date_str:
        return 2024
    try:
        year = int(date_str[:4])
        month = int(date_str[5:7])
        if month >= 8:  # Août -> décembre = début de saison
            return year
        return year - 1  # Janvier -> juin = fin de saison précédente
    except (ValueError, IndexError):
        return 2024


def get_test_fixtures_multi_season(league_id, seasons, start_date, end_date):
    """Récupère les matchs pour plusieurs saisons et les fusionne (dédupliqués par id)."""
    import time
    seen_ids = set()
    all_fixtures = []
    for season in seasons:
        fixtures = get_test_fixtures(league_id, season, start_date, end_date)
        for f in fixtures:
            fid = f.get('fixture', {}).get('id')
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                all_fixtures.append(f)
        if len(seasons) > 1 and fixtures:
            print(f"      Saison {season}: {len(fixtures)} matchs")
        if len(seasons) > 1:
            time.sleep(1)
    return all_fixtures

# ==========================================
# 2. BACKTESTING
# ==========================================

def backtest_match(predictor, fixture, league_id, season):
    """Teste une prédiction sur un match historique"""
    fixture_data = fixture.get('fixture', {})
    score = fixture.get('score', {}) or fixture_data.get('score', {})
    home_team_data = fixture.get('teams', {}).get('home', {})
    away_team_data = fixture.get('teams', {}).get('away', {})
    
    home_team = home_team_data.get('name', '')
    away_team = away_team_data.get('name', '')
    
    # Extraire les scores réels (plusieurs formats API)
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
        return None
    
    # Déterminer le résultat réel
    if home_goals > away_goals:
        actual_result = 'home'
    elif home_goals == away_goals:
        actual_result = 'draw'
    else:
        actual_result = 'away'
    
    # Récupérer les IDs des équipes depuis le fixture
    home_team_id = home_team_data.get('id')
    away_team_id = away_team_data.get('id')
    fixture_id = fixture_data.get('id')
    
    # Récupérer la forme récente (si disponible)
    try:
        home_form, away_form = get_form_recente_api(
            home_team, away_team, league_id, season, max_matches=5
        )
    except:
        home_form, away_form = None, None
    
    # Récupérer blessures et suspensions
    injuries = None
    try:
        if fixture_id and home_team_id and away_team_id:
            injuries = get_injuries_for_match(fixture_id, home_team_id, away_team_id)
    except:
        injuries = None
    
    # Récupérer confrontations directes (H2H)
    h2h = None
    try:
        if home_team_id and away_team_id:
            h2h = get_head_to_head(
                home_team_id, away_team_id,
                league_id=league_id,
                season=season,
                last=5
            )
    except:
        h2h = None
    
    # Faire la prédiction
    try:
        prediction = predictor.predict_match(
            home_team, away_team,
            home_form=home_form, away_form=away_form,
            injuries=injuries, h2h=h2h,
            league_id=league_id,
        )
        prob_model = prediction['probabilities']
        
        # Même logique que la production backend (avec seuils par ligue).
        predicted_result, _, predicted_prob_pct = select_recommended_outcome(
            prob_model,
            home_team,
            away_team,
            league_id=league_id,
            league_name=None,
            thresholds_map=_DRAW_THRESHOLDS,
        )
        predicted_prob = predicted_prob_pct / 100.0
        
        # Vérifier si la prédiction est correcte
        is_correct = (predicted_result == actual_result)
        
        # Charger les cotes historiques si disponibles
        match_date = fixture_data.get('date', '')[:10]
        historical_odds = load_odds(match_date, home_team, away_team)
        predicted_odd = None
        if historical_odds:
            predicted_odd = historical_odds.get(f"{predicted_result}_avg")

        return {
            'home_team': home_team,
            'away_team': away_team,
            'actual_result': actual_result,
            'predicted_result': predicted_result,
            'predicted_prob': predicted_prob,
            'is_correct': is_correct,
            'probabilities': prob_model,
            'score': f"{home_goals}-{away_goals}",
            'predicted_odd': predicted_odd,  # cote bookmaker sur l'outcome prédit (ou None)
        }
    except Exception as e:
        return None

def backtest_league(league_id, league_name, seasons, start_date, end_date):
    """Effectue le backtesting pour une ligue. seasons: int (ex. 2024) ou list (ex. [2024, 2025])."""
    season_list = [seasons] if isinstance(seasons, int) else seasons
    print(f"\n{'='*60}")
    print(f"BACKTESTING: {league_name}")
    print(f"Période: {start_date} à {end_date}")
    print(f"Saison(s): {season_list}")
    print(f"{'='*60}")
    
    # Initialiser le prédicteur
    predictor = AdvancedPredictor()
    
    # Charger les stats Poisson si disponibles
    stats_dict = load_team_stats(league_name)
    if stats_dict:
        for team_name, stats in stats_dict.items():
            predictor.poisson.update_stats(
                team_name,
                stats['goals_for'],
                stats['goals_against'],
                stats['matches_played'],
                league_id=league_id,
            )
    
    # Récupérer les matchs de test (une ou plusieurs saisons)
    print(f"\nRécupération des matchs de test...")
    if len(season_list) > 1:
        fixtures = get_test_fixtures_multi_season(league_id, season_list, start_date, end_date)
    else:
        fixtures = get_test_fixtures(league_id, season_list[0], start_date, end_date)
    
    if not fixtures:
        print(f"   [ERREUR] Aucun match trouvé pour cette période")
        return None
    
    print(f"   {len(fixtures)} matchs trouvés")
    
    # Trier par date
    fixtures.sort(key=lambda x: x.get('fixture', {}).get('date', ''))
    
    # Tester chaque match
    print(f"\nTest des prédictions...")
    results = []
    
    for i, fixture in enumerate(fixtures):
        # Saison du match (pour form/H2H) : déduite de la date si plusieurs saisons
        match_season = get_season_from_fixture_date(fixture.get('fixture', {}).get('date', '')) if len(season_list) > 1 else season_list[0]
        result = backtest_match(predictor, fixture, league_id, match_season)
        if result:
            results.append(result)
        
        if (i + 1) % 50 == 0:
            print(f"   → {i + 1}/{len(fixtures)} matchs testés...")
    
    if not results:
        print(f"   [ERREUR] Aucun résultat valide")
        return None
    
    # Calculer les statistiques
    total = len(results)
    correct = sum(1 for r in results if r['is_correct'])
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    # Précision par résultat
    home_correct = sum(1 for r in results if r['actual_result'] == 'home' and r['is_correct'])
    home_total = sum(1 for r in results if r['actual_result'] == 'home')
    home_accuracy = (home_correct / home_total * 100) if home_total > 0 else 0
    
    draw_correct = sum(1 for r in results if r['actual_result'] == 'draw' and r['is_correct'])
    draw_total = sum(1 for r in results if r['actual_result'] == 'draw')
    draw_accuracy = (draw_correct / draw_total * 100) if draw_total > 0 else 0
    
    away_correct = sum(1 for r in results if r['actual_result'] == 'away' and r['is_correct'])
    away_total = sum(1 for r in results if r['actual_result'] == 'away')
    away_accuracy = (away_correct / away_total * 100) if away_total > 0 else 0
    
    # Value bets détectés (si probabilité > 50%)
    value_bets = [r for r in results if r['predicted_prob'] > 0.5]
    value_bets_correct = sum(1 for r in value_bets if r['is_correct'])
    value_bets_accuracy = (value_bets_correct / len(value_bets) * 100) if value_bets else 0

    # ---- ROI simulé (mise fixe 1 unité par pari) ----
    results_with_odds = [r for r in results if r.get('predicted_odd') and r['predicted_odd'] > 1.0]
    roi_flat = None
    roi_vb = None
    if results_with_odds:
        stake = len(results_with_odds)
        returns = sum(r['predicted_odd'] if r['is_correct'] else 0.0 for r in results_with_odds)
        roi_flat = (returns - stake) / stake * 100

        # ROI sur les value bets uniquement (prob > 50% + cote dispo)
        vb_with_odds = [r for r in results_with_odds if r['predicted_prob'] > 0.5]
        if vb_with_odds:
            vb_stake = len(vb_with_odds)
            vb_returns = sum(r['predicted_odd'] if r['is_correct'] else 0.0 for r in vb_with_odds)
            roi_vb = (vb_returns - vb_stake) / vb_stake * 100

    # Afficher les résultats
    print(f"\n{'='*60}")
    print(f"RÉSULTATS DU BACKTESTING")
    print(f"{'='*60}")
    print(f"\nPrécision globale: {accuracy:.1f}% ({correct}/{total})")
    print(f"\nPrécision par résultat:")
    print(f"   Home: {home_accuracy:.1f}% ({home_correct}/{home_total})")
    print(f"   Draw: {draw_accuracy:.1f}% ({draw_correct}/{draw_total})")
    print(f"   Away: {away_accuracy:.1f}% ({away_correct}/{away_total})")

    if roi_flat is not None:
        print(f"\nROI (mise fixe, {len(results_with_odds)} matchs avec cotes): {roi_flat:+.1f}%")
    if roi_vb is not None:
        print(f"ROI value bets uniquement (prob>50%): {roi_vb:+.1f}%")

    if value_bets:
        print(f"\nValue bets (prob > 50%):")
        print(f"   Nombre: {len(value_bets)}")
        print(f"   Précision: {value_bets_accuracy:.1f}% ({value_bets_correct}/{len(value_bets)})")

    # Sauvegarder les résultats
    season_label = '_'.join(map(str, season_list)) if len(season_list) > 1 else str(season_list[0])
    output_file = f"backtest_{league_name.replace(' ', '_')}_{season_label}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'league': league_name,
            'season': season_list,
            'period': {'start': start_date, 'end': end_date},
            'statistics': {
                'total_matches': total,
                'correct_predictions': correct,
                'accuracy': accuracy,
                'home_accuracy': home_accuracy,
                'draw_accuracy': draw_accuracy,
                'away_accuracy': away_accuracy,
                'value_bets': len(value_bets),
                'value_bets_accuracy': value_bets_accuracy,
                'roi_flat_pct': round(roi_flat, 2) if roi_flat is not None else None,
                'roi_value_bets_pct': round(roi_vb, 2) if roi_vb is not None else None,
                'matches_with_odds': len(results_with_odds),
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\nRésultats sauvegardés dans: {output_file}")

    return {
        'total': total,
        'correct': correct,
        'accuracy': accuracy,
        'home_accuracy': home_accuracy,
        'draw_accuracy': draw_accuracy,
        'away_accuracy': away_accuracy,
        'value_bets': len(value_bets),
        'value_bets_accuracy': value_bets_accuracy,
        'roi_flat_pct': roi_flat,
        'roi_value_bets_pct': roi_vb,
    }

# ==========================================
# 3. BACKTESTING MULTI-LIGUES
# ==========================================

def backtest_all_leagues(leagues, seasons, start_date, end_date):
    """Effectue le backtesting pour plusieurs ligues. seasons: int ou list (ex. [2024, 2025])."""
    print("=" * 50)
    print("  SYSTÈME DE BACKTESTING")
    print("  Test des prédictions historiques")
    print("=" * 50)
    
    all_stats = []
    
    for league in leagues:
        try:
            stats = backtest_league(
                league['id_foot'],
                league['nom'],
                seasons,
                start_date,
                end_date
            )
            if stats:
                all_stats.append({
                    'league': league['nom'],
                    **stats
                })
            
            import time
            time.sleep(1)  # Pause pour API
        except Exception as e:
            print(f"   [ERREUR] {league['nom']}: {e}")
    
    # Résumé global
    if all_stats:
        print(f"\n{'='*60}")
        print(f"RÉSUMÉ GLOBAL")
        print(f"{'='*60}")
        
        total_matches = sum(s['total'] for s in all_stats)
        total_correct = sum(s['correct'] for s in all_stats)
        global_accuracy = (total_correct / total_matches * 100) if total_matches > 0 else 0
        
        print(f"\nTotal matchs testés: {total_matches}")
        print(f"Prédictions correctes: {total_correct}")
        print(f"Précision globale: {global_accuracy:.1f}%")
        
        print(f"\nDétail par ligue:")
        for stats in all_stats:
            roi_str = f" | ROI: {stats['roi_flat_pct']:+.1f}%" if stats.get('roi_flat_pct') is not None else ""
            print(f"   {stats['league']}: {stats['accuracy']:.1f}% ({stats['correct']}/{stats['total']}){roi_str}")
        
        # Sauvegarder le résumé
        season_label = '_'.join(map(str, seasons)) if isinstance(seasons, list) else str(seasons)
        summary_file = f"backtest_summary_{season_label}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'period': {'start': start_date, 'end': end_date, 'seasons': seasons if isinstance(seasons, list) else [seasons]},
                'global_statistics': {
                    'total_matches': total_matches,
                    'total_correct': total_correct,
                    'global_accuracy': global_accuracy
                },
                'leagues': all_stats
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nRésumé sauvegardé dans: {summary_file}")

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    # Configuration des ligues
    LIGUES = [
        {"nom": "Premier League (Ang)", "id_foot": 39},
        {"nom": "Ligue 1 (Fra)", "id_foot": 61},
        {"nom": "La Liga (Esp)", "id_foot": 140},
        {"nom": "Bundesliga (All)", "id_foot": 78},
        {"nom": "Serie A (Ita)", "id_foot": 135},
        {"nom": "Ligue des Champions", "id_foot": 2},
    ]
    
    # Période de test : une saison (ex. 2024) ou plusieurs (ex. [2024, 2025] pour 2025-05-31 -> 2026-02-04)
    SEASONS = [2024, 2025]  # ou 2024 seul, ou 2025 seul
    START_DATE = "2025-05-31"
    END_DATE = "2026-02-04"
    
    # Ou utiliser les 30 derniers jours
    # end_date = datetime.now() - timedelta(days=1)
    # start_date = end_date - timedelta(days=30)
    # START_DATE = start_date.strftime('%Y-%m-%d')
    # END_DATE = end_date.strftime('%Y-%m-%d')
    
    print(f"\nConfiguration:")
    print(f"   Saison(s): {SEASONS}")
    print(f"   Période: {START_DATE} à {END_DATE}")
    print(f"   Ligues: {len(LIGUES)}")
    
    # Lancer le backtesting
    backtest_all_leagues(LIGUES, SEASONS, START_DATE, END_DATE)
    
    print(f"\n[OK] Backtesting terminé !")
