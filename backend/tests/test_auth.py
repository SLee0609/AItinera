import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import auth
from app.config import Settings
from app.errors import NotSignedIn, StorageError

URL = "https://proj.supabase.co"
SETTINGS = Settings(supabase_url=URL, supabase_secret_key="s", _env_file=None)
KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


def make_token(key=KEY, **overrides) -> str:
    claims = {
        "sub": "user-1",
        "aud": "authenticated",
        "iss": f"{URL}/auth/v1",
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
        **overrides,
    }
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "k1"})


@pytest.fixture(autouse=True)
def fake_jwks(monkeypatch):
    """Serves KEY's public half as the project's only signing key."""
    seen = {}

    class Client:
        def get_signing_key_from_jwt(self, token):
            if jwt.get_unverified_header(token).get("kid") != "k1":
                raise jwt.PyJWKClientError("Unable to find a signing key that matches")
            return SimpleNamespace(key=KEY.public_key())

    def jwks_client(url):
        seen["url"] = url
        return Client()

    monkeypatch.setattr(auth, "_jwks_client", jwks_client)
    return seen


def test_valid_token_returns_user_id(fake_jwks):
    assert auth.verify_token(make_token(), SETTINGS) == "user-1"
    assert fake_jwks["url"] == f"{URL}/auth/v1/.well-known/jwks.json"


@pytest.mark.parametrize(
    "token",
    [
        make_token(exp=int(time.time()) - 10),
        make_token(aud="anon"),
        make_token(iss="https://other.supabase.co/auth/v1"),
        make_token(sub=None),
        make_token(key=OTHER_KEY),
        "not-a-jwt",
    ],
    ids=["expired", "audience", "issuer", "no-sub", "wrong-key", "garbage"],
)
def test_invalid_tokens_are_rejected(token):
    with pytest.raises(NotSignedIn):
        auth.verify_token(token, SETTINGS)


def test_hs256_tokens_are_rejected():
    token = jwt.encode(
        {"sub": "u", "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 60},
        "a-legacy-shared-secret-of-sufficient-length",
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    with pytest.raises(NotSignedIn):
        auth.verify_token(token, SETTINGS)


def test_unconfigured_supabase_rejects_everything():
    with pytest.raises(NotSignedIn):
        auth.verify_token(make_token(), Settings(_env_file=None))


@pytest.mark.parametrize(
    "header, expected",
    [
        (None, None),
        ("", None),
        ("Bearer abc", "abc"),
        ("bearer  abc ", "abc"),
        ("Basic abc", None),
        ("Bearer", None),
    ],
)
def test_bearer_parsing(header, expected):
    assert auth._bearer(header) == expected


def test_current_user_requires_a_token():
    with pytest.raises(NotSignedIn):
        auth.current_user(SETTINGS, None)
    assert auth.current_user(SETTINGS, f"Bearer {make_token()}") == "user-1"


def test_optional_user_treats_bad_tokens_as_guests(monkeypatch):
    assert auth.optional_user(SETTINGS, None) is None
    assert auth.optional_user(SETTINGS, "Bearer nope") is None
    assert auth.optional_user(SETTINGS, f"Bearer {make_token()}") == "user-1"

    def unreachable(*_args):
        raise StorageError("down")

    monkeypatch.setattr(auth, "verify_token", unreachable)
    assert auth.optional_user(SETTINGS, f"Bearer {make_token()}") is None
