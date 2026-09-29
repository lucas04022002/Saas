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

Un premier relevé réel (131 matchs) montre que Pinnacle ne poste la ligne 2,5 que dans 19 cas sur 131 (36 à 2,75, 26 à 3,0, 14 à 2,25, 14 à 3,25, 12 à 3,5, 10 ailleurs) : la formule ci-dessus, limitée aux lignes demies, retombait donc sur le repli de ligue dans ~85 % des cas. Généralisée (11/09/2026) à tout multiple de 0,25 en décomposant une ligne quart en deux demi-mises sur l'entière et la demie voisines (convention Asian handicap), et en résolvant λ par annulation de l'espérance du pari Over à la cote équitable du marché plutôt que par égalité de probabilité — les deux méthodes coïncident sur une ligne demie.

## Complément (29/09/2026) : les totaux hauts sont-ils un biais ? Non.

Soupçon : au relevé du 28/09 08:00 UTC, 10 affiches du 10-11/10 affichaient un total de 3,11 à 4,59 buts, toutes au-dessus des moyennes de ligue (2,43 à 3,24).

1. **Calcul** : `total_goals_from_market` recalculé hors du code (balayage de λ au pas de 1e-4) sur 11 cas — écart ≤ 1e-4 partout (2,5 à 50/50 → 2,674 ; 3,0 → 3,159 ; 2,75 → 2,908 ; cotes inversées → λ du bon côté). Figé dans `tests/test_engine_score.py::test_total_goals_from_market_matches_independent_reference`.
2. **Choix de la ligne** : The Odds API ne renvoie qu'**une** ligne `totals` Pinnacle par match et par relevé (maximum 1 sur les 1 153 relevés en base) : la ligne principale. Pas de ligne alternative possible, et le `min |over − under|` de `latest_totals_snapshot` n'a jamais eu à trancher. Les cotes de ces lignes sont toutes équilibrées (p_over 0,47 à 0,53), signature d'une ligne principale.
3. **Les 10 affiches** sont simplement le haut de la distribution du relevé (140 matchs : 2,75 est la ligne la plus fréquente, 39 fois) : Augsburg-Bayern 4,5 à 1,97/1,85 ; Barcelone-Getafe 4,25 ; PSG-Le Mans 4,0 ; Leipzig-Francfort et Real-Villarreal 3,75 ; Dortmund-Brême et Inter-Parme 3,5 ; Man Utd-Tottenham 3,25 ; Liverpool-City et Troyes-Marseille 3,0.
4. **Calibration** — 56 matchs joués en base avec un relevé O/U avant le coup d'envoi (15-20/09/2026) : λ moyen 3,07 contre 3,05 buts réels (biais +0,02) ; λ ≥ 3,3 (n 14) : 3,77 annoncé, 4,00 marqué. Saison 2025/26 (893 matchs, O/U 2,5 Pinnacle clôture) : calibré par tranche, 3,65 → 3,62 au plus haut. Bayern à l'extérieur en 2025/26 : 4,40 buts par match.
5. **Effet sur le carnet** de l'alternative (constante de ligue au lieu du marché) sur ces 56 matchs : exact 4/56 contre 7/56 avec le marché, vainqueur identique (28/56), log-loss 3,088 contre 2,946, RMSE 1,877 contre 1,652. Rien à corriger.
