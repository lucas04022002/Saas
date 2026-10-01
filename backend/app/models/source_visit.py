from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourceVisit(Base):
    """Arrivées par le lien d'un réseau (`rushplay.fr/?ref=tiktok`), comptées par jour (heure de Paris).

    Un compteur, pas un journal : ni adresse, ni navigateur, ni heure. Le navigateur n'envoie la visite
    qu'à l'arrivée avec `?ref=` dans l'adresse, donc on compte des clics sur le lien, pas des pages vues.
    """
    __tablename__ = "source_visits"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    visits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
