"""Facturation Stripe : ce qui touche à l'argent, isolé ici.

Deux règles gouvernent ce module.

**Le serveur ne croit que Stripe.** Le plan d'un utilisateur ne change jamais
sur la foi d'une redirection de navigateur, d'un paramètre d'URL ou d'un appel
du client : il change quand un webhook signé par Stripe le dit. Une page de
succès peut être ouverte par n'importe qui, à n'importe quel moment.

**Le prix affiché est le prix facturé.** Le montant n'est écrit nulle part
dans le code : il est lu chez Stripe, sur le tarif désigné par
`STRIPE_PRICE_ID`. Une constante recopiée finit toujours par diverger du
tarif réel, et c'est l'utilisateur qui découvre l'écart sur son relevé.
"""
from __future__ import annotations

from datetime import datetime, timezone

import stripe

from app.core.config import settings

#: Les statuts Stripe qui ouvrent l'accès payant.
STATUTS_OUVRANTS = {"active", "trialing"}

#: La version d'API que cette application parle à Stripe.
#:
#: Le SDK Python épingle la sienne (2024-12-18.acacia pour stripe 11.x), et
#: cette version-là ignore Managed Payments : le compte de RushPlay l'utilise,
#: et Stripe refusait donc toute création de session de paiement — en laissant
#: passer les lectures, ce qui rendait la panne invisible jusqu'au premier clic
#: sur « S'abonner ».
#:
#: La valeur choisie est celle du point de terminaison des webhooks. Les objets
#: que Stripe nous ENVOIE et ceux que nous LUI DEMANDONS ont ainsi exactement la
#: même forme ; c'est cette divergence qui déplace `current_period_end` sur les
#: lignes d'articles (voir `fin_de_periode`). Si la version du webhook change
#: dans le tableau de bord Stripe, celle-ci doit suivre.
VERSION_API = "2026-08-26.dahlia"


class BillingNotConfigured(RuntimeError):
    """Stripe n'est pas configuré : aucune commande ne peut aboutir."""


def est_configure() -> bool:
    return bool(
        settings.stripe_secret_key and settings.stripe_webhook_secret and settings.stripe_price_id
    )


def configurer() -> None:
    """Arme le SDK : la clé, et la version d'API que nous parlons."""
    if not est_configure():
        raise BillingNotConfigured(
            "STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET et STRIPE_PRICE_ID sont requis."
        )
    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = VERSION_API


def lire_tarif() -> dict:
    """Le tarif réel, lu chez Stripe.

    Renvoyé au client pour que la page Tarifs affiche ce qui sera prélevé, et
    non un nombre recopié à la main.
    """
    configurer()
    price = stripe.Price.retrieve(settings.stripe_price_id)
    recurrence = price.get("recurring") or {}
    return {
        "amount_cents": price.get("unit_amount"),
        "currency": (price.get("currency") or "eur").upper(),
        "interval": recurrence.get("interval"),
        "interval_count": recurrence.get("interval_count", 1),
        # Test ou reel ? Stripe porte l'information sur chaque objet. Sans elle,
        # rien ne distingue de l'exterieur un site branche sur des cles de test
        # — qui affiche un prix, propose de payer, et n'encaissera jamais — d'un
        # site en production. C'est exactement le genre de panne qui ne se voit
        # qu'au premier client perdu.
        "livemode": bool(price.get("livemode")),
        # « inclusive » : le montant EST le prix payé. « exclusive » : la taxe
        # s'ajoute par-dessus, et le prix affiché n'est pas celui qui sera
        # prélevé. En France, un prix montré à un consommateur s'affiche TTC :
        # sans cette information, le site annonce un montant et en facture un
        # autre, y compris dans les CGU.
        "tax_behavior": price.get("tax_behavior"),
    }


def ouvrir_paiement(*, user_email: str, user_id: str, customer_id: str | None) -> dict:
    """Ouvre une session de paiement et rend l'adresse où envoyer l'utilisateur.

    `client_reference_id` porte l'identifiant du compte : c'est lui qui permet
    au webhook de rattacher le paiement, même si l'adresse e-mail saisie chez
    Stripe diffère de celle du compte.
    """
    configurer()
    base = settings.public_site_url.rstrip("/")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        client_reference_id=user_id,
        # Un client existant est réutilisé : sans cela, chaque paiement créerait
        # un nouveau client pour la même personne, et son historique se
        # disperserait.
        customer=customer_id or None,
        customer_email=None if customer_id else user_email,
        success_url=f"{base}/compte?paiement=ok",
        cancel_url=f"{base}/tarifs?paiement=annule",
        # Obligatoire en Europe : Stripe collecte l'accord de prélèvement
        # récurrent et l'adresse de facturation quand la loi l'exige.
        billing_address_collection="auto",
        allow_promotion_codes=True,
    )
    return {"url": session.url, "id": session.id}


def ouvrir_portail(customer_id: str) -> str:
    """Le portail de facturation : résiliation, moyen de paiement, factures.

    Les CGU promettent une résiliation « en un clic depuis la page Compte ».
    Le portail de Stripe la fournit, et il gère aussi le RIB, les factures et
    les relances — que nous n'aurions aucune raison de réimplémenter.
    """
    configurer()
    base = settings.public_site_url.rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=f"{base}/compte"
    )
    return session.url


def verifier_signature(charge_utile: bytes, entete_signature: str | None) -> stripe.Event:
    """Rend l'événement seulement si Stripe l'a bien signé.

    Sans cette vérification, n'importe qui pourrait appeler le webhook et
    s'offrir un abonnement. C'est la seule chose qui distingue un paiement
    d'une requête HTTP quelconque.
    """
    configurer()
    if not entete_signature:
        raise stripe.error.SignatureVerificationError("Signature absente", None)
    return stripe.Webhook.construct_event(
        payload=charge_utile,
        sig_header=entete_signature,
        secret=settings.stripe_webhook_secret,
    )


def fin_de_periode(abonnement: dict) -> datetime:
    """La date jusqu'à laquelle l'accès est dû, telle que Stripe la donne.

    Deux formes coexistent, et les deux arrivent dans cette application :

    - jusqu'aux versions « acacia », `current_period_end` est porté par
      l'abonnement lui-même. Depuis que `VERSION_API` est imposée, nous ne
      recevons plus cette forme — mais elle reste lue, parce qu'un retour en
      arrière sur la version la ramènerait sans autre signe qu'une date de fin
      de période silencieusement fixée à l'instant présent ;
    - à partir de « basil », Stripe l'a déplacé sur les lignes d'articles
      (`items.data[].current_period_end`). C'est ce que livre le webhook, dont
      la version est celle configurée sur le point de terminaison.

    Ne lire que la première forme donnerait `None` sur les événements du
    webhook, et daterait la fin de période à l'instant présent : l'abonné
    verrait son abonnement expirer le jour même de son paiement.
    """
    horodatage = abonnement.get("current_period_end")

    if horodatage is None:
        lignes = (abonnement.get("items") or {}).get("data") or []
        echeances = [
            ligne.get("current_period_end")
            for ligne in lignes
            if ligne.get("current_period_end")
        ]
        # La plus lointaine : un abonnement à plusieurs lignes court jusqu'à la
        # dernière échéance payée.
        horodatage = max(echeances) if echeances else None

    if horodatage is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(horodatage, tz=timezone.utc)
