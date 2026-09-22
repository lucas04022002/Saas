"""Ce que le conteneur de l'API doit faire, lisible dans le Dockerfile.

Ces tests lisent un fichier, pas du code : c'est la seule façon d'empêcher qu'une
option de la ligne de commande disparaisse dans un nettoyage."""
from pathlib import Path

DOCKERFILE = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(encoding="utf-8")


def test_uvicorn_fait_confiance_au_proxy_pour_l_ip_du_client():
    """Audit du 22/09/2026 : sans ces options, derrière Traefik, tous les visiteurs ont l'IP du
    proxy — la limitation de débit plafonnait les inscriptions à 5 par heure POUR TOUT LE SITE."""
    assert "--proxy-headers" in DOCKERFILE
    assert "--forwarded-allow-ips" in DOCKERFILE


def test_uvicorn_n_annonce_pas_sa_version():
    assert "--no-server-header" in DOCKERFILE


def test_le_conteneur_ne_tourne_pas_en_root():
    lignes = [l.strip() for l in DOCKERFILE.splitlines()]
    users = [l for l in lignes if l.startswith("USER ")]
    assert users and users[-1] != "USER root"
    # l'utilisateur est posé avant la commande de démarrage
    assert lignes.index(users[-1]) < next(i for i, l in enumerate(lignes) if l.startswith("CMD"))
