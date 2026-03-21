from datetime import datetime

from pydantic import BaseModel


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    current_period_end: datetime


class UpgradeSubscriptionRequest(BaseModel):
    plan: str
