"""Sérialisation des horodatages en JSON : SQLite (dev/tests, base en mémoire) renvoie des datetimes naïves
même pour une colonne DateTime(timezone=True) — jsonable_encoder les émet alors sans offset (`2026-09-11T19:45:00`),
que `new Date(iso)` côté front interprète dans le fuseau du serveur au lieu d'UTC. Toute date renvoyée par l'API
doit passer par `to_utc_iso` : naïve -> supposée UTC, aware -> convertie en UTC, toujours émise avec le suffixe
`Z` plutôt que `+00:00` (équivalents, mais `Z` est ce qu'attend `new Date()` sans ambiguïté)."""
from datetime import datetime, timezone


def to_utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
