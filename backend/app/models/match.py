import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MatchStatus


class Match(Base):
    """Un match, à venir ou joué. Les résultats vivent ici (home_score/away_score, status FINISHED)."""

    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("competition", "kickoff_at", "home_team_id", "away_team_id", name="uq_match_natural"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)   # "fdo:<id>" (football-data.org)
    fd_uk_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)     # "E0:2025-08-15:Liverpool:Bournemouth"
    competition: Mapped[str] = mapped_column(String(8), nullable=False, index=True)             # E0, F1, SP1, D1, I1, CL
    home_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    away_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    home_team: Mapped[str] = mapped_column(String(120), nullable=False)   # nom canonique (copie pour l'affichage)
    away_team: Mapped[str] = mapped_column(String(120), nullable=False)
    league: Mapped[str] = mapped_column(String(120), nullable=False, index=True)   # libellé (« Premier League »)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    home = relationship("Team", foreign_keys=[home_team_id])
    away = relationship("Team", foreign_keys=[away_team_id])
    favorites = relationship("Favorite", back_populates="match", cascade="all, delete-orphan")
    snapshots = relationship("OddsSnapshot", back_populates="match", cascade="all, delete-orphan", order_by="OddsSnapshot.taken_at")
    totals = relationship("TotalsSnapshot", back_populates="match", cascade="all, delete-orphan", order_by="TotalsSnapshot.taken_at")
    bets = relationship("Bet", back_populates="match")
