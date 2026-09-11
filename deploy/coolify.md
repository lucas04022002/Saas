# Déploiement RushPlay — Hetzner + Coolify

Procédure pour mettre le backend en production sur un VPS, sans coller la
moindre clé dans le chat : chaque secret est saisi par Lucas directement dans
l'interface Coolify.

1. **VPS** : Hetzner CX22 (Ubuntu 24.04). Installer Coolify avec le script
   officiel (`curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash`).

2. **Base de données** : créer une ressource Postgres 16 dans Coolify et noter
   l'URL de connexion qu'elle fournit.

3. **Migration depuis Supabase** (facultatif, seulement si les anciens comptes
   doivent être conservés ; sinon partir d'une base vide) : exporter les données existantes avec
   `pg_dump --no-owner --no-privileges "$SUPABASE_URL" > rushplay.sql` puis les
   importer avec `psql "$VPS_URL" < rushplay.sql`. Seules les tables
   `users`, `subscriptions`, `favorites` et `matches` doivent être reprises ;
   `analyses`, `team_stats` et `warning_points` seront supprimées par la
   migration `0005` au premier déploiement.

4. **Application Docker** : créer une application Coolify de type Docker
   pointant sur le dépôt GitHub `lucas04022002/Saas`, branche `master`. Renseigner les
   variables d'environnement (saisies par Lucas dans Coolify, jamais dans le
   chat) : `DATABASE_URL=postgresql+psycopg://…`, `JWT_SECRET`, `CRON_SECRET`,
   `CORS_ORIGINS`, `THE_ODDS_API_KEY`, `FOOTBALL_DATA_ORG_KEY`,
   `ENV=production`.

5. **Premier déploiement** : contexte de build = racine du dépôt, avec le
   `Dockerfile` à la racine (unique Dockerfile du projet ; il copie
   `backend/requirements.txt` puis `backend/`). Au démarrage du conteneur,
   `alembic upgrade head` s'exécute avant `uvicorn` (voir ce `Dockerfile`) —
   le schéma est mis à jour automatiquement.

6. **Amorçage des collecteurs** : depuis le terminal Coolify du service,
   lancer à la main dans l'ordre `python -m app.collectors.run seed`, puis
   `python -m app.collectors.run fd_uk --seasons 2324 2425 2526`, puis
   `python -m app.collectors.run fd_org`, puis
   `python -m app.collectors.run fixtures`, puis
   `python -m app.collectors.run odds` (21 crédits), puis
   `python -m app.collectors.run dedup`. Vérifier ensuite `/health` : les
   collecteurs doivent apparaître avec un horodatage récent et `stale: false`,
   et `python -m app.collectors.run quarantine` doit répondre « Aucun match en
   quarantaine » (sinon ajouter les alias manquants dans `KNOWN_TEAMS`).

7. **Crons** : coller le contenu de `deploy/crontab.txt` dans les
   « Scheduled Tasks » de Coolify, sur le service `api`.

8. **Domaine et HTTPS** : à configurer dans Coolify une fois le nom de
   domaine choisi (certificat Let's Encrypt automatique).

9. **Frontend** : créer un second service Coolify de type Docker, à côté de
   `api`, pointant sur le même dépôt GitHub mais avec le contexte de build
   `frontend/` et son `Dockerfile` (`frontend/Dockerfile`, build standalone
   Next.js). Renseigner l'argument de build
   `NEXT_PUBLIC_API_URL=https://<domaine de l'API>` (saisi dans Coolify, pas
   dans le chat) puis pointer le domaine du site sur ce service `front`.

10. **Avant d'ouvrir au public** : remplir l'identité de l'éditeur dans
    `frontend/lib/legal.ts` (mentions légales et CGU), activer la vérification
    stricte `CI_STRICT_LEGAL=1` dans la CI, remplacer les photos Unsplash
    (`frontend/PHOTOS.md`), et régler `CORS_ORIGINS` sur le domaine du front.

## Ce que fait Claude et ce que fait Lucas

- Lucas : compte Hetzner (paiement), création du VPS avec la clé SSH publique
  fournie par Claude, achat du domaine, saisie des secrets dans Coolify
  (`JWT_SECRET`, `CRON_SECRET`, clés API), remplissage de `lib/legal.ts`.
- Claude, par SSH avec sa clé : installation de Coolify, création des
  ressources (Postgres, api, front), crons, domaine, vérification de `/health`,
  amorçage des collecteurs.
