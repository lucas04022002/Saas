from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import UpgradeSubscriptionRequest

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

VALID_PLANS = {SubscriptionPlan.STARTER, SubscriptionPlan.PRO, SubscriptionPlan.ELITE}


@router.get("/me")
def get_my_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "success": True,
        "message": "Subscription fetched successfully",
        "data": {
            "plan": subscription.plan.value,
            "status": subscription.status.value,
            "current_period_end": subscription.current_period_end,
        },
    }


@router.post("/upgrade")
def upgrade_subscription(
    payload: UpgradeSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        plan = SubscriptionPlan(payload.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")

    if plan not in VALID_PLANS:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")

    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if subscription is None:
        subscription = Subscription(
            user_id=current_user.id,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(subscription)
    else:
        subscription.plan = plan
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)

    current_user.subscription_plan = plan

    db.add(current_user)
    db.commit()

    return {
        "success": True,
        "message": "Subscription updated successfully",
        "data": {
            "plan": plan.value,
            "status": SubscriptionStatus.ACTIVE.value,
            "current_period_end": subscription.current_period_end,
        },
    }
