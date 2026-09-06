"""Seed a demo tenant so the app is worth looking at on first boot.

    uv run python scripts/seed.py          # against $DATABASE_URL
    docker compose run --rm seed           # inside the stack

Creates (or resets) ``demo@recruit.me`` / ``demo-password-123`` with one active
job profile, a parsed résumé, three finished runs, ~40 job matches spread across
the last two weeks, and a notification per run. Re-running wipes the demo user
first (FK cascades clear the rest), so it is safe to call repeatedly.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import UTC, datetime, timedelta

from recruit_api.config import get_settings
from recruit_api.models.job_profile import JobProfile
from recruit_api.models.resume import Resume, ResumeParse, ResumeStatus
from recruit_api.models.run import (
    JobMatch,
    MatchStatus,
    Notification,
    Run,
    RunSource,
    RunStatus,
    RunStep,
    RunTrigger,
)
from recruit_api.models.user import User, UserPlan, UserRole, UserStatus
from recruit_api.security.passwords import hash_password
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DEMO_EMAIL = "demo@recruit.me"
DEMO_PASSWORD = "demo-password-123"

_RNG = random.Random(20260906)

COMPANIES = [
    "Stripe",
    "Vercel",
    "Linear",
    "Ramp",
    "Notion",
    "Retool",
    "Supabase",
    "PlanetScale",
    "Fly.io",
    "Render",
    "Neon",
    "Modal",
    "Replit",
    "Sentry",
    "Cloudflare",
    "Datadog",
    "HashiCorp",
    "Temporal",
    "Airbyte",
    "Dagster",
]
TITLES = [
    "Backend Engineer",
    "Senior Backend Engineer",
    "Platform Engineer",
    "Full-Stack Engineer",
    "Site Reliability Engineer",
    "Data Platform Engineer",
    "Infrastructure Engineer",
    "Software Engineer, Payments",
]
LOCATIONS = ["Remote", "Bengaluru", "Remote (India)", "Hybrid — Bengaluru"]
SOURCES = ["wellfound", "yc", "hackernews"]
SKILL_POOL = [
    "Kubernetes",
    "Kafka",
    "gRPC",
    "Terraform",
    "GraphQL",
    "Rust",
    "Go",
    "Redis",
    "PostgreSQL",
    "AWS",
    "Airflow",
    "ClickHouse",
    "OpenTelemetry",
]
URGENCY = ["LOW", "MEDIUM", "HIGH"]
ACTIONS = ["review", "apply_now", "apply_soon", "skip"]
STATUS_WEIGHTS = (
    [MatchStatus.new] * 6
    + [MatchStatus.saved] * 2
    + [MatchStatus.applied]
    + [MatchStatus.dismissed]
)


def _hash(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


async def _reset_demo(db) -> None:
    existing = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing is not None:
        await db.delete(existing)  # cascades to profiles / resumes / runs / matches
        await db.flush()


def _make_user() -> User:
    return User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="Demo Candidate",
        role=UserRole.user,
        plan=UserPlan.pro,
        status=UserStatus.active,
    )


def _make_profile(user_id) -> JobProfile:
    return JobProfile(
        user_id=user_id,
        name="Backend / platform roles",
        is_active=True,
        target_roles=["Backend Engineer", "Platform Engineer"],
        locations=["Remote", "Bengaluru"],
        job_types=["Full-time"],
        enabled_sources=["wellfound", "yc", "hackernews"],
        must_have_skills=["Python", "PostgreSQL", "Docker"],
        nice_to_have_skills=["Kubernetes", "Go", "Kafka"],
        exclude_companies=["Acme Staffing"],
        watchlist_companies=["Stripe", "Linear"],
        min_match_percent=55,
        min_salary=0,
        big3_optin=False,
        schedule_cron="0 7 * * *",
        timezone="Asia/Kolkata",
    )


def _make_resume(user_id, profile_id) -> Resume:
    return Resume(
        user_id=user_id,
        job_profile_id=profile_id,
        original_filename="demo_candidate_cv.pdf",
        storage_key=f"resumes/{user_id}/demo.pdf",
        content_sha256=_hash("demo-resume", user_id),
        size_bytes=48_213,
        mime="application/pdf",
        status=ResumeStatus.parsed,
    )


def _make_parse(resume_id) -> ResumeParse:
    return ResumeParse(
        resume_id=resume_id,
        model="seed/demo",
        parsed_json={
            "name": "Demo Candidate",
            "technical_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            "years_experience": 5,
            "summary": "Backend engineer, distributed systems and payments.",
        },
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Redis"],
        tokens_used=1234,
    )


def _make_run(user_id, profile_id, *, days_ago: int, status: RunStatus, trigger: RunTrigger) -> Run:
    started = datetime.now(UTC) - timedelta(days=days_ago, minutes=_RNG.randint(0, 240))
    finished = started + timedelta(seconds=_RNG.randint(40, 190))
    sources_failed = 1 if status == RunStatus.partial else 0
    return Run(
        user_id=user_id,
        job_profile_id=profile_id,
        trigger=trigger,
        status=status,
        idempotency_key=f"seed:{profile_id}:{days_ago}",
        attempt=1,
        queued_at=started - timedelta(seconds=3),
        started_at=started,
        finished_at=finished,
        notified_at=finished + timedelta(seconds=5),
        worker_id="seed-worker",
        report_key=f"reports/{user_id}/{days_ago}.xlsx",
        stats={
            "scraped": _RNG.randint(60, 140),
            "matched": 0,  # filled in after matches are attached
            "sources_ok": len(SOURCES) - sources_failed,
            "sources_failed": sources_failed,
        },
        created_at=started,
        updated_at=finished,
    )


def _make_run_children(run_id, started_at: datetime, *, partial: bool) -> list:
    rows: list = []
    at = started_at
    for name in ("scrape", "dedupe", "match", "report"):
        at = at + timedelta(seconds=_RNG.randint(3, 20))
        rows.append(RunStep(run_id=run_id, name=name, status="succeeded", detail={}, at=at))
    for i, src in enumerate(SOURCES):
        failed = partial and i == len(SOURCES) - 1
        rows.append(
            RunSource(
                run_id=run_id,
                source=src,
                status="failed" if failed else "succeeded",
                jobs_found=0 if failed else _RNG.randint(15, 60),
                latency_ms=_RNG.randint(400, 5200),
                error="429 Too Many Requests" if failed else None,
            )
        )
    return rows


def _make_match(user_id, run_id, profile_id, idx: int) -> JobMatch:
    company = _RNG.choice(COMPANIES)
    title = _RNG.choice(TITLES)
    pct = _RNG.randint(42, 96)
    missing = _RNG.sample(SKILL_POOL, _RNG.randint(0, 3))
    matched = _RNG.sample(["Python", "PostgreSQL", "Docker", "FastAPI", "AWS"], _RNG.randint(2, 5))
    created = datetime.now(UTC) - timedelta(days=_RNG.randint(0, 13), hours=_RNG.randint(0, 23))
    return JobMatch(
        user_id=user_id,
        run_id=run_id,
        job_profile_id=profile_id,
        external_hash=_hash(company, title, idx),
        source=_RNG.choice(SOURCES),
        company=company,
        title=title,
        location=_RNG.choice(LOCATIONS),
        url=f"https://example.com/jobs/{_hash(company, title, idx)[:12]}",
        description_excerpt=f"{title} at {company}. Own services end to end.",
        salary=_RNG.choice(["", "₹40–60L", "$150k–190k", "$120k–160k"]),
        posted_date=(created - timedelta(days=_RNG.randint(0, 4))).date().isoformat(),
        match_percentage=pct,
        matched_skills=matched,
        missing_skills=missing,
        why_fit="Strong overlap on the backend stack; distributed-systems experience lines up.",
        urgency=_RNG.choice(URGENCY),
        recommended_action=_RNG.choice(ACTIONS),
        matched_profile_id=str(profile_id),
        status=_RNG.choice(STATUS_WEIGHTS),
        applied_at=created if _RNG.random() < 0.1 else None,
        created_at=created,
        updated_at=created,
    )


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        await _reset_demo(db)

        user = _make_user()
        db.add(user)
        await db.flush()

        profile = _make_profile(user.id)
        db.add(profile)
        await db.flush()

        resume = _make_resume(user.id, profile.id)
        db.add(resume)
        await db.flush()
        db.add(_make_parse(resume.id))

        plan = [
            (9, RunStatus.succeeded, RunTrigger.scheduled, 14, False),
            (5, RunStatus.succeeded, RunTrigger.scheduled, 16, False),
            (1, RunStatus.partial, RunTrigger.manual, 12, True),
        ]
        total_matches = 0
        for days_ago, status, trigger, n_matches, partial in plan:
            run = _make_run(user.id, profile.id, days_ago=days_ago, status=status, trigger=trigger)
            run.stats = {**run.stats, "matched": n_matches}
            db.add(run)
            await db.flush()

            db.add_all(_make_run_children(run.id, run.started_at, partial=partial))
            db.add_all(
                _make_match(user.id, run.id, profile.id, total_matches + i)
                for i in range(n_matches)
            )
            total_matches += n_matches

            db.add(
                Notification(
                    user_id=user.id,
                    run_id=run.id,
                    channel="email",
                    to_addr=DEMO_EMAIL,
                    subject=f"{n_matches} new matches from your job hunt",
                    status="sent",
                    provider_message_id=f"seed-{run.id}",
                )
            )

        await db.commit()

    await engine.dispose()
    print(
        f"seeded {DEMO_EMAIL} / {DEMO_PASSWORD}: 1 profile, 1 résumé, "
        f"{len(plan)} runs, {total_matches} matches"
    )


if __name__ == "__main__":
    asyncio.run(main())
