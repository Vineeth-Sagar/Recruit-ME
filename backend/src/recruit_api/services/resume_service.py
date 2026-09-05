"""Résumé upload: validate, store to object storage, enqueue a parse job."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import AppError, NotFoundError
from ..models.job_profile import JobProfile
from ..models.resume import Resume, ResumeParse, ResumeStatus
from ..queue import Enqueue
from .object_store import ObjectStore

_PDF_MAGIC = b"%PDF-"


class UnsupportedMediaError(AppError):
    status_code = 415
    code = "unsupported_media_type"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


def resume_key(user_id: uuid.UUID, resume_id: uuid.UUID) -> str:
    return f"resumes/{user_id}/{resume_id}.pdf"


class ResumeService:
    def __init__(self, db: AsyncSession, store: ObjectStore, enqueue: Enqueue, *, max_bytes: int):
        self.db = db
        self.store = store
        self.enqueue = enqueue
        self.max_bytes = max_bytes

    async def upload(
        self,
        user_id: uuid.UUID,
        filename: str,
        content: bytes,
        *,
        job_profile_id: uuid.UUID | None = None,
    ) -> Resume:
        if not content.startswith(_PDF_MAGIC):
            raise UnsupportedMediaError("only PDF résumés are accepted")
        if len(content) > self.max_bytes:
            raise PayloadTooLargeError(f"résumé exceeds {self.max_bytes} bytes")

        resume = Resume(
            id=uuid.uuid4(),
            user_id=user_id,
            job_profile_id=job_profile_id,
            original_filename=filename[:255],
            storage_key="",  # set below
            content_sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            mime="application/pdf",
            status=ResumeStatus.uploaded,
        )
        resume.storage_key = resume_key(user_id, resume.id)
        self.db.add(resume)
        await self.db.flush()

        await self.store.put(resume.storage_key, content, content_type="application/pdf")
        await self.enqueue("parse_resume", str(resume.id))
        return resume

    async def get(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        resume = await self.db.get(Resume, resume_id)
        if resume is None or resume.user_id != user_id:
            raise NotFoundError("résumé not found")
        return resume

    async def set_profile(
        self, user_id: uuid.UUID, resume_id: uuid.UUID, job_profile_id: uuid.UUID | None
    ) -> Resume:
        resume = await self.get(user_id, resume_id)
        if job_profile_id is not None:
            profile = await self.db.get(JobProfile, job_profile_id)
            if profile is None or profile.user_id != user_id:
                raise NotFoundError("job profile not found")
        resume.job_profile_id = job_profile_id
        await self.db.flush()
        await self.db.refresh(resume)
        return resume

    async def latest_parse(self, resume_id: uuid.UUID) -> ResumeParse | None:
        return await self.db.scalar(
            select(ResumeParse)
            .where(ResumeParse.resume_id == resume_id)
            .order_by(ResumeParse.created_at.desc())
            .limit(1)
        )

    async def delete(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> None:
        resume = await self.get(user_id, resume_id)
        key = resume.storage_key
        await self.db.delete(resume)
        await self.db.flush()
        await self.store.delete(key)

    async def list_for_profile(self, user_id: uuid.UUID, job_profile_id: uuid.UUID) -> list[Resume]:
        rows = await self.db.scalars(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.job_profile_id == job_profile_id)
            .order_by(Resume.created_at.desc())
        )
        return list(rows)
