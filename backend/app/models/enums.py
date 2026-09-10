import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class SubscriptionPlan(str, enum.Enum):
    STARTER = "STARTER"
    PRO = "PRO"
    ELITE = "ELITE"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    QUARANTINE = "QUARANTINE"   # nom d'équipe non résolu : jamais affiché


class Outcome(str, enum.Enum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


class BetStatus(str, enum.Enum):
    PENDING = "PENDING"
    WON = "WON"
    LOST = "LOST"
    VOID = "VOID"
