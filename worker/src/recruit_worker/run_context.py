"""Assemble an ``EngineInput`` (+ the tenant's known job-hashes) from DB rows."""

from __future__ import annotations

from recruit_api.config import get_settings
from recruit_api.models.job_profile import JobProfile
from recruit_api.models.resume import Resume, ResumeParse, ResumeStatus
from recruit_api.models.run import Run
from recruit_api.security.crypto import Envelope, build_envelope
from recruit_engine.types import EngineInput, EngineLimits, ProfileSpec
from recruit_engine.types import ResumeParse as EngineResumeParse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .adapters.seen_store_pg import load_known_hashes
from .credentials import load_source_credentials


async def build_input(
    db: AsyncSession, run: Run, *, envelope: Envelope | None = None
) -> tuple[EngineInput, set[str]]:
    profile = await db.get(JobProfile, run.job_profile_id)
    if profile is None:
        raise RuntimeError(f"job profile {run.job_profile_id} vanished")

    resume_rows = list(
        await db.scalars(
            select(Resume).where(
                Resume.user_id == run.user_id,
                Resume.job_profile_id == run.job_profile_id,
                Resume.status == ResumeStatus.parsed,
            )
        )
    )
    resumes: list[EngineResumeParse] = []
    for r in resume_rows:
        parse = await db.scalar(
            select(ResumeParse)
            .where(ResumeParse.resume_id == r.id)
            .order_by(ResumeParse.created_at.desc())
            .limit(1)
        )
        if parse is not None:
            resumes.append(
                EngineResumeParse(
                    resume_id=str(r.id),
                    parsed=dict(parse.parsed_json),
                    skills=list(parse.skills),
                )
            )

    spec = ProfileSpec(
        profile_id=str(profile.id),
        target_roles=list(profile.target_roles),
        locations=list(profile.locations),
        job_types=list(profile.job_types),
        min_match_percent=profile.min_match_percent,
        must_have_skills=list(profile.must_have_skills),
        nice_to_have_skills=list(profile.nice_to_have_skills),
        exclude_companies=list(profile.exclude_companies),
        watchlist_companies=list(profile.watchlist_companies),
        big3_optin=profile.big3_optin,
    )

    known = await load_known_hashes(db, run.user_id)

    envelope = envelope or build_envelope(get_settings())
    credentials = await load_source_credentials(db, run.user_id, envelope)

    inp = EngineInput(
        run_id=str(run.id),
        tenant_id=str(run.user_id),
        profile=spec,
        resumes=resumes,
        enabled_sources=list(profile.enabled_sources),
        credentials=credentials,
        limits=EngineLimits(),
    )
    return inp, known
