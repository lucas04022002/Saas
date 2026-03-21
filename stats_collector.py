"""
Collecte et mise en cache des statistiques de match via API-Football.
Fournit aussi l'index rolling pour les features XGBoost.

Stats collectées par match (home + away) :
  - Expected Goals (xG)
  - Shots on Goal
  - Total Shots
  - Ball Possession (%)
"""

import requests
import json
import os
import time
from collections import defaultdict, deque

STATS_CACHE_FILE = "fixture_stats_cache.json"

# Valeurs par défaut quand les stats sont indisponibles
STAT_DEFAULTS = {
    'xg':             1.25,
    'shots_on_goal':  4.5,
    'total_shots':    12.0,
    'possession':     50.0,
}

# ==========================================
# 1. FETCH / PARSE
# ==========================================

def _parse_stat(stats_list, stat_type, fallback=None):
    """Extrait la valeur d'un type de stat dans la liste renvoyée par l'API."""
    for s in stats_list:
        if s.get('type', '').lower() == stat_type.lower():
            val = s.get('value')
            if val is None:
                return fallback
            # Possession renvoyée sous forme "45%" → float 45.0
            if isinstance(val, str) and val.endswith('%'):
                try:
                    return float(val[:-1])
                except ValueError:
                    return fallback
            try:
                return float(val)
            except (ValueError, TypeError):
                return fallback
    return fallback


def parse_fixture_stats(response):
    """Transforme la réponse brute de l'API en dict {fixture_id: {home: {...}, away: {...}}}.

    L'API renvoie les stats dans l'ordre : index 0 = équipe domicile, index 1 = extérieur.
    """
    if not response or len(response) < 2:
        return None
    result = {}
    for idx, side in enumerate(('home', 'away')):
        team_data = response[idx]
        stats_list = team_data.get('statistics', [])
        result[side] = {
            'xg':            _parse_stat(stats_list, 'expected_goals',  STAT_DEFAULTS['xg']),
            'shots_on_goal': _parse_stat(stats_list, 'shots on goal',   STAT_DEFAULTS['shots_on_goal']),
            'total_shots':   _parse_stat(stats_list, 'total shots',     STAT_DEFAULTS['total_shots']),
            'possession':    _parse_stat(stats_list, 'ball possession',  STAT_DEFAULTS['possession']),
        }
    return result


def fetch_fixture_stats(fixture_id, api_key, retries=2, sleep_between=0.15):
    """Récupère les stats d'un match via API-Football.

    Args:
        fixture_id: ID du match.
        api_key:    Clé API-Football.
        retries:    Nombre de tentatives en cas d'erreur réseau.
        sleep_between: Délai entre requêtes (secondes) pour respecter les limites.

    Returns:
        Dict {home: {...}, away: {...}} ou None si indisponible.
    """
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': api_key,
    }
    params = {"fixture": fixture_id}

    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get('errors'):
                return None
            return parse_fixture_stats(data.get('response', []))
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(sleep_between)
    return None


# ==========================================
# 2. CACHE LOCAL
# ==========================================

def load_stats_cache(cache_file=STATS_CACHE_FILE):
    """Charge le cache de stats depuis un fichier JSON.
    Retourne un dict {str(fixture_id): {home: {...}, away: {...}}}.
    """
    if not os.path.exists(cache_file):
        return {}
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_stats_cache(cache, cache_file=STATS_CACHE_FILE):
    """Sauvegarde le cache de stats dans un fichier JSON."""
    with open(cache_file, 'w') as f:
        json.dump(cache, f)


def collect_stats_for_fixtures(fixtures, api_key, cache_file=STATS_CACHE_FILE,
                                sleep_between=0.15, verbose=True):
    """Récupère les stats manquantes pour une liste de fixtures et met à jour le cache.

    Seuls les matchs absents du cache sont téléchargés (idempotent).

    Args:
        fixtures:      Liste de fixtures (dicts API-Football).
        api_key:       Clé API-Football.
        cache_file:    Chemin du fichier cache.
        sleep_between: Délai entre requêtes (secondes).
        verbose:       Affiche la progression.

    Returns:
        Cache mis à jour {str(fixture_id): stats}.
    """
    cache = load_stats_cache(cache_file)
    missing = [
        f for f in fixtures
        if str(f.get('fixture', {}).get('id', '')) not in cache
    ]

    if not missing:
        if verbose:
            print(f"   [STATS] Cache complet ({len(cache)} matchs).")
        return cache

    if verbose:
        print(f"   [STATS] {len(missing)} matchs à télécharger (cache: {len(cache)})...")

    fetched = 0
    errors = 0
    SAVE_EVERY = 200   # Sauvegarde intermédiaire toutes les N stats (résistance aux interruptions)

    for i, fixture in enumerate(missing):
        fid = fixture.get('fixture', {}).get('id')
        if not fid:
            continue
        stats = fetch_fixture_stats(fid, api_key)
        if stats:
            cache[str(fid)] = stats
            fetched += 1
        else:
            errors += 1

        if sleep_between > 0:
            time.sleep(sleep_between)

        if (i + 1) % SAVE_EVERY == 0:
            save_stats_cache(cache, cache_file)   # Sauvegarde intermédiaire
            if verbose:
                print(f"   [STATS] {i + 1}/{len(missing)} téléchargés ({errors} erreurs)...")

    save_stats_cache(cache, cache_file)
    if verbose:
        print(f"   [STATS] Terminé : {fetched} nouveaux, {errors} erreurs.")
    return cache


# ==========================================
# 3. INDEX ROLLING (O(N))
# ==========================================

def build_rolling_stats_index(fixtures, stats_cache, n=5):
    """Pré-calcule les stats rolling de chaque équipe à chaque instant.

    Pour chaque match i, le snapshot contient la moyenne des n derniers matchs
    AVANT le match i pour chaque équipe (pas de data leakage).

    Args:
        fixtures:    Liste triée par date (plus ancien → plus récent).
        stats_cache: Dict {str(fixture_id): {home: {...}, away: {...}}}.
        n:           Taille de la fenêtre glissante.

    Returns:
        Liste de snapshots (un par fixture).
        snapshot[i][team] = {'avg_xg', 'avg_shots_on_goal', 'avg_total_shots', 'avg_possession'}
    """
    team_history = defaultdict(lambda: deque(maxlen=n))
    snapshots = []

    def _avg_stats(dq):
        """Moyenne des stats sur la fenêtre courante."""
        if not dq:
            return None
        keys = dq[0].keys()
        return {k: sum(d[k] for d in dq) / len(dq) for k in keys}

    def _snapshot(team_history):
        return {team: _avg_stats(dq) for team, dq in team_history.items() if dq}

    for fixture in fixtures:
        snapshots.append(_snapshot(team_history))

        fid = str(fixture.get('fixture', {}).get('id', ''))
        stats = stats_cache.get(fid)
        if not stats:
            continue

        home_team = fixture.get('teams', {}).get('home', {}).get('name', '')
        away_team = fixture.get('teams', {}).get('away', {}).get('name', '')

        if home_team and stats.get('home'):
            team_history[home_team].append(stats['home'])
        if away_team and stats.get('away'):
            team_history[away_team].append(stats['away'])

    return snapshots


def get_rolling_stats(snapshot, team):
    """Récupère les stats rolling d'une équipe depuis un snapshot.

    Retourne None si aucun historique disponible (équipe nouvelle ou stats manquantes).
    """
    return snapshot.get(team)
