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


# --- Les deux formes de l'objet Stripe ---------------------------------------


def test_fin_de_periode_lit_l_ancienne_forme():
    """`stripe.Subscription.retrieve` rend la forme épinglée par le SDK."""
    fin = billing.fin_de_periode({"current_period_end": PERIODE})
    assert int(fin.timestamp()) == PERIODE


def test_fin_de_periode_lit_la_forme_des_versions_recentes():
    """Le webhook livre la version configurée sur le point de terminaison.

    À partir de « basil », `current_period_end` vit sur les lignes d'articles.
    Ne lire que l'ancienne forme daterait la fin de période à l'instant présent :
    l'abonné verrait son abonnement expirer le jour de son paiement.
    """
    fin = billing.fin_de_periode(
        {"id": "sub_1", "items": {"data": [{"id": "si_1", "current_period_end": PERIODE}]}}
    )
    assert int(fin.timestamp()) == PERIODE


def test_fin_de_periode_prend_la_plus_lointaine_echeance():
    plus_tard = PERIODE + 86_400
    fin = billing.fin_de_periode(
        {
            "items": {
                "data": [
                    {"current_period_end": PERIODE},
                    {"current_period_end": plus_tard},
                ]
            }
        }
    )
    assert int(fin.timestamp()) == plus_tard


def test_un_paiement_en_version_recente_date_correctement_la_periode(
    client, db, starter_user, stripe_configure
):
    """Le cas réel : webhook en version récente, abonnement daté au mois prochain."""
    event = _evenement(
        "customer.subscription.updated",
        {
            "id": "sub_1",
            "customer": "cus_1",
            "status": "active",
            "cancel_at_period_end": False,
            # Pas de `current_period_end` à la racine : c'est la forme récente.
            "items": {"data": [{"current_period_end": PERIODE}]},
        },
    )
    db.add(
        Subscription(
            user_id=starter_user.id,
            plan=SubscriptionPlan.STARTER,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc),
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
        )
    )
    db.commit()

    with patch.object(billing, "verifier_signature", return_value=event):
        client.post("/api/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})

    sub = db.query(Subscription).filter_by(user_id=starter_user.id).one()

    # SQLite rend la date sans fuseau : on le repose avant de comparer, sinon
    # `.timestamp()` la relit comme une heure locale et décale de deux heures.
    fin = sub.current_period_end
    if fin.tzinfo is None:
        fin = fin.replace(tzinfo=timezone.utc)

    assert int(fin.timestamp()) == PERIODE
    # Le vrai enjeu : la période ne se termine PAS le jour du paiement.
    assert fin > datetime.now(timezone.utc) + timedelta(days=29)


# --- Savoir sur quoi le site est branché ------------------------------------


def test_le_tarif_dit_s_il_est_en_mode_reel(stripe_configure):
    """Test ou réel : rien d'autre ne le distingue vu de l'extérieur.

    Un site branché sur des clés de test affiche un prix, ouvre une page de
    paiement, accepte une carte — et n'encaisse jamais rien. La panne ne se
    voit qu'au premier relevé bancaire qui ne vient pas.
    """
    base = {"unit_amount": 900, "currency": "eur", "recurring": {"interval": "month", "interval_count": 1}}

    with patch.object(stripe.Price, "retrieve", return_value={**base, "livemode": False}):
        assert billing.lire_tarif()["livemode"] is False

    with patch.object(stripe.Price, "retrieve", return_value={**base, "livemode": True}):
        assert billing.lire_tarif()["livemode"] is True


def test_un_refus_de_stripe_nomme_son_motif(client, starter_user, stripe_configure):
    """« Réessayez » est un mensonge quand la cause est structurelle.

    Un compte non activé, un tarif appartenant à l'autre mode, une devise
    refusée : aucun de ces cas ne se répare en réessayant. Le motif de Stripe
    doit remonter, sinon la panne est indiscernable d'un incident passager.
    """
    refus = stripe.error.InvalidRequestError(
        "You cannot create a live Checkout Session until you activate your account.",
        param=None,
        code="account_invalid",
    )

    with patch.object(billing, "ouvrir_paiement", side_effect=refus):
        r = client.post("/api/v1/billing/checkout", headers=auth_header(starter_user))

    assert r.status_code == 502
    # L'application enveloppe ses erreurs : le `detail` de HTTPException ressort
    # en `message`. C'est cette enveloppe-là que lit le client.
    assert "account_invalid" in r.json()["message"]
