import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import BetStatus, Outcome


class Bet(Base):
    """Carnet de bankroll : un pari saisi par le client, réglé automatiquement au résultat."""

    __tablename__ = "bets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    outcome: Mapped[Outcome] = mapped_column(Enum(Outcome), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(40), nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[BetStatus] = mapped_column(Enum(BetStatus), nullable=False, default=BetStatus.PENDING)
    payout: Mapped[float | None] = mapped_column(Float, nullable=True)   # gain brut (mise × cote) si gagné, 0 si perdu, mise si annulé
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    match = relationship("Match", back_populates="bets")
