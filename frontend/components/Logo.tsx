/**
 * Le logo RushPlay.
 *
 * Deux formes, un seul dessin : l'emblème seul (`LogoMark`) et l'emblème suivi
 * du mot (`LogoLockup`).
 *
 * Tout est tracé en `currentColor`. Le logo prend donc la couleur du texte qui
 * l'entoure — blanc sur la barre noire, encre sur fond clair — sans qu'aucune
 * variante de fichier ait à exister, et il suit les thèmes clair et sombre du
 * site sans une ligne de plus.
 *
 * « Play » est posé à 55 % d'opacité, comme dans le fichier d'origine : le mot
 * se lit en deux temps, la marque reste un seul bloc.
 */

/** Les six éclats de l'emblème, découpés par le cercle qui les contient. */
const ECLATS = [
  "M50.00 -65.64 L64.87 -54.83 L59.19 -37.35 L40.81 -37.35 L35.13 -54.83 Z",
  "M65.95 -71.96 L61.44 -85.84 L73.25 -94.42 L85.06 -85.84 L80.55 -71.96 Z",
  "M75.81 -41.61 L87.62 -50.20 L99.44 -41.61 L94.92 -27.73 L80.32 -27.73 Z",
  "M50.00 -22.86 L61.81 -14.28 L57.30 -0.39 L42.70 -0.39 L38.19 -14.28 Z",
  "M24.19 -41.61 L19.68 -27.73 L5.08 -27.73 L0.56 -41.61 L12.38 -50.20 Z",
  "M34.05 -71.96 L19.45 -71.96 L14.94 -85.84 L26.75 -94.42 L38.56 -85.84 Z",
];

/**
 * L'emblème, dans le repère du fichier d'origine.
 *
 * `clipId` est un paramètre, et non une constante : deux emblèmes sur la même
 * page partageraient sinon le même identifiant de masque. Le navigateur
 * résoudrait le premier, ce qui marche par accident tant que le dessin est
 * identique — mais c'est du HTML invalide, et ça cesse de marcher le jour où
 * une variante apparaît.
 */
function Embleme({ clipId }: { clipId: string }) {
  return (
    <g transform="translate(-5.83 22.83) scale(1.4565)">
      <clipPath id={clipId}>
        <circle cx="50" cy="-50" r="46" />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        {ECLATS.map((d) => (
          <path key={d} d={d} fill="currentColor" />
        ))}
      </g>
      <circle cx="50" cy="-50" r="42.5" fill="none" stroke="currentColor" strokeWidth="7" />
    </g>
  );
}

type LogoProps = {
  className?: string;
  /** Rendu unique du masque : à changer si deux logos coexistent sur une page. */
  clipId?: string;
};

/** L'emblème seul, pour les espaces étroits. */
export function LogoMark({ className, clipId = "rp-mark" }: LogoProps) {
  return (
    <svg
      viewBox="0 0 134 134"
      fill="currentColor"
      role="img"
      aria-label="RushPlay"
      className={className}
    >
      <g transform="translate(0 117)">
        <Embleme clipId={clipId} />
      </g>
    </svg>
  );
}

/** L'emblème et le mot : la forme normale de la marque. */
export function LogoLockup({ className, clipId = "rp-lockup" }: LogoProps) {
  return (
    <svg
      viewBox="0 0 711.08 145.06"
      fill="currentColor"
      role="img"
      aria-label="RushPlay"
      className={className}
    >
      <g transform="translate(0 117)">
        <Embleme clipId={clipId} />
        <g transform="translate(158.36 0)">
          {/* « Rush » */}
          <path d="M5.64 0.00V-100.00H46.85Q58.12 -100.00 66.31 -95.94Q74.50 -91.88 78.96 -84.40Q83.42 -76.91 83.42 -66.71Q83.42 -56.31 78.89 -49.06Q74.36 -41.81 65.97 -38.02Q57.58 -34.23 46.17 -34.23H20.07V-53.29H41.68Q47.11 -53.29 50.84 -54.70Q54.56 -56.11 56.48 -59.09Q58.39 -62.08 58.39 -66.71Q58.39 -71.34 56.48 -74.40Q54.56 -77.45 50.84 -78.96Q47.11 -80.47 41.61 -80.47H29.73V0.00ZM60.40 0.00 36.04 -45.70H61.88L86.85 0.00Z" />
          <path d="M53.96 -32.35V-75.03H77.85V0.00H55.03V-13.96H54.23Q51.81 -7.11 45.84 -3.05Q39.87 1.01 31.41 0.94Q23.76 0.94 17.95 -2.55Q12.15 -6.04 8.89 -12.38Q5.64 -18.72 5.64 -27.18V-75.03H29.53V-31.81Q29.53 -25.77 32.72 -22.25Q35.91 -18.72 41.41 -18.79Q44.97 -18.79 47.79 -20.37Q50.60 -21.95 52.28 -24.97Q53.96 -27.99 53.96 -32.35Z" transform="translate(81.68 0)" />
          <path d="M71.01 -52.08 49.19 -51.54Q48.72 -55.03 45.60 -57.32Q42.48 -59.60 37.79 -59.60Q33.62 -59.60 30.77 -57.95Q27.92 -56.31 27.92 -53.49Q27.92 -51.28 29.70 -49.60Q31.48 -47.92 36.24 -46.98L50.67 -44.30Q61.88 -42.21 67.38 -37.25Q72.89 -32.28 72.89 -24.03Q72.89 -16.31 68.39 -10.60Q63.89 -4.90 56.07 -1.74Q48.26 1.41 38.19 1.41Q22.15 1.41 12.89 -5.20Q3.62 -11.81 2.28 -22.95L25.84 -23.49Q26.64 -19.40 29.93 -17.28Q33.22 -15.17 38.26 -15.17Q42.89 -15.17 45.77 -16.88Q48.66 -18.59 48.66 -21.34Q48.66 -26.11 39.53 -27.85L26.44 -30.40Q15.23 -32.55 9.70 -37.99Q4.16 -43.42 4.16 -52.08Q4.16 -59.66 8.22 -64.97Q12.28 -70.27 19.73 -73.12Q27.18 -75.97 37.38 -75.97Q52.62 -75.97 61.38 -69.60Q70.13 -63.22 71.01 -52.08Z" transform="translate(159.68 0)" />
          <path d="M29.53 -42.75V0.00H5.64V-100.00H28.66V-61.21H29.53Q32.08 -68.12 37.85 -72.05Q43.62 -75.97 52.08 -75.97Q59.93 -75.97 65.81 -72.45Q71.68 -68.93 74.90 -62.62Q78.12 -56.31 78.12 -47.79V0.00H54.23V-43.09Q54.23 -49.33 51.07 -52.85Q47.92 -56.38 42.15 -56.38Q38.39 -56.38 35.54 -54.77Q32.68 -53.15 31.11 -50.10Q29.53 -47.05 29.53 -42.75Z" transform="translate(229.34 0)" />
          {/* « Play », en retrait. Le groupe ne porte que l'opacité : les
              lettres gardent les positions du fichier d'origine. */}
          <g opacity="0.55">
            <path d="M8.05 0.00V-100.00H43.76Q55.37 -100.00 63.02 -95.74Q70.67 -91.48 74.50 -84.13Q78.32 -76.78 78.32 -67.58Q78.32 -58.39 74.50 -51.04Q70.67 -43.69 62.99 -39.43Q55.30 -35.17 43.62 -35.17H19.19V-47.92H42.21Q49.66 -47.92 54.26 -50.47Q58.86 -53.02 60.97 -57.48Q63.09 -61.95 63.09 -67.58Q63.09 -73.29 60.97 -77.68Q58.86 -82.08 54.23 -84.56Q49.60 -87.05 42.15 -87.05H23.15V0.00Z" transform="translate(307.67 0)" />
            <path d="M21.48 -100.00V0.00H6.98V-100.00Z" transform="translate(384.19 0)" />
            <path d="M28.72 1.61Q21.61 1.61 15.84 -1.04Q10.07 -3.69 6.71 -8.79Q3.36 -13.89 3.36 -21.21Q3.36 -27.58 5.81 -31.64Q8.26 -35.70 12.42 -38.12Q16.58 -40.54 21.68 -41.74Q26.78 -42.95 32.15 -43.62Q38.93 -44.36 43.09 -44.90Q47.25 -45.44 49.16 -46.61Q51.07 -47.79 51.07 -50.40V-50.74Q51.07 -57.11 47.48 -60.60Q43.89 -64.09 36.85 -64.09Q29.53 -64.09 25.27 -60.91Q21.01 -57.72 19.40 -53.69L5.64 -56.85Q8.12 -63.69 12.85 -67.89Q17.58 -72.08 23.72 -74.03Q29.87 -75.97 36.58 -75.97Q41.07 -75.97 46.11 -74.93Q51.14 -73.89 55.60 -71.11Q60.07 -68.32 62.89 -63.15Q65.70 -57.99 65.70 -49.80V0.00H51.41V-10.27H50.87Q49.53 -7.52 46.68 -4.77Q43.83 -2.01 39.40 -0.20Q34.97 1.61 28.72 1.61ZM31.88 -10.07Q37.99 -10.07 42.28 -12.45Q46.58 -14.83 48.86 -18.72Q51.14 -22.62 51.14 -26.98V-36.71Q50.34 -35.97 48.12 -35.30Q45.91 -34.63 43.09 -34.16Q40.27 -33.69 37.58 -33.32Q34.90 -32.95 33.09 -32.75Q28.86 -32.15 25.37 -30.91Q21.88 -29.66 19.77 -27.28Q17.65 -24.90 17.65 -21.01Q17.65 -15.57 21.68 -12.82Q25.70 -10.07 31.88 -10.07Z" transform="translate(407.15 0)" />
            <path d="M16.11 28.05Q12.82 28.12 10.17 27.62Q7.52 27.11 6.11 26.44L9.66 14.56L10.67 14.83Q16.24 16.24 20.10 14.66Q23.96 13.09 26.58 5.97L28.39 1.01L1.01 -75.03H16.64L35.57 -16.78H36.38L55.37 -75.03H71.01L40.13 9.93Q37.99 15.84 34.70 19.90Q31.41 23.96 26.81 26.01Q22.21 28.05 16.11 28.05Z" transform="translate(474.33 0)" />
          </g>
        </g>
      </g>
    </svg>
  );
}
