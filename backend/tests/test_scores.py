"""Collecteur de résultats via The Odds API /scores (30/09/2026) : Ligue des Nations et Ligue Europa n'ont aucune
source gratuite de résultats ; leurs matchs restaient SCHEDULED, hors du carnet et du bilan vidéo."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

import app.collectors.scores as scores
from app.collectors import run as run_cli
from app.collectors.aliases import seed_aliases
from app.collectors.scores import competitions_sans_resultats, parse_scores, pending_matches, store_scores
from app.main import STALE_AFTER
from app.models.bet import Bet
from app.models.collector_heartbeat import CollectorHeartbeat
from app.models.enums import BetStatus, MatchStatus, Outcome
from app.models.match import Match
from app.models.team import Team
from tests.conftest import make_match, make_user

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "odds_api_scores_nations_league.json").read_text(encoding="utf-8"))
NL = "soccer_uefa_nations_league"
NOW = datetime(2026, 9, 30, 7, 30, tzinfo=timezone.utc)


def _team(db, name):
    return db.query(Team).filter_by(name=name).one()


def _nl_match(db, home, away, kickoff, **kw):
    return make_match(db, _team(db, home), _team(db, away), competition="NL", kickoff=kickoff, **kw)


def _no_http(*a, **k):
    raise AssertionError("aucun appel HTTP attendu")


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.headers = payload, status, {"x-requests-remaining": "88"}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def test_competitions_couvertes_sont_deduites_de_competitions():
    """Cotes live sans fd_uk ni calendrier fd_org gratuit : Ligue Europa et Ligue des Nations, pas la LdC (fd_org gratuit)."""
    codes = {c.code for c in competitions_sans_resultats()}
    assert codes == {"EL", "NL"}


def test_parse_garde_les_termines_et_lit_les_scores_chaines():
    report = scores.ScoresReport()
    events = parse_scores(NL, PAYLOAD, report)
    assert [(e.home, e.away, e.home_score, e.away_score) for e in events] == [
        ("Germany", "Netherlands", 2, 1), ("England", "Denmark", 0, 0), ("Bosnia and Herzegovina", "Croatia", 1, 3)]
    assert report.not_completed == 2   # Écosse-Grèce pas encore marqué terminé, Italie-Norvège à venir (scores null)
    assert all(e.competition_code == "NL" for e in events)


def test_parse_ecarte_un_score_illisible():
    bad = [{**PAYLOAD[0], "scores": [{"name": "Germany", "score": "2"}]}]   # score de l'extérieur absent
    report = scores.ScoresReport()
    assert parse_scores(NL, bad, report) == [] and report.invalid == 1


def test_score_ecrit_et_match_termine(db):
    seed_aliases(db)
    m = _nl_match(db, "Allemagne", "Pays-Bas", datetime(2026, 9, 28, 18, 45, tzinfo=timezone.utc))
    report = store_scores(db, parse_scores(NL, PAYLOAD))
    db.refresh(m)
    assert (m.home_score, m.away_score, m.status) == (2, 1, MatchStatus.FINISHED)
    assert report.finished == 1


def test_match_non_termine_ignore(db):
    seed_aliases(db)
    m = _nl_match(db, "Écosse", "Grèce", datetime(2026, 9, 29, 18, 45, tzinfo=timezone.utc))
    store_scores(db, parse_scores(NL, PAYLOAD))
    db.refresh(m)
    assert (m.home_score, m.away_score, m.status) == (None, None, MatchStatus.SCHEDULED)


def test_nom_inconnu_ou_match_absent_ne_cree_aucun_match(db):
    """« Bosnia and Herzegovina » n'est pas un alias connu (le relevé de cotes écrit « Bosnia & Herzegovina ») :
    quarantaine journalisée. Allemagne-Pays-Bas et Angleterre-Danemark sont connus mais absents de la base."""
    seed_aliases(db)
    report = store_scores(db, parse_scores(NL, PAYLOAD))
    assert db.query(Match).count() == 0
    assert (report.quarantined, report.unmatched, report.finished) == (1, 2, 0)


def test_pas_d_ecrasement_silencieux(db, caplog):
    seed_aliases(db)
    m = _nl_match(db, "Angleterre", "Danemark", datetime(2026, 9, 29, 18, 45, tzinfo=timezone.utc),
                  status=MatchStatus.FINISHED, home_score=1, away_score=0)
    with caplog.at_level("WARNING", logger="rushplay.collectors.scores"):
        report = store_scores(db, parse_scores(NL, PAYLOAD))
    db.refresh(m)
    assert (m.home_score, m.away_score) == (1, 0)   # le score en base est conservé
    assert report.conflicts == 1
    assert any("conflit" in r.message and "1-0" in r.message and "0-0" in r.message for r in caplog.records)


def test_meme_score_deja_en_base_n_est_pas_un_conflit(db):
    seed_aliases(db)
    _nl_match(db, "Angleterre", "Danemark", datetime(2026, 9, 29, 18, 45, tzinfo=timezone.utc),
              status=MatchStatus.FINISHED, home_score=0, away_score=0)
    report = store_scores(db, parse_scores(NL, PAYLOAD))
    assert (report.already, report.conflicts) == (1, 0)


def test_en_attente_seulement_dans_la_fenetre_de_l_api(db):
    seed_aliases(db)
    ok = _nl_match(db, "Allemagne", "Pays-Bas", datetime(2026, 9, 28, 18, 45, tzinfo=timezone.utc))
    _nl_match(db, "France", "Italie", datetime(2026, 9, 25, 18, 45, tzinfo=timezone.utc))        # > 3 jours : hors de portée
    _nl_match(db, "Espagne", "Suisse", datetime(2026, 9, 30, 6, 30, tzinfo=timezone.utc))       # il y a 1 h : pas fini
    _nl_match(db, "Suède", "Pologne", datetime(2026, 9, 29, 18, 45, tzinfo=timezone.utc),
              status=MatchStatus.FINISHED, home_score=2, away_score=2)                           # déjà réglé
    assert [m.id for m in pending_matches(db, "NL", NOW)] == [ok.id]


def test_aucun_appel_http_sans_match_en_attente(db, monkeypatch):
    seed_aliases(db)
    _nl_match(db, "Allemagne", "Pays-Bas", datetime(2026, 10, 9, 18, 45, tzinfo=timezone.utc))   # à venir
    monkeypatch.setattr(scores.requests, "get", _no_http)
    report = scores.run(db, now=NOW)
    assert (report.calls, report.credits) == (0, 0)
    assert sorted(report.skipped) == ["EL", "NL"]


def test_run_appelle_seulement_la_competition_en_attente(db, monkeypatch):
    seed_aliases(db)
    m = _nl_match(db, "Allemagne", "Pays-Bas", datetime(2026, 9, 28, 18, 45, tzinfo=timezone.utc))
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params))
        return _Resp(PAYLOAD)

    monkeypatch.setattr(scores.requests, "get", fake_get)
    report = scores.run(db, now=NOW)
    assert len(calls) == 1
    url, params = calls[0]
    assert url.endswith(f"/{NL}/scores/") and params["daysFrom"] == 3 and params["dateFormat"] == "iso"
    assert (report.calls, report.credits, report.fetched, report.skipped) == (1, 2, ["NL"], ["EL"])
    db.refresh(m)
    assert (m.home_score, m.away_score, m.status) == (2, 1, MatchStatus.FINISHED)


def test_run_s_arrete_proprement_sur_401(db, monkeypatch):
    seed_aliases(db)
    _nl_match(db, "Allemagne", "Pays-Bas", datetime(2026, 9, 28, 18, 45, tzinfo=timezone.utc))
    monkeypatch.setattr(scores.requests, "get", lambda *a, **k: _Resp({"message": "quota"}, status=401))
    report = scores.run(db, now=NOW)
    assert report.calls == 0


def test_cli_scores_ecrit_le_battement_et_regle_les_paris(db, monkeypatch):
    monkeypatch.setattr(run_cli, "get_db", lambda: iter([db]))
    monkeypatch.setattr(scores.requests, "get", lambda *a, **k: _Resp(PAYLOAD))
    real_run = scores.run
    monkeypatch.setattr(run_cli.scores, "run", lambda db: real_run(db, now=NOW))
    seed_aliases(db)
    m = _nl_match(db, "Allemagne", "Pays-Bas", datetime(2026, 9, 28, 18, 45, tzinfo=timezone.utc))
    user = make_user(db)
    db.add(Bet(user_id=user.id, match_id=m.id, outcome=Outcome.HOME, bookmaker="betclic_fr", odds=2.1, stake=10.0)); db.commit()

    assert run_cli.main(["scores"]) == 0

    hb = db.get(CollectorHeartbeat, "scores")
    assert hb is not None
    summary = json.loads(hb.summary)
    assert summary["finished"] == 1 and summary["credits"] == 2 and summary["bets_settled"] == 1
    assert db.query(Bet).one().status == BetStatus.WON


def test_health_suit_le_battement_scores(client, db):
    assert "scores" in STALE_AFTER
    assert client.get("/health").json()["data"]["collectors"]["scores"] == {"at": None, "stale": True}
    run_cli.write_heartbeat(db, "scores", {"calls": 0})
    assert client.get("/health").json()["data"]["collectors"]["scores"]["stale"] is False


@pytest.mark.parametrize("line", ["30 7 * * 1,3,5   cd /app && python -m app.collectors.run scores"])
def test_crontab_planifie_les_scores(line):
    crontab = (Path(__file__).resolve().parents[2] / "deploy" / "crontab.txt").read_text(encoding="utf-8")
    assert line in crontab
