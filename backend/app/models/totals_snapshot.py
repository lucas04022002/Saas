import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TotalsSnapshot(Base):
    """Une photo des cotes over/under du marché total de buts (Pinnacle), à une ligne et un instant donnés.
    Sert à déduire le total de buts attendu par le marché (app/engine/score.py) plutôt que la moyenne de ligue.
    Jamais modifiée."""

    __tablename__ = "totals_snapshots"
    __table_args__ = (UniqueConstraint("match_id", "bookmaker", "taken_at", "line", name="uq_totals_snapshot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    bookmaker: Mapped[str] = mapped_column(String(32), nullable=False)   # "pinnacle" uniquement pour l'instant (région eu, 1 crédit)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    line: Mapped[float] = mapped_column(Float, nullable=False)   # 2.5, 3.5...
    over: Mapped[float] = mapped_column(Float, nullable=False)
    under: Mapped[float] = mapped_column(Float, nullable=False)

    match = relationship("Match", back_populates="totals")
