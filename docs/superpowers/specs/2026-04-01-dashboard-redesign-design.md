# Spec : Redesign Dashboard — RushPlay

**Date :** 2026-04-01
**Scope :** `frontend/app/dashboard/page.tsx` + nouveaux composants UI

---

## Contexte

Le dashboard actuel a un layout sidebar + topbar custom avec un style ancien (`#06090F`, `#0E1828`). On le porte dans le nouveau design système (fond `#10131a`, glass-cards, lime `#c8f000`) avec une sidebar de filtres fonctionnels et des signal cards en grille 2 colonnes.

---

## Architecture

- **`app/dashboard/page.tsx`** — Server Component (`force-dynamic`). Fetch toutes les données (matches + analyses). Passe tout à `DashboardClient`.
- **`components/ui/dashboard-client.tsx`** — Client Component. Gère `selectedLeague` (string | "all") et `minConfidence` (number 0–100). Filtre les matches côté client. Rend sidebar + KPIs + cards.
- **`components/ui/team-logo.tsx`** — Client Component. Tente de charger le logo depuis TheSportsDB (`https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={name}`). Fallback : cercle avec initiales du nom d'équipe.

---

## Sections — Détail

### Navbar
Même composant `Navbar` que la landing. Le lien "Dashboard" est mis en avant (lime + underline) via une prop `activePath` ou via `usePathname()` dans le composant.

### KPI Cards (4 colonnes)
| KPI | Source |
|---|---|
| Win Rate Global | Statique `57.6%` |
| ROI Mensuel | Statique `+12.4%` |
| Confiance Moyenne | Calculée : moyenne des `confidence_score` des matches |
| Signaux Actifs | `matches.length` + dot pulsant lime |

Styling : `glass-card`, border `#454933/20`, valeurs en lime ou blanc selon importance.

### Sidebar gauche (`lg:col-span-3`)

**Ligues Favorites**
- Liste des ligues uniques extraites des matches (`[...new Set(matches.map(m => m.league))]`)
- Item "Toutes les ligues" en premier (sélectionné par défaut)
- Item actif : bordure gauche lime + fond `#32353c/50` + texte blanc
- Item inactif : texte `slate-400`, hover fond `#32353c/30`
- Chaque item affiche le nombre de signaux de la ligue

**AI Filter**
- Titre "AI Filter"
- Label "Confiance Min." + valeur affichée en lime (ex: `85%`)
- Slider HTML `<input type="range" min="0" max="100" step="5">`
- Accent couleur lime via CSS

### Signal Cards (`lg:col-span-9`, grille `grid-cols-1 md:grid-cols-2`)

Chaque card visible :
- **Header** : badge `risk_level` (faible = vert, modéré = jaune, élevé = rouge) + badge valeur `+{value_percent}%`
- **Équipes** : `TeamLogo` home + score `vs` + `TeamLogo` away
- **Conseil IA** : `recommended_bet` + **Confiance** : `confidence_score`%
- **Cote** : `bookmaker_odds`
- **CTA** : bouton "VOIR LE SIGNAL" lime (lien vers `/historique` ou expansion future)

**Card verrouillée** (1 fixe en dernière position) :
- Overlay backdrop-blur avec lock 🔒
- Texte "Signal Premium" + CTA "Débloquer maintenant" → `/signup?plan=pro`
- Toujours affichée, même pour les users Pro (driver de conversion pour upgrade futur)

**Filtrage** :
- `selectedLeague !== "all"` → `matches.filter(m => m.league === selectedLeague)`
- `minConfidence > 0` → `matches.filter(m => m.confidence_score >= minConfidence)`
- Les deux filtres s'appliquent simultanément

### Footer
Même composant `FooterSection` que la landing.

---

## Données

- Endpoint : `GET /api/v1/matches?limit=20&sort_by=confidence_score&order=desc` (existant via `fetchMatches`)
- Champs utilisés : `home_team`, `away_team`, `league`, `confidence_score`, `recommended_bet`, `bookmaker_odds`, `risk_level`, `value_percent`
- Auth : requise (le dashboard est une page connectée — conserver le comportement existant)

## Logos équipes (TeamLogo)

1. Fetch `https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={teamName}` côté client
2. Si réponse valide → `<img src={teams[0].strTeamBadge} />`
3. Si erreur/timeout/null → fallback : cercle `#272a31` avec initiales (ex: `MC` pour "Man City") en lime

---

## Hors scope

- Authentification / redirection si non connecté (comportement existant conservé)
- Pagination des signaux
- Favoris persistants par ligue (juste filtre temporaire côté client)
- Scores live (données statiques `vs`)
