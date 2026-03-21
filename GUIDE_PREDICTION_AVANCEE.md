# 🎯 Guide : Prédiction Avancée avec Elo + Poisson + XGBoost

## 📋 Vue d'ensemble

Votre algorithme utilise maintenant **3 méthodes combinées** pour prédire les résultats de matchs :

1. **Système Elo** : Évalue la force relative des équipes
2. **Loi de Poisson** : Modélise la distribution des buts
3. **XGBoost** : Machine Learning pour combiner toutes les features

---

## 🔧 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Configuration

Ajoutez vos clés API dans `Algo plus APi.py` :
```python
KEY_API_FOOTBALL = "votre_clé_ici"
KEY_THE_ODDS = "votre_clé_ici"
```

---

## 🎲 Comment ça fonctionne ?

### 1. **Système Elo** ⭐

- **Principe** : Chaque équipe a un rating (score de force)
- **Mise à jour** : Après chaque match, les ratings sont ajustés
- **Avantage domicile** : +100 points Elo pour l'équipe à domicile
- **Fichier** : `elo_ratings.json` (sauvegarde automatique)

**Exemple** :
- Manchester City : 1850 points
- Burnley : 1450 points
- Probabilité de victoire City : ~75%

### 2. **Loi de Poisson** 📊

- **Principe** : Modélise le nombre de buts attendus
- **Calcul** : Basé sur l'attaque et la défense de chaque équipe
- **Expected Goals (xG)** : Nombre de buts attendus par équipe

**Exemple** :
- City (attaque forte) vs Burnley (défense faible)
- City xG : 2.1 buts
- Burnley xG : 0.8 buts
- Probabilité de victoire City : ~68%

### 3. **XGBoost** 🤖

- **Principe** : Machine Learning qui apprend des patterns
- **Features** : 
  - Ratings Elo
  - Statistiques d'attaque/défense
  - Forme récente
  - Différences entre équipes
- **Entraînement** : Nécessite des données historiques

---

## 📈 Utilisation

### Lancement simple

```bash
python "Algo plus APi.py"
```

### Résultat affiché

```
[FAVORI + VALUE] Manchester City vs Burnley
Favori: Manchester City | Cote moyenne: 1.45 | Meilleure: 1.52 (Bet365)
Probabilité modèle (Elo+Poisson+XGBoost): 72.3%
Probabilité bookmakers: 68.9%
Expected Goals: 2.1 - 0.8
Elo Ratings: 1850 vs 1450
```

---

## 🔍 Interprétation des résultats

### Probabilité Modèle vs Bookmakers

- **Probabilité modèle > Probabilité bookmakers + 5%** = **VALUE BET** ✅
  - Le modèle pense que l'équipe a plus de chances que ce que les bookmakers estiment
  - Opportunité de pari rentable

- **Probabilité modèle ≈ Probabilité bookmakers** = Match équilibré
  - Les bookmakers ont bien évalué le match

- **Probabilité modèle < Probabilité bookmakers** = Pas de value bet
  - Les bookmakers sont peut-être trop optimistes

---

## 🎓 Entraînement du modèle XGBoost

### Option 1 : Utilisation sans entraînement

Le système fonctionne avec **Elo + Poisson** uniquement si XGBoost n'est pas entraîné.

### Option 2 : Entraîner XGBoost (recommandé)

Pour entraîner XGBoost, vous avez besoin de :
1. **Données historiques** : Résultats de matchs passés
2. **Features** : Ratings Elo, stats d'attaque/défense, forme récente
3. **Labels** : Résultats réels (Home/Draw/Away)

**Exemple de code pour entraîner** :

```python
from prediction_engine import XGBoostPredictor
import numpy as np

# Préparer les données
X_train = [...]  # Features (ratings, stats, etc.)
y_train = [...]   # Labels (0=Home, 1=Draw, 2=Away)

# Entraîner
predictor = XGBoostPredictor()
predictor.train(X_train, y_train)
```

---

## ⚙️ Configuration avancée

### Ajuster les poids des méthodes

Dans `prediction_engine.py`, modifiez les poids :

```python
weights = {
    'elo': 0.3,      # 30% pour Elo
    'poisson': 0.3,  # 30% pour Poisson
    'xgboost': 0.4   # 40% pour XGBoost
}
```

### Ajuster le système Elo

```python
elo = EloRating(
    k_factor=32,           # Sensibilité (plus élevé = changements plus rapides)
    home_advantage=100,     # Avantage domicile en points
    initial_rating=1500     # Rating initial
)
```

### Ajuster Poisson

```python
poisson = PoissonPredictor(
    attack_factor=1.0,     # Facteur d'attaque
    defense_factor=1.0      # Facteur de défense
)
```

---

## 📊 Fichiers générés

- `elo_ratings.json` : Ratings Elo de toutes les équipes
- `xgboost_model.pkl` : Modèle XGBoost entraîné (si disponible)

---

## 🚀 Améliorations futures

1. **Récupération automatique des stats** : Utiliser l'API pour mettre à jour Poisson
2. **Entraînement automatique** : Entraîner XGBoost avec les données de l'API
3. **Forme récente** : Intégrer les 5 derniers matchs
4. **Confrontations directes** : Historique entre les équipes
5. **Blessures/Compositions** : Facteurs externes

---

## ⚠️ Avertissements

1. **XGBoost nécessite des données** : Sans entraînement, seule Elo+Poisson est utilisée
2. **Ratings Elo** : S'améliorent avec le temps (plus de matchs = plus précis)
3. **Pas de garantie** : Les prédictions sont des estimations, pas des certitudes
4. **Gestion du bankroll** : Ne jamais parier plus que ce que vous pouvez perdre

---

## 📝 Exemple complet

```python
from prediction_engine import AdvancedPredictor

predictor = AdvancedPredictor()

# Prédire un match
result = predictor.predict_match("Manchester City", "Burnley")

print(f"Probabilité victoire City: {result['probabilities']['home']*100:.1f}%")
print(f"Expected Goals: {result['expected_goals']['home']:.2f} - {result['expected_goals']['away']:.2f}")
print(f"Elo Ratings: {result['elo_ratings']['home']:.0f} vs {result['elo_ratings']['away']:.0f}")

# Mettre à jour après le match
predictor.update_after_match("Manchester City", "Burnley", 3, 0)
```

---

**Bon trading ! 🎯**
