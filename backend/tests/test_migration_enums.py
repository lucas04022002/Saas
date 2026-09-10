"""Garde-fou : les libellés PostgreSQL des enums outcome/betstatus doivent être les NOMS
SQLAlchemy (HOME/DRAW/AWAY...), pas les .value Python — SQLAlchemy persiste le nom du membre
pour un Enum(PyEnum) par défaut."""
import re
from pathlib import Path

from sqlalchemy import Enum

from app.models.enums import BetStatus, MatchStatus, Outcome

MIGRATION = (Path(__file__).parent.parent / "alembic" / "versions" / "0005_market_reading.py").read_text(encoding="utf-8")


def _labels_in_create_type(text: str, type_name: str) -> list[str]:
    m = re.search(rf"CREATE TYPE {type_name} AS ENUM \(([^)]*)\)", text)
    assert m is not None, f"CREATE TYPE {type_name} AS ENUM (...) introuvable dans la migration"
    return [v.strip().strip("'") for v in m.group(1).split(",")]


def test_outcome_enum_labels_match_sqlalchemy_names():
    assert _labels_in_create_type(MIGRATION, "outcome") == list(Enum(Outcome).enums)


def test_betstatus_enum_labels_match_sqlalchemy_names():
    assert _labels_in_create_type(MIGRATION, "betstatus") == list(Enum(BetStatus).enums)


def test_matchstatus_added_values_are_known_members():
    added = re.findall(r"ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS '([^']+)'", MIGRATION)
    assert added == ["POSTPONED", "QUARANTINE"]
    assert set(added) <= set(MatchStatus.__members__)
