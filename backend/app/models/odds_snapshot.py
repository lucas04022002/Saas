import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OddsSnapshot(Base):
    """Une photo des cotes 1N2 d'un bookmaker pour un match, à un instant. Jamais modifiée."""

    __tablename__ = "odds_snapshots"
    __table_args__ = (UniqueConstraint("match_id", "bookmaker", "taken_at", name="uq_snapshot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    bookmaker: Mapped[str] = mapped_column(String(40), nullable=False)    # clé The Odds API : betclic_fr, winamax_fr, unibet_fr, pmu_fr, netbet_fr, pinnacle ; ou fd_uk_avg / fd_uk_pinnacle
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    home: Mapped[float] = mapped_column(Float, nullable=False)
    draw: Mapped[float] = mapped_column(Float, nullable=False)
    away: Mapped[float] = mapped_column(Float, nullable=False)

    match = relationship("Match", back_populates="snapshots")
