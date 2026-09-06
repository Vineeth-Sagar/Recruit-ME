"""/api/v1/me — account self-service: password, email, delete."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from ..schemas.account import ChangeEmailIn, ChangePasswordIn, DeleteAccountIn
from ..security.deps import CurrentUser, get_account_service
from ..services.account_service import AccountService
from .auth import REFRESH_COOKIE, REFRESH_PATH

router = APIRouter(prefix="/me", tags=["account"])

SvcDep = Annotated[AccountService, Depends(get_account_service)]


def _drop_refresh(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn, user: CurrentUser, svc: SvcDep, response: Response
) -> None:
    await svc.change_password(user, body.current_password, body.new_password)
    _drop_refresh(response)


@router.post("/email", status_code=status.HTTP_202_ACCEPTED)
async def request_email_change(
    body: ChangeEmailIn, user: CurrentUser, svc: SvcDep
) -> dict[str, str]:
    await svc.request_email_change(user, body.new_email, body.current_password)
    return {"status": "confirmation_sent"}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: DeleteAccountIn, user: CurrentUser, svc: SvcDep, response: Response
) -> None:
    await svc.delete_account(user, body.password, body.confirm_email)
    _drop_refresh(response)
