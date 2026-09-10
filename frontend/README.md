# RushPlay — frontend

Application Next.js (App Router, React 19) qui affiche le favori de chaque
match d'après le marché des cotes : lecture publique du favori, écarts entre
bookmakers, mouvement des cotes et carnet de paris pour les abonnés. Aucune
prédiction, aucun conseil de mise — uniquement de la lecture de marché.

## Lancement

```bash
npm install
cp .env.example .env.local   # puis ajuster NEXT_PUBLIC_API_URL
npm run dev
```

Le serveur de dev démarre sur `http://localhost:3000` et s'attend à trouver
l'API RushPlay (backend FastAPI) à l'URL donnée par `NEXT_PUBLIC_API_URL`
(`http://localhost:8000` en local — voir `backend/README` pour le lancer).

### Variables d'environnement

| Variable | Rôle | Exemple |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | URL de base de l'API RushPlay, exposée au client | `http://localhost:8000` |

## Tests

```bash
npm test          # Vitest, une passe
npm run test:watch
```

Les tests rendent les pages serveur (`app/**/page.tsx`) directement en
composants async, avec MSW (`tests/msw/`) pour intercepter les appels à
l'API. `tests/a11y.test.tsx` vérifie, sur les pages publiques rendues avec
des données vides, qu'il y a exactement un `h1`, que chaque `img` porte un
`alt`, que chaque `table` a des `th`, et que le bandeau ANJ (« 09 74 75 13
13 ») est présent dans le pied de page.

## Build

```bash
npm run lint
npm test
npm run build
```

Les trois doivent être verts avant tout commit ou déploiement. Le build
utilise la sortie `standalone` de Next.js (voir `next.config.mjs` et le
`Dockerfile`, section Déploiement).

Aucune page ne déclare plus `export const revalidate` : `Nav` (dans le
layout racine) lit le cookie de session via `next/headers`, ce qui force
Next.js à rendre dynamiquement toute la page — l'option de segment
`revalidate`, qui ne s'applique qu'au rendu statique/ISR, n'y avait donc
aucun effet. La mise en cache des données reste assurée par `revalidate`
posé sur chaque `fetch` dans `lib/api.ts`.

### Sécurité

`next.config.mjs` pose `X-Content-Type-Options`, `X-Frame-Options`,
`Referrer-Policy`, `Permissions-Policy` sur toutes les routes, et
`Strict-Transport-Security` en production. Pas de `Content-Security-Policy`
pour l'instant : une CSP correcte demanderait de générer un nonce par
requête et de l'injecter dans les scripts/styles de Next.js — à faire en
suivi.

## Structure des dossiers

```
app/            pages et routes (App Router), une route = un dossier
  api/session/  route interne : pose/retire le cookie httpOnly du jeton
  matchs/       liste des matchs + détail d'un match ([id])
  carnet/       carnet de paris de l'abonné (client, "use client")
  ...           tarifs, bookmakers, track-record, compte, connexion,
                inscription, cgu, mentions-légales
  not-found.tsx, error.tsx, loading.tsx  états globaux (voir plus bas)
components/     un composant par fichier, réutilisés entre plusieurs pages
lib/            api.ts (client HTTP typé), session.ts (lecture du cookie
                côté serveur), client-session.ts (côté client), format.ts,
                pricing.ts, types.ts
tests/          Vitest + Testing Library, tests/msw/ pour les mocks HTTP
public/photos/  photos du site (voir Photos ci-dessous)
```

### États

- `app/loading.tsx`, `app/matchs/loading.tsx`, `app/matchs/[id]/loading.tsx` :
  squelettes gris (`animate-pulse`) affichés pendant le rendu serveur de la
  page correspondante.
- `app/not-found.tsx` : page 404 (route inexistante).
- `app/error.tsx` : erreur inattendue (API indisponible, etc.), avec un
  bouton « Réessayer ».

## Les jetons — aucune couleur hors jetons

Toutes les couleurs du site sont déclarées une fois dans `app/globals.css`
(`@theme { --color-* }`) et consommées via les classes Tailwind générées
(`bg-ink`, `text-muted`, `border-line`, etc.). **Règle stricte : aucune
couleur ne doit apparaître en dur (`#rrggbb`, `rgb()`, nom CSS) dans
`app/`, `components/` ou `lib/`** — toute nouvelle couleur doit d'abord être
ajoutée comme jeton dans `globals.css`. Se vérifie avec :

```bash
grep -rnE "#[0-9a-fA-F]{3,6}\b" app components lib --include=*.tsx --include=*.ts
```

qui doit ne rien retourner.

Les mêmes jetons portent aussi les tailles de titres (`h-section`,
`num-hero`, `num-page`, `num-row`, …) et les composants de base (`btn`,
`btn-ghost`, `link`, `eyebrow`) : les réutiliser plutôt que dupliquer des
classes Tailwind brutes pour une nouvelle page.

**Exception documentée :** le voile en dégradé posé sur la photo du héros
(`components/Hero.tsx`, classe `bg-[linear-gradient(180deg,rgba(0,0,0,.72)…)]`)
utilise du noir translucide en dur plutôt qu'un jeton. Ce n'est pas une
couleur au sens propre mais un assombrissement de photo à plusieurs arrêts
(0 %, 45 %, 100 %) — un jeton `--color-*` ne peut pas porter de dégradé
multi-arrêts avec des opacités différentes à chaque arrêt. Le grep ci-dessus
ne le détecte pas (il ne matche que les couleurs hex), c'est volontaire.

## Photos

`public/photos/` contient deux photos de stade (jour/nuit), chacune en
pleine résolution et en variante `-900` (utilisée en `<picture>` sous 700 px
de large). Voir `PHOTOS.md` (à la racine de `frontend/`, pas dans `public/`
pour ne pas l'exposer sur le site) : ce sont des photos Unsplash de
démonstration, **à remplacer avant mise en ligne** par des photos dont
RushPlay détient les droits (achat, licence libre de droits ou production
propre), avec crédit mis à jour dans le même fichier.

## Déploiement

Le frontend se déploie comme un second service Coolify, à côté de l'API
(`api`), avec son propre `Dockerfile` (build multi-étage Node 22 alpine,
sortie `standalone` de Next.js) :

1. Service Docker Coolify, contexte de build `frontend/`, fichier
   `frontend/Dockerfile`.
2. Argument de build `NEXT_PUBLIC_API_URL=https://<domaine de l'API>` (saisi
   dans l'interface Coolify, jamais dans un commit ou un chat).
3. Domaine du site pointé sur ce service.

Détails complets : voir `deploy/coolify.md` à la racine du dépôt (étape 9).
