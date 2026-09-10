import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)   # nom canonique affiché
    country: Mapped[str] = mapped_column(String(120), nullable=False)

    aliases = relationship("TeamAlias", back_populates="team", cascade="all, delete-orphan")


class TeamAlias(Base):
    """Nom d'une équipe tel qu'écrit par une source. source ∈ {fd_uk, fd_org, odds_api}."""

    __tablename__ = "team_aliases"
    __table_args__ = (UniqueConstraint("source", "alias", name="uq_alias_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    alias: Mapped[str] = mapped_column(String(120), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    team = relationship("Team", back_populates="aliases")
