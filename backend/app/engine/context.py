"""Contexte descriptif : forme récente et face-à-face. Descriptif, jamais prédictif."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PastMatch:
    kickoff_at: datetime
    home: str
    away: str
    hg: int
    ag: int


@dataclass
class Form:
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    sequence: str = ""   # "V" victoire, "N" nul, "D" défaite — du plus récent au plus ancien


def form(team: str, history: list[PastMatch], n: int = 5) -> Form:
    mine = sorted((m for m in history if team in (m.home, m.away)), key=lambda m: m.kickoff_at, reverse=True)[:n]
    f = Form()
    for m in mine:
        gf, ga = (m.hg, m.ag) if m.home == team else (m.ag, m.hg)
        f.played += 1; f.goals_for += gf; f.goals_against += ga
        if gf > ga:
            f.wins += 1; f.sequence += "V"
        elif gf == ga:
            f.draws += 1; f.sequence += "N"
        else:
            f.losses += 1; f.sequence += "D"
    return f


def head_to_head(home: str, away: str, history: list[PastMatch], n: int = 5) -> list[PastMatch]:
    pair = {home, away}
    return sorted((m for m in history if {m.home, m.away} == pair), key=lambda m: m.kickoff_at, reverse=True)[:n]
