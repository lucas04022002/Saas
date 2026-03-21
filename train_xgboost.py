"""
Script pour entraîner XGBoost avec des données historiques
Collecte les matchs passés, extrait les features et entraîne le modèle
"""

import requests
import json
import numpy as np
from datetime import datetime
from prediction_engine import EloRating, PoissonPredictor, XGBoostPredictor, days_since_last_match
from stats_collector import (collect_stats_for_fixtures, load_stats_cache,
                              build_rolling_stats_index, get_rolling_stats)
from data_collector import load_team_stats
from config import KEY_API_FOOTBALL, SAISON


def _season_from_date(date_str):
    """Retourne l'année de début de saison à partir d'une date ISO.
    Ex: 2025-09-01 → 2025 (saison 2025-26), 2026-02-01 → 2025 (saison 2025-26).
    """
    if not date_str:
        return None
    try:
        year, month = int(date_str[:4]), int(date_str[5:7])
        return year if month >= 8 else year - 1
    except (ValueError, IndexError):
        return None


def _extract_fulltime_score(fixture):
    """Extrait le score final d'une fixture malgré les variantes de payload API."""
    score = fixture.get('score', {}) or fixture.get('fixture', {}).get('score', {}) or {}

    home_goals = None
    away_goals = None

    if isinstance(score, dict) and score.get('fulltime'):
        home_goals = score['fulltime'].get('home')
        away_goals = score['fulltime'].get('away')

    if home_goals is None and isinstance(score, dict) and 'home' in score:
        home_goals = score.get('home')
        away_goals = score.get('away')

    if home_goals is None:
        goals = fixture.get('goals', {}) or {}
        home_goals = goals.get('home')
        away_goals = goals.get('away')

    return home_goals, away_goals

# ==========================================
# 1. RÉCUPÉRATION DES MATCHS HISTORIQUES
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
        # Ne pas utiliser status=FT dans les params, on filtrera après
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        
        # Vérifier le code de statut
        if r.status_code == 403:
            print(f"   [ERREUR 403] Accès refusé. Vérifiez:")
            print(f"      - Votre clé API est valide")
            print(f"      - Votre quota API n'est pas dépassé (100 req/jour en gratuit)")
            print(f"      - Votre plan permet l'accès aux données historiques")
            data = r.json()
            if data.get('errors'):
                print(f"      Détails: {data.get('errors')}")
            return []
        
        r.raise_for_status()
        data = r.json()
        
        if data.get('errors'):
            print(f"   [ERREUR API] {data.get('errors')}")
            return []
        
        if data.get('response') is None:
            print(f"   [ERREUR] Pas de réponse de l'API")
            return []
        
        fixtures = data.get('response', [])
        # Filtrer seulement les matchs terminés (FT = Full Time)
        fixtures_terminated = [f for f in fixtures if f.get('fixture', {}).get('status', {}).get('short') == 'FT']
        print(f"   → {len(fixtures_terminated)} matchs terminés trouvés pour la saison {season} (sur {len(fixtures)} total)")
        return fixtures_terminated
    except requests.exceptions.HTTPError as e:
        print(f"   [ERREUR HTTP] {e}")
        if hasattr(e.response, 'json'):
            try:
                error_data = e.response.json()
                print(f"      Détails: {error_data}")
            except:
                pass
        return []
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return []

def build_form_index(fixtures, max_matches=5):
    """
    Pré-calcule la forme récente de chaque équipe à chaque instant.
    Retourne un dict: {i: {team_name: {'wins', 'draws', 'losses'}}}
    où i est l'index du match courant (forme = matchs [0..i-1]).
    Complexité O(N) au lieu de O(N²).
    """
    from collections import defaultdict, deque

    # Pour chaque équipe, on maintient une deque des max_matches derniers résultats
    team_results = defaultdict(lambda: deque(maxlen=max_matches))
    # À l'index i, on veut la forme AVANT le match i → snapshot avant chaque match
    snapshots = []  # snapshots[i] = {team: {'wins', 'draws', 'losses'}} au moment du match i

    def _snapshot(team_results):
        snap = {}
        for team, dq in team_results.items():
            snap[team] = {
                'wins':   sum(1 for r in dq if r == 'win'),
                'draws':  sum(1 for r in dq if r == 'draw'),
                'losses': sum(1 for r in dq if r == 'loss'),
            }
        return snap

    for fixture in fixtures:
        snapshots.append(_snapshot(team_results))

        home_team = fixture.get('teams', {}).get('home', {}).get('name', '')
        away_team = fixture.get('teams', {}).get('away', {}).get('name', '')
        score = fixture.get('score', {}) or fixture.get('fixture', {}).get('score', {})

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

        if home_goals > away_goals:
            team_results[home_team].append('win')
            team_results[away_team].append('loss')
        elif home_goals < away_goals:
            team_results[home_team].append('loss')
            team_results[away_team].append('win')
        else:
            team_results[home_team].append('draw')
            team_results[away_team].append('draw')

    return snapshots


def get_form_from_snapshot(snapshot, team_name):
    """Récupère la forme d'une équipe depuis un snapshot pré-calculé."""
    return snapshot.get(team_name, {'wins': 0, 'draws': 0, 'losses': 0})

# ==========================================
# 2. PRÉPARATION DES DONNÉES
# ==========================================

def prepare_training_data(league_id, league_name, seasons=[2022, 2023, 2024, 2025]):
    """
    Prépare les données d'entraînement pour XGBoost
    Retourne X (features) et y (labels)
    """
    print(f"\n📊 Préparation des données pour {league_name}")
    print("=" * 50)
    
    # Initialiser les systèmes
    elo = EloRating()
    poisson = PoissonPredictor()
    
    # Charger les stats de saison si disponibles
    stats_dict = load_team_stats(league_name)
    if stats_dict:
        print(f"   → Stats chargées pour {len(stats_dict)} équipes")
        for team_name, stats in stats_dict.items():
            poisson.update_stats(
                team_name,
                stats['goals_for'],
                stats['goals_against'],
                stats['matches_played']
            )
    
    # Collecter tous les matchs historiques
    all_fixtures = []
    for season in seasons:
        print(f"\n   Récupération saison {season}...")
        fixtures = get_historical_fixtures(league_id, season)
        all_fixtures.extend(fixtures)
        import time
        time.sleep(1)  # Pause pour API
    # Elo sera mis à jour progressivement pendant l'extraction (pas de pré-calcul)
    print(f"\n   ✓ Total: {len(all_fixtures)} matchs collectés")
    
    # Trier par date (plus ancien d'abord)
    all_fixtures.sort(key=lambda x: x.get('fixture', {}).get('date', ''))

    # Pré-calculer la forme récente en O(N)
    form_snapshots = build_form_index(all_fixtures)

    # Préparer les features et labels
    X = []
    y = []
    last_match_date = {}   # {team: 'YYYY-MM-DD'} — date du dernier match joué
    xgboost = XGBoostPredictor()

    print(f"\n   Extraction des features...")

    for i, fixture in enumerate(all_fixtures):
        fixture_data = fixture.get('fixture', {})
        home_team_data = fixture.get('teams', {}).get('home', {})
        away_team_data = fixture.get('teams', {}).get('away', {})

        home_team = home_team_data.get('name', '')
        away_team = away_team_data.get('name', '')

        if fixture_data.get('status', {}).get('short') != 'FT':
            continue

        home_goals, away_goals = _extract_fulltime_score(fixture)

        if home_goals is None or away_goals is None:
            continue

        # Déterminer le résultat (label)
        if home_goals > away_goals:
            result = 0  # Home win
        elif home_goals == away_goals:
            result = 1  # Draw
        else:
            result = 2  # Away win

        match_date = fixture_data.get('date', '')[:10] if fixture_data.get('date') else None

        # Jours de récupération depuis le dernier match (None si première apparition)
        home_days_rest = days_since_last_match(last_match_date.get(home_team), match_date)
        away_days_rest = days_since_last_match(last_match_date.get(away_team), match_date)

        # Obtenir les ratings Elo au moment du match
        home_rating = elo.get_rating(home_team)
        away_rating = elo.get_rating(away_team)

        # Obtenir les stats Poisson
        home_attack = poisson.team_stats.get(home_team, {}).get('attack', 1.25)
        home_defense = poisson.team_stats.get(home_team, {}).get('defense', 1.25)
        away_attack = poisson.team_stats.get(away_team, {}).get('attack', 1.25)
        away_defense = poisson.team_stats.get(away_team, {}).get('defense', 1.25)

        # Forme récente depuis l'index pré-calculé (O(1) par match)
        snapshot = form_snapshots[i] if i < len(form_snapshots) else {}
        home_form = get_form_from_snapshot(snapshot, home_team)
        away_form = get_form_from_snapshot(snapshot, away_team)

        # Charger les cotes historiques si disponibles
        bookmaker_odds = None
        if match_date:
            try:
                from odds_logger import load_odds
                bookmaker_odds = load_odds(match_date, home_team, away_team)
            except ImportError:
                pass

        # Créer les features
        elo_ratings = {home_team: home_rating, away_team: away_rating}
        poisson_stats = {
            home_team: {'attack': home_attack, 'defense': home_defense},
            away_team: {'attack': away_attack, 'defense': away_defense}
        }

        features = xgboost.create_features(
            home_team, away_team, elo_ratings, poisson_stats,
            home_form, away_form, bookmaker_odds=bookmaker_odds,
            league_id=league_id,
            home_days_rest=home_days_rest, away_days_rest=away_days_rest,
        )

        X.append(features[0])
        y.append(result)

        # Mettre à jour la date du dernier match APRÈS extraction
        if match_date:
            last_match_date[home_team] = match_date
            last_match_date[away_team] = match_date

        # Seasonal decay : appliqué une fois par saison avant la mise à jour Elo
        match_season = _season_from_date(fixture_data.get('date', ''))
        if match_season is not None:
            elo.apply_season_decay(match_season)

        # Mise à jour Elo APRÈS extraction — fix data leakage
        elo.update_ratings(home_team, away_team, home_goals, away_goals)

        if (i + 1) % 50 == 0:
            print(f"   → {i + 1}/{len(all_fixtures)} matchs traités...")

    print(f"\n   ✓ {len(X)} échantillons préparés")

    return np.array(X), np.array(y)

# ==========================================
# 3. ENTRAÎNEMENT DU MODÈLE
# ==========================================

def train_model(league_id, league_name, seasons=[2022, 2023, 2024, 2025]):
    """Entraîne XGBoost pour une ligue spécifique"""
    print(f"\n🚀 ENTRAÎNEMENT XGBOOST - {league_name}")
    print("=" * 50)
    
    # Préparer les données
    X, y = prepare_training_data(league_id, league_name, seasons)
    
    if len(X) < 100:
        print(f"   ⚠️ Pas assez de données ({len(X)} matchs). Minimum recommandé: 100")
        return False
    
    # Diviser en train/test (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n   Données d'entraînement: {len(X_train)} matchs")
    print(f"   Données de test: {len(X_test)} matchs")
    
    # Entraîner le modèle
    print(f"\n   Entraînement en cours...")
    xgboost = XGBoostPredictor()
    xgboost.train(X_train, y_train)
    
    # Évaluer
    from sklearn.metrics import accuracy_score, classification_report
    
    y_pred = xgboost.model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n   ✓ Modèle entraîné !")
    print(f"   Précision sur le test: {accuracy*100:.1f}%")
    print(f"\n   Rapport détaillé:")
    print(classification_report(y_test, y_pred, target_names=['Home', 'Draw', 'Away']))
    
    return True

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    import sys
    import io
    # Configurer l'encodage UTF-8 pour Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 50)
    print("  ENTRAINEMENT XGBOOST")
    print("  Collecte de donnees historiques")
    print("=" * 50)
    
    # Configuration des ligues (toutes les ligues majeures + Ligue des Champions)
    LIGUES = [
        {"nom": "Premier League (Ang)", "id_foot": 39},
        {"nom": "Ligue 1 (Fra)",        "id_foot": 61},
        {"nom": "La Liga (Esp)",        "id_foot": 140},
        {"nom": "Bundesliga (All)",     "id_foot": 78},
        {"nom": "Serie A (Ita)",        "id_foot": 135},
        {"nom": "Ligue des Champions",  "id_foot": 2},
        # Europa League (3) et Conference League (848) exclus du training :
        # trop de bruit (équipes hétérogènes, peu de stats xG) → dégrade le Brier Score
    ]
    
    # Saisons à utiliser : inclure la saison en cours + 3 saisons précédentes
    # Note : 2020 et 2021 (COVID, huis clos) dégradent le modèle → exclus volontairement
    def _current_season_year():
        now = datetime.now()
        return now.year if now.month >= 7 else now.year - 1
    current = _current_season_year()
    SAISONS_CHAMPIONS = [current - 3, current - 2, current - 1, current]
    SAISONS_UCL = SAISONS_CHAMPIONS  # Même chose pour la Ligue des Champions
    print(f"Saisons utilisees (saison en cours: {current}): {SAISONS_CHAMPIONS}")
    
    # Entrainer un modele unique avec TOUTES les ligues combinees (RECOMMANDE)
    print("\nMODE : Entrainement avec TOUTES les ligues combinees")
    print("=" * 50)
    
    # Initialiser Elo et Poisson une seule fois pour toutes les ligues
    elo = EloRating()
    poisson = PoissonPredictor()
    
    # Charger toutes les stats disponibles (isolées par ligue)
    print("\nChargement des stats de toutes les ligues...")
    for ligue in LIGUES:
        stats_dict = load_team_stats(ligue['nom'])
        if stats_dict:
            for team_name, stats in stats_dict.items():
                poisson.update_stats(
                    team_name,
                    stats['goals_for'],
                    stats['goals_against'],
                    stats['matches_played'],
                    league_id=ligue['id_foot'],
                )
    
    # Collecter TOUS les matchs de TOUTES les ligues
    print("\n🔄 Collecte de tous les matchs historiques...")
    all_fixtures = []
    for ligue in LIGUES:
        try:
            if ligue['id_foot'] == 2:  # Ligue des Champions
                seasons = SAISONS_UCL
                print(f"\n🏆 {ligue['nom']} (saisons {seasons})")
            else:
                seasons = SAISONS_CHAMPIONS
                print(f"\n⚽ {ligue['nom']} (saisons {seasons})")
            
            for season in seasons:
                fixtures = get_historical_fixtures(ligue['id_foot'], season)
                # Ajouter league_id à chaque fixture pour pouvoir l'utiliser plus tard
                for fixture in fixtures:
                    fixture['_league_id'] = ligue['id_foot']
                all_fixtures.extend(fixtures)
                import time
                time.sleep(1)
        except Exception as e:
            print(f"   [ERREUR] {e}")
    
    # Trier tous les matchs par date
    all_fixtures.sort(key=lambda x: x.get('fixture', {}).get('date', ''))
    print(f"\n   [OK] Total: {len(all_fixtures)} matchs collectes de toutes les ligues")
    # Elo sera mis à jour progressivement pendant l'extraction des features (pas de pré-calcul)
    
    # Pré-calculer la forme récente en O(N)
    print("\nPré-calcul des formes récentes...")
    form_snapshots = build_form_index(all_fixtures)

    # Collecter les stats de match (xG, tirs, possession) et construire l'index rolling
    print("\nCollecte des stats de match (xG, tirs, possession)...")
    stats_cache = collect_stats_for_fixtures(all_fixtures, KEY_API_FOOTBALL, sleep_between=0.05)
    rolling_stats_snapshots = build_rolling_stats_index(all_fixtures, stats_cache, n=5)

    # Extraire les features pour tous les matchs
    print("\nExtraction des features...")
    all_X = []
    all_y = []
    last_match_date = {}   # {team: 'YYYY-MM-DD'}
    xgboost = XGBoostPredictor()

    skipped_status = 0
    skipped_goals = 0
    errors = 0

    for i, fixture in enumerate(all_fixtures):
        try:
            fixture_data = fixture.get('fixture', {})
            score = fixture.get('score', {}) or fixture_data.get('score', {})
            home_team_data = fixture.get('teams', {}).get('home', {})
            away_team_data = fixture.get('teams', {}).get('away', {})

            home_team = home_team_data.get('name', '')
            away_team = away_team_data.get('name', '')

            if not home_team or not away_team:
                continue

            if fixture_data.get('status', {}).get('short') != 'FT':
                skipped_status += 1
                continue

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
                skipped_goals += 1
                if skipped_goals <= 3:
                    print(f"\n   [DEBUG] Match {i}: score introuvable — {score}")
                continue

            # Label
            if home_goals > away_goals:
                result = 0  # Home win
            elif home_goals == away_goals:
                result = 1  # Draw
            else:
                result = 2  # Away win

            match_date = fixture_data.get('date', '')[:10] if fixture_data.get('date') else None

            # Récupérer league_id depuis la fixture (avant tout appel Elo)
            league_id = fixture.get('_league_id') or fixture.get('league', {}).get('id')

            # Jours de récupération depuis le dernier match
            home_days_rest = days_since_last_match(last_match_date.get(home_team), match_date)
            away_days_rest = days_since_last_match(last_match_date.get(away_team), match_date)

            home_rating = elo.get_rating(home_team, league_id=league_id)
            away_rating = elo.get_rating(away_team, league_id=league_id)

            h_stats = poisson.get_stats(home_team, league_id=league_id)
            a_stats = poisson.get_stats(away_team, league_id=league_id)
            home_attack  = h_stats.get('attack',  1.25)
            home_defense = h_stats.get('defense', 1.25)
            away_attack  = a_stats.get('attack',  1.25)
            away_defense = a_stats.get('defense', 1.25)

            # Forme récente depuis l'index pré-calculé (O(1) par match)
            snapshot = form_snapshots[i] if i < len(form_snapshots) else {}
            home_form = get_form_from_snapshot(snapshot, home_team)
            away_form = get_form_from_snapshot(snapshot, away_team)

            # Stats rolling (xG, tirs, possession) depuis l'index pré-calculé
            stats_snap = rolling_stats_snapshots[i] if i < len(rolling_stats_snapshots) else {}
            home_match_stats = get_rolling_stats(stats_snap, home_team)
            away_match_stats = get_rolling_stats(stats_snap, away_team)

            elo_ratings = {home_team: home_rating, away_team: away_rating}
            poisson_stats = {
                home_team: {'attack': home_attack, 'defense': home_defense},
                away_team: {'attack': away_attack, 'defense': away_defense}
            }

            # H2H non disponible en données historiques hors-API (évite O(N²))
            h2h = None
            injuries = None

            # Charger les cotes historiques si disponibles
            bookmaker_odds = None
            if match_date:
                try:
                    from odds_logger import load_odds
                    bookmaker_odds = load_odds(match_date, home_team, away_team)
                except ImportError:
                    pass

            features = xgboost.create_features(
                home_team, away_team, elo_ratings, poisson_stats,
                home_form, away_form, injuries=injuries, h2h=h2h, bookmaker_odds=bookmaker_odds,
                league_id=league_id,
                home_days_rest=home_days_rest, away_days_rest=away_days_rest,
                home_match_stats=home_match_stats, away_match_stats=away_match_stats,
            )

            all_X.append(features[0])
            all_y.append(result)

            # Mettre à jour la date du dernier match APRÈS extraction
            if match_date:
                last_match_date[home_team] = match_date
                last_match_date[away_team] = match_date

            # Seasonal decay : appliqué une fois par saison avant la mise à jour Elo
            match_season = _season_from_date(fixture_data.get('date', ''))
            if match_season is not None:
                elo.apply_season_decay(match_season)

            # ── MISE À JOUR ELO APRÈS extraction des features ──────────────
            elo.update_ratings(home_team, away_team, home_goals, away_goals,
                               league_id=league_id)

            if (i + 1) % 500 == 0:
                print(f"   → {i + 1}/{len(all_fixtures)} matchs traités... ({len(all_X)} features extraites)")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   [ERREUR] Match {i}: {e}")
            continue

    # Sauvegarder les ratings Elo finaux (état après tous les matchs connus)
    elo.save_ratings()
    print(f"\n   [OK] Extraction terminee:")
    print(f"      - Features extraites: {len(all_X)}")
    print(f"      - Matchs sautes (status): {skipped_status}")
    print(f"      - Matchs sautes (scores): {skipped_goals}")
    print(f"      - Erreurs: {errors}")
    
    # Entrainer le modele avec TOUTES les donnees combinees
    print(f"\n{'='*50}")
    print(f"ENTRAINEMENT DU MODELE UNIQUE")
    print(f"{'='*50}")
    print(f"Total de matchs collectes: {len(all_X)}")
    
    if len(all_X) < 100:
        print(f"   [ATTENTION] Pas assez de donnees ({len(all_X)} matchs). Minimum recommande: 100")
        print("   Arret de l'entrainement.")
        exit(1)
    
    # Split TEMPOREL 60 / 20 / 20 : train → calibration → test
    # Pas de shuffle : le temps doit rester ordonné pour éviter le data leakage.
    all_X = np.array(all_X)
    all_y = np.array(all_y)

    n = len(all_X)
    idx_cal  = int(n * 0.60)
    idx_test = int(n * 0.80)
    X_train, y_train = all_X[:idx_cal],         all_y[:idx_cal]
    X_cal,   y_cal   = all_X[idx_cal:idx_test],  all_y[idx_cal:idx_test]
    X_test,  y_test  = all_X[idx_test:],         all_y[idx_test:]

    print(f"\n   Split TEMPOREL 60/20/20 :")
    print(f"      Entrainement : {len(X_train)} matchs")
    print(f"      Calibration  : {len(X_cal)} matchs")
    print(f"      Test         : {len(X_test)} matchs")

    # 1. Entraîner XGBoost
    print(f"\n   Entrainement en cours...")
    xgboost = XGBoostPredictor()
    xgboost.train(X_train, y_train)

    # 2. Calibrer les probabilités (isotonic regression sur jeu de calibration)
    print(f"\n   Calibration des probabilites (isotonic regression)...")
    xgboost.calibrate(X_cal, y_cal, method='isotonic')
    print(f"   [OK] Modele calibre et sauvegarde.")

    # 3. Evaluer
    from sklearn.metrics import accuracy_score, classification_report, brier_score_loss
    from sklearn.preprocessing import label_binarize

    y_pred  = xgboost.model.predict(X_test)
    y_proba = xgboost.model.predict_proba(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Brier Score multi-classe (moyenne sur les 3 classes)
    Y_bin = label_binarize(y_test, classes=[0, 1, 2])
    brier = sum(brier_score_loss(Y_bin[:, k], y_proba[:, k]) for k in range(3)) / 3

    print(f"\n   [OK] Modele entraine et calibre avec TOUTES les ligues !")
    print(f"   Precision sur le test : {accuracy*100:.1f}%")
    print(f"   Brier Score           : {brier:.4f}  (0 = parfait, 0.333 = aleatoire)")
    print(f"\n   Rapport detaille:")
    print(classification_report(y_test, y_pred, target_names=['Home', 'Draw', 'Away']))
    
    print("\n[OK] Entrainement termine !")
    print("\nLe modele XGBoost est maintenant sauvegarde dans xgboost_model.pkl")
    print(f"Modele entraine avec {len(all_X)} matchs de {len(LIGUES)} ligues differentes")
