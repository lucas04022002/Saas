import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MatchUnlock(Base):
    """Un match ouvert par un compte gratuit, au prix d'un crédit hebdomadaire.

    Le déblocage est DÉFINITIF : la ligne n'est jamais effacée, et relire le
    match ne coûte rien. Punir celui qui revient vérifier une cote avant le
    coup d'envoi n'aurait aucun sens — il a déjà payé son crédit.

    Le quota se compte donc sur `unlocked_at`, pas sur le nombre de lignes :
    « combien de matchs ai-je ouverts depuis lundi ».
    """

    __tablename__ = "match_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_match_unlock_user_match"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="match_unlocks")
    match = relationship("Match", back_populates="unlocks")
