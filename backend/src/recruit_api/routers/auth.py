"""/api/v1/auth — signup, login, refresh, logout, verify-email, forgot, reset."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from ..config import Settings
from ..errors import AuthError
from ..schemas.auth import (
    ForgotPasswordIn,
    LoginIn,
    ResetPasswordIn,
    SignupIn,
    TokenOut,
    VerifyEmailIn,
)
from ..schemas.user import UserOut
from ..security.deps import get_auth_service, get_settings_dep
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "recruit_refresh"
REFRESH_PATH = "/api/v1/auth"

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def _set_refresh_cookie(resp: Response, raw: str, settings: Settings) -> None:
    resp.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.is_prod,
        samesite="lax",
        path=REFRESH_PATH,
    )


def _clear_refresh_cookie(resp: Response, settings: Settings) -> None:
    resp.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


def _agent_ip(request: Request) -> tuple[str, str]:
    return request.headers.get("user-agent", ""), (request.client.host if request.client else "")


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupIn, svc: AuthServiceDep) -> UserOut:
    user = await svc.signup(body.email, body.password, body.full_name)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn, request: Request, response: Response, svc: AuthServiceDep, settings: SettingsDep
) -> TokenOut:
    ua, ip = _agent_ip(request)
    access, raw_refresh, ttl = await svc.login(body.email, body.password, user_agent=ua, ip=ip)
    _set_refresh_cookie(response, raw_refresh, settings)
    return TokenOut(access_token=access, expires_in=ttl)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    request: Request, response: Response, svc: AuthServiceDep, settings: SettingsDep
) -> TokenOut:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise AuthError("no refresh token")
    ua, ip = _agent_ip(request)
    access, new_raw, ttl = await svc.refresh(raw, user_agent=ua, ip=ip)
    _set_refresh_cookie(response, new_raw, settings)
    return TokenOut(access_token=access, expires_in=ttl)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request, response: Response, svc: AuthServiceDep, settings: SettingsDep
) -> None:
    await svc.logout(request.cookies.get(REFRESH_COOKIE))
    _clear_refresh_cookie(response, settings)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(body: VerifyEmailIn, svc: AuthServiceDep) -> None:
    await svc.verify_email(body.token)


@router.post("/forgot", status_code=status.HTTP_204_NO_CONTENT)
async def forgot(body: ForgotPasswordIn, svc: AuthServiceDep) -> None:
    await svc.start_password_reset(body.email)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset(body: ResetPasswordIn, svc: AuthServiceDep) -> None:
    await svc.finish_password_reset(body.token, body.password)
