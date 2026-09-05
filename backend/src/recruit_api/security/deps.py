"""Request dependencies: current user, role/plan guards, service wiring."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..db import get_db
from ..errors import AuthError, ForbiddenError
from ..models.user import User, UserStatus
from ..services.auth_service import AuthService
from ..services.email_service import EmailSender, build_email_sender
from .jwt import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_settings_dep() -> Settings:
    return get_settings()


def get_email_sender(settings: Annotated[Settings, Depends(get_settings_dep)]) -> EmailSender:
    return build_email_sender(settings)


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    email: Annotated[EmailSender, Depends(get_email_sender)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> AuthService:
    return AuthService(db, email, settings)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if creds is None:
        raise AuthError("not authenticated")
    claims = decode_access_token(creds.credentials)
    try:
        user = await db.get(User, uuid.UUID(claims.sub))
    except ValueError as exc:
        raise AuthError("invalid token subject") from exc
    if user is None:
        raise AuthError("account no longer exists")
    if user.status == UserStatus.suspended:
        raise ForbiddenError("this account is suspended")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, User]]:
    async def _dep(user: CurrentUser) -> User:
        if user.role.value not in roles:
            raise ForbiddenError("insufficient role")
        return user

    return _dep


def require_plan(*plans: str) -> Callable[..., Coroutine[Any, Any, User]]:
    async def _dep(user: CurrentUser) -> User:
        if user.plan.value not in plans:
            raise ForbiddenError("upgrade required")
        return user

    return _dep
