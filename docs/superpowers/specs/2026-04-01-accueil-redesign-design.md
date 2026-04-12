# Spec : Redesign Landing Page Accueil — RushPlay

**Date :** 2026-04-01
**Scope :** `frontend/` — page d'accueil uniquement (`app/page.tsx` + sections)

---

## Contexte

La landing page actuelle utilise des composants génériques (Launch UI / shadcn). Le nouveau design adopte une esthétique plus premium : fond très sombre, typographie bold, glass-cards, chart SVG animé. L'objectif est de porter le design de référence (`rushplay_accueil_version_transparence/code.html`) dans l'archi Next.js existante.

---

## Architecture

Approche retenue : **mise à jour in-place** des composants section existants. Même structure de fichiers, même `page.tsx`. Pas de nouveaux fichiers de section sauf `signal-preview`.

### Mapping sections

| Ancien composant | Nouveau composant | Action |
|---|---|---|
| `Navbar` | Navbar v2 | Mise à jour |
| `Hero` | Hero v2 (chart SVG) | Mise à jour |
| `Stats` | Stats v2 | Mise à jour |
| `CapitalChart` | — | **Supprimé** (absorbé dans Hero) |
| `Opportunities` | Signal Preview | **Remplacement complet** |
| `Items` | Comment ça marche | **Remplacement complet** |
| `Pricing` | Pricing v2 | Mise à jour styling |
| `FAQ` | FAQ v2 | Mise à jour styling |
| `Footer` | Footer v2 | Mise à jour |

---

## Sections — Détail

### 1. Globals (`globals.css` + `layout.tsx`)
- Font : remplacer par `Plus Jakarta Sans` (Google Fonts)
- Background : `#10131a` (était `#06090F`)
- Ajouter classes utilitaires : `.glass-card`, `.hero-glow`, `.chart-line`

### 2. Navbar
- Fixed, `backdrop-blur-xl`, bg `#10131a/80`
- Logo `RushPlay` en lime (`#c8f000`), font-black
- Liens : Accueil (actif = lime + underline) / Dashboard / Historique / Tarifs
- Bouton "Connexion" ghost + bouton "Commencer" CTA lime
- Mobile : menu hamburger (sheet existant)

### 3. Hero
- Badge animé "Algorithme V4.2 Live" avec dot pulsant
- Titre `text-8xl font-black` : "Les bookmakers se trompent. RushPlay le voit." (span lime)
- 2 CTAs : "Accéder aux signaux" (lime) + "Voir les résultats" (ghost)
- Chart SVG de performance animé (courbe lime + gradient fill) avec axe temporel Jan→Sept 2024
- Sidebar métriques : ROI Global +145.2% / Taux de réussite 74.8% / Mise moy. 2.5%
- Supprime `MockupFrame` / `Screenshot` / import `CapitalChart`

### 4. Stats
- 3 colonnes : `57.6%` Précision / `+12.4%` ROI Mensuel / `24/7` Analyse Temps Réel
- Fond `surface-container-lowest` (`#0b0e15`)
- Texte descriptif sous chaque chiffre

### 5. Signal Preview *(remplace Opportunities)*
- **Server Component** Next.js — fetch `GET https://saas-oi6c.onrender.com/api/v1/opportunities/top?limit=3`
- 3 cards en grille `grid-cols-1 md:grid-cols-3`
- Cards 1 & 2 : home_team vs away_team, marché (`recommended_bet`), probabilité IA (`confidence_score`), value (`value_percent`), badge risk_level
- Card 3 : overlay locked "Signal Pro Exclusive" avec CTA "Passer à RushPlay Pro" → `/signup?plan=pro`
- Hover : bordure lime + bouton passe en fond lime
- Filtres sport (Foot / Tennis / NBA) : statiques, décoratifs pour l'instant
- Si fetch échoue : afficher 2 cards skeleton + 1 locked

### 6. Comment ça marche *(remplace Items)*
- 3 blocs identiques : icône + titre + texte
  1. Ingestion de données
  2. Analyse Neuronale
  3. Signaux Immédiats
- Fond `surface-container-low`
- Icônes : `database` / `psychology` / `notifications_active` (Material Symbols ou équivalent lucide-react)

### 7. Pricing
- Conserver contenu : Starter 0€ / Pro 10€
- Styling : Pro avec `border-2 border-[#c8f000]`, badge "Recommandé", shadow glow lime
- Pro légèrement surélevé (`-translate-y-4` sur desktop)
- Icônes check `check_circle` (lime) / `cancel` (gris)

### 8. FAQ
- Accordion shadcn existant, nouveau styling sombre
- 3 questions : précision / connaissances sport / bookmakers compatibles

### 9. Footer
- 4 colonnes : RushPlay (logo + tagline + icônes sociales) / Produit / Compagnie / Légal
- Copyright "© 2024 RushPlay. Tous droits réservés." + "Made for winners."

---

## Données

- **Endpoint public** : `GET /api/v1/opportunities/top?limit=3` — pas d'auth requise
- Champs utilisés : `home_team`, `away_team`, `league`, `confidence_score`, `recommended_bet`, `bookmaker_odds`, `value_percent`, `risk_level`
- Fetch côté serveur (pas de loading state côté client pour les 2 premières cards)
- En cas d'erreur fetch : fallback silencieux avec cards skeleton

---

## Hors scope

- Pages Dashboard, Historique, Tarifs (traitées séparément)
- Authentification / gestion de session sur la landing
- Filtres sport fonctionnels (décoratifs)
- Animations complexes au scroll
