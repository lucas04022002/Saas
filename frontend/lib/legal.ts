/**
 * Informations légales de RushPlay, centralisées pour les pages /mentions-legales et /cgu.
 *
 * Les champs liés à l'hébergeur et la date de mise à jour sont connus et renseignés ci-dessous.
 * Les champs liés à l'éditeur (personne physique) ne sont volontairement PAS renseignés : ils
 * valent TO_FILL ("À COMPLÉTER") tant que Lucas ne les a pas remplis lui-même. Ne jamais inventer
 * de nom, d'adresse ou de numéro SIREN ici.
 *
 * Garde-fou de mise en ligne : voir tests/pages.legal.test.tsx. Ce test échoue si un champ vaut
 * encore TO_FILL, mais UNIQUEMENT quand la variable d'environnement CI_STRICT_LEGAL vaut "1" —
 * ce qui n'est pas le cas de la CI actuelle, qui reste donc verte tant que ces champs sont vides.
 * Pour activer le contrôle au lancement commercial : ajouter `CI_STRICT_LEGAL: "1"` dans le
 * bloc `env:` du job `frontend-checks` de .github/workflows/quality-checks.yml (ou l'exporter
 * avant `npm test` en local), une fois tous les champs ci-dessous renseignés.
 */

export const TO_FILL = "À COMPLÉTER";

export interface LegalInfo {
  /** Nom et prénom de l'entrepreneur individuel éditeur du site. */
  editorName: string;
  /** Statut juridique de l'éditeur, ex. « Entrepreneur individuel (EI) ». */
  editorStatus: string;
  /** Adresse du siège de l'activité (adresse postale). */
  editorAddress: string;
  /** Numéro SIREN de l'entrepreneur individuel. */
  editorSiren: string;
  /** Adresse e-mail de contact de l'éditeur. */
  editorEmail: string;
  /** Directeur de la publication (généralement l'éditeur lui-même en EI). */
  publicationDirector: string;
  /** Raison sociale de l'hébergeur. */
  hostName: string;
  /** Adresse postale de l'hébergeur. */
  hostAddress: string;
  /** Numéro de téléphone de l'hébergeur. */
  hostPhone: string;
  /** Date de dernière mise à jour des pages légales, au format long français. */
  lastUpdate: string;
}

export const LEGAL: LegalInfo = {
  editorName: TO_FILL,
  editorStatus: "Entrepreneur individuel (EI)",
  editorAddress: TO_FILL,
  editorSiren: TO_FILL,
  editorEmail: TO_FILL,
  publicationDirector: TO_FILL,
  hostName: "Hetzner Online GmbH",
  hostAddress: "Industriestr. 25, 91710 Gunzenhausen, Allemagne",
  hostPhone: "+49 9831 505-0",
  lastUpdate: "11 septembre 2026",
};
