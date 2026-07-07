# Sécurité — corrigé & reste à faire

Suivi des points de l'audit du 2026-07-07.

## ✅ Corrigé dans ce commit

- **Paywall côté serveur** : `/matches`, `/matches/{id}`, `/signal/{id}`,
  `/analyses`, `/analyses/{id}` appliquent désormais le plan de l'utilisateur.
  Les champs premium sont masqués (`null`) pour les non-abonnés et
  `/signal` renvoie `403` hors Pro/Elite. Logique partagée dans
  `backend/app/core/access.py`.
- **Faille revenus** : `POST /subscriptions/upgrade` est réservé aux admins.
  Un utilisateur ne peut plus se passer ELITE gratuitement.
- **Anti brute-force** : `login` (10/min) et `signup` (5/h) sont rate-limités.
- **Fuite d'infos** : le cron ne renvoie plus le détail des exceptions au client.
- **Startup** : `on_event` déprécié remplacé par un `lifespan`.
- **Cookie** : flag `Secure` ajouté en HTTPS.

## ⚠️ Reste à faire (nécessite une décision / infra)

### 1. Paiement Stripe (bloquant pour vendre)
`/subscriptions/upgrade` est admin-only en attendant. Pour ouvrir la vente :
- Intégrer Stripe Checkout côté frontend.
- Endpoint webhook backend vérifiant la signature Stripe
  (`checkout.session.completed`) → c'est LUI qui passe l'utilisateur en PRO/ELITE.
- Ne jamais faire confiance au client pour attribuer un plan payant.

### 2. Token JWT en `localStorage` (risque XSS)
Le token est lisible en JS (localStorage + cookie non-HttpOnly) car le fetch
client en a besoin. Pour un vrai cookie `HttpOnly` :
- Backend et frontend étant sur des domaines différents (Render/Vercel), il faut
  un **proxy via des Route Handlers Next.js** (`app/api/.../route.ts`) qui posent
  le cookie `HttpOnly; Secure; SameSite`.
- Migrer les fetch client pour passer par ce proxy plutôt que d'ajouter le
  header `Authorization` depuis le JS.

### 3. Révocation / expiration de session
Le logout est purement client ; un token volé reste valide `JWT_EXPIRE_MINUTES`.
Options : liste de révocation (jti + Redis) ou rotation de refresh tokens.

### 4. Gestion du schéma DB
Trois mécanismes coexistent : `Base.metadata.create_all`, Alembic, et
`ensure_runtime_columns` (ALTER TABLE manuel). À unifier sur Alembic seul.

### 5. Ménage du dépôt
- Algo dupliqué : scripts Python à la racine vs `backend/app/providers/` — deux
  sources de vérité pour le modèle.
- Gros artefacts committés (`fixture_stats_cache.json` ~2.4 Mo, `xgboost_model.json`,
  30 `backtest_*.json`, `elo_ratings.json` en double) → sortir de Git (LFS / bucket).
- `.env` local contient les vrais secrets : bien vérifier qu'il reste gitignoré
  (c'est le cas) et **faire tourner les secrets** s'ils ont déjà transité ailleurs.
