"""D'où viennent les visiteurs : le `?ref=` du lien posé dans la bio de chaque réseau (01/10/2026).

Liste fermée : n'importe qui peut appeler `/visits` ou ajouter `?ref=` à l'adresse, donc on ne compte que
les sources qu'on a nous-mêmes posées. Une valeur inconnue est ignorée (pas comptée, pas d'erreur).
Aucune donnée personnelle : la visite est un compteur par jour et par source ; l'inscription garde la
source déclarée par le navigateur, rien d'autre.
"""

SOURCES = ("tiktok", "insta", "youtube", "facebook", "snap", "x")


def source_valide(valeur: str | None) -> str | None:
    """`" TikTok "` -> `"tiktok"` ; inconnue, vide ou absente -> None."""
    if not valeur:
        return None
    v = valeur.strip().lower()
    return v if v in SOURCES else None
