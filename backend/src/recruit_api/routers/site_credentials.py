"""/api/v1/me/site-credentials — sealed per-site credentials.

Every response is a :class:`SiteCredentialOut`, which by construction has no
secret field. This router only ever seals a secret; opening one happens in the
worker.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ..models.site_credential import CredentialSite
from ..schemas.site_credential import SiteCredentialIn, SiteCredentialOut
from ..security.deps import CurrentUser, get_site_credential_service
from ..services.site_credential_service import SiteCredentialService

router = APIRouter(prefix="/me/site-credentials", tags=["site-credentials"])

SvcDep = Annotated[SiteCredentialService, Depends(get_site_credential_service)]


@router.get("", response_model=list[SiteCredentialOut])
async def list_credentials(user: CurrentUser, svc: SvcDep) -> list[SiteCredentialOut]:
    return [SiteCredentialOut.model_validate(c) for c in await svc.list(user.id)]


@router.put("/{site}", response_model=SiteCredentialOut)
async def put_credential(
    site: CredentialSite, body: SiteCredentialIn, user: CurrentUser, svc: SvcDep
) -> SiteCredentialOut:
    return SiteCredentialOut.model_validate(await svc.upsert(user.id, site, body))


@router.post(
    "/{site}:verify", response_model=SiteCredentialOut, status_code=status.HTTP_202_ACCEPTED
)
async def verify_credential(
    site: CredentialSite, user: CurrentUser, svc: SvcDep
) -> SiteCredentialOut:
    return SiteCredentialOut.model_validate(await svc.verify(user.id, site))


@router.delete("/{site}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(site: CredentialSite, user: CurrentUser, svc: SvcDep) -> None:
    await svc.delete(user.id, site)
