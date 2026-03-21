import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RiskLevel


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), unique=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    recommended_bet: Mapped[str] = mapped_column(String(120), nullable=False)
    bookmaker_odds: Mapped[float] = mapped_column(Float, nullable=False)
    value_percent: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    ai_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    match = relationship("Match", back_populates="analysis")
    warning_points = relationship("WarningPoint", back_populates="analysis", cascade="all, delete-orphan")
