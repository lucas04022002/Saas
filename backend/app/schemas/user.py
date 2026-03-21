from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    id: str
    first_name: str
    email: EmailStr
    role: str
    subscription_plan: str


class UserUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
