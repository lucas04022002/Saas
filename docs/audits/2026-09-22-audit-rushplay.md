# Audit RushPlay — 22 septembre 2026

Périmètre : le site en production (`rushplay.fr`, `api.rushplay.fr`), le dépôt à `0d4a236`.

Méthode : **mesurer d'abord, lire ensuite**. Chaque constat porte sa preuve — une requête
réelle contre la production, ou une ligne de code. Ce qui n'a pas pu être mesuré est marqué
« à vérifier ». Aucune donnée n'a été créée en production (pas de compte de test, pas de
paiement) ; la seule action active a été 12 tentatives de connexion avec un mot de passe faux
sur un compte inexistant, pour mesurer la limitation de débit.

## Verdict en une phrase

Le socle est sain (en-têtes, cookies, CORS, JWT, propriété des données, signature Stripe,
aucun secret dans l'historique) ; **mais le paywall est percé par un champ oublié, la
limitation de débit ne distingue personne derrière le proxy, un abonné résilié peut rester
abonné, et la page publique la plus lourde met 14 secondes.** Quatre corrections d'une
journée, avant toute promotion.

## Ce qui est sain (mesuré)

| Point | Preuve |
|---|---|
| En-têtes du site | HSTS 1 an, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` |
| CORS de l'API | une origine étrangère n'obtient pas `Allow-Origin` ; le preflight est refusé (400) |
| Cookie de session | `httpOnly`, `secure`, `SameSite=Lax`, posé par un Route Handler, garde d'origine (`Sec-Fetch-Site` + `Origin`) |
| JWT | HS256 épinglé (`algorithms=[…]`), `exp` présent, secret validé au démarrage (≥ 16 caractères) |
| Mots de passe | bcrypt, 8 à 128 caractères, rôle non modifiable à l'inscription |
| Carnet | chaque lecture/suppression filtre `Bet.user_id == current_user.id` |
| Paywall (champs) | anonyme : `favourite`, `reference`, `top_score`, `best_gap`, `movement`, `books`, `history`, `score_distribution` tous `null`, en liste comme en détail |
| Erreurs | 404 enveloppés, exceptions inattendues journalisées et masquées (500 générique) |
| Secrets | historique git : seuls des `JWT_SECRET=test-s…` / `change-me` de développement ; aucun `.env` suivi ; `sk_live` absent |
| Dépendances front | `npm audit --omit=dev` : 0 vulnérabilité |
| Conteneur front | `USER node` |
| Limitation de débit | présente : 429 après 10 tentatives de connexion (mais voir C2) |
| Stripe | seul le webhook signé rend un compte payant ; `tax_behavior` et `livemode` exposés et vérifiés |

## Constats, par gravité

### C1 — CRITIQUE · Le paywall est percé par le champ `analysis`

**Mesuré.** Sans compte, `GET /api/v1/matches/4418a708-…` (Lens – Sporting CP, LdC, verrouillé)
rend tous les champs premium à `null`… et, juste à côté :

> `analysis` : « Match serré : **Lens favori de peu à 40 %**. Le marché voit **Lens l'emporter, 2-1 en tête**. Un score exact reste le pari le plus dur : même le plus probable ne dépasse pas 9 %. »

Le favori, sa probabilité et le score exact — **les trois choses qu'on fait payer** — sont
donnés gratuitement dans la phrase d'à côté. Le mode `public` du gabarit
(`engine/narrative.py`, `describe(public=True)`) cache les écarts et le mouvement ; il date
d'avant le paywall à trois niveaux et n'a jamais été aligné dessus. `analysis` n'apparaît dans
aucune des listes de champs verrouillés de `core/access.py`.

**Correctif.** Pour un match verrouillé, le texte ne doit contenir ni le favori, ni sa
probabilité, ni le score : garder la forme et le face-à-face, remplacer le reste par une
phrase neutre (« Ouvrez ce match pour lire le favori et le score le plus probable »). Test
de non-régression : pour tout match verrouillé, `analysis` ne contient ni nom d'équipe
suivi de « favori », ni motif `\d-\d`, ni pourcentage. ~1 h.

À trancher, même famille : `expected_goals` (total de buts attendu, source « marché ») est
visible sans compte. Le rapport de recherche classe le total comme la donnée la plus
exploitable ; c'est une décision produit, pas un bug.

### C2 — CRITIQUE · La limitation de débit compte tout le monde comme une seule personne

**Lu, très probable.** `Dockerfile` : `uvicorn app.main:app --host 0.0.0.0 --port …` sans
`--proxy-headers` ni `--forwarded-allow-ips`. Uvicorn ne fait alors confiance à
`X-Forwarded-For` que depuis `127.0.0.1` ; le proxy Coolify (Traefik) n'y est pas. Résultat :
`request.client.host` — la clé de `slowapi` — vaut l'IP du proxy **pour tous les visiteurs**.

Conséquences : `signup` est limité à **5 inscriptions par heure pour tout le site** (le jour
d'une promotion, la sixième personne est refusée) ; `login` à 10 par minute pour tout le
monde ; et un attaquant n'est jamais distingué d'un client.

**Correctif.** `--proxy-headers --forwarded-allow-ips='*'` dans la commande uvicorn (le
conteneur n'est joignable que par Traefik). ~15 min. **Preuve après déploiement** : je
déclenche 429 depuis ici, Lucas se connecte normalement depuis chez lui.

### C3 — CRITIQUE · Un abonné résilié peut rester abonné

**Lu.** `core/access.py` : `is_pro = user.subscription_plan in PAID_PLANS`. Ni
`Subscription.status` ni `current_period_end` ne sont consultés. Le plan ne repasse à
STARTER **que** si le webhook `customer.subscription.deleted` arrive. Si le secret du webhook
réel n'est pas le bon (non prouvé à ce jour), si l'API est indisponible à ce moment-là, ou
si Stripe cesse de réémettre : l'accès reste ouvert, sans paiement, sans limite.

**Correctif.** `is_pro` exige aussi `status == ACTIVE` et `current_period_end > maintenant`
(avec une tolérance de quelques jours pour les retards de prélèvement), et un passage
quotidien qui rétrograde les périodes échues. ~2 h. Cela couvre aussi le cas inverse
(le webhook réel prouvé par un vrai paiement reste à faire).

### C4 — CRITIQUE (juridique) · Les mentions légales disent « site sans activité commerciale »

**Mesuré.** `rushplay.fr/mentions-legales` : « Éditeur du site : Lucas Guilhot, Personne
physique — site sans activité commerciale ». Le site encaisse 9 € par mois en clés Stripe
réelles depuis le 18 septembre. SIREN absent.

**Correctif.** Texte honnête immédiat (« micro-entreprise en cours d'immatriculation »), puis
le SIREN dès réception. **Aucune promotion avant.** Ce point n'est pas technique.

### E1 — ÉLEVÉ · `/track-record` met 14 secondes et n'est pas borné

**Mesuré.** `GET /api/v1/track-record` : **13,9 s**, 5 357 matchs notés. Le code recharge
tous les matchs terminés avec tous leurs relevés et recalcule la grille de Poisson de chacun
**à chaque requête**. Public, sans authentification : dix requêtes simultanées suffisent à
saturer l'API. Et le temps croît avec chaque championnat ajouté (16 aujourd'hui).

**Correctif.** Résultat mis en cache par compétition avec une durée de vie d'une heure
(les résultats n'arrivent qu'une fois par jour), ou précalculé par le cron après les
collecteurs. ~2 h.

### E2 — ÉLEVÉ · Dépendances Python vulnérables

**Mesuré** (`pip-audit`) : 25 avis sur 5 paquets. Les trois qui comptent :

| Paquet | Version | Avis | Corrigé en |
|---|---|---|---|
| `python-jose` (la bibliothèque JWT) | 3.3.0 | PYSEC-2024-232, -233 | 3.4.0 |
| `starlette` (sous FastAPI) | 0.38.6 | 8 avis, dont DoS sur les formulaires | ≥ 0.47.2 |
| `requests` | 2.32.5 | PYSEC-2026-2275 | 2.33.0 |

**Correctif.** Monter `fastapi` (entraîne starlette), `python-jose` → 3.4.0 (ou remplacer
par PyJWT), `requests` → 2.33. Relancer les 222 tests. ~1 h.

### E3 — ÉLEVÉ · Aucune sauvegarde de la base

**Lu.** `deploy/coolify.md` ne mentionne `pg_dump` que pour la migration initiale. Rien de
planifié. Si le VPS meurt : comptes, abonnements, carnets et deux saisons de relevés
disparaissent. **À vérifier dans Coolify** (la base Postgres a un onglet *Backups* :
planification + destination S3 ou locale). Rien à coder ; à activer par Lucas.

### M1 — MOYEN · Swagger exposé en production

**Mesuré.** `api.rushplay.fr/docs` → 200, `/openapi.json` → 200. Toute la surface est
documentée pour qui veut l'attaquer, webhook compris. **Correctif** : `docs_url=None,
openapi_url=None` quand `ENV=production`. 10 min.

### M2 — MOYEN · Pas de Content-Security-Policy sur le site

**Mesuré.** Aucun en-tête CSP. Le jeton est en cookie `httpOnly`, ce qui limite l'enjeu
d'un XSS, mais un script injecté pourrait toujours appeler les Route Handlers au nom de
l'utilisateur. **Correctif** : CSP avec nonce via un middleware Next.js. ~2 h.

### M3 — MOYEN · Cookie de 7 jours, jeton d'une heure

**Lu.** Le cookie `rp_token` vit 7 jours (`maxAge`), le JWT expire après
`JWT_EXPIRE_MINUTES` (60 par défaut). Passé une heure, chaque page voit un 401, `getUser()`
rend `null`, et l'utilisateur se retrouve « Se connecter » sans avoir rien fait — le cookie,
lui, est toujours là. **À vérifier** : la valeur réelle de `JWT_EXPIRE_MINUTES` dans
Coolify. **Correctif** : aligner (jeton 7 jours + révocation au changement de mot de passe,
comme sur Le Local), ou renouveler le jeton côté Route Handler. ~2 h.

### M4 — MOYEN · Le conteneur API tourne en root

**Lu.** `Dockerfile` sans `USER`. Le front, lui, tourne en `node`. **Correctif** : un
utilisateur non privilégié. 15 min.

### M5 — MOYEN · L'API n'envoie aucun en-tête de sécurité

**Mesuré.** `api.rushplay.fr` : seulement `Server: uvicorn`. Pas de HSTS sur ce
sous-domaine, pas de `nosniff`. **Correctif** : un middleware d'en-têtes ; masquer `Server`.
15 min.

### M6 — MOYEN · Routes héritées `/subscriptions/*`

**Lu.** `/subscriptions/upgrade` (réservé ADMIN) attribue un plan payant **sans Stripe**,
pour 30 jours ; `/subscriptions/me` fait doublon avec `/billing/abonnement`. Un compte
admin compromis vend des abonnements gratuits. **Correctif** : supprimer `upgrade` (ou le
journaliser et l'assortir d'un motif), garder un seul endpoint d'état. 30 min.

### F1 — FAIBLE · Énumération d'adresses

`signup` répond 409 « Email already exists » ; `login` n'exécute pas de hachage factice
quand l'adresse est inconnue (temps de réponse différent). Tolérable une fois C2 corrigé
(la limitation redevient réelle). 30 min.

### F2 — FAIBLE · Erreurs 422 hors enveloppe

`/matches?competition=ZZ` rend la forme brute de FastAPI (avec l'expression régulière
complète), pas `{success, message, data}`. 30 min.

### F3 — FAIBLE · `robots.txt` et `sitemap.xml` absents (404)

Aucun effet de sécurité ; un effet SEO le jour où le site doit être trouvé. 20 min.

### F4 — FAIBLE · `docs/SECURITY_TODO.md` périmé

Il annonce encore « Stripe à intégrer » et « jeton en localStorage », tous deux réglés.
Un document de sécurité faux est pire qu'absent. 10 min.

## Ordre proposé

**Jour 1 — un déploiement, ~2 h de code** : C1 (`analysis`), C2 (`--proxy-headers`), M1
(Swagger), M4 (root), M5 (en-têtes API). Chaque point est petit ; ensemble ils ferment ce
qui est ouvert aujourd'hui.

**Jour 2 — ~5 h** : C3 (expiration d'abonnement), E1 (cache du track record), E2
(dépendances).

**Ensuite** : M2 (CSP), M3 (session), M6, F1–F4.

**Lucas, sans code** : C4 (mentions légales, puis SIREN), E3 (sauvegardes dans Coolify),
la valeur de `JWT_EXPIRE_MINUTES`, et le webhook réel prouvé par un vrai paiement.

## Ce que cet audit ne couvre pas

- Le front n'a pas été passé au crible XSS composant par composant. Next.js échappe par
  défaut, et **aucun `dangerouslySetInnerHTML`** n'existe dans `app/`, `components/`, `lib/` (mesuré : 1 occurrence).
- Pas de test de charge au-delà des mesures ponctuelles ci-dessus.
- Pas de revue des collecteurs sous l'angle « données empoisonnées » (un CSV de
  football-data.co.uk malformé) : les parseurs ignorent les lignes invalides, sans plus.
- La conformité RGPD (registre, durée de conservation, droit d'accès) n'a pas été examinée.
