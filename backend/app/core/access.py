"""Paywall côté serveur : trois niveaux d'accès, tranchés ici et nulle part ailleurs.

    sans compte      rien. Le nom des équipes, la date, la compétition — pas un
                     chiffre. Ni favori, ni probabilité, ni score.
    compte gratuit   deux matchs par semaine, entièrement ouverts : favori,
                     probabilité, score exact le plus probable.
    abonnement       tous les matchs, plus ce que le marché ne dit pas au
                     premier regard : écarts, mouvement, comparateur,
                     historique, distribution complète des scores.

Le déblocage d'un match par un compte gratuit est un GESTE EXPLICITE, jamais un
effet de bord de la lecture. Sans cela, le préchargement de Next.js au survol
d'un lien dépenserait les crédits de l'utilisateur avant même qu'il clique.
"""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import SubscriptionPlan
from app.models.match_unlock import MatchUnlock
from app.models.user import User

PAID_PLANS = {SubscriptionPlan.PRO, SubscriptionPlan.ELITE}

#: Matchs qu'un compte gratuit peut ouvrir par semaine.
FREE_UNLOCKS_PER_WEEK = 2

#: Ce qu'un compte gratuit voit sur un match qu'il a ouvert — et rien de plus.
FREE_TIER_FIELDS = ("favourite", "top_score")

#: Masqué tant que le match n'est pas ouvert, quel que soit le plan.
# `top_score` figure aussi dans la liste : l'oublier ici laisserait le score
# exact gratuit à l'endroit où on le lit le plus.
#
# `reference` porte les probabilités par issue. Masquer `favourite` en le
# laissant passer ne verrouillerait rien : la plus haute des trois EST le
# favori, et sa valeur EST sa probabilité. Le paywall serait cosmétique, et
# contournable en lisant l'API directement.
LOCKED_LIST_FIELDS = ("favourite", "reference", "top_score", "best_gap", "movement")
LOCKED_DETAIL_FIELDS = (
    "favourite",
    "reference",
    "top_score",
    "best_gap",
    "movement",
    "books",
    "reference_book",
    "history",
    "score_distribution",
)

#: Réservé à l'abonnement, même sur un match ouvert par un compte gratuit.
SUBSCRIBER_ONLY_FIELDS = (
    "best_gap",
    "movement",
    "books",
    "reference_book",
    "history",
    "score_distribution",
)


def is_pro(user: User | None) -> bool:
    return user is not None and user.subscription_plan in PAID_PLANS


def week_start(now: datetime | None = None) -> datetime:
    """Le lundi 00:00 UTC de la semaine en cours.

    Une semaine calendaire, et non une fenêtre glissante de sept jours : « il te
    reste un match cette semaine » se comprend sans explication, et « ton quota
    se recharge lundi » est une promesse vérifiable.
    """
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    lundi = (moment - timedelta(days=moment.weekday())).date()
    return datetime.combine(lundi, time.min, tzinfo=timezone.utc)


def unlocks_used(user: User, db: Session, now: datetime | None = None) -> int:
    """Crédits consommés depuis lundi."""
    return (
        db.query(MatchUnlock)
        .filter(MatchUnlock.user_id == user.id, MatchUnlock.unlocked_at >= week_start(now))
        .count()
    )


def quota_for(user: User | None, db: Session, now: datetime | None = None) -> dict:
    """L'état du quota, tel que le client l'affiche."""
    if user is None:
        return {"plan": "ANONYMOUS", "limit": 0, "used": 0, "remaining": 0, "resets_at": None}
    if is_pro(user):
        return {"plan": "PRO", "limit": None, "used": 0, "remaining": None, "resets_at": None}

    used = unlocks_used(user, db, now)
    return {
        "plan": "STARTER",
        "limit": FREE_UNLOCKS_PER_WEEK,
        "used": used,
        "remaining": max(FREE_UNLOCKS_PER_WEEK - used, 0),
        "resets_at": week_start(now) + timedelta(days=7),
    }


def unlocked_match_ids(user: User | None, db: Session) -> set[str]:
    """Les matchs que ce compte a ouverts, toutes semaines confondues.

    Un déblocage ne se périme pas : le crédit a été dépensé une fois.

    Les identifiants sont rendus en CHAÎNES, et non en UUID : les dictionnaires
    de match sérialisent déjà `"id": str(match.id)`. Comparer un UUID à une
    chaîne échoue sans lever d'erreur — aucun match n'aurait jamais été reconnu
    comme ouvert, et le compte gratuit n'aurait rien vu du tout.
    """
    if user is None or is_pro(user):
        return set()
    rows = db.query(MatchUnlock.match_id).filter(MatchUnlock.user_id == user.id).all()
    return {str(row[0]) for row in rows}


def can_unlock(user: User | None, db: Session, now: datetime | None = None) -> bool:
    if user is None:
        return False
    if is_pro(user):
        return True
    return unlocks_used(user, db, now) < FREE_UNLOCKS_PER_WEEK


def _hide(item: dict, fields) -> None:
    for field in fields:
        if field in item:
            item[field] = None


def gate_list(items: list[dict], user: User | None, unlocked: set | None = None) -> list[dict]:
    """La liste : un abonné voit tout, les autres ne voient que ce qu'ils ont ouvert."""
    if is_pro(user):
        for item in items:
            item["locked"] = False
        return items

    ouverts = unlocked or set()
    for item in items:
        est_ouvert = item.get("id") in ouverts
        item["locked"] = not est_ouvert
        if est_ouvert:
            # Un match ouvert par un compte gratuit montre le favori, pas le
            # comparateur : l'abonnement garde ce qu'il vend.
            _hide(item, SUBSCRIBER_ONLY_FIELDS)
        else:
            _hide(item, LOCKED_LIST_FIELDS)
    return items


def gate_detail(detail: dict, user: User | None, unlocked: set | None = None) -> dict:
    """La fiche d'un match, selon le plan et selon qu'il a été ouvert."""
    if is_pro(user):
        detail["locked"] = False
        return detail

    est_ouvert = detail.get("id") in (unlocked or set())
    detail["locked"] = not est_ouvert
    _hide(detail, SUBSCRIBER_ONLY_FIELDS if est_ouvert else LOCKED_DETAIL_FIELDS)
    return detail
