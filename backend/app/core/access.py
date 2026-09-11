"""Paywall côté serveur : le favori et sa probabilité sont publics ; écarts, mouvements, relevés et comparateur sont réservés."""
from app.models.enums import SubscriptionPlan
from app.models.user import User

PAID_PLANS = {SubscriptionPlan.PRO, SubscriptionPlan.ELITE}
PREMIUM_LIST_FIELDS = ("best_gap", "movement")
PREMIUM_DETAIL_FIELDS = ("best_gap", "movement", "books", "reference_book", "history", "score_distribution")


def is_pro(user: User | None) -> bool:
    return user is not None and user.subscription_plan in PAID_PLANS


def gate_list(items: list[dict], user: User | None) -> list[dict]:
    pro = is_pro(user)
    for item in items:
        item["locked"] = not pro
        if not pro:
            for f in PREMIUM_LIST_FIELDS:
                item[f] = None
    return items


def gate_detail(detail: dict, user: User | None) -> dict:
    pro = is_pro(user)
    detail["locked"] = not pro
    if not pro:
        for f in PREMIUM_DETAIL_FIELDS:
            detail[f] = None
    return detail
