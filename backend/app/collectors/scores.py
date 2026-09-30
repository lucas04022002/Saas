"""The Odds API, endpoint /scores : résultats des compétitions à cotes live qu'aucune source gratuite ne couvre.

Le trou constaté le 30/09/2026 : les matchs de Ligue des Nations joués du 24 au 29/09 restaient SCHEDULED,
sans score — ni football-data.co.uk ni le plan gratuit de football-data.org ne donnent leurs résultats (même
régime pour la Ligue Europa). Sans résultat : pas de carnet (/track-record), pas de bilan vidéo.

Doc officielle (https://the-odds-api.com/liveapi/guides/v4/, relue le 30/09/2026) :
`GET /v4/sports/{sport}/scores/?apiKey=…&daysFrom=3&dateFormat=iso` — `daysFrom` de 1 à 3 ; sans lui, seuls les
matchs en cours et à venir sont rendus (aucun terminé). Coût : 2 crédits avec `daysFrom`, 1 sans. Les scores
sont des CHAÎNES (« "2" »), `scores` vaut null tant que le match n'a pas commencé.

Règles : on n'appelle l'API que pour une compétition qui a en base un match au coup d'envoi passé (dans la
fenêtre de `daysFrom`) encore sans score ; un événement inconnu est journalisé, jamais transformé en match ; un
score déjà en base n'est jamais écrasé (un désaccord est journalisé et compté)."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS, Competition, by_odds_api_key
from app.collectors.dedup import find_existing
from app.collectors.odds_api import BASE
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match

log = logging.getLogger("rushplay.collectors.scores")
DAYS_FROM = 3                               # maximum accepté par l'API ; 2 crédits quelle que soit la valeur
CREDITS_PER_CALL = 2
MIN_MATCH_DURATION = timedelta(hours=2)     # un coup d'envoi il y a moins de 2 h : le match n'est pas fini, inutile de payer
PENDING_STATUSES = (MatchStatus.SCHEDULED, MatchStatus.LIVE)


def competitions_sans_resultats() -> list[Competition]:
    """Compétitions à cotes live (clé Odds API) dont aucune source gratuite ne donne les résultats : pas de
    code football-data.co.uk, et pas de calendrier football-data.org gratuit. Déduit de COMPETITIONS (EL et NL
    aujourd'hui) : une compétition ajoutée dans ce régime est couverte sans toucher à ce fichier."""
    return [c for c in COMPETITIONS.values()
            if c.odds_api_key is not None and c.fd_uk_code is None and not (c.fd_org_free and c.fd_org_code)]


@dataclass
class ScoreEvent:
    event_id: str
    competition_code: str
    commence: datetime
    home: str
    away: str
    home_score: int
    away_score: int


@dataclass
class ScoresReport:
    calls: int = 0              # appels HTTP réellement faits
    credits: int = 0            # crédits consommés (2 par appel)
    finished: int = 0           # matchs passés FINISHED avec leur score
    already: int = 0            # score déjà en base, identique
    conflicts: int = 0          # score déjà en base, DIFFÉRENT : laissé tel quel et journalisé
    unmatched: int = 0          # équipes connues mais aucun match en base : rien créé
    quarantined: int = 0        # nom d'équipe inconnu : rien créé
    not_completed: int = 0      # événements rendus mais pas terminés (à venir, en cours)
    invalid: int = 0            # événements terminés au score illisible
    skipped: list[str] = field(default_factory=list)   # compétitions sans match en attente : aucun appel
    fetched: list[str] = field(default_factory=list)


def pending_matches(db: Session, competition: str, now: datetime) -> list[Match]:
    """Matchs de la compétition au coup d'envoi passé d'au moins 2 h et d'au plus `DAYS_FROM` jours (ce que
    l'API peut encore rendre), toujours sans score. Au-delà de 3 jours, l'API ne sait plus rien : inutile de payer."""
    lo, hi = now - timedelta(days=DAYS_FROM), now - MIN_MATCH_DURATION
    return list(db.scalars(
        select(Match).where(Match.competition == competition, Match.status.in_(PENDING_STATUSES),
                            Match.home_score.is_(None), Match.kickoff_at >= lo, Match.kickoff_at <= hi)
    ).all())


def _score(value) -> int | None:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def parse_scores(sport_key: str, payload: list, report: ScoresReport | None = None) -> list[ScoreEvent]:
    """Garde les événements `completed: true` dont les deux scores se lisent ; compte le reste dans `report`."""
    report = report if report is not None else ScoresReport()
    comp = by_odds_api_key(sport_key)
    if comp is None:
        return []
    out = []
    for e in payload:
        if not e.get("completed"):
            report.not_completed += 1
            continue
        try:
            home, away = e["home_team"], e["away_team"]
            by_name = {s["name"]: _score(s.get("score")) for s in (e.get("scores") or [])}
            hg, ag = by_name.get(home), by_name.get(away)
            if hg is None or ag is None:
                raise ValueError(f"scores illisibles : {e.get('scores')!r}")
            out.append(ScoreEvent(event_id=str(e.get("id")), competition_code=comp.code,
                                  commence=datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")),
                                  home=home, away=away, home_score=hg, away_score=ag))
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("scores %s : événement %s ignoré : %s", sport_key, e.get("id"), exc)
            report.invalid += 1
    return out


def store_scores(db: Session, events: list[ScoreEvent], report: ScoresReport | None = None) -> ScoresReport:
    report = report if report is not None else ScoresReport()
    for ev in events:
        label = f"{ev.competition_code} {ev.home} v {ev.away} ({ev.commence.isoformat()})"
        try:
            home, away = resolve_team(db, "odds_api", ev.home), resolve_team(db, "odds_api", ev.away)
        except TeamAliasError as e:
            db.rollback()
            log.warning("quarantaine scores %s : %s — aucun match créé", label, e)
            report.quarantined += 1
            continue
        match = find_existing(db, ev.competition_code, home.id, away.id, ev.commence)
        if match is None:
            db.commit()   # garde l'éventuel alias appris par le repli de resolve_team
            log.warning("scores : aucun match en base pour %s — rien créé", label)
            report.unmatched += 1
            continue
        if match.home_score is not None or match.away_score is not None:
            if (match.home_score, match.away_score) == (ev.home_score, ev.away_score):
                if match.status != MatchStatus.FINISHED:
                    match.status = MatchStatus.FINISHED
                report.already += 1
            else:
                log.warning("scores : conflit pour %s — en base %s-%s, Odds API %s-%s ; score en base conservé",
                            label, match.home_score, match.away_score, ev.home_score, ev.away_score)
                report.conflicts += 1
            db.commit()
            continue
        match.home_score, match.away_score = ev.home_score, ev.away_score
        match.status = MatchStatus.FINISHED
        db.commit()
        log.info("scores : %s %s-%s", label, ev.home_score, ev.away_score)
        report.finished += 1
    return report


def fetch_scores(sport_key: str) -> tuple[list, str | None]:
    """2 crédits (daysFrom présent). Rend aussi les matchs à venir et en cours (scores null / completed false)."""
    resp = requests.get(f"{BASE}/{sport_key}/scores/",
                        params={"apiKey": settings.the_odds_api_key, "daysFrom": DAYS_FROM, "dateFormat": "iso"}, timeout=30)
    resp.raise_for_status()
    return resp.json(), resp.headers.get("x-requests-remaining")


def run(db: Session, now: datetime | None = None) -> ScoresReport:
    """Un appel (2 crédits) par compétition sans source de résultats, et seulement si elle a des matchs en attente."""
    now = now or datetime.now(timezone.utc)
    report = ScoresReport()
    for comp in competitions_sans_resultats():
        pending = pending_matches(db, comp.code, now)
        if not pending:
            report.skipped.append(comp.code)
            continue
        try:
            payload, remaining = fetch_scores(comp.odds_api_key)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                log.error("scores : quota épuisé ou clé invalide, arrêt propre")
                break
            raise
        report.calls += 1
        report.credits += CREDITS_PER_CALL
        report.fetched.append(comp.code)
        store_scores(db, parse_scores(comp.odds_api_key, payload, report), report)
        log.info("scores %s : %s match(s) en attente, %s événement(s) rendus, crédits restants %s",
                 comp.code, len(pending), len(payload), remaining)
    log.info("scores : %s", report)
    return report
