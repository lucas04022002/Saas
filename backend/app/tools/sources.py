"""D'où viennent les visiteurs et les abonnés : le bilan des liens `rushplay.fr/?ref=…` posés en bio.

    python -m app.tools.sources                 # depuis le début
    python -m app.tools.sources --depuis 2026-10-01

Visites = arrivées par le lien du réseau (une par clic, comptée par le navigateur) ; inscriptions =
comptes créés avec cette source ; abonnés = parmi ces inscrits, ceux qui paient aujourd'hui.
« sans lien » = inscrits arrivés autrement (adresse tapée, Google, bouche-à-oreille, ou avant le 01/10/2026).
"""
import argparse
import sys
from datetime import date

from app.services.sources import bilan


def _jour(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"date attendue AAAA-MM-JJ, reçu « {s} »")


def _pct(a: int, b: int | None) -> str:
    return f"{100 * a / b:.1f} %" if b else "—"


def tableau(lignes: list[dict]) -> str:
    entete = f"{'source':<12}{'visites':>9}{'inscrits':>10}{'visite→inscrit':>16}{'abonnés':>9}{'inscrit→abonné':>16}"
    out = [entete, "-" * len(entete)]
    for l in lignes:
        v = "—" if l["visites"] is None else str(l["visites"])
        out.append(f"{l['source']:<12}{v:>9}{l['inscriptions']:>10}{_pct(l['inscriptions'], l['visites']):>16}"
                   f"{l['abonnes']:>9}{_pct(l['abonnes'], l['inscriptions']):>16}")
    if len(out) == 2:
        out.append("(rien encore : aucune visite par un lien ?ref= ni aucune inscription sur la période)")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None, session_factory=None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.tools.sources", description="Visites, inscriptions et abonnés par réseau.")
    p.add_argument("--depuis", type=_jour, metavar="AAAA-MM-JJ", help="premier jour compté (heure de Paris)")
    a = p.parse_args(argv)
    if session_factory is None:
        from app.core.database import SessionLocal
        session_factory = SessionLocal
    db = session_factory()
    try:
        lignes = bilan(db, depuis=a.depuis)
    finally:
        db.close()
    titre = f"Réseaux — depuis le {a.depuis.isoformat()}\n" if a.depuis else "Réseaux — depuis le début\n"
    # octets UTF-8 quel que soit l'encodage de la console (Windows : cp1252)
    sys.stdout.buffer.write((titre + tableau(lignes)).encode("utf-8"))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
