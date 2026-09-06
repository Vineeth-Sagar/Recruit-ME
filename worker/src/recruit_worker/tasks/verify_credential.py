"""verify_credential — decrypt a stored credential and sanity-check its shape.

This is a *structural* check: it confirms the secret decrypts and carries the
fields a scraper will look for (e.g. a LinkedIn ``li_at`` cookie). A live
authenticated round-trip against each site is deliberately out of scope — it is
fragile, rate-limited, and risks tripping anti-bot heuristics. The result is
recorded on the row as ``valid`` / ``invalid`` with ``verify_error``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from recruit_api.models.site_credential import CredentialStatus, SiteCredential
from recruit_api.security.crypto import CryptoError

from ..credentials import open_secret

logger = logging.getLogger("recruit_worker.verify_credential")

# (site, auth_type) -> at least one of these keys must be present & non-empty.
# A missing entry falls back to "any non-empty value".
_REQUIRED_KEYS: dict[tuple[str, str], tuple[str, ...]] = {
    ("linkedin", "cookie"): ("li_at",),
    ("indeed", "cookie"): ("CTK", "SHARED_INDEED_CSRF_TOKEN", "cookie"),
    ("glassdoor", "cookie"): ("gdId", "cookie"),
    ("wellfound", "api_key"): ("api_key",),
}


def _structural_error(site: str, auth_type: str, secret: dict) -> str | None:
    non_empty = {k: v for k, v in secret.items() if isinstance(v, str) and v.strip()}
    if not non_empty:
        return "secret has no non-empty values"

    if auth_type == "api_key" and not non_empty.get("api_key"):
        return "api_key auth needs a non-empty 'api_key' value"

    required = _REQUIRED_KEYS.get((site, auth_type))
    if required and not any(non_empty.get(k) for k in required):
        return f"{site} {auth_type} auth expects one of: {', '.join(required)}"
    return None


def _now() -> datetime:
    return datetime.now(UTC)


async def verify_credential(ctx: dict, credential_id: str) -> None:
    sessionmaker = ctx["sessionmaker"]
    envelope = ctx["envelope"]

    async with sessionmaker() as db:
        row = await db.get(SiteCredential, uuid.UUID(credential_id))
        if row is None:
            logger.warning("credential %s vanished before verify", credential_id)
            return

        try:
            secret = open_secret(envelope, row)
        except (CryptoError, ValueError) as exc:
            row.status = CredentialStatus.invalid
            row.verify_error = f"could not decrypt: {exc}"[:400]
            row.last_verified_at = _now()
            await db.commit()
            logger.error("credential %s failed to decrypt", credential_id)
            return

        err = _structural_error(str(row.site), str(row.auth_type), secret)
        if err:
            row.status = CredentialStatus.invalid
            row.verify_error = err[:400]
        else:
            row.status = CredentialStatus.valid
            row.verify_error = ""
        row.last_verified_at = _now()
        await db.commit()
        logger.info("credential %s -> %s", credential_id, row.status)
