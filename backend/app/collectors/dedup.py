"""Déduplication entre sources : fd_uk, fd_org et odds_api peuvent chacun créer un match avant que leurs
identifiants respectifs (fd_uk_key, external_id) ne soient rapprochés. `find_existing` sert de garde à la
création dans chaque importeur (avant de créer, on cherche un match déjà posé par une autre source, à coup
d'envoi proche). `merge_matches` fusionne deux lignes qui désignent le même match (utilisé à la fois par les
importeurs, quand la sortie de quarantaine entre en conflit d'unicité avec un match déjà résolu par une autre
source, et par la commande CLI `dedup`). `dedup_matches` nettoie après coup les doublons déjà en base."""
import logging
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bet import Bet
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot

log = logging.getLogger("rushplay.collectors.dedup")
DEFAULT_WINDOW_HOURS = 36


def find_existing(db: Session, competition: str, home_id, away_id, kickoff, window_hours: int = DEFAULT_WINDOW_HOURS) -> Match | None:
    """Match non-quarantaine déjà en base pour cette compétition et ces équipes, à coup d'envoi à moins de
    `window_hours` heures de `kickoff`. Sert à retrouver, avant de créer, un match déjà posé par une autre
    source dont les identifiants n'ont pas encore été rapprochés."""
    if home_id is None or away_id is None:
        return None
    lo, hi = kickoff - timedelta(hours=window_hours), kickoff + timedelta(hours=window_hours)
    return db.scalar(
        select(Match)
        .where(Match.competition == competition, Match.home_team_id == home_id, Match.away_team_id == away_id,
               Match.kickoff_at >= lo, Match.kickoff_at <= hi, Match.status != MatchStatus.QUARANTINE)
        .order_by(Match.kickoff_at.asc())
    )


def merge_matches(db: Session, keep: Match, remove: Match) -> None:
    """Fusionne `remove` dans `keep` : déplace les relevés de cotes et les paris de `remove` vers `keep`
    (abandonne un relevé s'il ferait doublon avec un relevé déjà présent sur `keep`, même bookmaker/taken_at),
    recopie external_id/fd_uk_key manquants sur `keep`, puis supprime `remove`. `keep` et `remove` doivent déjà
    être flush/persistés (ids assignés) ; ne commit pas — laisse l'appelant décider."""
    for snap in list(db.scalars(select(OddsSnapshot).where(OddsSnapshot.match_id == remove.id))):
        conflict = db.scalar(select(OddsSnapshot.id).where(
            OddsSnapshot.match_id == keep.id, OddsSnapshot.bookmaker == snap.bookmaker, OddsSnapshot.taken_at == snap.taken_at))
        if conflict:
            db.delete(snap)
        else:
            snap.match_id = keep.id
    for bet in db.scalars(select(Bet).where(Bet.match_id == remove.id)):
        bet.match_id = keep.id
    # external_id/fd_uk_key sont uniques : vider la valeur sur `remove` et la poser sur `keep` dans le même flush
    # échoue (la contrainte n'est pas différée — SQLite comme Postgres la vérifient ligne par ligne dans le lot),
    # même si le résultat final ne collisionne pas. On vide et flush `remove` d'abord, puis on pose sur `keep`.
    take_external_id = remove.external_id if not keep.external_id and remove.external_id else None
    take_fd_uk_key = remove.fd_uk_key if not keep.fd_uk_key and remove.fd_uk_key else None
    if take_external_id:
        remove.external_id = None
    if take_fd_uk_key:
        remove.fd_uk_key = None
    if take_external_id or take_fd_uk_key:
        db.flush()
    if take_external_id:
        keep.external_id = take_external_id
    if take_fd_uk_key:
        keep.fd_uk_key = take_fd_uk_key
    db.flush()
    db.delete(remove)
    db.flush()


@dataclass
class DedupReport:
    groups: int = 0
    removed: int = 0

    def __str__(self) -> str:
        return f"{self.groups} groupe(s) de doublons, {self.removed} match(s) fusionné(s)/supprimé(s)"


def _pick_survivor(cluster: list[Match]) -> Match:
    """external_id (fd_org, calendrier UTC faisant autorité) d'abord, sinon fd_uk_key, sinon le plus ancien créé."""
    with_ext = [m for m in cluster if m.external_id]
    if with_ext:
        return min(with_ext, key=lambda m: m.created_at)
    with_key = [m for m in cluster if m.fd_uk_key]
    if with_key:
        return min(with_key, key=lambda m: m.created_at)
    return min(cluster, key=lambda m: m.created_at)


def dedup_matches(db: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> DedupReport:
    """Scanne les matchs SCHEDULED/QUARANTINE dont les équipes sont résolues, les regroupe par (compétition,
    équipe domicile, équipe extérieur) à coup d'envoi mutuellement à moins de `window_hours` heures, garde un
    survivant par groupe (cf. `_pick_survivor`) et fusionne les autres dedans via `merge_matches`. Fonction pure
    (aucun appel réseau) ; commit à la fin."""
    report = DedupReport()
    rows = list(db.scalars(
        select(Match).where(Match.status.in_((MatchStatus.SCHEDULED, MatchStatus.QUARANTINE)),
                            Match.home_team_id.is_not(None), Match.away_team_id.is_not(None))
        .order_by(Match.kickoff_at.asc())
    ).all())
    seen: set = set()
    for m in rows:
        if m.id in seen:
            continue
        cluster = [m]
        for other in rows:
            if other.id == m.id or other.id in seen:
                continue
            if other.competition != m.competition or other.home_team_id != m.home_team_id or other.away_team_id != m.away_team_id:
                continue
            if abs(other.kickoff_at - m.kickoff_at) <= timedelta(hours=window_hours):
                cluster.append(other)
        for c in cluster:
            seen.add(c.id)
        if len(cluster) < 2:
            continue
        survivor = _pick_survivor(cluster)
        for dup in cluster:
            if dup.id == survivor.id:
                continue
            merge_matches(db, survivor, dup)
            report.removed += 1
        report.groups += 1
    db.commit()
    log.info("dedup : %s", report)
    return report
