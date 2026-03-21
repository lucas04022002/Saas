import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TeamType


class TeamStats(Base):
    __tablename__ = "team_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    team_type: Mapped[TeamType] = mapped_column(Enum(TeamType), nullable=False)
    recent_form: Mapped[str] = mapped_column(String(20), nullable=False)
    goals_scored: Mapped[int] = mapped_column(Integer, nullable=False)
    goals_conceded: Mapped[int] = mapped_column(Integer, nullable=False)
    xg: Mapped[float] = mapped_column(Float, nullable=False)
    xga: Mapped[float] = mapped_column(Float, nullable=False)
    possession_avg: Mapped[float] = mapped_column(Float, nullable=False)
    shots_on_target_avg: Mapped[float] = mapped_column(Float, nullable=False)
    clean_sheets: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    match = relationship("Match", back_populates="team_stats")
