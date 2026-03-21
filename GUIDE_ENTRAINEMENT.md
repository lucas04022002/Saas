# 🎓 Guide : Entraîner XGBoost

## 📋 Vue d'ensemble

Pour améliorer la précision des prédictions, vous devez entraîner le modèle XGBoost avec des données historiques. Ce guide vous explique comment faire.

---

## 🎯 Ce qui doit être entraîné

### 1. **XGBoost** (Machine Learning) ⭐⭐⭐
- **État actuel** : Non entraîné (utilise seulement Elo + Poisson)
- **Impact** : Améliore significativement la précision des prédictions
- **Temps** : 30-60 minutes selon le nombre de matchs

### 2. **Ratings Elo** (Initialisation) ⭐⭐
- **État actuel** : Toutes les équipes à 1500 points
- **Impact** : Prédictions Elo plus précises
- **Temps** : 10-20 minutes

### 3. **Stats Poisson** (Données réelles) ⭐⭐
- **État actuel** : Valeurs par défaut (1.25 buts/match)
- **Impact** : Expected Goals plus réalistes
- **Temps** : 10-15 minutes

---

## 🚀 Entraînement XGBoost

### Étape 1 : Installer les dépendances

Assurez-vous d'avoir toutes les dépendances :

```bash
pip install -r requirements.txt
```

Si `scikit-learn` n'est pas installé :

```bash
pip install scikit-learn
```

### Étape 2 : Lancer l'entraînement

```bash
python train_xgboost.py
```

### Ce que fait le script :

1. **Collecte les matchs historiques** (saisons 2024-2025)
2. **Initialise les ratings Elo** avec l'historique
3. **Charge les stats Poisson** si disponibles
4. **Extrait les features** pour chaque match :
   - Ratings Elo (home, away)
   - Stats attaque/défense (home, away)
   - Forme récente (5 derniers matchs)
   - Différences entre équipes
5. **Prépare les labels** (résultats réels : Home/Draw/Away)
6. **Entraîne XGBoost** avec ces données
7. **Évalue les performances** (précision, rapport détaillé)
8. **Sauvegarde le modèle** dans `xgboost_model.pkl`

### Exemple de sortie :

```
╔════════════════════════════════════════╗
║  ENTRAÎNEMENT XGBOOST                 ║
║  Collecte de données historiques      ║
╚════════════════════════════════════════╝

🚀 ENTRAÎNEMENT XGBOOST - Premier League (Ang)
==================================================

📊 Préparation des données pour Premier League (Ang)
==================================================
   → Stats chargées pour 20 équipes

   Récupération saison 2024...
   → 380 matchs terminés trouvés pour la saison 2024
   → Initialisation Elo avec 380 matchs...

   Récupération saison 2025...
   → 150 matchs terminés trouvés pour la saison 2025
   → Initialisation Elo avec 150 matchs...

   ✓ Total: 530 matchs collectés

   Extraction des features...
   → 50/530 matchs traités...
   → 100/530 matchs traités...
   ...
   ✓ 530 échantillons préparés

   Données d'entraînement: 424 matchs
   Données de test: 106 matchs

   Entraînement en cours...

   ✓ Modèle entraîné !
   Précision sur le test: 58.5%

   Rapport détaillé:
                precision    recall  f1-score   support

        Home       0.62      0.65      0.63        35
        Draw       0.45      0.38      0.41        29
        Away       0.65      0.69      0.67        42

    accuracy                           0.58       106
```

---

## ⚙️ Configuration

### Modifier les saisons à utiliser

Dans `train_xgboost.py`, ligne ~280 :

```python
train_model(
    ligue['id_foot'],
    ligue['nom'],
    seasons=[2024, 2025]  # ← Modifier ici
)
```

**Recommandations** :
- **Minimum** : 1 saison complète (380 matchs pour Premier League)
- **Idéal** : 2-3 saisons (760-1140 matchs)
- **Maximum** : 5 saisons (attention aux quotas API)

### Modifier les ligues

Dans `train_xgboost.py`, lignes ~270-277 :

```python
LIGUES = [
    {"nom": "Premier League (Ang)", "id_foot": 39},
    {"nom": "Ligue 1 (Fra)", "id_foot": 61},
    # Ajouter/supprimer des ligues ici
]
```

---

## 📊 Améliorer les données avant l'entraînement

### Option 1 : Récupérer les stats réelles (Recommandé)

```bash
python data_collector.py
```

Cela va :
- Récupérer les stats de saison pour toutes les équipes
- Mettre à jour Poisson avec des valeurs réelles
- Améliorer la qualité des features pour XGBoost

### Option 2 : Initialiser Elo séparément

Le script `train_xgboost.py` initialise Elo automatiquement, mais vous pouvez aussi le faire manuellement :

```bash
python data_collector.py
```

---

## ⚠️ Quotas API

### Limites (Plan Gratuit)

- **API-Football** : 100 requêtes/jour
- **The-Odds-API** : 500 requêtes/mois

### Estimation des requêtes

Pour entraîner XGBoost sur 1 ligue, 2 saisons :
- **Récupération matchs** : ~2 requêtes (1 par saison)
- **Total** : ~2 requêtes par ligue

**→ Vous pouvez entraîner plusieurs ligues en une fois !**

---

## ✅ Vérification

Après l'entraînement, vérifiez que le modèle est sauvegardé :

```bash
# Vérifier que le fichier existe
dir xgboost_model.pkl
```

Ensuite, testez l'algorithme :

```bash
python "Algo plus APi.py"
```

Si XGBoost est entraîné, vous verrez des prédictions plus précises !

---

## 🔧 Dépannage

### Erreur : "Pas assez de données"

**Solution** :
- Utilisez plus de saisons : `seasons=[2023, 2024, 2025]`
- Vérifiez que les matchs sont bien terminés (status='FT')

### Erreur : "ModuleNotFoundError: No module named 'sklearn'"

**Solution** :
```bash
pip install scikit-learn
```

### Erreur : "Quota API dépassé"

**Solution** :
- Attendez 24h pour le quota journalier
- Ou entraînez une ligue à la fois

### Précision faible (< 50%)

**Causes possibles** :
- Pas assez de données (< 200 matchs)
- Stats Poisson non mises à jour
- Ratings Elo non initialisés

**Solutions** :
1. Utilisez plus de saisons
2. Lancez `python data_collector.py` avant
3. Vérifiez que les features sont bien extraites

---

## 📈 Résultats attendus

### Précision typique

- **Sans entraînement** (Elo + Poisson seulement) : ~45-50%
- **Avec XGBoost entraîné** : ~55-65%
- **Avec données améliorées** : ~60-70%

### Interprétation

- **> 60%** : Excellent ! Le modèle est bien entraîné
- **50-60%** : Bon, mais peut être amélioré
- **< 50%** : Problème, vérifiez les données

**Note** : La précision dépend beaucoup de la ligue et de la qualité des données.

---

## 🎯 Prochaines étapes

Après avoir entraîné XGBoost :

1. **Tester les prédictions** : `python "Algo plus APi.py"`
2. **Comparer avec les bookmakers** : Vérifier les value bets
3. **Tracker les résultats** : Enregistrer les prédictions et comparer avec les résultats réels
4. **Ré-entraîner régulièrement** : Mettre à jour le modèle avec les nouvelles données

---

**Bon entraînement ! 🚀**
