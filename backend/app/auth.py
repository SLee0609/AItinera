"""Verifies the Supabase access token the frontend sends as `Authorization: Bearer <token>`.

Tokens are checked against the project's public signing keys (JWKS), so the project must use asymmetric
JWT signing keys (the default for new Supabase projects).
"""

import logging
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Header

from .config import Settings, get_settings
from .errors import NotSignedIn, StorageError

log = logging.getLogger(__name__)

ALGORITHMS = ["ES256", "RS256"]
AUDIENCE = "authenticated"


@lru_cache
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # Keys are cached for 5 minutes; an unknown key ID triggers a refetch.
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=300, timeout=5)


def verify_token(token: str, settings: Settings) -> str:
    """Returns the user ID (`sub`) of a valid access token. Raises NotSignedIn for any invalid token."""
    if not settings.supabase_url:
        raise NotSignedIn()
    base = settings.supabase_base_url
    try:
        signing_key = _jwks_client(f"{base}/auth/v1/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=f"{base}/auth/v1",
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.PyJWKClientConnectionError as err:
        raise StorageError(f"JWKS fetch failed: {err!r}") from err
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as err:
        log.info("Rejected access token: %s", err)
        raise NotSignedIn() from err
    return str(claims["sub"])


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


# Sync dependencies: PyJWKClient fetches keys with blocking I/O, so FastAPI runs these in its thread pool.
def current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    token = _bearer(authorization)
    if token is None:
        raise NotSignedIn()
    return verify_token(token, settings)


def optional_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """The signed-in user, or None for guests. An invalid or expired token counts as a guest."""
    token = _bearer(authorization)
    if token is None:
        return None
    try:
        return verify_token(token, settings)
    except (NotSignedIn, StorageError):
        return None
