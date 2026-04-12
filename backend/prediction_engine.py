"""
Module de prédiction avancée pour le football
Combine : Elo Rating + Loi de Poisson + XGBoost
"""

import numpy as np
from scipy.stats import poisson
from xgboost import XGBClassifier
import pickle
import os
from datetime import datetime
import json

# ==========================================
# 1. SYSTÈME ELO
# ==========================================

class EloRating:
    """Système de classement Elo pour les équipes de football"""

    # Paliers du K-factor dynamique (matchs joués → K)
    K_THRESHOLDS = [
        (10, 40),   # < 10 matchs  : nouvelle équipe, forte incertitude
        (30, 32),   # 10–29 matchs : en développement
        (None, 24), # ≥ 30 matchs  : équipe établie, rating stable
    ]

    # Home advantage par équipe
    HA_LEARNING_RATE = 2.0   # Elo points ajoutés par match (convergence ~50 matchs)
    HA_MIN           = 0     # Plancher : aucun avantage domicile
    HA_MAX           = 300   # Plafond  : avantage très fort (ex. équipes de haute altitude)
    DRAW_BASE        = 0.27  # Taux de nul max quand les équipes sont proches
    DRAW_MIN         = 0.08  # Taux plancher pour éviter "nul≈0"
    DRAW_DECAY       = 280.0 # Plus grand = le nul baisse moins vite avec l'écart Elo

    def __init__(self, k_factor=32, home_advantage=100, initial_rating=1500):
        """
        k_factor: ignoré — conservé pour rétro-compatibilité, K est maintenant dynamique
        home_advantage: Avantage à domicile global par défaut (points Elo)
        initial_rating: Rating initial pour une nouvelle équipe
        """
        self.home_advantage = home_advantage
        self.initial_rating = initial_rating
        self.ratings = {}           # {team_name: rating}
        self.matches_played = {}    # {team_name: int}
        self.home_advantages = {}   # {team_name: float} — HA perso, défaut = self.home_advantage
        self.last_decay_season = None
        self.history_file = "elo_ratings.json"
        self.load_ratings()

    def load_ratings(self):
        """Charge les ratings depuis un fichier.
        Supporte l'ancien format {team: rating} et le nouveau
        format {ratings, matches_played, home_advantages, last_decay_season}.
        """
        if not os.path.exists(self.history_file):
            self.ratings = {}
            self.matches_played = {}
            self.home_advantages = {}
            self.last_decay_season = None
            return
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'ratings' in data:
                self.ratings = data.get('ratings', {})
                self.matches_played = data.get('matches_played', {})
                self.home_advantages = data.get('home_advantages', {})
                self.last_decay_season = data.get('last_decay_season', None)
            else:
                # Ancien format plat — migration transparente
                self.ratings = data
                self.matches_played = {}
                self.home_advantages = {}
                self.last_decay_season = None
        except Exception:
            self.ratings = {}
            self.matches_played = {}
            self.home_advantages = {}
            self.last_decay_season = None

    def save_ratings(self):
        """Sauvegarde les ratings, les compteurs, les HA perso et la dernière saison décayée."""
        with open(self.history_file, 'w') as f:
            json.dump({
                'ratings': self.ratings,
                'matches_played': self.matches_played,
                'home_advantages': self.home_advantages,
                'last_decay_season': self.last_decay_season,
            }, f, indent=2)

    def apply_season_decay(self, season: int, decay: float = 0.2) -> int:
        """Régresse les ratings vers la moyenne en début de nouvelle saison.

        Chaque rating est ramené de decay*100% vers initial_rating (1500) :
            new_rating = rating * (1 - decay) + initial_rating * decay

        Les compteurs matches_played sont divisés par 2 pour que le K-factor
        remonte légèrement, reflétant l'incertitude liée aux transferts.

        Args:
            season: Année de début de saison (ex. 2025 pour 2025-26).
            decay:  Fraction de régression vers la moyenne (défaut 0.2 = 20%).

        Returns:
            Nombre d'équipes affectées (0 si déjà appliqué pour cette saison).
        """
        if self.last_decay_season == season:
            return 0  # Déjà appliqué pour cette saison

        affected = 0
        all_teams = set(self.ratings) | set(self.matches_played)
        for team in all_teams:
            old = self.ratings.get(team, self.initial_rating)
            self.ratings[team] = old * (1 - decay) + self.initial_rating * decay
            self.matches_played[team] = max(0, self.matches_played.get(team, 0) // 2)
            affected += 1

        self.last_decay_season = season
        return affected

    @staticmethod
    def _key(team_name, league_id=None):
        """Clé interne : 'league_id:team' si league_id fourni, sinon 'team' seul."""
        return f"{league_id}:{team_name}" if league_id is not None else team_name

    def get_rating(self, team_name, league_id=None):
        """Récupère le rating d'une équipe, éventuellement spécifique à la ligue.

        Si league_id est fourni, cherche d'abord la clé 'league_id:team',
        puis se rabat sur la clé 'team' seule (migration transparente de l'ancien format).
        """
        key = self._key(team_name, league_id)
        if key in self.ratings:
            return self.ratings[key]
        # Fallback : ancien rating sans league (migration transparente)
        if league_id is not None and team_name in self.ratings:
            return self.ratings[team_name]
        return self.initial_rating

    def _get_k_factor(self, team_name, league_id=None):
        """Retourne le K-factor dynamique selon le nombre de matchs joués (par ligue)."""
        key = self._key(team_name, league_id)
        # Cherche d'abord la clé ligue+équipe, puis la clé équipe seule (migration)
        n = self.matches_played.get(key,
            self.matches_played.get(team_name, 0) if league_id is not None else 0)
        for threshold, k in self.K_THRESHOLDS:
            if threshold is None or n < threshold:
                return k
        return self.K_THRESHOLDS[-1][1]

    def _get_home_advantage(self, team_name, league_id=None):
        """Retourne l'avantage à domicile personnalisé de l'équipe (par ligue).

        Utilise la valeur apprise si elle existe, sinon la valeur globale par défaut.
        Fallback sur la clé sans league pour la migration.
        """
        key = self._key(team_name, league_id)
        if key in self.home_advantages:
            return self.home_advantages[key]
        if league_id is not None and team_name in self.home_advantages:
            return self.home_advantages[team_name]
        return self.home_advantage

    def expected_score(self, rating_a, rating_b, home_advantage=0):
        """Calcule le score attendu (probabilité de victoire)."""
        diff = rating_a - rating_b + home_advantage
        return 1 / (1 + 10 ** (-diff / 400))

    @staticmethod
    def _mov_multiplier(home_goals, away_goals):
        """Multiplicateur Margin of Victory (formule eloratings.net).

        Pondère K selon l'écart de buts pour qu'une large victoire
        apporte plus de points qu'une victoire étriquée :
            diff = 1 → ×1.00
            diff = 2 → ×1.50
            diff ≥ 3 → ×(11 + diff) / 8

        Pour un match nul (diff = 0) le multiplicateur vaut 1.0.
        """
        diff = abs(home_goals - away_goals)
        if diff <= 1:
            return 1.0
        if diff == 2:
            return 1.5
        return (11 + diff) / 8

    def _estimate_draw_probability(self, rating_diff):
        """Estime la probabilité de nul à partir de l'écart Elo effectif."""
        draw = self.DRAW_BASE * np.exp(-abs(rating_diff) / self.DRAW_DECAY)
        return max(self.DRAW_MIN, min(self.DRAW_BASE, float(draw)))

    def update_ratings(self, home_team, away_team, home_goals, away_goals, is_home=True,
                       league_id=None):
        """Met à jour les ratings après un match avec K-factor dynamique, MOV et HA perso.

        league_id : si fourni, les ratings/compteurs/HA sont stockés sous la clé
                    'league_id:team' pour isoler chaque compétition.
        """
        h_key = self._key(home_team, league_id)
        a_key = self._key(away_team, league_id)

        home_rating = self.get_rating(home_team, league_id)
        away_rating = self.get_rating(away_team, league_id)

        # K-factor propre à chaque équipe selon son historique (par ligue)
        k_home = self._get_k_factor(home_team, league_id)
        k_away = self._get_k_factor(away_team, league_id)

        # Multiplicateur Margin of Victory
        mov = self._mov_multiplier(home_goals, away_goals)

        # Home advantage personnalisé (ou global si nouveau)
        ha = self._get_home_advantage(home_team, league_id) if is_home else 0

        # Score attendu avec HA perso
        home_expected = self.expected_score(home_rating, away_rating, ha)
        away_expected = 1 - home_expected

        # Score réel (0, 0.5, 1)
        if home_goals > away_goals:
            home_score, away_score = 1.0, 0.0
        elif home_goals < away_goals:
            home_score, away_score = 0.0, 1.0
        else:
            home_score, away_score = 0.5, 0.5

        # Mise à jour Elo avec K individuel × MOV
        self.ratings[h_key] = home_rating + k_home * mov * (home_score - home_expected)
        self.ratings[a_key] = away_rating + k_away * mov * (away_score - away_expected)

        # Mise à jour du home advantage perso (uniquement pour les matchs à domicile)
        # Signal : résidu entre score réel et score attendu avec HA actuel
        # Si home_score > home_expected → équipe surperforme à domicile → HA monte
        if is_home:
            current_ha = self._get_home_advantage(home_team, league_id)
            new_ha = current_ha + self.HA_LEARNING_RATE * (home_score - home_expected)
            self.home_advantages[h_key] = max(self.HA_MIN, min(self.HA_MAX, new_ha))

        # Incrémenter les compteurs
        self.matches_played[h_key] = self.matches_played.get(h_key, 0) + 1
        self.matches_played[a_key] = self.matches_played.get(a_key, 0) + 1

        self.save_ratings()

    def predict_match(self, home_team, away_team, league_id=None):
        """Prédit les probabilités d'un match avec le HA personnalisé de l'équipe domicile.

        league_id : si fourni, utilise les ratings spécifiques à la compétition.
        """
        home_rating = self.get_rating(home_team, league_id)
        away_rating = self.get_rating(away_team, league_id)

        ha = self._get_home_advantage(home_team, league_id)
        # Elo donne naturellement un duel "home vs away". On réintroduit un nul
        # explicite en fonction de la proximité Elo, puis on répartit le reste.
        effective_diff = (home_rating + ha) - away_rating
        prob_draw = self._estimate_draw_probability(effective_diff)
        non_draw_mass = 1.0 - prob_draw

        win_share_home = self.expected_score(home_rating, away_rating, ha)
        prob_home = non_draw_mass * win_share_home
        prob_away = non_draw_mass * (1.0 - win_share_home)
        
        # Normaliser
        total = prob_home + prob_draw + prob_away
        if total > 0:
            prob_home /= total
            prob_draw /= total
            prob_away /= total
        
        return {
            'home': prob_home,
            'draw': prob_draw,
            'away': prob_away,
            'home_rating': home_rating,
            'away_rating': away_rating
        }


# ==========================================
# 2. LOI DE POISSON
# ==========================================

class PoissonPredictor:
    """Prédiction des buts avec la loi de Poisson + correction Dixon-Coles"""

    def __init__(self, attack_factor=1.0, defense_factor=1.0, rho=-0.13):
        self.attack_factor = attack_factor
        self.defense_factor = defense_factor
        self.rho = rho          # Paramètre de corrélation Dixon-Coles (papier original : ~-0.13)
        self.team_stats = {}  # {'league_id:team' ou 'team': {'attack': float, 'defense': float}}

    @staticmethod
    def _key(team_name, league_id=None):
        """Clé interne : 'league_id:team' si league_id fourni, sinon 'team' seul."""
        return f"{league_id}:{team_name}" if league_id is not None else team_name

    def get_stats(self, team_name, league_id=None):
        """Récupère les stats attack/defense d'une équipe, avec fallback migration.

        Cherche d'abord la clé 'league_id:team', puis 'team' seule (ancien format).
        Retourne {'attack': float, 'defense': float} ou {} si inconnu.
        """
        key = self._key(team_name, league_id)
        if key in self.team_stats:
            return self.team_stats[key]
        # Fallback : stats sans league (migration transparente de l'ancien format)
        if league_id is not None and team_name in self.team_stats:
            return self.team_stats[team_name]
        return {}

    def update_stats(self, team, goals_for, goals_against, matches_played, league_id=None):
        """Met à jour les statistiques d'attaque et de défense (par ligue si league_id fourni)."""
        if matches_played > 0:
            avg_goals_for = goals_for / matches_played
            avg_goals_against = goals_against / matches_played

            key = self._key(team, league_id)
            if key not in self.team_stats:
                self.team_stats[key] = {'attack': avg_goals_for, 'defense': avg_goals_against}
            else:
                # Moyenne mobile pondérée
                self.team_stats[key]['attack']  = 0.7 * self.team_stats[key]['attack']  + 0.3 * avg_goals_for
                self.team_stats[key]['defense'] = 0.7 * self.team_stats[key]['defense'] + 0.3 * avg_goals_against

    def get_expected_goals(self, home_team, away_team, league_avg_goals=2.5, league_id=None):
        """Calcule le nombre de buts attendus pour chaque équipe (stats par ligue si disponibles)."""
        default = league_avg_goals / 2
        h = self.get_stats(home_team, league_id)
        a = self.get_stats(away_team, league_id)

        home_attack  = h.get('attack',  default)
        home_defense = h.get('defense', default)
        away_attack  = a.get('attack',  default)
        away_defense = a.get('defense', default)

        # Expected goals avec ajustement domicile/extérieur
        home_xg = home_attack * (away_defense / league_avg_goals) * 1.1  # +10% à domicile
        away_xg = away_attack * (home_defense / league_avg_goals) * 0.9  # -10% à l'extérieur

        return home_xg, away_xg
    
    @staticmethod
    def _dixon_coles_tau(x, y, lam, mu, rho):
        """Facteur de correction Dixon-Coles pour les scores faibles (x+y <= 1).

        Le modèle Poisson indépendant sous-estime les 0-0 et 1-1 et surestime
        les 1-0 et 0-1. Ce facteur corrige cette dépendance :

            τ(0,0) = 1 - λμρ   → booste 0-0  (ρ < 0 ⟹ facteur > 1)
            τ(1,0) = 1 + μρ    → réduit  1-0
            τ(0,1) = 1 + λρ    → réduit  0-1
            τ(1,1) = 1 - ρ     → booste  1-1
            τ(x,y) = 1         → inchangé pour x+y > 1

        Référence : Dixon & Coles (1997), Applied Statistics, 46(2).
        """
        if x == 0 and y == 0:
            return 1.0 - lam * mu * rho
        if x == 1 and y == 0:
            return 1.0 + mu * rho
        if x == 0 and y == 1:
            return 1.0 + lam * rho
        if x == 1 and y == 1:
            return 1.0 - rho
        return 1.0

    def predict_match(self, home_team, away_team, max_goals=10, league_id=None):
        """Prédit les probabilités de résultat avec Poisson + correction Dixon-Coles.

        league_id : si fourni, utilise les stats spécifiques à la compétition.
        """
        home_xg, away_xg = self.get_expected_goals(home_team, away_team, league_id=league_id)

        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0

        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                tau = self._dixon_coles_tau(i, j, home_xg, away_xg, self.rho)
                prob = tau * poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)

                if i > j:
                    prob_home += prob
                elif i == j:
                    prob_draw += prob
                else:
                    prob_away += prob

        # Normaliser (la correction brise légèrement la somme à 1)
        total = prob_home + prob_draw + prob_away
        if total > 0:
            prob_home /= total
            prob_draw /= total
            prob_away /= total

        return {
            'home': prob_home,
            'draw': prob_draw,
            'away': prob_away,
            'home_xg': home_xg,
            'away_xg': away_xg
        }


# ==========================================
# 3. XGBOOST MODEL
# ==========================================

class XGBoostPredictor:
    """Modèle XGBoost pour prédire les résultats"""
    
    def __init__(self):
        self.model = None
        self.model_file = "xgboost_model.pkl"
        self.is_trained = False
        self.is_calibrated = False
        self._calibrators = None
        self._calibration_method = None
        self.load_model()

    def _default_model_json_path(self):
        return os.path.splitext(self.model_file)[0] + ".json"

    def _resolve_model_json_path(self, model_json=None):
        if not model_json:
            return self._default_model_json_path()
        if os.path.isabs(model_json):
            return model_json
        model_dir = os.path.dirname(self.model_file)
        return os.path.join(model_dir, model_json) if model_dir else model_json
    
    def load_model(self):
        """Charge un modèle pré-entraîné (brut ou calibré)"""
        if os.path.exists(self.model_file):
            try:
                legacy_model_loaded = False
                with open(self.model_file, 'rb') as f:
                    data = pickle.load(f)
                if isinstance(data, dict) and data.get('model_format') == 'xgboost_json':
                    model_json_path = self._resolve_model_json_path(data.get('model_json'))
                    model = XGBClassifier()
                    model.load_model(model_json_path)
                    self.model = model
                    self.is_calibrated = data.get('is_calibrated', False)
                    self._calibrators = data.get('calibrators', None)
                    self._calibration_method = data.get('calibration_method', None)
                elif isinstance(data, dict) and 'model' in data:
                    self.model = data['model']
                    self.is_calibrated = data.get('is_calibrated', False)
                    self._calibrators = data.get('calibrators', None)
                    self._calibration_method = data.get('calibration_method', None)
                    legacy_model_loaded = True
                else:
                    # Ancien format : modèle brut sans dict
                    self.model = data
                    self.is_calibrated = False
                    self._calibrators = None
                    self._calibration_method = None
                    legacy_model_loaded = True
                self.is_trained = self.model is not None
                # Migration transparente vers un format stable inter-versions XGBoost.
                if legacy_model_loaded and self.model is not None:
                    try:
                        self._save_model()
                    except Exception:
                        pass
            except Exception:
                self.model = None
                self.is_trained = False
                self.is_calibrated = False
                self._calibrators = None
                self._calibration_method = None
        elif os.path.exists(self._default_model_json_path()):
            try:
                model = XGBClassifier()
                model.load_model(self._default_model_json_path())
                self.model = model
                self.is_trained = True
                self.is_calibrated = False
                self._calibrators = None
                self._calibration_method = None
            except Exception:
                self.model = None
                self.is_trained = False
                self.is_calibrated = False
                self._calibrators = None
                self._calibration_method = None
        else:
            self.model = None
            self.is_trained = False
            self.is_calibrated = False
            self._calibrators = None
            self._calibration_method = None
    
    # Jours de récupération : valeurs de référence
    REST_CAP     = 14   # Au-delà de 14 jours, récupération complète
    REST_DEFAULT = 7    # Valeur neutre quand l'info n'est pas disponible

    # Valeurs par défaut pour les stats rolling (quand historique insuffisant)
    STAT_DEFAULTS = {
        'xg':            1.25,
        'shots_on_goal': 4.5,
        'total_shots':   12.0,
        'possession':    50.0,
    }

    def create_features(self, home_team, away_team, elo_ratings, poisson_stats,
                        home_form=None, away_form=None, injuries=None, h2h=None,
                        bookmaker_odds=None, league_id=None,
                        home_days_rest=None, away_days_rest=None,
                        home_match_stats=None, away_match_stats=None):
        """
        Crée les features pour XGBoost (44 base + 3 fatigue + 10 stats = 57 total)

        Args:
            home_team / away_team: Noms des équipes
            elo_ratings: Dict avec ratings Elo
            poisson_stats: Dict avec stats Poisson
            home_form / away_form: Forme récente (wins, draws, losses)
            injuries: Blessures/suspensions
            h2h: Stats confrontations directes
            bookmaker_odds: Cotes bookmakers (home_avg, draw_avg, away_avg)
            league_id: ID de la ligue (2 = Ligue des Champions)
            home_days_rest / away_days_rest: Jours repos (None → 7)
            home_match_stats / away_match_stats: Stats rolling précédents matchs
                {'xg', 'shots_on_goal', 'total_shots', 'possession'} ou None
        """
        home_rating = elo_ratings.get(home_team, 1500)
        away_rating = elo_ratings.get(away_team, 1500)
        
        home_attack = poisson_stats.get(home_team, {}).get('attack', 1.25)
        home_defense = poisson_stats.get(home_team, {}).get('defense', 1.25)
        away_attack = poisson_stats.get(away_team, {}).get('attack', 1.25)
        away_defense = poisson_stats.get(away_team, {}).get('defense', 1.25)
        
        # Features de base
        elo_diff = home_rating - away_rating
        home_attack_defense_ratio = home_attack / (home_defense + 0.1)  # +0.1 pour éviter division par 0
        away_attack_defense_ratio = away_attack / (away_defense + 0.1)
        
        features = [
            home_rating,                    # 0: Rating Elo domicile
            away_rating,                    # 1: Rating Elo extérieur
            elo_diff,                       # 2: Différence Elo
            home_attack,                    # 3: Attaque domicile
            home_defense,                   # 4: Défense domicile
            away_attack,                    # 5: Attaque extérieur
            away_defense,                   # 6: Défense extérieur
            home_attack - away_defense,     # 7: Attaque home vs Défense away
            away_attack - home_defense,     # 8: Attaque away vs Défense home
            home_attack_defense_ratio,      # 9: Ratio attaque/défense home
            away_attack_defense_ratio,      # 10: Ratio attaque/défense away
            (home_attack + home_defense) / 2,  # 11: Force moyenne home
            (away_attack + away_defense) / 2,  # 12: Force moyenne away
        ]
        
        # Ajouter forme récente si disponible
        if home_form:
            home_wins = home_form.get('wins', 0)
            home_draws = home_form.get('draws', 0)
            home_losses = home_form.get('losses', 0)
            home_total = home_wins + home_draws + home_losses
            home_form_score = (home_wins * 3 + home_draws) / (home_total * 3 + 0.1) if home_total > 0 else 0
            features.extend([home_wins, home_draws, home_losses, home_form_score])
        else:
            features.extend([0, 0, 0, 0])
        
        if away_form:
            away_wins = away_form.get('wins', 0)
            away_draws = away_form.get('draws', 0)
            away_losses = away_form.get('losses', 0)
            away_total = away_wins + away_draws + away_losses
            away_form_score = (away_wins * 3 + away_draws) / (away_total * 3 + 0.1) if away_total > 0 else 0
            features.extend([away_wins, away_draws, away_losses, away_form_score])
        else:
            features.extend([0, 0, 0, 0])
        
        # Différence de forme entre équipes
        if home_form and away_form:
            home_form_score = (home_form.get('wins', 0) * 3 + home_form.get('draws', 0)) / (max(home_form.get('wins', 0) + home_form.get('draws', 0) + home_form.get('losses', 0), 1) * 3)
            away_form_score = (away_form.get('wins', 0) * 3 + away_form.get('draws', 0)) / (max(away_form.get('wins', 0) + away_form.get('draws', 0) + away_form.get('losses', 0), 1) * 3)
            features.append(home_form_score - away_form_score)  # Différence de forme
        else:
            features.append(0)
        
        # Ajouter blessures et suspensions si disponibles
        if injuries:
            features.extend([
                injuries.get('home_injuries', 0),           # Nombre de blessés home
                injuries.get('away_injuries', 0),           # Nombre de blessés away
                injuries.get('home_suspensions', 0),        # Nombre de suspendus home
                injuries.get('away_suspensions', 0),        # Nombre de suspendus away
                injuries.get('home_questionable', 0),       # Nombre de douteux home
                injuries.get('away_questionable', 0),       # Nombre de douteux away
                (injuries.get('home_injuries', 0) + injuries.get('home_suspensions', 0)),  # Total absents home
                (injuries.get('away_injuries', 0) + injuries.get('away_suspensions', 0)),    # Total absents away
            ])
        else:
            features.extend([0, 0, 0, 0, 0, 0, 0, 0])
        
        # Ajouter confrontations directes (H2H) si disponibles
        if h2h and h2h.get('total_matches', 0) > 0:
            total_h2h = h2h.get('total_matches', 1)
            home_wins_h2h = h2h.get('home_wins', 0)
            away_wins_h2h = h2h.get('away_wins', 0)
            draws_h2h = h2h.get('draws', 0)
            
            features.extend([
                home_wins_h2h / total_h2h,                  # Taux de victoires home en H2H
                away_wins_h2h / total_h2h,                  # Taux de victoires away en H2H
                draws_h2h / total_h2h,                      # Taux de matchs nuls en H2H
                h2h.get('home_goals_avg', 0.0),             # Moyenne buts home en H2H
                h2h.get('away_goals_avg', 0.0),             # Moyenne buts away en H2H
                h2h.get('home_goals_avg', 0.0) - h2h.get('away_goals_avg', 0.0),  # Différence buts H2H
                total_h2h,                                 # Nombre total de matchs H2H
            ])
        else:
            features.extend([0, 0, 0, 0, 0, 0, 0])
        
        # Ajouter cotes bookmakers si disponibles (feature importante : le marché apporte de l'info)
        if bookmaker_odds:
            home_odd = bookmaker_odds.get('home_avg', 0)
            draw_odd = bookmaker_odds.get('draw_avg', 0)
            away_odd = bookmaker_odds.get('away_avg', 0)
            # Proba implicites (1/cote, normalisées)
            if home_odd > 0 and draw_odd > 0 and away_odd > 0:
                prob_home_impl = 1.0 / home_odd
                prob_draw_impl = 1.0 / draw_odd
                prob_away_impl = 1.0 / away_odd
                total_impl = prob_home_impl + prob_draw_impl + prob_away_impl
                if total_impl > 0:
                    prob_home_impl /= total_impl
                    prob_draw_impl /= total_impl
                    prob_away_impl /= total_impl
                features.extend([
                    home_odd,              # Cote moyenne home
                    draw_odd,               # Cote moyenne draw
                    away_odd,               # Cote moyenne away
                    prob_home_impl,         # Proba implicite home
                    prob_draw_impl,         # Proba implicite draw
                    prob_away_impl,         # Proba implicite away
                ])
            else:
                features.extend([0, 0, 0, 0, 0, 0])
        else:
            features.extend([0, 0, 0, 0, 0, 0])
        
        # Ajouter feature "is_champions_league" (1 si league_id == 2, 0 sinon)
        is_champions_league = 1.0 if league_id == 2 else 0.0
        features.append(is_champions_league)

        # ── Fatigue / récupération ───────────────────────────────────────────
        h_rest = min(home_days_rest if home_days_rest is not None else self.REST_DEFAULT, self.REST_CAP)
        a_rest = min(away_days_rest if away_days_rest is not None else self.REST_DEFAULT, self.REST_CAP)
        features.extend([
            h_rest,
            a_rest,
            h_rest - a_rest,
        ])

        # ── Stats rolling (xG, tirs, possession) ────────────────────────────
        # Moyennes des N derniers matchs de chaque équipe AVANT ce match.
        # Valeurs par défaut quand l'historique est insuffisant.
        d = self.STAT_DEFAULTS
        h = home_match_stats or {}
        a = away_match_stats or {}
        h_xg   = h.get('xg',            d['xg'])
        h_sog  = h.get('shots_on_goal',  d['shots_on_goal'])
        h_ts   = h.get('total_shots',    d['total_shots'])
        h_poss = h.get('possession',     d['possession'])
        a_xg   = a.get('xg',            d['xg'])
        a_sog  = a.get('shots_on_goal',  d['shots_on_goal'])
        a_ts   = a.get('total_shots',    d['total_shots'])
        a_poss = a.get('possession',     d['possession'])
        features.extend([
            h_xg,  h_sog,  h_ts,  h_poss,   # Stats rolling home (4)
            a_xg,  a_sog,  a_ts,  a_poss,   # Stats rolling away (4)
            h_xg  - a_xg,                    # Avantage xG
            h_sog - a_sog,                   # Avantage tirs cadrés
        ])

        return np.array(features).reshape(1, -1)
    
    def train(self, X, y):
        """Entraîne le modèle XGBoost"""
        # Calculer les poids des classes pour équilibrer (surtout pour les matchs nuls)
        from collections import Counter
        class_counts = Counter(y)
        total = len(y)
        
        # Compter les classes
        home_count = class_counts.get(0, 1)
        draw_count = class_counts.get(1, 1)
        away_count = class_counts.get(2, 1)
        
        # Calculer les poids pour un équilibre réaliste entre les 3 classes
        # On donne 1.2x plus de poids aux matchs nuls (équilibre réaliste)
        # Objectif : Home ~45%, Draw ~25%, Away ~30% (proportions réalistes du football)
        avg_count = (home_count + away_count) / 2  # Moyenne Home/Away
        draw_weight_multiplier = avg_count / draw_count * 1.2  # Boost x1.2 pour les matchs nuls (léger)
        
        class_weights = {
            0: 1.0,  # Home: poids normal
            1: draw_weight_multiplier,  # Draw: poids modéré
            2: 1.0   # Away: poids normal
        }
        
        # Créer sample_weight pour équilibrer les classes
        sample_weight = [class_weights[label] for label in y]
        
        # Hyperparamètres : un peu plus de régularisation pour limiter l'overfitting
        # XGBoost 2.x : early_stopping_rounds se passe dans le constructeur
        self.model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.04,
            min_child_weight=4,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.15,
            reg_alpha=0.15,
            reg_lambda=1.2,
            random_state=42,
            eval_metric='mlogloss',
            early_stopping_rounds=25,
        )
        # Validation sur 10% des données pour early stopping
        n = len(X)
        val_size = max(100, n // 10)
        X_fit, X_val = X[:-val_size], X[-val_size:]
        y_fit, y_val = y[:-val_size], y[-val_size:]
        w_fit = sample_weight[:-val_size] if len(sample_weight) == n else None
        fit_kw = dict(sample_weight=w_fit) if w_fit else {}
        self.model.fit(
            X_fit, y_fit,
            eval_set=[(X_val, y_val)],
            verbose=False,
            **fit_kw
        )
        self.is_trained = True
        self.is_calibrated = False
        self._save_model()

    def calibrate(self, X_cal, y_cal, method='isotonic'):
        """Calibre les probabilités du modèle sur un jeu de calibration dédié.

        Approche : calibration isotonique (ou Platt/sigmoid) par classe.
        Pour chaque classe k, on ajuste un régresseur sur les probabilités brutes
        du XGBoost afin de corriger les biais systématiques.

        Args:
            X_cal: Features de calibration (numpy array), jamais vues à l'entraînement.
            y_cal: Labels de calibration (0=Home, 1=Draw, 2=Away).
            method: 'isotonic' (recommandé si > 1000 exemples) ou 'sigmoid' (Platt).
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Le modèle doit être entraîné avant la calibration.")

        from sklearn.isotonic import IsotonicRegression
        from sklearn.linear_model import LogisticRegression

        raw_proba = self.model.predict_proba(X_cal)   # (n, 3)
        n_classes = raw_proba.shape[1]
        calibrators = []

        for k in range(n_classes):
            y_bin = (np.array(y_cal) == k).astype(float)
            if method == 'isotonic':
                cal = IsotonicRegression(out_of_bounds='clip')
                cal.fit(raw_proba[:, k], y_bin)
            else:  # sigmoid / Platt scaling
                cal = LogisticRegression(C=1.0)
                cal.fit(raw_proba[:, k].reshape(-1, 1), y_bin)
            calibrators.append(cal)

        self._calibrators = calibrators
        self._calibration_method = method
        self.is_calibrated = True
        self._save_model()

    def _save_model(self):
        """Sauvegarde le modèle avec ses métadonnées."""
        if self.model is None:
            return

        model_json_path = self._default_model_json_path()
        model_json_name = os.path.basename(model_json_path)

        try:
            # Format stable entre versions XGBoost.
            self.model.save_model(model_json_path)
            with open(self.model_file, 'wb') as f:
                pickle.dump({
                    'model_format': 'xgboost_json',
                    'model_json': model_json_name,
                    'is_calibrated': self.is_calibrated,
                    'calibrators': self._calibrators,
                    'calibration_method': self._calibration_method,
                }, f)
        except Exception:
            # Fallback pour ne pas bloquer l'entraînement en cas de souci I/O.
            with open(self.model_file, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'is_calibrated': self.is_calibrated,
                    'calibrators': self._calibrators,
                    'calibration_method': self._calibration_method,
                }, f)
    
    def predict(self, features):
        """Prédit les probabilités avec XGBoost (+ calibration si disponible)"""
        if not self.is_trained or self.model is None:
            return None

        try:
            raw = self.model.predict_proba(features)[0]   # [p_home, p_draw, p_away]

            if self.is_calibrated and self._calibrators:
                # Appliquer chaque calibrateur sur la proba brute de sa classe
                cal = self._calibrators
                method = self._calibration_method
                if method == 'isotonic':
                    probs = np.array([cal[k].predict([raw[k]])[0] for k in range(3)])
                else:  # sigmoid
                    probs = np.array([cal[k].predict_proba([[raw[k]]])[0][1] for k in range(3)])
                # Re-normaliser (la calibration peut légèrement déséquilibrer la somme)
                total = probs.sum()
                if total > 0:
                    probs /= total
            else:
                probs = raw

            return {
                'home': float(probs[0]) if len(probs) > 0 else 0.33,
                'draw': float(probs[1]) if len(probs) > 1 else 0.33,
                'away': float(probs[2]) if len(probs) > 2 else 0.33,
            }
        except Exception:
            return None


# ==========================================
# 4. COMBINAISON DES MÉTHODES
# ==========================================

# ==========================================
# KELLY CRITERION
# ==========================================

def days_since_last_match(last_date_str, current_date_str, cap=14):
    """Calcule les jours entre deux dates ISO (YYYY-MM-DD), plafonné à cap.

    Retourne None si une des deux dates est absente ou invalide.
    """
    if not last_date_str or not current_date_str:
        return None
    try:
        last = datetime.strptime(last_date_str[:10], '%Y-%m-%d')
        curr = datetime.strptime(current_date_str[:10], '%Y-%m-%d')
        diff = (curr - last).days
        return min(max(diff, 0), cap)
    except (ValueError, TypeError):
        return None


def kelly_fraction(prob: float, decimal_odd: float, fraction: float = 0.5, max_bet: float = 0.25) -> float:
    """Calcule la mise optimale selon le critère de Kelly.

    Formule de Kelly :
        f* = (p · b - q) / b     où b = decimal_odd - 1, q = 1 - p

    En pratique on utilise le « fractional Kelly » (fraction=0.5 par défaut)
    pour réduire la variance sans trop sacrifier la croissance.

    Args:
        prob:         Probabilité de victoire estimée par le modèle (0-1).
        decimal_odd:  Cote décimale du bookmaker (ex. 1.90).
        fraction:     Fraction de Kelly à appliquer (0.5 = demi-Kelly).
        max_bet:      Plafond de mise en fraction du bankroll (défaut 25 %).

    Returns:
        Fraction du bankroll à miser (0 si pas d'edge, jamais > max_bet).
    """
    if decimal_odd <= 1.0 or prob <= 0.0 or prob >= 1.0:
        return 0.0
    b = decimal_odd - 1.0
    q = 1.0 - prob
    f = (prob * b - q) / b
    if f <= 0:
        return 0.0          # Pas d'edge → pas de mise
    return min(f * fraction, max_bet)


class AdvancedPredictor:
    """Combine Elo + Poisson + XGBoost pour des prédictions précises"""
    
    def __init__(self):
        self.elo = EloRating()
        self.poisson = PoissonPredictor()
        self.xgboost = XGBoostPredictor()
    
    def predict_match(self, home_team, away_team, weights=None, home_form=None, away_form=None,
                      injuries=None, h2h=None, bookmaker_odds=None, league_id=None,
                      home_days_rest=None, away_days_rest=None,
                      home_match_stats=None, away_match_stats=None):
        """
        Prédit un match en combinant les 3 méthodes.

        home_match_stats / away_match_stats : stats rolling des matchs précédents
            {'xg', 'shots_on_goal', 'total_shots', 'possession'} ou None
        """
        if weights is None:
            weights = {'elo': 0.3, 'poisson': 0.3, 'xgboost': 0.4}
        
        # Prédictions Elo (avec ratings spécifiques à la compétition si league_id fourni)
        elo_pred = self.elo.predict_match(home_team, away_team, league_id=league_id)
        
        # Prédictions Poisson (avec stats spécifiques à la compétition si league_id fourni)
        poisson_pred = self.poisson.predict_match(home_team, away_team, league_id=league_id)

        # Prédictions XGBoost
        elo_ratings = {home_team: elo_pred['home_rating'],
                      away_team: elo_pred['away_rating']}
        _default = 1.25
        h_stats = self.poisson.get_stats(home_team, league_id)
        a_stats = self.poisson.get_stats(away_team, league_id)
        poisson_stats = {
            home_team: {
                'attack':  h_stats.get('attack',  _default),
                'defense': h_stats.get('defense', _default),
            },
            away_team: {
                'attack':  a_stats.get('attack',  _default),
                'defense': a_stats.get('defense', _default),
            },
        }
        
        features = self.xgboost.create_features(
            home_team, away_team, elo_ratings, poisson_stats,
            home_form=home_form, away_form=away_form,
            injuries=injuries, h2h=h2h, bookmaker_odds=bookmaker_odds,
            league_id=league_id,
            home_days_rest=home_days_rest, away_days_rest=away_days_rest,
            home_match_stats=home_match_stats, away_match_stats=away_match_stats,
        )
        xgboost_pred = self.xgboost.predict(features)
        
        # Si XGBoost n'est pas entraîné, utiliser seulement Elo + Poisson
        if xgboost_pred is None:
            weights = {'elo': 0.5, 'poisson': 0.5, 'xgboost': 0.0}
            xgboost_pred = {'home': 0.33, 'draw': 0.33, 'away': 0.33}
        
        # Combinaison pondérée
        final_probs = {
            'home': (weights['elo'] * elo_pred['home'] + 
                    weights['poisson'] * poisson_pred['home'] + 
                    weights['xgboost'] * xgboost_pred['home']),
            'draw': (weights['elo'] * elo_pred['draw'] + 
                    weights['poisson'] * poisson_pred['draw'] + 
                    weights['xgboost'] * xgboost_pred['draw']),
            'away': (weights['elo'] * elo_pred['away'] + 
                    weights['poisson'] * poisson_pred['away'] + 
                    weights['xgboost'] * xgboost_pred['away'])
        }
        
        # Normaliser
        total = sum(final_probs.values())
        if total > 0:
            for key in final_probs:
                final_probs[key] /= total
        
        return {
            'probabilities': final_probs,
            'elo': elo_pred,
            'poisson': poisson_pred,
            'xgboost': xgboost_pred,
            'elo_ratings': {'home': elo_pred['home_rating'], 
                          'away': elo_pred['away_rating']},
            'expected_goals': {'home': poisson_pred.get('home_xg', 0), 
                            'away': poisson_pred.get('away_xg', 0)}
        }
    
    def update_after_match(self, home_team, away_team, home_goals, away_goals, league_id=None):
        """Met à jour tous les modèles après un match"""
        # Mettre à jour Elo (avec isolation par ligue si league_id fourni)
        self.elo.update_ratings(home_team, away_team, home_goals, away_goals,
                                league_id=league_id)
        
        # Mettre à jour Poisson (nécessite des stats de saison)
        # À implémenter avec les données de l'API
