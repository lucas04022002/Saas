from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.auth import LoginRequest, SignUpRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(payload: SignUpRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        first_name=payload.first_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    subscription = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.STARTER,
        status=SubscriptionStatus.ACTIVE,
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(subscription)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return {
        "success": True,
        "message": "User created successfully",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "first_name": user.first_name,
                "email": user.email,
                "role": user.role.value,
                "subscription_plan": user.subscription_plan.value,
            },
        },
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "first_name": user.first_name,
                "email": user.email,
                "role": user.role.value,
                "subscription_plan": user.subscription_plan.value,
            },
        },
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "message": "Current user fetched successfully",
        "data": {
            "id": str(current_user.id),
            "first_name": current_user.first_name,
            "email": current_user.email,
            "role": current_user.role.value,
            "subscription_plan": current_user.subscription_plan.value,
        },
    }
