"""Security regression tests for app.dependencies.get_current_user.

These tests specifically target JWT "algorithm confusion" attacks, where an
attacker forges a token and relies on the server trusting the algorithm
asserted in the (unverified, attacker-controlled) token header rather than a
fixed server-side allowlist. JWKS `kid` values are public - fetchable from
`/.well-known/jwks.json` - so an attacker always has a valid kid to pair with
a forged header.
"""

import base64
import json

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt as jose_jwt

from app import dependencies


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _forge_alg_none_token(payload: dict, kid: str) -> str:
    """Hand-construct an unsigned JWT. python-jose's own encoder refuses to
    produce alg=none tokens, but a real attacker isn't using python-jose -
    they just build the three base64url segments directly, leaving the
    signature segment empty (the defining trait of an 'alg: none' token)."""
    header = {"alg": "none", "kid": kid, "typ": "JWT"}
    header_seg = _b64url(json.dumps(header).encode())
    payload_seg = _b64url(json.dumps(payload).encode())
    return f"{header_seg}.{payload_seg}."

FAKE_KID = "real-public-kid-anyone-can-fetch"
FAKE_JWKS = {
    "keys": [
        {
            "kid": FAKE_KID,
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": "wM7XnQ7vH9sFAKE",
            "e": "AQAB",
        }
    ]
}


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def _fake_get_jwks():
    return FAKE_JWKS


@pytest.mark.asyncio
async def test_alg_none_forged_token_is_rejected(monkeypatch):
    """Attacker forges an unsigned token (alg=none) claiming to be any user,
    using a real public kid. Must be rejected cleanly with 401 - 'alg: none'
    is a classic JWT auth-bypass technique. (On the pre-fix code, the
    forged token wasn't accepted, but it crashed with an unhandled
    JWKError/500 instead of a clean 401 - still a bug, since the code only
    caught JWTError. The real risk is architectural: trusting the
    attacker-supplied alg header to select verification parameters is
    version- and key-set-dependent: it happened to fail safe here only
    because of incidental type-checking inside jose's crypto backend.)"""
    monkeypatch.setattr(dependencies, "_get_jwks", _fake_get_jwks)

    forged = _forge_alg_none_token(
        {"sub": "victim-user-id", "aud": "authenticated"}, kid=FAKE_KID
    )

    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(_creds(forged))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_hs256_signed_with_attacker_chosen_secret_via_jwks_branch_is_rejected(
    monkeypatch,
):
    """Attacker tries to assert an unexpected algorithm (e.g. HS384) hoping
    the server will blindly trust algorithms=[header['alg']]. Must be
    rejected since HS384 is not in the fixed JWKS allowlist."""
    monkeypatch.setattr(dependencies, "_get_jwks", _fake_get_jwks)

    forged = jose_jwt.encode(
        {"sub": "victim-user-id", "aud": "authenticated"},
        key="attacker-knows-this-string",
        algorithm="HS384",
        headers={"kid": FAKE_KID},
    )

    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(_creds(forged))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_hs256_token_is_accepted(monkeypatch):
    """Sanity check: a correctly-signed HS256 token (the real Supabase
    legacy-secret signing path) must still work after the fix."""
    monkeypatch.setattr(dependencies.settings, "SUPABASE_JWT_SECRET", "real-secret")

    token = jose_jwt.encode(
        {"sub": "user-123", "aud": "authenticated"},
        "real-secret",
        algorithm="HS256",
    )

    user_id = await dependencies.get_current_user(_creds(token))
    assert user_id == "user-123"


@pytest.mark.asyncio
async def test_hs256_token_with_wrong_secret_is_rejected(monkeypatch):
    """Sanity check: tampered/forged HS256 token with the wrong secret must
    still be rejected (basic signature verification sanity)."""
    monkeypatch.setattr(dependencies.settings, "SUPABASE_JWT_SECRET", "real-secret")

    forged = jose_jwt.encode(
        {"sub": "attacker-controlled", "aud": "authenticated"},
        "wrong-secret",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(_creds(forged))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_credentials_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(None)
    assert exc_info.value.status_code == 401
