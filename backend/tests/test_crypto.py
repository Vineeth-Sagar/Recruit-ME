"""recruit_api.security.crypto — envelope encryption for site credentials."""

from __future__ import annotations

import base64
import os

import pytest
from recruit_api.config import Settings
from recruit_api.security.crypto import (
    CryptoError,
    Envelope,
    EnvMasterKey,
    build_envelope,
    generate_master_key_b64,
)


def _key_b64() -> str:
    return base64.b64encode(os.urandom(32)).decode()


def _settings(**kw) -> Settings:
    return Settings(env="test", **kw)


def test_round_trip():
    env = build_envelope(_settings(credential_master_key=_key_b64()))
    ct, nonce, ver = env.encrypt(b"li_at=abc123")
    assert ct != b"li_at=abc123"
    assert env.decrypt(ct, nonce, ver) == b"li_at=abc123"
    assert ver == 1


def test_each_encrypt_is_unique():
    env = build_envelope(_settings(credential_master_key=_key_b64()))
    a = env.encrypt(b"same")
    b = env.encrypt(b"same")
    assert a[0] != b[0] and a[1] != b[1]  # ciphertext + nonce both differ
    assert env.decrypt(*a) == env.decrypt(*b) == b"same"


def test_tampered_ciphertext_is_rejected():
    env = build_envelope(_settings(credential_master_key=_key_b64()))
    ct, nonce, ver = env.encrypt(b"secret-cookie")
    flipped = bytes([ct[0] ^ 0x01]) + ct[1:]
    with pytest.raises(CryptoError):
        env.decrypt(flipped, nonce, ver)


def test_wrong_key_cannot_decrypt():
    a = build_envelope(_settings(credential_master_key=_key_b64()))
    b = build_envelope(_settings(credential_master_key=_key_b64()))
    ct, nonce, ver = a.encrypt(b"payload")
    with pytest.raises(CryptoError):
        b.decrypt(ct, nonce, ver)


def test_key_rotation_keeps_old_rows_readable():
    k1, k2 = _key_b64(), _key_b64()
    # v1 only: seal a row.
    v1_env = build_envelope(_settings(credential_master_keys=f"1:{k1}", credential_key_version=1))
    old_ct, old_nonce, old_ver = v1_env.encrypt(b"old-secret")
    assert old_ver == 1

    # v2 becomes current; v1 is still known.
    rotated = build_envelope(
        _settings(credential_master_keys=f"1:{k1},2:{k2}", credential_key_version=2)
    )
    assert rotated.decrypt(old_ct, old_nonce, old_ver) == b"old-secret"
    new_ct, new_nonce, new_ver = rotated.encrypt(b"new-secret")
    assert new_ver == 2
    assert rotated.decrypt(new_ct, new_nonce, new_ver) == b"new-secret"


def test_unknown_version_raises():
    env = build_envelope(_settings(credential_master_keys=f"1:{_key_b64()}"))
    ct, nonce, _ = env.encrypt(b"x")
    with pytest.raises(CryptoError):
        env.decrypt(ct, nonce, 9)


def test_prod_requires_a_configured_key():
    with pytest.raises(CryptoError):
        EnvMasterKey(Settings(env="prod"))


def test_dev_falls_back_to_a_zero_key():
    # No key configured, env != prod -> deterministic dev key, no crash.
    env = build_envelope(Settings(env="dev"))
    ct, nonce, ver = env.encrypt(b"dev")
    assert env.decrypt(ct, nonce, ver) == b"dev"


def test_bad_key_length_is_rejected():
    with pytest.raises(CryptoError):
        EnvMasterKey(_settings(credential_master_key=base64.b64encode(b"too-short").decode()))


def test_generate_master_key_b64_is_32_bytes():
    assert len(base64.b64decode(generate_master_key_b64())) == 32


def test_envelope_accepts_a_custom_provider():
    class _Fixed:
        current_version = 7

        def key(self, version: int) -> bytes:
            assert version == 7
            return b"\x11" * 32

    env = Envelope(_Fixed())
    ct, nonce, ver = env.encrypt(b"hello")
    assert ver == 7
    assert env.decrypt(ct, nonce, ver) == b"hello"
