"""RS256 access tokens."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..config import get_settings
from ..errors import AuthError

logger = logging.getLogger(__name__)

_ALGO = "RS256"


@dataclass(frozen=True)
class AccessClaims:
    sub: str
    role: str
    plan: str
    jti: str
    exp: int


@lru_cache
def _keypair() -> tuple[str, str]:
    s = get_settings()
    priv = s.jwt_private_key.replace("\\n", "\n").strip()
    pub = s.jwt_public_key.replace("\\n", "\n").strip()
    if priv and pub:
        return priv, pub
    if s.is_prod:
        raise RuntimeError("JWT_PRIVATE_KEY and JWT_PUBLIC_KEY must be set when env=prod")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    logger.warning("JWT keys not configured — generated an ephemeral %s dev keypair", s.env)
    return priv, pub


def create_access_token(*, sub: str, role: str, plan: str, ttl_s: int | None = None) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "plan": plan,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + (ttl_s if ttl_s is not None else s.access_token_ttl_seconds),
        "typ": "access",
    }
    return jwt.encode(payload, _keypair()[0], algorithm=_ALGO)


def decode_access_token(token: str) -> AccessClaims:
    try:
        data = jwt.decode(token, _keypair()[1], algorithms=[_ALGO])
    except jwt.PyJWTError as exc:
        raise AuthError("invalid or expired token") from exc
    if data.get("typ") != "access":
        raise AuthError("wrong token type")
    return AccessClaims(
        sub=data["sub"], role=data["role"], plan=data["plan"], jti=data["jti"], exp=data["exp"]
    )
