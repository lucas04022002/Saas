from app.models.enums import SubscriptionPlan
from app.models.user import User

PAID_PLANS = {SubscriptionPlan.PRO, SubscriptionPlan.ELITE}


def is_pro(user: User | None) -> bool:
    return user is not None and user.subscription_plan in PAID_PLANS
