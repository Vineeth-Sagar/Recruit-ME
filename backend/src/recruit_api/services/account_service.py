"""Account self-service: change password, change email, delete account.

Any credential change (new password, confirmed new email) revokes every live
refresh token. Deleting the account wipes the tenant's object-storage prefixes
and then removes the ``users`` row; the FK cascades take every dependent table
with it, and the still-valid access JWT stops working on its next request
because :func:`get_current_user` can no longer load the user.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..errors import AuthError, ConflictError
from ..models.auth import EmailChangeToken
from ..models.user import User
from ..security.passwords import hash_password, verify_password
from .auth_service import revoke_all_refresh_tokens
from .email_service import EmailSender
from .object_store import ObjectStore


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


class AccountService:
    def __init__(
        self,
        db: AsyncSession,
        email: EmailSender,
        settings: Settings,
        object_store: ObjectStore,
    ):
        self.db = db
        self.email = email
        self.settings = settings
        self.store = object_store

    # ── password ─────────────────────────────────────────────────────

    async def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.password_hash):
            raise AuthError("current password is incorrect")
        user.password_hash = hash_password(new)
        await self.db.flush()
        await revoke_all_refresh_tokens(self.db, user.id)

    # ── email change (confirm-by-link) ───────────────────────────────

    async def request_email_change(self, user: User, new_email: str, current_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AuthError("current password is incorrect")
        if new_email.lower() == user.email.lower():
            raise ConflictError("that is already your email address")
        taken = await self.db.scalar(select(User).where(User.email == new_email))
        if taken is not None:
            raise ConflictError("an account with that email already exists", code="email_taken")

        raw = secrets.token_urlsafe(48)
        self.db.add(
            EmailChangeToken(
                user_id=user.id,
                new_email=new_email,
                token_hash=_hash_token(raw),
                expires_at=_now() + timedelta(hours=2),
            )
        )
        await self.db.flush()
        await self.email.send(
            to=new_email,
            subject="Confirm your new Recruit-ME email",
            html=(
                "Confirm this address for your Recruit-ME account: "
                f'<a href="{self.settings.frontend_base_url}/email-change/confirm?token={raw}">'
                "confirm email change</a>. The link expires in 2 hours."
            ),
        )

    async def confirm_email_change(self, token: str) -> None:
        row = await self.db.scalar(
            select(EmailChangeToken).where(EmailChangeToken.token_hash == _hash_token(token))
        )
        if row is None or row.used_at is not None or row.expires_at <= _now():
            raise AuthError("invalid or expired email-change token")

        # Someone else may have claimed the address in the meantime.
        taken = await self.db.scalar(select(User).where(User.email == row.new_email))
        if taken is not None and taken.id != row.user_id:
            raise ConflictError("an account with that email already exists", code="email_taken")

        user = await self.db.get(User, row.user_id)
        if user is None:
            raise AuthError("invalid or expired email-change token")
        user.email = row.new_email
        row.used_at = _now()
        await self.db.flush()
        await revoke_all_refresh_tokens(self.db, user.id)

    # ── delete account ───────────────────────────────────────────────

    async def delete_account(self, user: User, password: str, confirm_email: str) -> None:
        if not verify_password(password, user.password_hash):
            raise AuthError("password is incorrect")
        if confirm_email.lower() != user.email.lower():
            raise AuthError("confirmation email does not match this account")

        user_id: uuid.UUID = user.id
        await self.store.delete_prefix(f"resumes/{user_id}/")
        await self.store.delete_prefix(f"reports/{user_id}/")

        await self.db.delete(user)
        await self.db.flush()
