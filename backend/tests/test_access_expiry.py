"""Un abonnement payant n'ouvre l'accès que s'il est actif et non échu (audit du 22/09/2026, C3).

`is_pro` ne lisait que `user.subscription_plan`. Le plan ne repassait à STARTER que si le webhook
`customer.subscription.deleted` arrivait : secret faux, API indisponible, Stripe qui cesse de
réémettre — et l'accès restait ouvert sans paiement, sans limite.
"""
from datetime import datetime, timedelta, timezone

from app.core.access import GRACE, is_pro, retrograder_echus
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from tests.conftest import make_user

NOW = datetime.now(timezone.utc)


def _abonne(db, status=SubscriptionStatus.ACTIVE, fin=NOW + timedelta(days=20), plan=SubscriptionPlan.PRO):
    user = make_user(db, plan=plan)
    db.add(Subscription(user_id=user.id, plan=plan, status=status, current_period_end=fin))
    db.commit(); db.refresh(user)
    return user


def test_actif_et_non_echu_est_pro(db):
    assert is_pro(_abonne(db)) is True


def test_resilie_n_est_plus_pro_meme_si_le_plan_dit_pro(db):
    """Le cas de l'audit : le plan est resté PRO, mais l'abonnement est CANCELED."""
    assert is_pro(_abonne(db, status=SubscriptionStatus.CANCELED)) is False


def test_impaye_n_est_plus_pro(db):
    assert is_pro(_abonne(db, status=SubscriptionStatus.PAST_DUE)) is False


def test_periode_echue_depuis_longtemps_n_est_plus_pro(db):
    assert is_pro(_abonne(db, fin=NOW - timedelta(days=10))) is False


def test_periode_echue_de_peu_reste_pro_le_temps_du_prelevement(db):
    """Stripe réessaie un prélèvement pendant quelques jours : couper l'accès le jour J
    punirait un client dont la carte a juste expiré."""
    assert GRACE >= timedelta(days=2)
    assert is_pro(_abonne(db, fin=NOW - timedelta(days=1))) is True


def test_plan_payant_sans_abonnement_n_est_pas_pro(db):
    """Un plan PRO sans ligne d'abonnement ne vient que d'une modification à la main : on ferme."""
    assert is_pro(make_user(db, plan=SubscriptionPlan.PRO)) is False


def test_anonyme_et_gratuit_ne_sont_pas_pro(db):
    assert is_pro(None) is False
    assert is_pro(make_user(db)) is False


def test_retrograder_echus_remet_le_plan_a_starter(db):
    """Le passage quotidien : le champ que lit chaque requête doit finir par dire la vérité."""
    echu = _abonne(db, fin=NOW - timedelta(days=10))
    resilie = _abonne(db, status=SubscriptionStatus.CANCELED)
    en_cours = _abonne(db)

    n = retrograder_echus(db)

    for u in (echu, resilie, en_cours):
        db.refresh(u)
    assert n == 2
    assert echu.subscription_plan == SubscriptionPlan.STARTER
    assert resilie.subscription_plan == SubscriptionPlan.STARTER
    assert en_cours.subscription_plan == SubscriptionPlan.PRO
