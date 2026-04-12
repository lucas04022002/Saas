from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    id: str
    first_name: str
    email: EmailStr
    role: str
    subscription_plan: str
