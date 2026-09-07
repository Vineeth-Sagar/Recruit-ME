"""/api/v1/resumes — upload a PDF, then poll for the parse result."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from pydantic import BaseModel

from ..schemas.resume import ResumeOut, ResumeParseOut
from ..security.deps import CurrentUser, get_resume_service
from ..services.resume_service import PayloadTooLargeError, ResumeService


class ResumeLinkIn(BaseModel):
    job_profile_id: uuid.UUID | None = None


router = APIRouter(prefix="/resumes", tags=["resumes"])

SvcDep = Annotated[ResumeService, Depends(get_resume_service)]


async def _to_out(svc: ResumeService, resume) -> ResumeOut:
    out = ResumeOut.model_validate(resume)
    parse = await svc.latest_parse(resume.id)
    if parse is not None:
        out.parse = ResumeParseOut.model_validate(parse)
    return out


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    request: Request,
    user: CurrentUser,
    svc: SvcDep,
    file: Annotated[UploadFile, File()],
    job_profile_id: Annotated[uuid.UUID | None, Form()] = None,
) -> ResumeOut:
    # Reject on the declared size before reading the body into memory.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > svc.max_bytes * 2:
        raise PayloadTooLargeError(f"upload exceeds {svc.max_bytes} bytes")

    # Read in bounded chunks; abort as soon as the cap is exceeded.
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1 << 20):
        total += len(chunk)
        if total > svc.max_bytes:
            raise PayloadTooLargeError(f"résumé exceeds {svc.max_bytes} bytes")
        chunks.append(chunk)

    resume = await svc.upload(
        user.id, file.filename or "resume.pdf", b"".join(chunks), job_profile_id=job_profile_id
    )
    return await _to_out(svc, resume)


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> ResumeOut:
    return await _to_out(svc, await svc.get(user.id, resume_id))


@router.patch("/{resume_id}", response_model=ResumeOut)
async def link_resume(
    resume_id: uuid.UUID, body: ResumeLinkIn, user: CurrentUser, svc: SvcDep
) -> ResumeOut:
    resume = await svc.set_profile(user.id, resume_id, body.job_profile_id)
    return await _to_out(svc, resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> None:
    await svc.delete(user.id, resume_id)
