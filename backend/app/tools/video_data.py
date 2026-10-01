"""Données des vidéos TikTok RushPlay : un seul JSON (contrat `rushplay-formats/SCHEMA.md`, v1).

    python -m app.tools.video_data --a-venir-du 2026-10-10 --a-venir-au 2026-10-12
    python -m app.tools.video_data --termines-du 2026-10-03 --termines-au 2026-10-05 --sortie bilan.json

Aucun calcul nouveau : la lecture vient du moteur du site (`reading_for`, `score_for`, `expected_total`).
Pour les matchs terminés, la lecture `avant` est refaite UNIQUEMENT avec les relevés pris avant le coup
d'envoi, comme le carnet `/track-record` ; un match sans relevé d'avant-match est absent (jamais de chiffre
inventé). Les probabilités sortent brutes (0..1) : l'arrondi et le format français sont faits par les modèles.
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.endpoints.matches import _paris_day_utc_bounds
from app.collectors.competitions import COMPETITIONS, FRENCH_BOOKMAKERS
from app.core.time import to_utc_iso
from app.engine.market import read
from app.engine.narrative import BOOK_LABELS
from app.engine.score import expected_total
from app.engine.types import BookQuote, Reading
from app.models.enums import MatchStatus
from app.models.match import Match
from app.services.market_reading import latest_totals_snapshot, reading_for, score_for

VERSION = 1
PARIS = ZoneInfo("Europe/Paris")
COMPETITIONS_PAR_DEFAUT = ("E0", "F1", "SP1", "I1", "D1", "CL", "EL")
ISSUES = {"home": "domicile", "draw": "nul", "away": "exterieur"}
NUL = "Match nul"


def _utc(dt: datetime) -> datetime:
    """SQLite rend des dates naïves (supposées UTC), Postgres des dates avec fuseau : on compare en UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _paris_iso(dt: datetime) -> str:
    return _utc(dt).astimezone(PARIS).isoformat()


def _issue_reelle(m: Match) -> str:
    if m.home_score > m.away_score:
        return "home"
    return "away" if m.away_score > m.home_score else "draw"


def _entete(m: Match) -> dict:
    return {
        "id": str(m.id), "competition": m.competition, "championnat": m.league,
        "domicile": m.home_team, "exterieur": m.away_team,
        "coup_envoi_utc": to_utc_iso(m.kickoff_at), "coup_envoi_paris": _paris_iso(m.kickoff_at),
    }


def _lecture(m: Match, r: Reading, totals_snapshot) -> dict:
    """chances / favori / score_probable / releve d'une lecture — commun à `a_venir` et à `termines.avant`."""
    equipe = {"home": m.home_team, "away": m.away_team, "draw": NUL}[r.favourite]
    d = score_for(m.competition, r, totals_snapshot)
    return {
        "chances": {"domicile": r.reference[0], "nul": r.reference[1], "exterieur": r.reference[2]},
        "favori": {"issue": ISSUES[r.favourite], "equipe": equipe, "proba": r.favourite_prob},
        "score_probable": {"score": d.top, "proba": d.top_probability} if d else None,
        "releve": to_utc_iso(r.last_taken_at),
    }


def _matchs(db: Session, statut: MatchStatus, du: date, au: date, competitions: tuple[str, ...]) -> list[Match]:
    debut, _ = _paris_day_utc_bounds(du)
    _, fin = _paris_day_utc_bounds(au)
    q = (select(Match)
         .where(Match.status == statut, Match.kickoff_at >= debut, Match.kickoff_at <= fin,
                Match.competition.in_(competitions))
         .options(selectinload(Match.snapshots), selectinload(Match.totals))
         .order_by(Match.kickoff_at.asc()))
    return list(db.scalars(q).unique().all())


def a_venir(db: Session, du: date, au: date, competitions: tuple[str, ...]) -> list[dict]:
    out = []
    for m in _matchs(db, MatchStatus.SCHEDULED, du, au, competitions):
        r = reading_for(m)   # lecture courante, comme la fiche du match
        if r is None:
            continue         # pas de relevé exploitable : rien à montrer, rien à inventer
        totals = latest_totals_snapshot(m.totals)
        item = _entete(m)
        lecture = _lecture(m, r, totals)
        cote = None
        if r.reference_source in r.latest_by_book:   # "moyenne" : pas de bookmaker de référence unique
            o = r.latest_by_book[r.reference_source]
            cote = {"bookmaker": BOOK_LABELS.get(r.reference_source, r.reference_source),
                    "domicile": o[0], "nul": o[1], "exterieur": o[2], "marge": r.margin_by_book[r.reference_source]}
        item.update({
            "chances": lecture["chances"], "favori": lecture["favori"], "score_probable": lecture["score_probable"],
            "buts_attendus": expected_total(m.competition, totals)[0],
            "cote_reference": cote,
            "releve": lecture["releve"],
        })
        out.append(item)
    return out


def lus_par_jour(db: Session, du: date, au: date) -> dict[str, int]:
    """Matchs à venir que le site sait lire, TOUTES compétitions, par jour (heure de Paris) : ce qui rend vrai
    « + 38 autres matchs du week-end sur rushplay.fr » à la fin des vidéos (01/10/2026). Même règle que
    `a_venir` : un match sans relevé exploitable n'est pas compté, le site n'en montre rien."""
    out: dict[str, int] = {}
    for m in _matchs(db, MatchStatus.SCHEDULED, du, au, tuple(COMPETITIONS)):
        if reading_for(m) is not None:
            j = _utc(m.kickoff_at).astimezone(PARIS).date().isoformat()
            out[j] = out.get(j, 0) + 1
    return out


def termines(db: Session, du: date, au: date, competitions: tuple[str, ...]) -> list[dict]:
    out = []
    for m in _matchs(db, MatchStatus.FINISHED, du, au, competitions):
        if m.home_score is None or m.away_score is None:
            continue
        coup_envoi = _utc(m.kickoff_at)
        # UNIQUEMENT les relevés pris avant le coup d'envoi (même règle que /track-record)
        quotes = [BookQuote(s.bookmaker, s.taken_at, (s.home, s.draw, s.away))
                  for s in m.snapshots if _utc(s.taken_at) <= coup_envoi]
        if not quotes:
            continue
        try:
            r = read(quotes, FRENCH_BOOKMAKERS)
        except ValueError:
            continue
        totals = latest_totals_snapshot([t for t in m.totals if _utc(t.taken_at) <= coup_envoi])
        item = _entete(m)
        item.update({
            "avant": _lecture(m, r, totals),
            "resultat": {"domicile": m.home_score, "exterieur": m.away_score},
            "favori_a_gagne": r.favourite == _issue_reelle(m),
        })
        out.append(item)
    return out


def build(db: Session, *, a_venir_du: date | None = None, a_venir_au: date | None = None,
          termines_du: date | None = None, termines_au: date | None = None,
          competitions: tuple[str, ...] = COMPETITIONS_PAR_DEFAUT, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    return {
        "version": VERSION,
        "genere_le": to_utc_iso(now.replace(microsecond=0)),
        "a_venir": a_venir(db, a_venir_du, a_venir_au, competitions) if a_venir_du else [],
        "lus_par_jour": lus_par_jour(db, a_venir_du, a_venir_au) if a_venir_du else {},
        "termines": termines(db, termines_du, termines_au, competitions) if termines_du else [],
    }


class ParametresInvalides(ValueError):
    """Paramètres refusés — mêmes règles pour la commande et pour la route `/api/v1/internal/video-data`."""


def jour(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ParametresInvalides(f"date attendue au format AAAA-MM-JJ, reçu « {s} »") from None


def valider(*, a_venir_du: date | None, a_venir_au: date | None, termines_du: date | None,
            termines_au: date | None, competitions: str, option=lambda nom: nom) -> tuple[str, ...]:
    """Contrôle les deux fenêtres et la liste de compétitions ; rend les codes normalisés.
    `option` met en forme le nom d'un paramètre dans le message (`--a-venir-du` pour la commande)."""
    bornes = {"a_venir": (a_venir_du, a_venir_au), "termines": (termines_du, termines_au)}
    for nom, (du, au) in bornes.items():
        o_du, o_au = option(f"{nom}_du"), option(f"{nom}_au")
        if (du is None) != (au is None):
            raise ParametresInvalides(f"{o_du} et {o_au} vont ensemble")
        if du and du > au:
            raise ParametresInvalides(f"{o_du} est après {o_au}")
    if a_venir_du is None and termines_du is None:
        raise ParametresInvalides(f"rien à produire : donner {option('a_venir_du')}/{option('a_venir_au')} "
                                  f"et/ou {option('termines_du')}/{option('termines_au')}")
    codes = tuple(c.strip().upper() for c in competitions.split(",") if c.strip())
    inconnus = [c for c in codes if c not in COMPETITIONS]
    if not codes or inconnus:
        raise ParametresInvalides(f"compétition inconnue : {', '.join(inconnus) or '(aucune)'} — "
                                  f"codes possibles : {', '.join(COMPETITIONS)}")
    return codes


def _jour(s: str) -> date:
    try:
        return jour(s)
    except ParametresInvalides as e:
        raise argparse.ArgumentTypeError(str(e))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.tools.video_data",
                                description="Données des vidéos RushPlay en un JSON (jours comptés en heure de Paris, bornes incluses).")
    p.add_argument("--a-venir-du", type=_jour, metavar="AAAA-MM-JJ")
    p.add_argument("--a-venir-au", type=_jour, metavar="AAAA-MM-JJ")
    p.add_argument("--termines-du", type=_jour, metavar="AAAA-MM-JJ")
    p.add_argument("--termines-au", type=_jour, metavar="AAAA-MM-JJ")
    p.add_argument("--competitions", default=",".join(COMPETITIONS_PAR_DEFAUT),
                   help=f"codes séparés par des virgules (défaut : {','.join(COMPETITIONS_PAR_DEFAUT)})")
    p.add_argument("--sortie", metavar="FICHIER", help="fichier JSON à écrire (défaut : sortie standard)")
    return p


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    p = _parser()
    a = p.parse_args(argv)
    try:
        a.competitions = valider(a_venir_du=a.a_venir_du, a_venir_au=a.a_venir_au, termines_du=a.termines_du,
                                 termines_au=a.termines_au, competitions=a.competitions,
                                 option=lambda nom: "--" + nom.replace("_", "-"))
    except ParametresInvalides as e:
        p.error(str(e))
    return a


def main(argv: list[str] | None = None, session_factory=None) -> int:
    a = _arguments(argv)
    if session_factory is None:
        from app.core.database import SessionLocal
        session_factory = SessionLocal
    db = session_factory()
    try:
        data = build(db, a_venir_du=a.a_venir_du, a_venir_au=a.a_venir_au,
                     termines_du=a.termines_du, termines_au=a.termines_au, competitions=a.competitions)
    finally:
        db.close()
    texte = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if a.sortie:
        with open(a.sortie, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
        print(f"{len(data['a_venir'])} à venir, {len(data['termines'])} terminés -> {a.sortie}", file=sys.stderr)
    else:
        # octets UTF-8 quel que soit l'encodage de la console (Windows : cp1252)
        sys.stdout.buffer.write(texte.encode("utf-8"))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
