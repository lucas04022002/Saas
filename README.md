# RushPlay

RushPlay lit le marché des paris sportifs pour le montrer clairement : le
favori et sa probabilité réelle une fois la marge du bookmaker retirée, les
écarts entre les bookmakers français et une référence, les mouvements de
cotes, et un carnet de bankroll pour suivre ses propres paris. « Nous ne
prédisons pas. Nous vous montrons ce que le marché pense, et où il se
contredit. »

RushPlay n'est pas un outil de prédiction. Il ne calcule aucune probabilité
de victoire propre, ne recommande aucun pari et n'affiche aucun « value bet » :
tout ce qui est montré est une lecture des cotes publiées par les
bookmakers, pas une opinion sur le résultat du match. Conformément à la
réglementation ANJ, un bandeau de prévention (numéro d'aide : 09 74 75 13 13)
apparaît sur chaque page publique et l'inscription exige d'avoir 18 ans ou
plus.

Le détail de la refonte (données, moteur, écrans, ce qui a été retiré) est
dans [`docs/superpowers/specs/2026-09-10-rushplay-refonte-design.md`](docs/superpowers/specs/2026-09-10-rushplay-refonte-design.md).
La procédure de déploiement du backend sur un VPS via Coolify est dans
[`deploy/coolify.md`](deploy/coolify.md). En production, RushPlay tourne sur un
VPS OVH : front, API et PostgreSQL, plus cinq tâches planifiées pour la collecte.

## Lancer en local

Une seule commande, à la racine du dépôt :

```
npm run dev
```

Elle démarre l'API (FastAPI, port 8000, sur la base de démonstration `dev.db`)
et le front (Next.js, port 3000) dans la même console, et les arrête ensemble
au `Ctrl+C`.

Deux détails qui font gagner du temps :

- si un des deux ports est déjà occupé, le script nomme le processus coupable
  au lieu de laisser chercher ;
- l'arrêt descend tout l'arbre des processus, sans quoi le port 3000 reste
  tenu après un `Ctrl+C` sous Windows.

Les ports se changent par `PORT_API` et `PORT_WEB`.
