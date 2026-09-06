"""Signup, login, rotating refresh, email verification, password reset."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..errors import AuthError, ConflictError, ForbiddenError
from ..models.auth import EmailVerificationToken, PasswordResetToken, RefreshToken
from ..models.user import User, UserStatus
from ..security.jwt import create_access_token
from ..security.passwords import hash_password, verify_password
from .email_service import EmailSender


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_raw_token() -> str:
    return secrets.token_urlsafe(48)


def _now() -> datetime:
    return datetime.now(UTC)


async def revoke_all_refresh_tokens(db: AsyncSession, user_id) -> None:
    """Kill every live session for a user — used on password/email change too."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


class AuthService:
    def __init__(self, db: AsyncSession, email: EmailSender, settings: Settings):
        self.db = db
        self.email = email
        self.settings = settings

    # ── signup / verify ────────────────────────────────────────────────

    async def signup(self, email: str, password: str, full_name: str) -> User:
        existing = await self.db.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise ConflictError("an account with that email already exists", code="email_taken")

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            status=UserStatus.pending_verification,
        )
        self.db.add(user)
        await self.db.flush()

        raw = _new_raw_token()
        self.db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=_hash_token(raw),
                expires_at=_now() + timedelta(hours=24),
            )
        )
        await self._send(
            user.email,
            "Confirm your Recruit-ME email",
            f'Confirm your address: <a href="{self.settings.frontend_base_url}/verify?token={raw}">'
            "verify email</a>",
        )
        return user

    async def verify_email(self, token: str) -> None:
        row = await self.db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == _hash_token(token)
            )
        )
        if row is None or row.used_at is not None or row.expires_at <= _now():
            raise AuthError("invalid or expired verification token")
        user = await self.db.get(User, row.user_id)
        if user is not None and user.status == UserStatus.pending_verification:
            user.status = UserStatus.active
        row.used_at = _now()

    # ── login / refresh / logout ──────────────────────────────────────

    async def login(
        self, email: str, password: str, *, user_agent: str, ip: str
    ) -> tuple[str, str, int]:
        user = await self.db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("invalid email or password")
        if user.status == UserStatus.suspended:
            raise ForbiddenError("this account is suspended")

        access = self._access_for(user)
        raw_refresh = await self._issue_refresh(user, user_agent=user_agent, ip=ip)
        return access, raw_refresh, self.settings.access_token_ttl_seconds

    async def refresh(self, raw: str, *, user_agent: str, ip: str) -> tuple[str, str, int]:
        row = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
        )
        if row is None:
            raise AuthError("invalid refresh token")
        if row.revoked_at is not None:
            # Reuse of an already-rotated token — treat the whole family as compromised.
            await self._revoke_all_for_user(row.user_id)
            raise AuthError("refresh token reuse detected; all sessions revoked")
        if row.expires_at <= _now():
            raise AuthError("refresh token expired")

        user = await self.db.get(User, row.user_id)
        if user is None or user.status == UserStatus.suspended:
            raise ForbiddenError("account unavailable")

        row.revoked_at = _now()
        new_raw = await self._issue_refresh(
            user, user_agent=user_agent, ip=ip, rotated_from_id=row.id
        )
        return self._access_for(user), new_raw, self.settings.access_token_ttl_seconds

    async def logout(self, raw: str | None) -> None:
        if not raw:
            return
        row = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
        )
        if row is not None and row.revoked_at is None:
            row.revoked_at = _now()

    # ── password reset ───────────────────────────────────────────────

    async def start_password_reset(self, email: str) -> None:
        user = await self.db.scalar(select(User).where(User.email == email))
        if user is None:
            return  # do not reveal whether the address exists
        raw = _new_raw_token()
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=_hash_token(raw),
                expires_at=_now() + timedelta(hours=1),
            )
        )
        await self._send(
            user.email,
            "Reset your Recruit-ME password",
            f'Reset your password: <a href="{self.settings.frontend_base_url}/reset?token={raw}">'
            "choose a new password</a>",
        )

    async def finish_password_reset(self, token: str, new_password: str) -> None:
        row = await self.db.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
        )
        if row is None or row.used_at is not None or row.expires_at <= _now():
            raise AuthError("invalid or expired reset token")
        user = await self.db.get(User, row.user_id)
        if user is None:
            raise AuthError("invalid or expired reset token")
        user.password_hash = hash_password(new_password)
        row.used_at = _now()
        await self._revoke_all_for_user(user.id)

    # ── internals ────────────────────────────────────────────────────

    def _access_for(self, user: User) -> str:
        return create_access_token(sub=str(user.id), role=user.role.value, plan=user.plan.value)

    async def _issue_refresh(
        self,
        user: User,
        *,
        user_agent: str,
        ip: str,
        rotated_from_id=None,
    ) -> str:
        raw = _new_raw_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=_hash_token(raw),
                expires_at=_now() + timedelta(seconds=self.settings.refresh_token_ttl_seconds),
                user_agent=user_agent[:400],
                ip=ip[:64],
                rotated_from_id=rotated_from_id,
            )
        )
        await self.db.flush()
        return raw

    async def _revoke_all_for_user(self, user_id) -> None:
        await revoke_all_refresh_tokens(self.db, user_id)

    async def _send(self, to: str, subject: str, html: str) -> None:
        await self.email.send(to=to, subject=subject, html=html)
