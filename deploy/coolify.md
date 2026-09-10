# Déploiement RushPlay — Hetzner + Coolify

Procédure pour mettre le backend en production sur un VPS, sans coller la
moindre clé dans le chat : chaque secret est saisi par Lucas directement dans
l'interface Coolify.

1. **VPS** : Hetzner CX22 (Ubuntu 24.04). Installer Coolify avec le script
   officiel (`curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash`).

2. **Base de données** : créer une ressource Postgres 16 dans Coolify et noter
   l'URL de connexion qu'elle fournit.

3. **Migration depuis Supabase** : exporter les données existantes avec
   `pg_dump --no-owner --no-privileges "$SUPABASE_URL" > rushplay.sql` puis les
   importer avec `psql "$VPS_URL" < rushplay.sql`. Seules les tables
   `users`, `subscriptions`, `favorites` et `matches` doivent être reprises ;
   `analyses`, `team_stats` et `warning_points` seront supprimées par la
   migration `0005` au premier déploiement.

4. **Application Docker** : créer une application Coolify de type Docker
   pointant sur le dépôt GitHub, branche `refonte-marche`. Renseigner les
   variables d'environnement (saisies par Lucas dans Coolify, jamais dans le
   chat) : `DATABASE_URL=postgresql+psycopg://…`, `JWT_SECRET`, `CRON_SECRET`,
   `CORS_ORIGINS`, `THE_ODDS_API_KEY`, `FOOTBALL_DATA_ORG_KEY`,
   `ENV=production`.

5. **Premier déploiement** : au démarrage du conteneur, `alembic upgrade head`
   s'exécute avant `uvicorn` (voir `Dockerfile`) — le schéma est mis à jour
   automatiquement.

6. **Amorçage des collecteurs** : depuis le terminal Coolify du service,
   lancer à la main dans l'ordre `python -m app.collectors.run seed`, puis
   `python -m app.collectors.run fd_uk --seasons 2324 2425 2526`, puis
   `python -m app.collectors.run fd_org`, puis
   `python -m app.collectors.run odds`. Vérifier ensuite `/health` : les trois
   collecteurs doivent apparaître avec un horodatage récent et `stale: false`.

7. **Crons** : coller le contenu de `deploy/crontab.txt` dans les
   « Scheduled Tasks » de Coolify, sur le service `api`.

8. **Domaine et HTTPS** : à configurer dans Coolify une fois le nom de
   domaine choisi (certificat Let's Encrypt automatique).
