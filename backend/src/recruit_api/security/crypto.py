"""Authenticated encryption for stored site credentials.

Secrets are sealed with ChaCha20-Poly1305 under a versioned master key. The row
keeps ``(ciphertext, nonce, key_version)`` and never the plaintext. Rotating the
master key means adding a higher version and pointing ``current_version`` at it;
old rows still decrypt under their recorded version.

For a real deployment ``EnvMasterKey`` is swapped for a KMS-backed provider that
wraps a per-row data key — the ``Envelope`` API stays the same.
"""

from __future__ import annotations

import base64
import os
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from ..config import Settings

_KEY_LEN = 32
_NONCE_LEN = 12


class CryptoError(Exception):
    pass


class MasterKeyProvider(Protocol):
    current_version: int

    def key(self, version: int) -> bytes: ...


class EnvMasterKey:
    """Keys from settings. ``CREDENTIAL_MASTER_KEYS`` is ``"1:<b64>,2:<b64>"``;
    a bare ``CREDENTIAL_MASTER_KEY`` is treated as version 1."""

    def __init__(self, settings: Settings):
        keys: dict[int, bytes] = {}
        raw_multi = settings.credential_master_keys.strip()
        if raw_multi:
            for part in raw_multi.split(","):
                ver, _, b64 = part.strip().partition(":")
                keys[int(ver)] = _decode_key(b64)
        elif settings.credential_master_key.strip():
            keys[1] = _decode_key(settings.credential_master_key)

        if not keys:
            if settings.is_prod:
                raise CryptoError("CREDENTIAL_MASTER_KEY(S) must be set when env=prod")
            keys[1] = _decode_key(base64.b64encode(b"\x00" * _KEY_LEN).decode())  # dev-only

        self._keys = keys
        self.current_version = settings.credential_key_version
        if self.current_version not in keys:
            self.current_version = max(keys)

    def key(self, version: int) -> bytes:
        try:
            return self._keys[version]
        except KeyError as exc:
            raise CryptoError(f"no master key for version {version}") from exc


def _decode_key(b64: str) -> bytes:
    raw = base64.b64decode(b64.strip())
    if len(raw) != _KEY_LEN:
        raise CryptoError("master key must be 32 bytes (base64-encoded)")
    return raw


class Envelope:
    def __init__(self, provider: MasterKeyProvider):
        self._provider = provider

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes, int]:
        version = self._provider.current_version
        nonce = os.urandom(_NONCE_LEN)
        ct = ChaCha20Poly1305(self._provider.key(version)).encrypt(nonce, plaintext, None)
        return ct, nonce, version

    def decrypt(self, ciphertext: bytes, nonce: bytes, key_version: int) -> bytes:
        try:
            return ChaCha20Poly1305(self._provider.key(key_version)).decrypt(
                nonce, ciphertext, None
            )
        except InvalidTag as exc:
            raise CryptoError("ciphertext failed authentication (wrong key or tampered)") from exc


def build_envelope(settings: Settings) -> Envelope:
    return Envelope(EnvMasterKey(settings))


def generate_master_key_b64() -> str:
    """Helper for ops: a fresh base64 master key."""
    return base64.b64encode(os.urandom(_KEY_LEN)).decode()
