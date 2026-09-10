# RushPlay — spec du front

Date : 2026-09-10. Direction validée en maquettes avec Lucas après vingt-quatre
propositions ; références assumées : Apple (vide, gros chiffres, gris clair),
Nike (titres courts qui claquent, noir), Mercedes (précision, filets fins).
Maquettes de référence : `.superpowers/brainstorm/823-1789066323/content/premium-site-v2.html`
(accueil + page match) et `premium-suite.html` (bookmakers, carnet, track
record, tarifs).

## 1. Ce que le front fait

Consommer l'API du socle (`docs/superpowers/specs/2026-09-10-rushplay-refonte-design.md`,
routes `/api/v1/*`) et l'afficher selon le système visuel ci-dessous. Aucune
logique métier côté front : probabilités, écarts, mouvements, textes viennent
tels quels de l'API. Le front ne parle jamais à la base.

## 2. Système visuel

**Principe** : le chiffre est le produit. Pas de cartes, pas de boîtes, pas de
pastilles, pas de motif, pas de couleur décorative. Des sections pleine
largeur qui alternent noir, blanc, gris ; des lignes séparées par des filets
d'un pixel ; une typographie énorme et serrée.

**Couleurs** (jetons CSS, un seul fichier `app/styles/tokens.css`) :
- `--ink #1d1d1f` texte et éléments forts · `--paper #ffffff` · `--grey #f5f5f7`
  fond des sections calmes · `--black #000000` sections scène · `--muted
  #6e6e73` texte secondaire · `--faint #a1a1a6` désactivé, chiffres de matchs
  serrés · `--line rgba(0,0,0,.10)` filets clairs · `--line-dark
  rgba(255,255,255,.14)` filets sur noir · `--link #2997ff` liens uniquement.
- Aucune autre couleur. Un écart positif se distingue par le gras et une
  pastille noire `+3,2 %`, jamais par une couleur.

**Typographie** : `Inter Tight` (600 à 900) pour titres et chiffres, `Inter`
(400 à 700) pour le texte. Échelle : chiffre héros 236 px (mobile 140), chiffre
de page match 180 px (mobile 120), titres de section 56 px (mobile 40), noms
d'équipes 30 px dans les listes et 96 px en page match (mobile 44), texte 16 à
19 px, méta 12 à 14 px. Interlettrage négatif de −0,035 em à −0,075 em sur
tout ce qui est en Inter Tight. Chiffres tabulaires dans les tableaux.

**Mise en page** : conteneur 1180 px, gouttières 48 px (mobile 20 px). Listes de
matchs = grille `1.6fr 1fr 1fr auto`, chiffre à droite (mobile : nom + chiffre
sur une ligne, méta dessous). Tableaux sans bordure, filet sous l'en-tête en
encre, filets clairs entre lignes.

**Photos** : héros de l'accueil et fond du manifeste = photo de stade de nuit
pleine largeur sous un voile noir (dégradé 72 % → 45 % → 85 %). Fichiers dans
`public/photos/`, en WebP, 2000 px, avec une version 900 px pour mobile. Les
deux photos Unsplash des maquettes servent au développement ; avant la mise en
ligne, Lucas fournit ses images ou une licence propre.

**Mouvement** : les grands chiffres se comptent de 0 à leur valeur en 600 ms à
l'arrivée dans l'écran, une seule fois. Les sections apparaissent avec un léger
fondu au défilement. Rien d'autre ne bouge. `prefers-reduced-motion` désactive
tout.

**Voix** : titres courts terminés par un point (« Aujourd'hui. », « Qui paie le
mieux. », « Ton vrai bilan. »). Tutoiement. Actions au verbe (« Voir les matchs
du jour », « Noter ce pari », « S'abonner »). Jamais « prédiction », « pronostic »,
« value bet », « confiance ». Toujours la provenance (« référence Pinnacle »,
« relevé de 12:00 », « moyenne, Pinnacle absent »).

## 3. Écrans

1. **Accueil `/`** : nav noire ; héros photo avec eyebrow (match phare, heure,
   référence), chiffre 236 px, titre « <Favori> favori. D'après le marché, pas
   d'après nous. », paragraphe, deux liens ; section blanche « Aujourd'hui. »
   (4 lignes de matchs, colonnes : équipes + méta, meilleur écart ou
   « Réservé », mouvement, chiffre) et lien « Tous les matchs du jour › » ;
   manifeste noir sur photo « On ne prédit rien. On lit le marché. » en trois
   colonnes (On relève / On retire la marge / On te montre) ; section grise
   track record (chiffre 200 px + phrase) ; pied de page avec bandeau ANJ. Le
   match phare = celui du jour avec le plus grand écart si Pro, sinon le
   premier match du jour.
2. **Matchs `/matchs`** : titre « Matchs. », sous-titre (date, nombre, heure du
   relevé), sélecteur de jours (segments), filtres de compétition (pilules),
   lignes de matchs groupées par compétition. Non abonné : colonne écart =
   « Réservé », mouvement visible ; abonné : écart et mouvement.
3. **Match `/matchs/[id]`** : fil d'Ariane, noms 96 px (l'équipe extérieure en
   gris), méta, grille 2 colonnes : chiffre 180 px + label + trois barres
   fines / analyse en 22 px + bouton « Noter ce pari » ; puis 2 colonnes :
   tableau bookmakers (Pinnacle en gras en tête, écart en pastille) / courbe du
   mouvement (SVG, une ligne) + tableau forme. Non abonné : tableau, courbe et
   pastilles remplacés par un bloc « Réservé aux abonnés › » ; l'analyse est
   celle renvoyée par l'API (déjà sans écart ni mouvement).
4. **Bookmakers `/bookmakers`** (Pro) : « Qui paie le mieux. », tableau une
   ligne par bookmaker (meilleur écart avec match et cote, écart en 40 px,
   nombre ≥ 3 %, marge moyenne, matchs), phrase « Les cotes changent… ».
   Non-Pro : la page existe, le tableau est remplacé par le bloc réservé.
5. **Carnet `/carnet`** (connecté) : fond gris, « Ton vrai bilan. », quatre
   KPI (engagé, réglé, résultat, rendement), tableau des paris (statut en
   texte : En attente / Gagné / Perdu / Annulé), ligne de saisie (match par
   recherche, pari, bookmaker, cote, mise) et bouton « Noter ce pari » ;
   suppression d'un pari en attente ; annulation si match reporté.
6. **Track record `/track-record`** (public) : fond noir, chiffre 200 px de la
   compétition sélectionnée (Ligue 1 par défaut), phrase de provenance,
   tableau par compétition.
7. **Tarifs `/tarifs`** : deux colonnes, gratuit / lecture complète (prix
   affiché depuis une constante, 9 € par mois par défaut), listes à filets,
   boutons.
8. **Compte** : `/connexion`, `/inscription` (prénom, e-mail, mot de passe,
   date de naissance, case 18 ans ; erreur « Vous devez avoir 18 ans ou plus »
   telle que renvoyée par l'API), `/compte` (plan, résiliation).
9. **Légal** : `/mentions-legales`, `/cgu` (texte statique fourni par Lucas ;
   gabarit en attendant), bandeau ANJ dans le pied de page de chaque page, texte
   pris sur `GET /api/v1/legal`.

## 4. Architecture

- Next.js 15, App Router, TypeScript, Tailwind v4 avec les jetons ci-dessus
  exposés en `@theme` ; pas de librairie de composants.
- `lib/api.ts` : un client `fetch` typé par route, base URL
  `NEXT_PUBLIC_API_URL`, jeton JWT dans un cookie `httpOnly` posé par une
  route handler `/api/session` (connexion, déconnexion) ; les pages serveur
  lisent le cookie et appellent l'API avec `Authorization: Bearer`.
- Rendu serveur pour les pages publiques (accueil, matchs, match, track
  record, tarifs) avec revalidation 60 s ; client pour le carnet et le compte.
- Composants : `Nav`, `Footer` (avec ANJ), `MatchRow`, `BigNumber` (compte
  animé), `Bars`, `MovementChart` (SVG), `BookTable`, `Reserved` (bloc réservé),
  `Kpi`, `BetForm`. Un composant = un fichier, jamais de style hors des jetons.
- États : chargement = squelettes gris ; vide = phrase d'invitation (« Aucun
  match aujourd'hui. Reviens demain. ») ; erreur = phrase qui dit quoi faire ;
  cotes anciennes = « relevé il y a N h » calculé côté front depuis
  `odds_taken_at`.
- Accessibilité : contraste AA sur toutes les paires, focus visible, tableaux
  avec en-têtes, `prefers-reduced-motion`.

## 5. Tests

- Composants : `BigNumber`, `Bars`, `MatchRow`, `Reserved` avec Vitest +
  Testing Library (rendu, valeurs, états Pro / non Pro).
- Pages : tests d'intégration avec l'API mockée par MSW sur les cas
  anonyme, Starter, Pro ; inscription refusée avant 18 ans ; carnet : ajout,
  suppression, statut.
- Build sans erreur ni avertissement ; Lighthouse ≥ 90 en accessibilité et
  performance sur l'accueil.

## 6. Hors périmètre

Application mobile native, mode sombre global (le site alterne déjà noir et
blanc par section), affiliation, LLM, notifications.
