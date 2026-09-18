import { LEGAL, TO_FILL } from "@/lib/legal";
import { lireTarif } from "@/lib/tarif";

export const metadata = { robots: { index: false } };

const h3 = "font-tight text-[18px] font-semibold tracking-[-0.02em] mt-6";
const p = "mt-3 text-[16px] leading-relaxed text-muted";
const ul = "mt-3 list-disc space-y-1 pl-5 text-[16px] leading-relaxed text-muted";

export default async function Cgu() {
  const tarif = await lireTarif();
  return (
    <section className="site py-16 md:py-24">
      <div className="max-w-[65ch]">
        <p className="eyebrow">Conditions générales</p>
        <h1 className="h-section mt-3">Conditions d&apos;utilisation.</h1>
        <p className="mt-3 text-[15px] text-muted">Dernière mise à jour : {LEGAL.lastUpdate}.</p>
        <p className={p}>
          Les présentes conditions générales d&apos;utilisation et de vente (« CGU ») s&apos;
          appliquent à l&apos;utilisation du site RushPlay et à la souscription de l&apos;abonnement
          payant. Elles sont conclues entre l&apos;éditeur du site, dont l&apos;identité figure
          dans les <a href="/mentions-legales" className="link">mentions légales</a>, et tout
          utilisateur du site (« l&apos;utilisateur »).
        </p>

        <div className="hair mt-8 pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Objet du service</h2>
          <p className={p}>
            RushPlay propose une lecture du marché des paris sportifs sur le football : le favori
            de chaque match et sa probabilité implicite, les écarts de cotes entre bookmakers, le
            mouvement des cotes dans le temps, le score le plus probable déduit du marché, ainsi
            qu&apos;un carnet de suivi personnel. RushPlay n&apos;est pas un opérateur de paris,
            ne prend aucune mise et ne fait aucune promesse de résultat. Le track record public du
            site montre que le favori affiché gagne environ une fois sur deux : ces informations
            sont fournies à titre indicatif, pas comme une garantie.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Accès au service</h2>
          <p className={p}>
            L&apos;accès au site est réservé aux personnes âgées de 18 ans révolus. La création
            d&apos;un compte est personnelle et incessible : un compte par personne. L&apos;
            utilisateur est responsable de la confidentialité de ses identifiants et de toute
            activité effectuée depuis son compte.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Offres et prix</h2>
          <p className={p}>
            Le site propose une offre gratuite, sur compte : elle permet d&apos;ouvrir deux
            matchs par semaine calendaire, avec le favori, sa probabilité et le score exact le
            plus probable. Un match ouvert le reste définitivement pour le compte qui l&apos;a
            ouvert ; le quota se recharge chaque lundi. Sans compte, aucune de ces données
            n&apos;est accessible. L&apos;offre « Lecture complète », à {tarif.montant} {tarif.devise} TTC {tarif.periodeLongue},
            ouvre tous les matchs sans quota, ainsi que les écarts entre bookmakers, le
            mouvement des cotes et le carnet automatisé.
            L&apos;offre payante est sans engagement et résiliable à tout moment depuis la page
            « Compte » de l&apos;utilisateur. La résiliation prend effet à la fin de la période
            déjà payée : aucun remboursement au prorata n&apos;est dû pour la période en cours.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Droit de rétractation</h2>
          <p className={p}>
            Conformément à l&apos;article L221-18 du code de la consommation, l&apos;utilisateur
            consommateur dispose d&apos;un délai de 14 jours à compter de la souscription de
            l&apos;abonnement pour se rétracter, sans avoir à justifier de motif.
          </p>
          <p className={p}>
            Lors de la souscription, il est demandé à l&apos;utilisateur qui souhaite un accès
            immédiat à l&apos;offre payante de renoncer expressément à ce délai de rétractation
            pour la partie du service déjà fournie. En donnant cet accord, l&apos;utilisateur
            reconnaît perdre son droit de rétractation dès que l&apos;exécution de
            l&apos;abonnement a commencé.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Paiement</h2>
          <p className={p}>
            À la date de mise à jour des présentes CGU, l&apos;abonnement payant n&apos;est pas
            encore ouvert au paiement sur le site. Les clauses de la présente section
            s&apos;appliqueront dès l&apos;ouverture du paiement en ligne, dont l&apos;utilisateur
            sera informé sur le site.
          </p>
          <p className={p}>
            Le paiement de l&apos;abonnement sera prélevé mensuellement, par reconduction
            automatique, jusqu&apos;à résiliation par l&apos;utilisateur. Les moyens de paiement
            acceptés et le prestataire de paiement seront précisés sur la page « Tarifs » et au
            moment de la souscription.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Obligations de l&apos;utilisateur</h2>
          <p className={p}>L&apos;utilisateur s&apos;engage à :</p>
          <ul className={ul}>
            <li>utiliser le site à des fins strictement personnelles ;</li>
            <li>ne procéder à aucune extraction automatisée des données du site (scraping) ;</li>
            <li>ne pas revendre, redistribuer ni communiquer à des tiers les données du service ;</li>
            <li>fournir des informations exactes lors de la création de son compte.</li>
          </ul>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Disponibilité et maintenance</h2>
          <p className={p}>
            L&apos;éditeur met en œuvre les moyens raisonnables pour assurer un accès continu au
            site, sans garantie de disponibilité permanente. Le site peut être interrompu
            ponctuellement pour maintenance, mise à jour ou en cas de panne, sans que cela ouvre
            droit à indemnité.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Propriété intellectuelle</h2>
          <p className={p}>
            La marque RushPlay, le site et ses contenus propres sont protégés par le droit de la
            propriété intellectuelle, dans les conditions détaillées dans les{" "}
            <a href="/mentions-legales" className="link">mentions légales</a>.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Responsabilité et jeu responsable</h2>
          <p className={p}>
            Les informations fournies par RushPlay (favoris, probabilités implicites, écarts de
            cotes, mouvement des cotes) le sont à titre indicatif, sans garantie de gain. RushPlay
            n&apos;est pas un opérateur de paris, ne prend aucune mise et n&apos;est affilié à
            aucun bookmaker.
          </p>
          <p className={p}>
            Les paris sportifs comportent des risques : endettement, isolement, dépendance. Si
            vous ou un proche êtes concerné, appelez le 09 74 75 13 13 (appel non surtaxé) ou
            rendez-vous sur joueurs-info-service.fr. Le jeu est interdit aux mineurs.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Données personnelles</h2>
          <p className={p}>
            Le traitement des données personnelles de l&apos;utilisateur est décrit dans les{" "}
            <a href="/mentions-legales" className="link">mentions légales</a>, section « Données
            personnelles ».
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Résiliation</h2>
          <p className={p}>
            L&apos;utilisateur peut résilier son abonnement à tout moment depuis sa page
            « Compte », ou supprimer son compte en écrivant à {LEGAL.editorEmail}. L&apos;éditeur
            peut suspendre ou supprimer un compte en cas de manquement grave aux présentes CGU,
            après en avoir informé l&apos;utilisateur.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Modification des CGU</h2>
          <p className={p}>
            L&apos;éditeur peut modifier les présentes CGU à tout moment, notamment pour tenir
            compte de l&apos;évolution du service ou de la réglementation. La date de dernière
            mise à jour figurant en tête de cette page fait foi. Les utilisateurs seront informés
            de toute modification substantielle.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Droit applicable et litiges</h2>
          <p className={p}>
            Les présentes CGU sont soumises au droit français. Conformément aux articles
            L616-1 et suivants du code de la consommation, en cas de litige non résolu directement
            avec l&apos;éditeur, l&apos;utilisateur consommateur peut recourir gratuitement au
            service de médiation de la consommation suivant : {TO_FILL}.
          </p>
          <p className={p}>
            À défaut de résolution amiable, les tribunaux français compétents seront ceux du
            ressort du domicile du défendeur, ou tout autre tribunal désigné par les règles de
            procédure applicables lorsque l&apos;utilisateur est un consommateur.
          </p>
        </div>
      </div>
    </section>
  );
}
