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
- **Limitation de débit réelle derrière le proxy** : uvicorn `--proxy-headers --forwarded-allow-ips='*'`
  (`Dockerfile`) + limiteur clé sur `X-Forwarded-For` (`core/client_ip.py`) ; `GET /api/v1/whoami` rend
  l'adresse vue. Prouvé à deux adresses (PC bloqué, téléphone 4G connecté), 22/09/2026 — audit C2.
- **Swagger fermé en production** (`create_app()`, 22/09/2026 — audit M1).
- **Conteneur API non-root**, en-têtes de sécurité et `Server` masqué (22/09/2026 — M4, M5).
- Anti brute-force `login` 10/min et `signup` 5/h (par vraie IP depuis le 22/09/2026).
- **C3** · `is_pro` exige un abonnement ACTIVE et une période non échue (3 jours de tolérance) ;
  `retrograder_echus` remet le plan à STARTER chaque jour (`core/access.py`, 22/09/2026).
- **E1** · `/track-record` en cache une heure par compétition (13,9 s → quelques ms au 2e appel, 22/09/2026).
- **E2** · fastapi 0.141.1 / starlette 1.6.0 / python-jose 3.5.0 / requests 2.34.2 ; il ne reste que
  `ecdsa` (dépendance de python-jose sans correctif ; l'application signe en HS256, 22/09/2026).
- **M2** · Content-Security-Policy avec nonce par requête (`frontend/proxy.ts`, `lib/csp.ts`), vérifiée
  dans le navigateur (22/09/2026).
- **M3** · Le cookie de session expire quand le jeton expire (`exp` lu dans le jeton) ; `JWT_EXPIRE_MINUTES`
  recommandé à 10080 (22/09/2026).
- **M6** · `/subscriptions/upgrade` et `/subscriptions/me` retirés (22/09/2026).
- **F1** · Hachage factice au login pour une adresse inconnue (22/09/2026). L'inscription répond toujours
  409 sur une adresse déjà prise : choix assumé (message clair > énumération, limitée par IP).
- **F2** · Toutes les erreurs dans l'enveloppe `{success, message, data}`, 422 et 404 compris (22/09/2026).
- **F3** · `robots.txt` et `sitemap.xml` (22/09/2026).

## Reste à faire (voir l'audit pour la preuve et l'effort)

- **Coolify** · poser des *Watch Paths* (`backend/**` pour l'API, `frontend/**` pour le site) : chaque push,
  même de documentation, redéploie les deux applications et provoque quelques 502 pendant la bascule.
- **Session** · aucune révocation de jeton avant expiration (pas de changement de mot de passe à ce jour).

- **C4** · Mentions légales : « site sans activité commerciale » est faux ; SIREN.
- **E3** · Sauvegardes de la base à planifier dans Coolify.
