import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MatchStatus


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    home_team: Mapped[str] = mapped_column(String(120), nullable=False)
    away_team: Mapped[str] = mapped_column(String(120), nullable=False)
    league: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    analysis = relationship("Analysis", back_populates="match", uselist=False, cascade="all, delete-orphan")
    team_stats = relationship("TeamStats", back_populates="match", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="match", cascade="all, delete-orphan")
