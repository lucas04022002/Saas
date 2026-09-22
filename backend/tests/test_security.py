import pytest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("mysecretpassword")
    assert hashed != "mysecretpassword"
    assert verify_password("mysecretpassword", hashed)


def test_wrong_password_fails_verification():
    hashed = hash_password("correct")
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token("user-123")
    subject = decode_access_token(token)
    assert subject == "user-123"


def test_invalid_token_raises():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_access_token("not.a.valid.token")


def test_tampered_token_raises():
    token = create_access_token("user-abc")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(ValueError):
        decode_access_token(tampered)


# ---- énumération par le temps de réponse (audit du 22/09/2026, F1) ----

def test_login_verifie_un_hachage_meme_quand_l_adresse_est_inconnue(client, monkeypatch):
    """Sans hachage factice, une adresse inconnue répond en 1 ms et une adresse connue en 100 ms :
    on devine qui a un compte au chronomètre."""
    from app.api.v1.endpoints import auth
    appels = {"n": 0}
    original = auth.verify_password

    def compte(*a, **k):
        appels["n"] += 1
        return original(*a, **k)

    monkeypatch.setattr(auth, "verify_password", compte)
    r = client.post("/api/v1/auth/login", json={"email": "personne@rushplay.fr", "password": "motdepasse123"})
    assert r.status_code == 401
    assert appels["n"] == 1
