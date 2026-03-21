from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "message": "Profile fetched successfully",
        "data": {
            "id": str(current_user.id),
            "first_name": current_user.first_name,
            "email": current_user.email,
            "role": current_user.role.value,
            "subscription_plan": current_user.subscription_plan.value,
        },
    }


@router.patch("/profile")
def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.email:
        existing = db.scalar(select(User).where(User.email == payload.email.lower(), User.id != current_user.id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        current_user.email = payload.email.lower()

    if payload.first_name:
        current_user.first_name = payload.first_name.strip()

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "id": str(current_user.id),
            "first_name": current_user.first_name,
            "email": current_user.email,
            "role": current_user.role.value,
            "subscription_plan": current_user.subscription_plan.value,
        },
    }
