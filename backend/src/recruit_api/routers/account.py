"""/api/v1/me — account self-service: password, email, delete."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from ..config import Settings
from ..schemas.account import ChangeEmailIn, ChangePasswordIn, DeleteAccountIn
from ..security.deps import CurrentUser, get_account_service, get_settings_dep
from ..services.account_service import AccountService
from .auth import _clear_refresh_cookie

router = APIRouter(prefix="/me", tags=["account"])

SvcDep = Annotated[AccountService, Depends(get_account_service)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn,
    user: CurrentUser,
    svc: SvcDep,
    response: Response,
    settings: SettingsDep,
) -> None:
    await svc.change_password(user, body.current_password, body.new_password)
    _clear_refresh_cookie(response, settings)


@router.post("/email", status_code=status.HTTP_202_ACCEPTED)
async def request_email_change(
    body: ChangeEmailIn, user: CurrentUser, svc: SvcDep
) -> dict[str, str]:
    await svc.request_email_change(user, body.new_email, body.current_password)
    return {"status": "confirmation_sent"}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: DeleteAccountIn,
    user: CurrentUser,
    svc: SvcDep,
    response: Response,
    settings: SettingsDep,
) -> None:
    await svc.delete_account(user, body.password, body.confirm_email)
    _clear_refresh_cookie(response, settings)
