from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class ChangeEmailIn(BaseModel):
    new_email: EmailStr
    current_password: str


class ConfirmEmailChangeIn(BaseModel):
    token: str


class DeleteAccountIn(BaseModel):
    password: str
    # The web UI makes the user type their email to arm the button; the server
    # re-checks it so a bare API call can't skip the speed bump.
    confirm_email: EmailStr
