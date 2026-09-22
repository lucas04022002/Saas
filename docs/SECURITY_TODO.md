# Sécurité — état et reste à faire

Le suivi détaillé, avec les preuves, est dans `docs/audits/2026-09-22-audit-rushplay.md`.
Ce fichier n'est qu'un index : un document de sécurité faux est pire qu'absent, il est donc
tenu à jour à chaque correctif.

## Réglé

- **Paiement** : Stripe Checkout + portail + webhook signé ; seul le webhook rend un compte
  payant (`backend/app/api/v1/endpoints/billing.py`, 18/09/2026).
- **Jeton en cookie `httpOnly`** posé par un Route Handler Next.js, garde d'origine ;
  le JS client ne voit jamais le jeton (`frontend/app/api/session/route.ts`, 11/09/2026).
- **Paywall côté serveur**, y compris le texte d'analyse d'un match verrouillé
  (`backend/app/core/access.py`, `engine/narrative.py`, 22/09/2026 — audit C1).
- **Limitation de débit réelle derrière le proxy** : uvicorn `--proxy-headers
  --forwarded-allow-ips='*'` (`Dockerfile`, 22/09/2026 — audit C2).
- **Swagger fermé en production** (`create_app()`, 22/09/2026 — audit M1).
- **Conteneur API non-root**, en-têtes de sécurité et `Server` masqué (22/09/2026 — M4, M5).
- Anti brute-force `login` 10/min et `signup` 5/h (par vraie IP depuis le 22/09/2026).

## Reste à faire (voir l'audit pour la preuve et l'effort)

- **C3** · `is_pro` doit exiger un abonnement actif et une période non échue.
- **C4** · Mentions légales : « site sans activité commerciale » est faux ; SIREN.
- **E1** · `/track-record` : cache ou précalcul (13,9 s, public, non borné).
- **E2** · `python-jose`, `starlette`, `requests` à monter (`pip-audit`).
- **E3** · Sauvegardes de la base à planifier dans Coolify.
- **M2** · Content-Security-Policy avec nonce (un seul script inline : le thème).
- **M3** · Cookie 7 jours vs jeton `JWT_EXPIRE_MINUTES` ; révocation à changer de mot de passe.
- **M6** · Retirer `/subscriptions/upgrade` (attribue un plan sans Stripe).
- **F1–F3** · Énumération d'adresses, 422 hors enveloppe, `robots.txt` / `sitemap.xml`.
