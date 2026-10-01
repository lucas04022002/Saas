from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.sources import source_valide


class SignUpRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    birth_date: date
    #: réseau d'arrivée gardé par le navigateur ; une valeur inconnue devient None, sans refuser l'inscription
    source: str | None = Field(default=None, max_length=32)

    @field_validator("source")
    @classmethod
    def _source(cls, v: str | None) -> str | None:
        return source_valide(v)

    @field_validator("birth_date")
    @classmethod
    def _adult(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Vous devez avoir 18 ans ou plus")
        return v


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
