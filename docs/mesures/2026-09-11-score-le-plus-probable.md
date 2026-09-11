# Mesure : score le plus probable déduit du marché (11/09/2026)

Question : si l'on affiche, pour chaque match, le score le plus probable déduit des cotes 1N2 (Poisson calibré sur le marché), que vaut-il réellement ? Mesuré sur les 1 752 matchs 2025/26 des cinq championnats (cotes de clôture Pinnacle, sinon moyenne, football-data.co.uk), scripts `backend/scripts/mesure_scores.py` et `mesure_scores_v2.py`.

| Variante | Exact touché | Annoncé | Bon vainqueur | λ moyen | log-loss score |
|---|---|---|---|---|---|
| A. λh, λa ajustés sur P(H) et P(A), score libre | 12,0 % | 13,7 % | 48,0 % | 2,46 | 2,890 |
| B. idem, score cohérent avec le favori | 11,2 % | 13,4 % | 53,4 % | 2,46 | 2,890 |
| C. total de buts de la ligue fixé, score libre | 12,6 % | 12,3 % | 44,5 % | 2,76 | 2,885 |
| **D. total de buts fixé, score cohérent avec le favori** | **11,1 %** | **11,4 %** | **53,4 %** | 2,76 | 2,885 |

Favori 1N2 direct : 53,4 % de bons vainqueurs. Buts moyens 2025/26 : SP1 2,69 · F1 2,82 · I1 2,43 · E0 2,75 · D1 3,24.

Décision : **variante D**. Raisons : (1) un score libre est très souvent 1-1 alors que le favori est net, la carte se contredirait et suivre le score ferait perdre 5 points de vainqueurs ; (2) sans total de buts, le Poisson ajusté sur le seul 1N2 sous-estime les buts (2,46 contre 2,8 réels) et affiche 1-0 presque partout ; (3) D est calibrée à 0,3 point près sur la probabilité annoncée du score en tête.

Calibration D (proba annoncée → taux réel) : 9 %→9 % (n 340), 10 %→11 % (409), 11 %→12 % (291), 12 %→12 % (248), 13 %→14 % (132), 14 %→10 % (88), 15 %→9 % (80), 16 %→15 % (65).

Ce que ça ne prouve pas : aucun avantage sur le marché (voir les deux notes du tribunal). C'est une traduction fidèle du marché en score, rien de plus, et c'est ce qui est affiché comme tel.

## Complément (11/09/2026) : total de buts du marché over/under 2,5

Mesuré sur les 901 matchs 2025/26 ayant les cotes O/U 2,5 de clôture (Pinnacle, sinon moyenne) dans les CSV de football-data.co.uk, script `backend/scripts/mesure_totals.py`. λ total = λ tel que P(Poisson(λ) > 2,5) = proba implicite de l'over.

| Total utilisé | Exact touché | Annoncé | Vainqueur | log-loss score | RMSE total |
|---|---|---|---|---|---|
| D. moyenne de la ligue | 10,8 % | 11,7 % | 53,7 % | 2,880 | 1,647 |
| **E. marché O/U 2,5 Pinnacle** | 11,0 % | 11,6 % | 53,7 % | **2,863** | **1,618** |
| F. moyenne des deux | 11,2 % | 11,5 % | 53,7 % | 2,865 | 1,623 |

Décision : **E**, avec repli sur la moyenne de la ligue quand le marché manque. Gain réel mais modeste (−0,017 de log-loss, −0,03 but d'erreur). Coût : 1 crédit The Odds API de plus par compétition et par relevé (marché `totals`, région `eu` = Pinnacle seul), soit 21 crédits par relevé au lieu de 14 → ~23 relevés par mois sur le plan gratuit.
