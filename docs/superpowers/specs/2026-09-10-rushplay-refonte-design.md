# RushPlay — refonte : lecture du marché, sans ML

Date : 2026-09-10. Validé par Lucas en discussion (design en 5 blocs).

## 1. Pourquoi cette refonte

Le tribunal du 10/09/2026 (notes du vault « RushPlay — tribunal du modèle »,
manches 1 et 2) a établi que le modèle Elo + Poisson + XGBoost **ne bat pas le
bookmaker** hors échantillon (2025/26, 1 752 matchs : log-loss 1,004 contre
0,978, ROI −5,6 % [−10,4 ; −0,9]) et le dégrade même quand il reçoit les cotes
en entrée. Il n'anticipe pas non plus le mouvement des cotes (CLV −0,51 %).
Par ailleurs les API de données payantes (API-Football, The Odds API payant)
ne sont plus financées.

Décision : RushPlay ne vend plus une prédiction. Il vend **la lecture du
marché** : le favori et sa probabilité réelle, les écarts entre bookmakers
français et une référence, les mouvements de cotes, un carnet de bankroll, et
une analyse textuelle produite par un script déterministe. Aucun LLM, aucun ML.

## 2. Promesse et conformité

- Phrase de positionnement : « Nous ne prédisons pas. Nous vous montrons ce que
  le marché pense, et où il se contredit. »
- Vocabulaire : « favori », « probabilité », « écart », « mouvement ». Le mot
  « value bet » et toute notion de « prédiction RushPlay » disparaissent du
  code, des textes et du marketing. Aucun ROI en vitrine.
- Conformité ANJ (France) : bandeau « Les paris sportifs comportent des
  risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non
  surtaxé) » sur chaque page publique ; case « j'ai 18 ans ou plus » obligatoire
  à l'inscription (date de naissance stockée) ; pas de lien d'affiliation vers
  les bookmakers dans la V1 (pour ne pas tomber sous le régime des
  influenceurs/pronostiqueurs commerciaux) ; mentions légales et CGU citant
  que le service est informatif.

## 3. Données (trois collecteurs, zéro coût)

| Source | Contenu | Cadence | Quota |
|---|---|---|---|
| The Odds API, régions `fr` + `eu` | cotes 1N2 de Betclic, Winamax, Unibet FR, PMU, NetBet, et Pinnacle en référence | 1 relevé/jour à 08:00 + 1 relevé les jours de match à H−2 des coups d'envoi (borné à 2/jour) | 500 crédits/mois ; 6 compétitions × 2 régions = 12 crédits par relevé → ≈ 40 relevés/mois |
| football-data.co.uk | résultats, tirs, corners, cotes d'ouverture et de clôture (historique depuis 2019 déjà téléchargé) | 1 fois/semaine (lundi) | illimité |
| football-data.org (plan gratuit) | calendrier, journées, classements, Ligue des Champions | 1 fois/jour | 10 appels/min |

Compétitions V1 : Premier League, Ligue 1, Liga, Bundesliga, Serie A, Ligue
des Champions (calendrier et cotes seulement pour la LdC, pas d'historique
football-data.co.uk).

**Chaque relevé de cotes est archivé tel quel** (table `odds_snapshots` :
match, bookmaker, horodatage, cote domicile/nul/extérieur). C'est l'archive
qui rend les mouvements et le track record possibles. Rien n'est écrasé.

Appariement des noms d'équipes entre sources : table de correspondance
`team_aliases` (source, nom source → équipe canonique), remplie au démarrage
pour les 98 équipes des 5 championnats, complétée manuellement pour la LdC ;
un nom inconnu lève une alerte dans les logs et le match est mis en attente,
jamais deviné.

## 4. Le moteur : un script, pas un modèle

Module `engine/` pur Python, sans dépendance externe, testé unitairement.

- **Probabilités implicites** : pour chaque bookmaker, `q_k = (1/cote_k) /
  Σ(1/cote_j)` (marge retirée par normalisation proportionnelle). Marge
  affichée : `Σ(1/cote_j) − 1`.
- **Référence** : Pinnacle si présent dans le relevé, sinon la moyenne des
  probabilités implicites de tous les bookmakers du relevé. La source de la
  référence est affichée.
- **Favori** : issue de probabilité de référence maximale. « Indice » = cette
  probabilité, en %, jamais renommé « confiance ».
- **Écart** : pour chaque bookmaker français et chaque issue, `cote_book ×
  q_ref − 1` en % (positif = le bookmaker paie plus que ce que la référence
  implique). Affiché brut, avec la marge du bookmaker à côté. Seuil de mise en
  avant : écart ≥ 3 % (paramètre).
- **Mouvement** : probabilité de référence au premier relevé vs au dernier,
  en points ; courbe des relevés.
- **Contexte** : forme sur 5 (V/N/D), buts pour/contre sur 5, face-à-face sur
  5 dernières rencontres, depuis football-data.co.uk. Descriptif, pas
  prédictif.
- **Texte** : gabarits en français remplis avec ces chiffres, 3 à 4 phrases,
  variantes choisies par règles (favori net > 60 %, match serré < 45 %,
  mouvement > 3 pts, écart > 3 %, forme). Exemple : « Lyon favori à 58 %. La
  cote a glissé de 1,80 à 1,72 depuis mardi. Betclic reste au-dessus du marché
  à 1,78. Trois victoires sur les cinq derniers. » Le générateur est une
  fonction pure `(match_context) → str`, testée sur des cas fixés.

Sortent du code : `prediction_engine.py`, `train_xgboost.py`, `backtesting.py`,
`draw_policy.py`, les fichiers modèle et les backtests JSON, les tables
`analysis` (prédictions) et `warning_point` si elles ne servent qu'au ML.

## 5. Écrans (front refait, Next.js)

1. **Accueil public** : promesse, aperçu de 3 matchs du jour, bandeau ANJ.
2. **Matchs du jour / à venir** : par compétition ; ligne = équipes, heure,
   favori et sa probabilité, meilleur écart du jour (bookmaker + %), badge
   « a bougé » si mouvement ≥ 3 pts.
3. **Page match** : les trois probabilités de référence ; tableau des 5
   bookmakers français avec cote, marge, écart ; courbe des relevés ; forme et
   face-à-face ; analyse textuelle ; bouton « noter ce pari » vers le carnet.
4. **Comparateur** : par bookmaker, sur les matchs à venir, où il paie le plus
   et le moins que la référence, marge moyenne.
5. **Carnet de bankroll** : le client saisit ses paris (match, issue,
   bookmaker, cote, mise) ; règlement automatique au résultat ; bilan réel
   (mises, gains, ROI, par bookmaker, par compétition). Pas de conseil de mise.
6. **Historique / track record public** : pour chaque match passé, ce que la
   référence disait (favori, %) et le résultat ; taux de réussite du favori
   par compétition, sans maquillage, avec la phrase « le favori gagne environ
   une fois sur deux : c'est le marché, pas nous ».
7. **Compte / abonnement** : existant, conservé ; gratuit = matchs du jour et
   favori ; payant = écarts, mouvements, comparateur, carnet.

## 6. Architecture et ce qu'on garde

- **Backend FastAPI** conservé : auth JWT/bcrypt, users, subscriptions,
  favorites, structure des routes `/api/v1`. Nouvelles routes : `matches`
  (à venir, du jour), `match/{id}` (détail complet), `books` (comparateur),
  `bankroll` (CRUD paris + bilan), `track-record`.
- **Postgres** sur le VPS (migration depuis Supabase = `pg_dump`/`psql` + une
  URL ; voir la note du vault « Serveur Mac mini — comment on fait »).
  Nouvelles tables : `competitions`, `teams`, `team_aliases`, `fixtures`,
  `odds_snapshots`, `results`, `bets` (carnet). Alembic pour tout.
- **Collecteurs** : 3 scripts `collectors/` lancés par cron sur le VPS,
  idempotents (relancer un relevé ne duplique rien : clé unique match +
  bookmaker + horodatage arrondi), journalisés, avec un heartbeat par
  collecteur consultable sur `/health`.
- **Front Next.js** refait à partir d'une page blanche (le template Launch UI
  actuel est abandonné), appels uniquement vers l'API, aucun accès direct à la
  base.
- **Déploiement** : VPS Hetzner + Coolify, un service par composant (api,
  front, postgres), crons dans Coolify ; les GitHub Actions keep-alive et
  daily-analysis sont supprimées.

## 7. Gestion des erreurs et cas limites

- Relevé de cotes incomplet (bookmaker absent) : on affiche ce qu'on a, la
  référence bascule sur la moyenne si Pinnacle manque, et la page le dit.
- Quota The Odds API atteint : le collecteur s'arrête proprement, le dernier
  relevé reste affiché avec son horodatage (« cotes relevées il y a 9 h »).
- Match reporté/annulé : détecté par football-data.org, marqué, sorti des
  listes, paris du carnet laissés « en attente » puis annulables par le client.
- Nom d'équipe inconnu : match en quarantaine, alerte log, jamais affiché
  avec un nom deviné.
- Résultat manquant après 48 h : le pari reste « en attente », un rappel de
  collecte est planifié.

## 8. Tests

- Moteur : tests unitaires sur les probabilités implicites (somme = 1, marge
  connue), les écarts (cas positif, nul, négatif), le favori, le mouvement,
  et le générateur de texte (10 contextes fixés → texte attendu).
- Collecteurs : tests sur des réponses enregistrées (fixtures JSON) pour le
  parsing, l'idempotence et l'appariement des noms ; un test « nom inconnu →
  quarantaine ».
- API : tests d'intégration sur Postgres de test pour chaque route, dont le
  règlement automatique du carnet et le paywall.
- Front : build sans erreur, parcours vérifié en navigateur sur les 7 écrans.

## 9. Hors périmètre V1

LLM, live/in-play, autres sports, application mobile, affiliation bookmakers,
alertes push/e-mail, ParionsSport/Zebet/Bwin (non couverts par la source
gratuite).

## 10. Ordre de construction (résumé, détaillé dans le plan)

1. Base et modèles (tables, Alembic, aliases), migration Supabase → Postgres.
2. Collecteurs football-data.co.uk puis football-data.org puis The Odds API,
   avec archive de relevés.
3. Moteur `engine/` et générateur de texte, testés.
4. Routes API.
5. Front, écran par écran.
6. Déploiement VPS, crons, suppression des béquilles Render/GitHub Actions.
