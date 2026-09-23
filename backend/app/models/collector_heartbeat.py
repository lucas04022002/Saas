from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CollectorHeartbeat(Base):
    """Le dernier passage de chaque collecteur, lu par `/health`.

    En base plutôt qu'en fichier (23/09/2026) : le dossier `heartbeats/` était un volume créé par root,
    et depuis que le conteneur tourne sans privilège, chaque collecteur écrivait ses données puis
    échouait sur ce fichier — `/health` annonçait en panne des collecteurs qui marchaient.
    """
    __tablename__ = "collector_heartbeats"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
