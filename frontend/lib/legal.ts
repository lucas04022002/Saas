/**
 * Informations légales de RushPlay, centralisées pour les pages /mentions-legales et /cgu.
 *
 * Ces champs restaient à TO_FILL, et les pages affichaient donc « À COMPLÉTER » à quatorze
 * endroits, en public. Ils sont désormais renseignés avec ce que l'éditeur publie déjà sur son
 * portfolio — rien n'est inventé ici, et surtout pas un numéro d'immatriculation.
 *
 * `editorSiren` vaut NOT_APPLICABLE et non une valeur vide : il n'y a pas d'immatriculation, et
 * les CGU disent elles-mêmes que « l'abonnement payant n'est pas encore ouvert au paiement ». La
 * page reprend cette réserve mot pour mot plutôt que d'affirmer une absence définitive d'activité
 * commerciale, que la page « Tarifs » contredirait. Le statut disait « Entrepreneur individuel (EI) », ce qui
 * anticipait une micro-entreprise qui n'existe pas encore. La page bascule d'elle-même sur la
 * forme professionnelle le jour où un numéro est renseigné ici (voir `isRegistered`).
 *
 * L'hébergeur était annoncé comme Hetzner. Il ne l'est pas : rushplay.fr répond sur
 * 51.254.216.32, un bloc OVH (FR-OVH-20150522). Une mention légale fausse est pire qu'une
 * mention absente.
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

/** Valeur d'un champ sans objet, par opposition à un champ non rempli. */
export const NOT_APPLICABLE = "Sans objet";

export const LEGAL: LegalInfo = {
  editorName: "Lucas Guilhot",
  editorStatus: "Personne physique — site sans activité commerciale à ce jour",
  editorAddress: "Haute-Garonne (31), France",
  editorSiren: NOT_APPLICABLE,
  editorEmail: "lucasguilhot7@gmail.com",
  publicationDirector: "Lucas Guilhot",
  hostName: "OVH SAS",
  hostAddress: "2 rue Kellermann, 59100 Roubaix, France",
  hostPhone: "1007",
  lastUpdate: "17 septembre 2026",
};

/**
 * L'éditeur est-il immatriculé ?
 *
 * La page écrit une phrase différente selon la réponse : mentionner un siège
 * social et un SIREN pour une personne physique qui n'en a pas serait faux.
 */
export function isRegistered(legal: LegalInfo = LEGAL): boolean {
  return legal.editorSiren !== NOT_APPLICABLE && legal.editorSiren !== TO_FILL;
}
