"""Paiement de l'abonnement : ouverture, résiliation, et le webhook qui fait foi."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.services import billing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


def _indisponible() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Le paiement en ligne n'est pas encore ouvert. Réessayez plus tard.",
    )


def _abonnement(db: Session, user: User) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub is None:
        sub = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.STARTER,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc),
        )
        db.add(sub)
        db.flush()
    return sub


@router.get("/plan")
def lire_plan():
    """Le tarif réel, lu chez Stripe, pour que la page affiche ce qui sera prélevé."""
    if not billing.est_configure():
        return {"success": True, "message": "Paiement non configuré", "data": None}
    try:
        return {"success": True, "message": "", "data": billing.lire_tarif()}
    except stripe.error.StripeError:
        logger.exception("Lecture du tarif Stripe impossible")
        return {"success": True, "message": "Tarif indisponible", "data": None}


@router.post("/checkout")
def ouvrir_paiement(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not billing.est_configure():
        raise _indisponible()

    sub = _abonnement(db, current_user)
    if sub.plan in {SubscriptionPlan.PRO, SubscriptionPlan.ELITE} and sub.status == SubscriptionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Vous êtes déjà abonné.")

    try:
        session = billing.ouvrir_paiement(
            user_email=current_user.email,
            user_id=str(current_user.id),
            customer_id=sub.stripe_customer_id,
        )
    except stripe.error.StripeError as erreur:
        # Le code et le message de Stripe disent POURQUOI : compte non activé,
        # tarif d'un autre mode, devise refusée... Sans eux, la panne se résume
        # à « réessayez », alors qu'aucun de ces cas ne se répare en réessayant.
        logger.error(
            "STRIPE checkout refusé : code=%s type=%s message=%s",
            getattr(erreur, "code", None),
            type(erreur).__name__,
            getattr(erreur, "user_message", None) or str(erreur),
        )
        # Le nom de la classe ne dit rien : « InvalidRequestError » couvre aussi
        # bien une URL de retour mal formée qu'un tarif d'un autre mode. C'est
        # le message de Stripe qui nomme le paramètre fautif, et sans lui il
        # faut aller fouiller les journaux du serveur pour une panne qui, elle,
        # est déjà visible à l'écran.
        motif = getattr(erreur, "user_message", None) or str(erreur) or type(erreur).__name__
        raise HTTPException(status_code=502, detail=f"Stripe a refusé la création du paiement : {motif[:300]}")

    db.commit()
    return {"success": True, "message": "", "data": session}


@router.post("/portal")
def ouvrir_portail(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Résiliation, moyen de paiement et factures, chez Stripe."""
    if not billing.est_configure():
        raise _indisponible()

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if sub is None or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="Aucun abonnement à gérer.")

    try:
        url = billing.ouvrir_portail(sub.stripe_customer_id)
    except stripe.error.StripeError:
        logger.exception("Ouverture du portail de facturation impossible")
        raise HTTPException(status_code=502, detail="Le portail est momentanément indisponible.")

    return {"success": True, "message": "", "data": {"url": url}}


def _appliquer(db: Session, sub: Subscription, abonnement_stripe: dict) -> None:
    """Recopie l'état Stripe sur l'abonnement local. Stripe fait foi, pas nous."""
    statut = abonnement_stripe.get("status")
    ouvert = statut in billing.STATUTS_OUVRANTS

    sub.stripe_subscription_id = abonnement_stripe.get("id")
    sub.plan = SubscriptionPlan.PRO if ouvert else SubscriptionPlan.STARTER
    sub.status = (
        SubscriptionStatus.ACTIVE
        if ouvert
        else SubscriptionStatus.PAST_DUE
        if statut == "past_due"
        else SubscriptionStatus.CANCELED
    )
    sub.cancel_at_period_end = bool(abonnement_stripe.get("cancel_at_period_end"))
    sub.current_period_end = billing.fin_de_periode(abonnement_stripe)

    # `users.subscription_plan` est ce que lit le paywall à chaque requête :
    # le laisser diverger de l'abonnement donnerait un accès que plus personne
    # ne paie, ou l'inverse.
    sub.user.subscription_plan = sub.plan
    db.add(sub)
    db.add(sub.user)


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Le seul endroit où un plan devient payant.

    Ni la page de succès, ni un appel du client ne changent quoi que ce soit :
    une redirection de navigateur s'ouvre à la main, un webhook signé, non.
    """
    if not billing.est_configure():
        raise _indisponible()

    charge_utile = await request.body()
    try:
        event = billing.verifier_signature(charge_utile, request.headers.get("stripe-signature"))
    except (stripe.error.SignatureVerificationError, ValueError):
        # Ni le corps ni la raison ne sont journalisés : une charge utile non
        # signée est une donnée hostile.
        logger.warning("Webhook Stripe refusé : signature invalide")
        raise HTTPException(status_code=400, detail="Signature invalide")

    objet = event["data"]["object"]
    type_evenement = event["type"]

    if type_evenement == "checkout.session.completed":
        # `client_reference_id` revient de Stripe en CHAÎNE. La colonne est un
        # UUID : comparer l'un à l'autre marche chez certains pilotes et casse
        # chez d'autres. On convertit, et une valeur illisible ne cherche rien.
        user = None
        reference = objet.get("client_reference_id")
        if reference:
            try:
                user = db.query(User).filter(User.id == uuid.UUID(str(reference))).first()
            except ValueError:
                user = None
        if user is None:
            # Un paiement qu'on ne sait pas rattacher doit se voir : sans cette
            # trace, l'utilisateur a payé et personne ne le sait.
            logger.error("Paiement Stripe sans compte rattachable (session %s)", objet.get("id"))
            return {"success": True, "message": "Compte introuvable", "data": None}

        sub = _abonnement(db, user)
        sub.stripe_customer_id = objet.get("customer") or sub.stripe_customer_id

        abonnement_id = objet.get("subscription")
        if abonnement_id:
            # Passer par `configurer` et non poser la clé à la main : c'est là
            # qu'est aussi choisie la version d'API. Une clé posée seule
            # relit l'abonnement dans la version épinglée par le SDK, dont
            # la forme diffère de celle de l'événement qu'on vient de recevoir.
            billing.configurer()
            _appliquer(db, sub, dict(stripe.Subscription.retrieve(abonnement_id)))
        else:
            sub.plan = SubscriptionPlan.PRO
            sub.status = SubscriptionStatus.ACTIVE
            sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
            sub.user.subscription_plan = SubscriptionPlan.PRO
            db.add(sub)
        db.commit()

    elif type_evenement in {"customer.subscription.updated", "customer.subscription.deleted"}:
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == objet.get("id"))
            .first()
        )
        if sub is None:
            sub = (
                db.query(Subscription)
                .filter(Subscription.stripe_customer_id == objet.get("customer"))
                .first()
            )
        if sub is None:
            logger.error("Abonnement Stripe inconnu (%s)", objet.get("id"))
            return {"success": True, "message": "Abonnement inconnu", "data": None}

        _appliquer(db, sub, dict(objet))
        db.commit()

    # Tout autre événement est acquitté sans rien changer : Stripe cesserait de
    # réémettre si nous renvoyions une erreur, et réémettrait indéfiniment si
    # nous ne répondions pas.
    return {"success": True, "message": "", "data": None}
