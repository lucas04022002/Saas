"""L'adresse du client, derrière le proxy.

Le serveur ne voit jamais le navigateur : il voit Traefik. L'adresse réelle voyage dans
`X-Forwarded-For`, que Traefik ÉCRASE par l'adresse de connexion (mesuré le 22/09/2026 : seize
valeurs inventées n'ont pas contourné le limiteur). On peut donc s'y fier — et il le faut : le
premier correctif, côté uvicorn (`--proxy-headers`), n'a pas suffi, et le limiteur de débit voyait
une seule adresse pour tout le monde (test à deux adresses, 22/09/2026, C2).
"""
from __future__ import annotations

from slowapi import Limiter


def client_ip(request) -> str:
    """La première adresse de `X-Forwarded-For` si elle existe, sinon l'adresse de connexion."""
    brut = request.headers.get("x-forwarded-for") or ""
    premiere = brut.split(",")[0].strip()
    if premiere:
        return premiere
    client = getattr(request, "client", None)
    return getattr(client, "host", None) or "127.0.0.1"


#: Le limiteur unique de l'application : les décorateurs des routes et `app.state.limiter`
#: doivent être la même instance.
limiter = Limiter(key_func=client_ip)
