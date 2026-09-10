"""Lecture du marché : favori, écarts bookmakers FR vs référence, mouvement entre relevés."""
from collections import defaultdict

from app.engine.probabilities import REFERENCE_BOOKMAKER, implied, margin, reference
from app.engine.types import OUTCOMES, BookQuote, Odds, Probs, Reading


def favourite(p: Probs) -> tuple[str, float]:
    i = max(range(3), key=lambda k: p[k])
    return OUTCOMES[i], p[i]


def gaps(latest: dict[str, Odds], ref: Probs) -> dict[str, tuple[float, float, float]]:
    return {book: (o[0] * ref[0] - 1, o[1] * ref[1] - 1, o[2] * ref[2] - 1) for book, o in latest.items()}


def movement(first_ref: Probs, last_ref: Probs) -> tuple[float, float, float]:
    return tuple((last_ref[k] - first_ref[k]) * 100 for k in range(3))  # type: ignore[return-value]


def _by_time(quotes: list[BookQuote]) -> dict:
    """relevés groupés par horodatage : {taken_at: {bookmaker: odds}}"""
    grouped: dict = defaultdict(dict)
    for q in quotes:
        grouped[q.taken_at][q.bookmaker] = q.odds
    return dict(sorted(grouped.items()))


def read(
    quotes: list[BookQuote],
    french_books: tuple[str, ...],
    reference_books: tuple[str, ...] = (REFERENCE_BOOKMAKER, "fd_uk_pinnacle"),
    fallback_books: tuple[str, ...] = ("fd_uk_avg",),
) -> Reading:
    keep = set(french_books) | set(reference_books) | set(fallback_books)
    kept = [q for q in quotes if q.bookmaker in keep]
    if not kept:
        raise ValueError("aucun relevé exploitable")
    latest: dict[str, BookQuote] = {}
    for q in sorted(kept, key=lambda q: q.taken_at):
        latest[q.bookmaker] = q
    latest_odds = {b: q.odds for b, q in latest.items()}
    ref, src = reference(latest_odds, reference_books=reference_books)
    fav, fav_p = favourite(ref)
    grouped = _by_time(kept)
    times = list(grouped)
    mov = None
    if len(times) >= 2:
        first_ref, _ = reference(grouped[times[0]], reference_books=reference_books)
        mov = movement(first_ref, ref)
    return Reading(
        reference=ref, reference_source=src, favourite=fav, favourite_prob=fav_p,
        margin_by_book={b: margin(o) for b, o in latest_odds.items()},
        latest_by_book=latest_odds,
        gaps=gaps({b: o for b, o in latest_odds.items() if b in french_books}, ref),
        movement=mov, first_taken_at=times[0], last_taken_at=times[-1],
    )
