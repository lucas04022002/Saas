"""`python -m app.tools.video_data` : le JSON des vidéos TikTok (contrat rushplay-formats/SCHEMA.md, v1)."""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.totals_snapshot import TotalsSnapshot
from app.tools import video_data
from app.tools.video_data import build, main
from tests.conftest import make_match, make_team

SAMEDI = date(2026, 10, 10)
KICK = datetime(2026, 10, 10, 18, 45, tzinfo=timezone.utc)   # 20:45 à Paris (CEST)

CLES_A_VENIR = ["id", "competition", "championnat", "domicile", "exterieur", "coup_envoi_utc", "coup_envoi_paris",
                "chances", "favori", "score_probable", "buts_attendus", "cote_reference", "releve"]
CLES_TERMINE = ["id", "competition", "championnat", "domicile", "exterieur", "coup_envoi_utc", "coup_envoi_paris",
                "avant", "resultat", "favori_a_gagne"]


@pytest.fixture
def equipes(db):
    return make_team(db, "Paris Saint-Germain"), make_team(db, "Le Mans FC")


def cotes(db, m, odds, taken_at, bookmaker="pinnacle"):
    db.add(OddsSnapshot(match_id=m.id, bookmaker=bookmaker, taken_at=taken_at, home=odds[0], draw=odds[1], away=odds[2]))
    db.commit()


def a_venir(db, du=SAMEDI, au=SAMEDI, competitions=("E0",)):
    return build(db, a_venir_du=du, a_venir_au=au, competitions=competitions)["a_venir"]


def termines(db, du=SAMEDI, au=SAMEDI, competitions=("E0",)):
    return build(db, termines_du=du, termines_au=au, competitions=competitions)["termines"]


def fini(db, h, a, hg, ag, odds=(1.50, 4.20, 6.50), kick=KICK, **kw):
    m = make_match(db, h, a, kickoff=kick, status=MatchStatus.FINISHED, home_score=hg, away_score=ag, **kw)
    cotes(db, m, odds, kick - timedelta(hours=2))
    return m


# --- format ---------------------------------------------------------------------------------------------------

def test_a_venir_format_conforme_au_schema(db, equipes):
    h, a = equipes
    m = make_match(db, h, a, kickoff=KICK)
    cotes(db, m, (1.09, 11.79, 18.03), datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc))
    cotes(db, m, (1.08, 12.0, 19.0), datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc), bookmaker="betclic_fr")
    data = build(db, a_venir_du=SAMEDI, a_venir_au=SAMEDI, competitions=("E0",), now=datetime(2026, 10, 9, 8, 5, 0, 123, tzinfo=timezone.utc))
    assert list(data) == ["version", "genere_le", "a_venir", "lus_par_jour", "termines"]
    assert data["version"] == 1 and data["genere_le"] == "2026-10-09T08:05:00Z" and data["termines"] == []
    [it] = data["a_venir"]
    assert list(it) == CLES_A_VENIR
    assert it["id"] == str(m.id) and it["competition"] == "E0" and it["championnat"] == "Premier League"
    assert (it["domicile"], it["exterieur"]) == ("Paris Saint-Germain", "Le Mans FC")
    assert it["coup_envoi_utc"] == "2026-10-10T18:45:00Z"
    assert it["coup_envoi_paris"] == "2026-10-10T20:45:00+02:00"
    assert list(it["chances"]) == ["domicile", "nul", "exterieur"]
    assert sum(it["chances"].values()) == pytest.approx(1.0)
    assert it["chances"]["domicile"] == pytest.approx((1 / 1.09) / (1 / 1.09 + 1 / 11.79 + 1 / 18.03))
    assert it["favori"] == {"issue": "domicile", "equipe": "Paris Saint-Germain", "proba": it["chances"]["domicile"]}
    assert set(it["score_probable"]) == {"score", "proba"}
    buts_dom, buts_ext = (int(x) for x in it["score_probable"]["score"].split("-"))
    assert buts_dom > buts_ext                     # score cohérent avec le favori
    assert 0 < it["score_probable"]["proba"] < 1
    assert it["buts_attendus"] == 2.75            # pas de relevé over/under : repli sur la ligue
    ref = it["cote_reference"]
    assert (ref["bookmaker"], ref["domicile"], ref["nul"], ref["exterieur"]) == ("Pinnacle", 1.09, 11.79, 18.03)
    assert ref["marge"] == pytest.approx(1 / 1.09 + 1 / 11.79 + 1 / 18.03 - 1)
    assert it["releve"] == "2026-09-28T08:00:00Z"


def test_a_venir_buts_attendus_du_marche_et_heure_d_hiver(db, equipes):
    h, a = equipes
    hiver = datetime(2026, 11, 7, 20, 0, tzinfo=timezone.utc)
    m = make_match(db, h, a, kickoff=hiver)
    cotes(db, m, (2.0, 3.5, 3.8), hiver - timedelta(days=1))
    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=hiver - timedelta(days=1), line=2.5, over=1.30, under=3.55))
    db.commit()
    [it] = a_venir(db, date(2026, 11, 7), date(2026, 11, 7))
    assert it["coup_envoi_paris"] == "2026-11-07T21:00:00+01:00"
    assert it["buts_attendus"] > 3.0              # marché très incliné vers l'over


def test_a_venir_sans_releve_ou_statut_different_absent(db, equipes):
    h, a = equipes
    make_match(db, h, a, kickoff=KICK)                                    # aucun relevé
    reporte = make_match(db, a, h, kickoff=KICK, status=MatchStatus.POSTPONED)
    cotes(db, reporte, (2.0, 3.5, 3.8), KICK - timedelta(days=1))
    assert a_venir(db) == []


def test_termine_format_conforme_au_schema(db, equipes):
    h, a = equipes
    m = fini(db, a, h, 1, 2, odds=(5.0, 4.2, 1.6))
    [it] = termines(db)
    assert list(it) == CLES_TERMINE
    assert it["id"] == str(m.id) and it["coup_envoi_paris"] == "2026-10-10T20:45:00+02:00"
    assert list(it["avant"]) == ["chances", "favori", "score_probable", "releve"]
    assert it["avant"]["favori"]["issue"] == "exterieur" and it["avant"]["favori"]["equipe"] == "Paris Saint-Germain"
    assert it["avant"]["releve"] == "2026-10-10T16:45:00Z"
    assert it["resultat"] == {"domicile": 1, "exterieur": 2}
    assert it["favori_a_gagne"] is True


# --- fenêtre de dates en heure de Paris -------------------------------------------------------------------------

def test_fenetre_comptee_en_heure_de_paris_bornes_incluses(db, equipes):
    h, a = equipes
    # 21:30 UTC le 9 = 23:30 le 9 à Paris : dehors ; 22:30 UTC le 9 = 00:30 le 10 : dedans
    # 21:30 UTC le 11 = 23:30 le 11 à Paris : dedans (borne haute incluse) ; 22:30 UTC le 11 = 00:30 le 12 : dehors
    instants = [datetime(2026, 10, 9, 21, 30), datetime(2026, 10, 9, 22, 30), datetime(2026, 10, 11, 21, 30), datetime(2026, 10, 11, 22, 30)]
    for t in instants:
        t = t.replace(tzinfo=timezone.utc)
        m = make_match(db, h, a, kickoff=t)
        cotes(db, m, (1.5, 4.2, 6.5), t - timedelta(days=1))
    items = a_venir(db, date(2026, 10, 10), date(2026, 10, 11))
    assert [i["coup_envoi_paris"] for i in items] == ["2026-10-10T00:30:00+02:00", "2026-10-11T23:30:00+02:00"]


# --- avant = uniquement les relevés d'avant coup d'envoi --------------------------------------------------------

def test_avant_ignore_tout_releve_posterieur_au_coup_d_envoi(db, equipes):
    h, a = equipes
    m = fini(db, h, a, 2, 0, odds=(1.50, 4.20, 6.50))
    cotes(db, m, (9.0, 9.0, 1.1), KICK + timedelta(hours=1))             # relevé en direct, favori inversé
    cotes(db, m, (9.0, 9.0, 1.1), KICK + timedelta(hours=1), bookmaker="betclic_fr")
    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=KICK + timedelta(minutes=30), line=2.5, over=1.01, under=50.0))
    db.commit()
    [it] = termines(db)
    av = it["avant"]
    assert av["releve"] == "2026-10-10T16:45:00Z"
    assert av["chances"]["domicile"] == pytest.approx((1 / 1.5) / (1 / 1.5 + 1 / 4.2 + 1 / 6.5))
    assert av["favori"]["issue"] == "domicile"
    assert av["score_probable"]["score"] == "1-0"                        # repli ligue, pas le total d'après-match
    assert it["favori_a_gagne"] is True


def test_termine_sans_releve_avant_coup_d_envoi_absent(db, equipes):
    h, a = equipes
    m = make_match(db, h, a, kickoff=KICK, status=MatchStatus.FINISHED, home_score=1, away_score=0)
    cotes(db, m, (1.5, 4.2, 6.5), KICK + timedelta(minutes=10))           # seulement après le coup d'envoi
    make_match(db, a, h, kickoff=KICK, status=MatchStatus.FINISHED, home_score=0, away_score=0)   # aucun relevé
    assert termines(db) == []


def test_termine_sans_score_ou_a_venir_absent(db, equipes):
    h, a = equipes
    m = make_match(db, h, a, kickoff=KICK, status=MatchStatus.FINISHED)
    cotes(db, m, (1.5, 4.2, 6.5), KICK - timedelta(hours=1))
    p = make_match(db, a, h, kickoff=KICK)
    cotes(db, p, (1.5, 4.2, 6.5), KICK - timedelta(hours=1))
    assert termines(db) == []


@pytest.mark.parametrize("score, attendu", [((2, 0), True), ((0, 1), False), ((1, 1), False)])
def test_favori_a_gagne_victoire_defaite_nul(db, equipes, score, attendu):
    h, a = equipes
    fini(db, h, a, *score, odds=(1.50, 4.20, 6.50))                       # favori domicile
    [it] = termines(db)
    assert it["favori_a_gagne"] is attendu


def test_favori_nul_gagne_sur_un_nul(db, equipes):
    h, a = equipes
    fini(db, h, a, 0, 0, odds=(3.6, 2.4, 3.6))                            # le nul est le favori
    [it] = termines(db)
    assert it["avant"]["favori"] == {"issue": "nul", "equipe": "Match nul", "proba": it["avant"]["chances"]["nul"]}
    assert it["favori_a_gagne"] is True


# --- filtre de compétitions ---------------------------------------------------------------------------------------

def test_filtre_de_competitions(db, equipes):
    h, a = equipes
    for code in ("E0", "F1", "N1"):
        m = make_match(db, h, a, kickoff=KICK, competition=code)
        cotes(db, m, (1.5, 4.2, 6.5), KICK - timedelta(days=1))
        fini(db, a, h, 1, 0, competition=code)
    assert [i["competition"] for i in a_venir(db, competitions=("E0", "F1"))] == ["E0", "F1"] or \
        sorted(i["competition"] for i in a_venir(db, competitions=("E0", "F1"))) == ["E0", "F1"]
    assert sorted(i["competition"] for i in termines(db, competitions=("N1",))) == ["N1"]
    assert "N1" not in video_data.COMPETITIONS_PAR_DEFAUT


def test_competitions_par_defaut_de_la_commande(db, equipes, capsys):
    h, a = equipes
    for code in ("F1", "N1"):
        m = make_match(db, h, a, kickoff=KICK, competition=code)
        cotes(db, m, (1.5, 4.2, 6.5), KICK - timedelta(days=1))
    main(["--a-venir-du", "2026-10-10", "--a-venir-au", "2026-10-10"], session_factory=lambda: db)
    data = json.loads(capsys.readouterr().out)
    assert [i["competition"] for i in data["a_venir"]] == ["F1"]


# --- sortie ---------------------------------------------------------------------------------------------------------

def test_sortie_standard_json_utf8(db, capsysbinary):
    h, a = make_team(db, "Saint-Étienne"), make_team(db, "Nîmes Olympique")
    m = make_match(db, h, a, kickoff=KICK, competition="F1")
    cotes(db, m, (2.1, 3.3, 3.6), KICK - timedelta(days=1))
    fini(db, a, h, 0, 3, competition="F1")
    assert main(["--a-venir-du", "2026-10-10", "--a-venir-au", "2026-10-10",
                 "--termines-du", "2026-10-10", "--termines-au", "2026-10-10", "--competitions", "f1"],
                session_factory=lambda: db) == 0
    brut = capsysbinary.readouterr().out
    assert "Saint-Étienne".encode("utf-8") in brut                         # pas d'échappement É
    data = json.loads(brut.decode("utf-8"))
    assert len(data["a_venir"]) == 1 and len(data["termines"]) == 1
    assert data["termines"][0]["favori_a_gagne"] is False                  # favori Nîmes (domicile), battu 0-3


def test_sortie_dans_un_fichier(db, equipes, tmp_path, capsys):
    h, a = equipes
    fini(db, h, a, 1, 0)
    fichier = tmp_path / "bilan.json"
    main(["--termines-du", "2026-10-10", "--termines-au", "2026-10-10", "--competitions", "E0", "--sortie", str(fichier)],
         session_factory=lambda: db)
    assert capsys.readouterr().out == ""
    data = json.loads(fichier.read_text(encoding="utf-8"))
    assert data["a_venir"] == [] and len(data["termines"]) == 1


@pytest.mark.parametrize("argv", [
    [],                                                                    # rien à produire
    ["--a-venir-du", "2026-10-10"],                                        # borne manquante
    ["--a-venir-du", "2026-10-12", "--a-venir-au", "2026-10-10"],         # bornes inversées
    ["--termines-du", "10/10/2026", "--termines-au", "2026-10-10"],       # format de date
    ["--a-venir-du", "2026-10-10", "--a-venir-au", "2026-10-10", "--competitions", "XX"],
])
def test_arguments_invalides(argv, capsys):
    with pytest.raises(SystemExit) as e:
        main(argv, session_factory=lambda: pytest.fail("aucune base ne doit être ouverte"))
    assert e.value.code == 2


# --- compteur « + N autres matchs » (fin des vidéos, 01/10/2026) -------------------------------------------------

def test_lus_par_jour_toutes_competitions_et_seulement_les_matchs_lisibles(db, equipes):
    h, a = equipes
    for code in ("E0", "N1", "P1"):                       # N1 et P1 hors des compétitions des vidéos : comptés quand même
        m = make_match(db, h, a, kickoff=KICK, competition=code)
        cotes(db, m, (1.5, 4.2, 6.5), KICK - timedelta(days=1))
    make_match(db, h, a, kickoff=KICK, competition="F1")   # sans relevé : le site n'en montre rien, pas compté
    dimanche = make_match(db, h, a, kickoff=datetime(2026, 10, 11, 22, 30, tzinfo=timezone.utc), competition="SP1")  # lundi 00:30 à Paris
    cotes(db, dimanche, (2.0, 3.4, 3.8), KICK)
    fini(db, a, h, 1, 0)                                    # terminé : pas « à venir »
    data = build(db, a_venir_du=SAMEDI, a_venir_au=date(2026, 10, 12), competitions=("E0",))
    assert data["lus_par_jour"] == {"2026-10-10": 3, "2026-10-12": 1}
    assert len(data["a_venir"]) == 1                        # le filtre de compétitions ne touche que la liste


def test_lus_par_jour_vide_sans_fenetre_a_venir(db, equipes):
    assert build(db, termines_du=SAMEDI, termines_au=SAMEDI)["lus_par_jour"] == {}
