"""Routes internes : pour les programmes de Lucas, pas pour le site.

`GET /api/v1/internal/video-data` rend le JSON de `python -m app.tools.video_data` (contrat
`rushplay-formats/SCHEMA.md`), tel quel, sans l'enveloppe `{success, data}` : le programme du PC le
récupère chaque matin au lieu d'un copier-coller depuis le terminal Coolify.

La route est invisible tant qu'on ne présente pas le bon jeton :
- `VIDEO_DATA_TOKEN` vide ou trop court → 404, comme une route inconnue ;
- en-tête `X-Video-Token` absent ou faux → 404 aussi, comparé en temps constant ;
- les paramètres ne sont lus QU'APRÈS le jeton : un 422 révélerait la route à qui n'a pas le jeton ;
- chaque adresse n'a droit qu'à `ESSAIS_RATES` jetons faux par heure ; au-delà, même le bon jeton
  reçoit 404 depuis cette adresse, donc l'essai systématique ne peut plus rien apprendre ;
- un appel authentifié est limité à `LIMITE` par adresse (429 : le porteur du jeton sait que la route existe).
Lecture seule, aucune donnée d'utilisateur ; le jeton n'est jamais journalisé.
"""
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from limits import parse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.client_ip import client_ip, limiter
from app.core.config import settings
from app.tools import video_data

log = logging.getLogger("rushplay")

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)

#: En dessous, le jeton n'est pas accepté : `secrets.token_urlsafe(32)` en donne 43.
LONGUEUR_MINIMALE = 32
LIMITE = "30/hour"
ESSAIS_RATES = parse("10/hour")
_PARAMETRES = ("a_venir_du", "a_venir_au", "termines_du", "termines_au")


def _introuvable() -> HTTPException:
    # Même corps que la 404 d'une route inconnue (`http_exception_handler`).
    return HTTPException(status_code=404, detail="Not Found")


def _jeton_configure() -> str | None:
    jeton = settings.video_data_token or ""
    if len(jeton) < LONGUEUR_MINIMALE:
        if jeton:
            log.warning("VIDEO_DATA_TOKEN trop court (< %d caractères) : route video-data fermée", LONGUEUR_MINIMALE)
        return None
    return jeton


def exiger_le_jeton(request: Request) -> None:
    """Dépendance : tout échec rend 404, et seulement 404."""
    attendu = _jeton_configure()
    if attendu is None:
        raise _introuvable()
    cle = client_ip(request)
    if not limiter.limiter.test(ESSAIS_RATES, "video-data-echecs", cle):
        raise _introuvable()      # adresse grillée : même le bon jeton ne passe plus pendant l'heure
    fourni = request.headers.get("x-video-token") or ""
    if not hmac.compare_digest(fourni.encode("utf-8"), attendu.encode("utf-8")):
        limiter.limiter.hit(ESSAIS_RATES, "video-data-echecs", cle)
        raise _introuvable()


@router.get("/video-data", dependencies=[Depends(exiger_le_jeton)])
@limiter.limit(LIMITE)
def donnees_des_videos(request: Request, db: Session = Depends(get_db)):
    q = request.query_params
    inconnus = sorted(set(q) - set(_PARAMETRES) - {"competitions"})
    try:
        if inconnus:   # la commande refuse aussi une option inconnue
            raise video_data.ParametresInvalides(f"paramètre inconnu : {', '.join(inconnus)}")
        bornes = {}
        for nom in _PARAMETRES:
            try:
                bornes[nom] = video_data.jour(q[nom]) if nom in q else None
            except video_data.ParametresInvalides as e:
                raise video_data.ParametresInvalides(f"{nom} : {e}") from None
        competitions = video_data.valider(
            **bornes, competitions=q.get("competitions", ",".join(video_data.COMPETITIONS_PAR_DEFAUT)))
    except video_data.ParametresInvalides as e:
        raise HTTPException(status_code=422, detail=str(e))
    return JSONResponse(video_data.build(db, **bornes, competitions=competitions))
