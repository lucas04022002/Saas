import { LEGAL, isRegistered } from "@/lib/legal";

export const metadata = { robots: { index: false } };

const h3 = "font-tight text-[18px] font-semibold tracking-[-0.02em] mt-6";
const p = "mt-3 text-[16px] leading-relaxed text-muted";
const ul = "mt-3 list-disc space-y-1 pl-5 text-[16px] leading-relaxed text-muted";

export default function MentionsLegales() {
  return (
    <section className="site py-16 md:py-24">
      <div className="max-w-[65ch]">
        <p className="eyebrow">Informations légales</p>
        <h1 className="h-section mt-3">Mentions légales.</h1>
        <p className="mt-3 text-[15px] text-muted">Dernière mise à jour : {LEGAL.lastUpdate}.</p>

        <div className="hair mt-8 pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Éditeur du site</h2>
          <p className={p}>
            {/* La phrase suit le statut : citer un siège social et un SIREN pour
                une personne physique qui n'en a pas serait faux, et l'omettre le
                deviendrait le jour de l'immatriculation. */}
            {isRegistered() ? (
              <>
                Le site RushPlay est édité par {LEGAL.editorName}, {LEGAL.editorStatus}, dont le
                siège de l&apos;activité est situé {LEGAL.editorAddress}, immatriculé sous le
                numéro SIREN {LEGAL.editorSiren}.
              </>
            ) : (
              <>
                Le site RushPlay est édité par {LEGAL.editorName}, {LEGAL.editorStatus}, établi
                en {LEGAL.editorAddress}. L&apos;abonnement payant n&apos;étant pas ouvert au
                paiement à ce jour, l&apos;éditeur n&apos;exerce aucune activité commerciale et
                n&apos;est pas immatriculé. Il le sera avant toute ouverture du paiement en ligne.
              </>
            )}
          </p>
          <p className={p}>Adresse e-mail de contact : {LEGAL.editorEmail}.</p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Directeur de la publication</h2>
          <p className={p}>
            Le directeur de la publication est {LEGAL.publicationDirector}, en sa qualité
            d&apos;éditeur du site.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Hébergeur</h2>
          <p className={p}>
            Le site est hébergé par {LEGAL.hostName}, {LEGAL.hostAddress}, téléphone :{" "}
            {LEGAL.hostPhone}.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Contact</h2>
          <p className={p}>
            Pour toute question relative au site, à un compte ou à ces mentions légales, écrire à{" "}
            {LEGAL.editorEmail}.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Propriété intellectuelle</h2>
          <p className={p}>
            La marque RushPlay, le nom de domaine, la structure du site, les textes, la mise en
            forme des données et l&apos;ensemble des contenus qui en sont propres sont la
            propriété exclusive de l&apos;éditeur. Toute reproduction ou réutilisation, totale ou
            partielle, sans autorisation préalable est interdite.
          </p>
          <p className={p}>
            Les cotes affichées sur le site sont relevées auprès d&apos;opérateurs de paris
            sportifs tiers, agréés par l&apos;Autorité nationale des jeux (ANJ), et restent la
            propriété de ces opérateurs. Elles sont susceptibles d&apos;avoir changé depuis leur
            dernier relevé. Les données de calendrier et de résultats des matchs proviennent des
            sources football-data.co.uk et football-data.org, citées ici à titre de sources.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Données personnelles</h2>
          <p className={p}>
            Le traitement des données personnelles des utilisateurs du site est soumis au
            règlement général sur la protection des données (RGPD).
          </p>
          <h3 className={h3}>Données collectées</h3>
          <ul className={ul}>
            <li>l&apos;adresse e-mail, utilisée pour la création et la connexion au compte ;</li>
            <li>le mot de passe, jamais stocké en clair : seule une version hachée est conservée ;</li>
            <li>la date de naissance, demandée uniquement pour vérifier la majorité de l&apos;utilisateur ;</li>
            <li>les paris que l&apos;utilisateur choisit d&apos;enregistrer dans son carnet de suivi.</li>
          </ul>
          <h3 className={h3}>Finalité et base légale</h3>
          <p className={p}>
            Ces données sont traitées pour permettre la création du compte, la fourniture du
            service (favoris, carnet, abonnement) et l&apos;amélioration du site. Le traitement
            repose sur l&apos;exécution du contrat qui lie l&apos;utilisateur à RushPlay lors de la
            création d&apos;un compte, et sur l&apos;intérêt légitime de l&apos;éditeur pour le
            suivi technique et la sécurité du service.
          </p>
          <h3 className={h3}>Durée de conservation</h3>
          <p className={p}>
            Les données sont conservées pendant toute la durée de vie du compte, puis pendant 3
            ans après sa fermeture, à des fins de preuve en cas de litige.
          </p>
          <h3 className={h3}>Droits de l&apos;utilisateur</h3>
          <p className={p}>
            Conformément au RGPD, chaque utilisateur dispose d&apos;un droit d&apos;accès, de
            rectification, d&apos;effacement et de portabilité de ses données. Ces droits
            s&apos;exercent en écrivant à {LEGAL.editorEmail}. En cas de désaccord persistant,
            l&apos;utilisateur peut introduire une réclamation auprès de la Commission nationale
            de l&apos;informatique et des libertés (CNIL, www.cnil.fr).
          </p>
          <p className={p}>
            RushPlay ne vend aucune donnée personnelle à des tiers. Le site est hébergé en
            Allemagne, au sein de l&apos;Union européenne.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Cookies</h2>
          <p className={p}>
            Le site dépose un seul cookie, nommé <code>rp_token</code>, strictement nécessaire au
            maintien de la connexion au compte. Ce cookie ne sert à aucune autre fin. RushPlay ne
            dépose aucun traceur publicitaire et ne recourt à aucune mesure d&apos;audience tierce.
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Avertissement jeux d&apos;argent</h2>
          <p className={p}>
            RushPlay n&apos;est pas un opérateur de paris sportifs, ne prend aucune mise et
            n&apos;est affilié à aucun bookmaker. Le site propose une lecture du marché des paris
            sportifs, à titre d&apos;information.
          </p>
          <p className={p}>
            Les paris sportifs comportent des risques : endettement, isolement, dépendance. Si
            vous ou un proche êtes concerné, appelez le 09 74 75 13 13 (appel non surtaxé) ou
            rendez-vous sur joueurs-info-service.fr. Le jeu est interdit aux mineurs. L&apos;offre
            des opérateurs de paris sportifs mentionnés est encadrée par l&apos;Autorité nationale
            des jeux (ANJ).
          </p>
        </div>

        <div className="hair pt-8 pb-6">
          <h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">Limitation de responsabilité</h2>
          <p className={p}>
            Les informations publiées sur le site (favoris, probabilités implicites, écarts entre
            bookmakers, mouvement des cotes, track record) sont fournies à titre indicatif. Les
            cotes affichées sont susceptibles d&apos;avoir changé depuis leur dernier relevé.
            RushPlay n&apos;offre aucune garantie de gain et ne saurait être tenu responsable des
            décisions prises par l&apos;utilisateur sur la base de ces informations.
          </p>
        </div>
      </div>
    </section>
  );
}
