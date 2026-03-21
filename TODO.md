# Todo – Amélioration de l'algorithme

## Ce qu'il faut lancer (ordre et fréquence)

| Ordre | Script | Quand le lancer | Rôle |
|-------|--------|-----------------|------|
| 1 | `python data_collector.py` | 1x par semaine (ou après un gros week-end de matchs) | Met à jour les stats équipes (Poisson) et les fichiers par ligue |
| 2 | `python train_xgboost.py` | Après data_collector, ou 1x par semaine / après avoir accumulé des cotes | Récupère les matchs passés via l’API, ré-entraîne le modèle (split temporel + early stopping) et sauvegarde `xgboost_model.pkl` |
| 3 | `python Algo plus APi.py` | Chaque jour où tu veux des pronos (ou la veille pour le lendemain) | Donne les pronos du jour, récupère les cotes et les enregistre dans `historical_odds.json` pour les futurs entraînements |
| 4 | `python backtesting.py` | Après avoir ré-entraîné (train_xgboost) ou pour comparer des réglages | Évalue la précision / ROI sur des matchs passés |

**Résumé rapide**
- **Mise à jour des données** : `data_collector.py` puis `train_xgboost.py`
- **Pronos du jour** : `Algo plus APi.py`
- **Vérifier la qualité** : `backtesting.py`

---

## Déjà fait
- [x] Split temporel à l’entraînement (train = passé, test = 20 % les plus récents)
- [x] Early stopping + régularisation dans XGBoost
- [x] Cotes bookmakers comme features XGBoost (via `historical_odds.json`)

---

## Données
- [ ] Lancer `data_collector.py` régulièrement (ex. 1x/semaine)
- [ ] Vérifier que les noms d’équipes correspondent entre API-Football et The-Odds-API (moins de matchs sans cotes)

## Modèle (XGBoost)
- [ ] Ajuster les poids des classes (1 / Nul / 2) si le modèle se trompe trop sur les nuls
- [ ] Vérifier / ajouter une calibration des probabilités (proba modèle ≈ taux de réussite réel)

## Features
- [ ] Enrichir les features : contexte (journée, enjeu), jours de repos, blessures plus détaillées
- [ ] S’assurer que l’avantage domicile est bien pris en compte partout (Elo, Poisson, XGBoost)

## Règles & Value
- [ ] Rendre le seuil de "value" plus strict (ex. écart min modèle vs bookmakers)
- [ ] Ignorer les matchs où le modèle est très incertain (proba max < 45 %) ou équipes peu vues
- [ ] Option : filtrer par "meilleure cote" min pour éviter cotes trop basses

## Backtest & Suivi
- [ ] Backtest détaillé : favoris seuls vs favoris+value vs value (nul / équipe), par ligue
- [ ] Logger chaque prono (match, sélection, cote, proba, résultat) pour calculer ROI / yield
- [ ] Script ou onglet "historique des paris" pour analyser ce qui marche

## Automatisation (optionnel)
- [ ] Script ou tâche planifiée pour mise à jour hebdo (data_collector + train_xgboost)
- [ ] Export des pronos du jour (CSV / Google Sheet) pour suivi facile

---

*Coché = fait. À prioriser selon ton temps et tes objectifs.*
