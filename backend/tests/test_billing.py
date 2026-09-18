"""Le paiement : ce qui doit tenir même quand quelqu'un essaie de tricher.

Le fil de ces tests est toujours le même : **seul un webhook signé par Stripe
rend un compte payant**. Ni une redirection de navigateur, ni un appel du
client, ni un webhook forgé.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import stripe

from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from app.services import billing
from tests.conftest import auth_header

PERIODE = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())


@pytest.fixture
def stripe_configure(monkeypatch):
    monkeypatch.setattr(billing.settings, "stripe_secret_key", "sk_test_factice", raising=False)
    monkeypatch.setattr(billing.settings, "stripe_webhook_secret", "whsec_factice", raising=False)
    monkeypatch.setattr(billing.settings, "stripe_price_id", "price_factice", raising=False)


def _abonnement_stripe(statut="active", cancel=False, sub_id="sub_1", customer="cus_1"):
    return {
        "id": sub_id,
        "customer": customer,
        "status": statut,
        "cancel_at_period_end": cancel,
        "current_period_end": PERIODE,
    }


def _evenement(type_, objet):
    return {"type": type_, "data": {"object": objet}}


# --- Sans configuration, rien ne s'ouvre ------------------------------------


def test_sans_cles_le_paiement_repond_503(client, starter_user):
    r = client.post("/api/v1/billing/checkout", headers=auth_header(starter_user))
    assert r.status_code == 503


def test_sans_cles_le_webhook_repond_503(client):
    r = client.post("/api/v1/billing/webhook", content=b"{}")
    assert r.status_code == 503


# --- La signature est la seule chose qui distingue un paiement d'une requête --


def test_un_webhook_sans_signature_est_refuse(client, stripe_configure):
    r = client.post("/api/v1/billing/webhook", content=b'{"type":"checkout.session.completed"}')
    assert r.status_code == 400


def test_un_webhook_mal_signe_ne_rend_personne_abonne(client, db, starter_user, stripe_configure):
    faux = _evenement(
        "checkout.session.completed",
        {"id": "cs_1", "customer": "cus_1", "subscription": "sub_1", "client_reference_id": str(starter_user.id)},
    )
    r = client.post(
        "/api/v1/billing/webhook",
        json=faux,
        headers={"stripe-signature": "t=1,v1=signature_inventee"},
    )

    assert r.status_code == 400
    db.refresh(starter_user)
    assert starter_user.subscription_plan == SubscriptionPlan.STARTER


# --- Le paiement abouti ------------------------------------------------------


def test_un_paiement_signe_rend_le_compte_abonne(client, db, starter_user, stripe_configure):
    event = _evenement(
        "checkout.session.completed",
        {
            "id": "cs_1",
            "customer": "cus_1",
            "subscription": "sub_1",
            "client_reference_id": str(starter_user.id),
        },
    )

    with patch.object(billing, "verifier_signature", return_value=event), patch.object(
        stripe.Subscription, "retrieve", return_value=_abonnement_stripe()
    ):
        r = client.post("/api/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    assert r.status_code == 200
    db.refresh(starter_user)
    assert starter_user.subscription_plan == SubscriptionPlan.PRO

    sub = db.query(Subscription).filter_by(user_id=starter_user.id).one()
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"


def test_un_paiement_sans_compte_rattachable_ne_credite_personne(client, db, stripe_configure):
    event = _evenement(
        "checkout.session.completed",
        {"id": "cs_1", "customer": "cus_9", "subscription": "sub_9", "client_reference_id": None},
    )

    with patch.object(billing, "verifier_signature", return_value=event):
        r = client.post("/api/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    # Acquitté pour que Stripe cesse de réémettre, mais rien n'est crédité.
    assert r.status_code == 200
    assert db.query(Subscription).count() == 0


# --- La fin de l'abonnement --------------------------------------------------


def test_une_resiliation_laisse_l_acces_jusqu_a_la_fin_de_periode(
    client, db, starter_user, stripe_configure
):
    """Résilier n'est pas couper : la période déjà payée est due."""
    db.add(
        Subscription(
            user_id=starter_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
        )
    )
    starter_user.subscription_plan = SubscriptionPlan.PRO
    db.commit()

    event = _evenement("customer.subscription.updated", _abonnement_stripe(cancel=True))
    with patch.object(billing, "verifier_signature", return_value=event):
        client.post("/api/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    db.refresh(starter_user)
    sub = db.query(Subscription).filter_by(user_id=starter_user.id).one()

    assert sub.cancel_at_period_end is True
    # Toujours abonné : l'accès court jusqu'à la date payée.
    assert sub.status == SubscriptionStatus.ACTIVE
    assert starter_user.subscription_plan == SubscriptionPlan.PRO


def test_un_abonnement_supprime_retire_l_acces(client, db, starter_user, stripe_configure):
    db.add(
        Subscription(
            user_id=starter_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
        )
    )
    starter_user.subscription_plan = SubscriptionPlan.PRO
    db.commit()

    event = _evenement("customer.subscription.deleted", _abonnement_stripe(statut="canceled"))
    with patch.object(billing, "verifier_signature", return_value=event):
        client.post("/api/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    db.refresh(starter_user)
    assert starter_user.subscription_plan == SubscriptionPlan.STARTER
    assert db.query(Subscription).filter_by(user_id=starter_user.id).one().status == SubscriptionStatus.CANCELED


def test_un_impaye_passe_en_past_due_et_ferme_l_acces(client, db, starter_user, stripe_configure):
    db.add(
        Subscription(
            user_id=starter_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
        )
    )
    starter_user.subscription_plan = SubscriptionPlan.PRO
    db.commit()

    event = _evenement("customer.subscription.updated", _abonnement_stripe(statut="past_due"))
    with patch.object(billing, "verifier_signature", return_value=event):
        client.post("/api/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    db.refresh(starter_user)
    assert starter_user.subscription_plan == SubscriptionPlan.STARTER
    assert db.query(Subscription).filter_by(user_id=starter_user.id).one().status == SubscriptionStatus.PAST_DUE


# --- Le client ne se sur-classe toujours pas lui-même ------------------------


def test_un_utilisateur_ne_peut_pas_s_offrir_le_plan_payant(client, starter_user):
    r = client.post(
        "/api/v1/subscriptions/upgrade",
        json={"plan": "PRO"},
        headers=auth_header(starter_user),
    )
    assert r.status_code == 403


def test_deja_abonne_le_paiement_est_refuse(client, db, starter_user, stripe_configure):
    db.add(
        Subscription(
            user_id=starter_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
        )
    )
    db.commit()

    r = client.post("/api/v1/billing/checkout", headers=auth_header(starter_user))
    assert r.status_code == 409
