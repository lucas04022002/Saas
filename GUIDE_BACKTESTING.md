# 📊 Guide : Système de Backtesting

## 🎯 Objectif

Le système de backtesting permet de tester les performances de votre modèle sur des données historiques. Cela vous permet de :
- Évaluer la précision réelle du modèle
- Identifier les forces et faiblesses
- Comparer les performances par ligue
- Analyser les value bets détectés

---

## 🚀 Utilisation

### Lancement simple

```bash
python backtesting.py
```

### Configuration

Dans `backtesting.py`, vous pouvez modifier :

```python
SEASON = 2024
START_DATE = "2024-12-01"  # Début de la période de test
END_DATE = "2024-12-31"    # Fin de la période de test
```

### Exemple : Tester les 30 derniers jours

```python
from datetime import datetime, timedelta

end_date = datetime.now() - timedelta(days=1)
start_date = end_date - timedelta(days=30)
START_DATE = start_date.strftime('%Y-%m-%d')
END_DATE = end_date.strftime('%Y-%m-%d')
```

---

## 📊 Résultats

### Statistiques affichées

1. **Précision globale** : Pourcentage de prédictions correctes
2. **Précision par résultat** :
   - Home (victoire domicile)
   - Draw (match nul)
   - Away (victoire extérieur)
3. **Value bets** : Prédictions avec probabilité > 50% et leur précision

### Fichiers générés

Pour chaque ligue :
- `backtest_[Ligue]_[Saison].json` : Détails de chaque prédiction

Résumé global :
- `backtest_summary_[Saison].json` : Statistiques globales

---

## 📈 Interprétation des résultats

### Précision globale

- **> 60%** : Excellent ! Le modèle est très performant
- **50-60%** : Bon, meilleur que le hasard (33.3%)
- **40-50%** : Acceptable, mais peut être amélioré
- **< 40%** : Problème, vérifier le modèle

### Précision par résultat

- **Home/Away** : Généralement plus facile à prédire
- **Draw** : Plus difficile (souvent < 30%)

### Value bets

Si la précision des value bets est > 60%, votre modèle détecte bien les opportunités !

---

## 🔧 Personnalisation

### Tester une seule ligue

```python
backtest_league(
    league_id=39,  # Premier League
    league_name="Premier League (Ang)",
    season=2024,
    start_date="2024-12-01",
    end_date="2024-12-31"
)
```

### Tester plusieurs périodes

```python
# Période 1
backtest_league(..., start_date="2024-11-01", end_date="2024-11-30")

# Période 2
backtest_league(..., start_date="2024-12-01", end_date="2024-12-31")
```

---

## ⚠️ Notes importantes

1. **Ratings Elo** : Utilise les ratings actuels (pas ceux au moment du match)
   - Pour plus de précision, il faudrait recalculer Elo à chaque match

2. **Forme récente** : Récupérée depuis l'API pour chaque match
   - Peut être lente si beaucoup de matchs

3. **Quotas API** : Chaque match nécessite 2 requêtes (forme home + away)
   - 100 matchs = 200 requêtes
   - Avec 7500 req/jour, vous pouvez tester ~3750 matchs/jour

---

## 📝 Exemple de sortie

```
============================================================
BACKTESTING: Premier League (Ang)
Période: 2024-12-01 à 2024-12-31
============================================================

Récupération des matchs de test...
   45 matchs trouvés

Test des prédictions...
   → 45/45 matchs testés...

============================================================
RÉSULTATS DU BACKTESTING
============================================================

Précision globale: 55.6% (25/45)

Précision par résultat:
   Home: 62.5% (10/16)
   Draw: 20.0% (2/10)
   Away: 68.4% (13/19)

Value bets (prob > 50%):
   Nombre: 28
   Précision: 64.3% (18/28)

Résultats sauvegardés dans: backtest_Premier_League_(Ang)_2024.json
```

---

**Le backtesting vous permet de valider votre modèle avant de l'utiliser en réel ! 🎯**
