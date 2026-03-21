"""
Repli sans dependance : remplace thefuzz avec la lib standard (compatible Python 3.14).
Utilise uniquement difflib pour le matching flou des noms d'equipes.
"""
import difflib


def _token_sort(s):
    """Tri des mots pour comparaison type token_sort_ratio."""
    return " ".join(sorted((s or "").lower().split()))


def token_sort_ratio(s1, s2):
    """Similaire a thefuzz fuzz.token_sort_ratio : retourne un score 0-100."""
    if not s1 and not s2:
        return 100
    if not s1 or not s2:
        return 0
    a, b = _token_sort(s1), _token_sort(s2)
    return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)


class _Fuzz:
    token_sort_ratio = staticmethod(token_sort_ratio)


class _Process:
    @staticmethod
    def extractOne(query, choices, scorer=token_sort_ratio):
        """Retourne (meilleur_choix, score)."""
        if not choices:
            return None, 0
        best_score = -1
        best_choice = None
        for c in choices:
            score = scorer(query, c)
            if score > best_score:
                best_score = score
                best_choice = c
        return best_choice, best_score


fuzz = _Fuzz()
process = _Process()
