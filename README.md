# RushPlay

**SaaS d'analyse du marché des paris sportifs.** Le favori et sa probabilité réelle
une fois la marge du bookmaker retirée, les écarts entre bookmakers, le mouvement des
cotes, et un carnet de bankroll.

[**Voir le produit en ligne →**](https://rushplay.fr) · [Étude de cas complète](https://lucasguilhot.fr/projets/rushplay) · [Portfolio](https://lucasguilhot.fr)

`Next.js` `TypeScript` `FastAPI` `Python` `PostgreSQL` `Docker`

<img src="https://raw.githubusercontent.com/lucas04022002/Saas/master/assets/apercu-rushplay.jpg" alt="Page d'accueil de RushPlay : le favori du jour et sa probabilité réelle." width="100%">

---

## Pourquoi ce projet existe

Les cotes d'un bookmaker contiennent une information utile — ce que le marché pense
vraiment d'un match — mais elle est illisible : trois nombres qui bougent toute la
journée, chez une dizaine d'opérateurs, et dont la somme des probabilités dépasse
100 % parce que la marge du bookmaker y est incluse.

RushPlay retire cette marge, compare les opérateurs entre eux, et montre le résultat
en une phrase compréhensible en trois secondes.

**Ce que le produit ne fait pas, volontairement :** il ne prédit rien. Aucune
probabilité propre, aucune recommandation de pari, aucun « value bet ». Tout ce qui
est affiché est une lecture des cotes publiées, pas une opinion sur l'issue du match.
Conformément à la réglementation ANJ, un bandeau de prévention (09 74 75 13 13)
apparaît sur chaque page publique et l'inscription exige d'avoir 18 ans ou plus.

## La décision qui compte

J'ai d'abord construit un modèle de prédiction — Elo, Poisson, XGBoost sur sept
saisons.

Le premier backtest annonçait **+7,3 % de rendement**. En le relisant, le protocole
contenait une fuite de données : le découpage entraînement/test était concaténé par
ligue, si bien que tout se retrouvait dans l'échantillon d'entraînement.

Rejoué proprement sur la saison 2025/26 — 1 752 matchs jamais vus :

| | Modèle | Bookmaker |
| --- | --- | --- |
| Log-loss | 1,004 | **0,978** |
| Rendement | **−5,6 %** | — |

Le modèle faisait moins bien que le marché qu'il prétendait battre. Ajouter les cotes
en variables d'entrée le rendait simplement moins bon que les cotes seules.

**Je l'ai retiré du produit.** Ce que RushPlay montre aujourd'hui est une lecture du
marché, pas une prédiction — et c'est la seule promesse que les mesures soutiennent.

## Architecture

| Couche | Rôle |
| --- | --- |
| **Collecte** | 6 sources de cotes relevées plusieurs fois par jour, avec reprise après panne et déduplication par identité de match |
| **Normalisation** | Alias d'équipes, fuseaux horaires, lignes quart pour les marchés over/under |
| **Moteur** | Retrait de la marge, probabilités implicites, score le plus probable déduit du marché |
| **API** | FastAPI, authentification par session, contrôle de rôle |
| **Interface** | Next.js, rendu statique là où c'est possible |

Chaque couche est remplaçable sans toucher aux autres — c'est ce qui a permis de
retirer le modèle de prédiction sans réécrire le produit.

## Chiffres

- **267 tests automatisés** — 174 côté Python, 93 côté front, joués à chaque envoi
- **6 sources de cotes**, relevées plusieurs fois par jour
- **1 752 matchs** de validation hors échantillon
- **100/100** en accessibilité Lighthouse, mesuré en thème clair et en thème sombre

## Lancer en local

Une seule commande, à la racine du dépôt :

```bash
npm run dev
```

Elle démarre l'API (FastAPI, port 8000, sur la base de démonstration `dev.db`) et le
front (Next.js, port 3000) dans la même console, et les arrête ensemble au `Ctrl+C`.

Deux détails qui font gagner du temps :

- si un des deux ports est déjà occupé, le script **nomme le processus** qui le tient
  au lieu de laisser chercher ;
- l'arrêt descend **tout l'arbre** des processus, sans quoi le port 3000 reste occupé
  après un `Ctrl+C` sous Windows.

Les ports se changent par `PORT_API` et `PORT_WEB`.

## Déploiement

En production, RushPlay tourne sur un VPS OVH : front, API et PostgreSQL, plus cinq
tâches planifiées pour la collecte. La procédure est dans
[`deploy/coolify.md`](deploy/coolify.md).

## Documentation

Le détail de la refonte — données, moteur, écrans, et ce qui a été retiré — est dans
[`docs/superpowers/specs/2026-09-10-rushplay-refonte-design.md`](docs/superpowers/specs/2026-09-10-rushplay-refonte-design.md).

## Ce que j'en retiens

Un backtest qui donne un bon résultat du premier coup est d'abord un backtest à
relire. La fuite de données ne se voyait pas dans le code : elle se voyait dans le
fait que le résultat était trop beau.

Et tester sur SQLite en mémoire ne remplace pas tester sur la base de production : une
migration passait en test et échouait sur PostgreSQL, faute d'un `CREATE TYPE` unique.
La CI joue maintenant les migrations sur un vrai PostgreSQL.
