"""Aggregates for the dashboard: run activity, match counts, a 14-day sparkline,
and the top missing skills."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.run import JobMatch, MatchStatus, Run


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summary(self, user_id: uuid.UUID) -> dict:
        now = datetime.now(UTC)
        since_30 = now - timedelta(days=30)

        runs_30d = (
            await self.db.scalar(
                select(func.count())
                .select_from(Run)
                .where(Run.user_id == user_id, Run.created_at >= since_30)
            )
            or 0
        )

        last_run = await self.db.scalar(
            select(Run).where(Run.user_id == user_id).order_by(Run.created_at.desc()).limit(1)
        )

        async def match_count(*extra) -> int:
            return (
                await self.db.scalar(
                    select(func.count())
                    .select_from(JobMatch)
                    .where(JobMatch.user_id == user_id, *extra)
                )
                or 0
            )

        matches_total = await match_count()
        matches_new = await match_count(JobMatch.status == MatchStatus.new)
        applied_count = await match_count(JobMatch.status == MatchStatus.applied)

        # ── 14-day sparkline: avg match % + count per day ────────────────
        day = func.date_trunc("day", func.timezone("UTC", JobMatch.created_at))
        rows = await self.db.execute(
            select(day.label("d"), func.avg(JobMatch.match_percentage), func.count())
            .where(JobMatch.user_id == user_id, JobMatch.created_at >= now - timedelta(days=14))
            .group_by("d")
        )
        by_day: dict[str, tuple[int, int]] = {}
        for d, avg, n in rows:
            by_day[d.date().isoformat()] = (round(float(avg or 0)), int(n))

        series = []
        for i in range(13, -1, -1):
            key = (now - timedelta(days=i)).date().isoformat()
            pct, cnt = by_day.get(key, (0, 0))
            series.append({"date": key, "pct": pct, "count": cnt})

        # ── top missing skills across recent matches ────────────────────
        skill_rows = await self.db.scalars(
            select(JobMatch.missing_skills).where(
                JobMatch.user_id == user_id, JobMatch.created_at >= since_30
            )
        )
        tally: Counter[str] = Counter()
        for arr in skill_rows:
            tally.update(s for s in (arr or []) if s)
        top_missing = [{"skill": s, "n": n} for s, n in tally.most_common(8)]

        return {
            "runs_30d": runs_30d,
            "last_run": (
                {"status": str(last_run.status), "at": last_run.created_at.isoformat()}
                if last_run is not None
                else None
            ),
            "matches_total": matches_total,
            "matches_new": matches_new,
            "applied_count": applied_count,
            "match_rate_series": series,
            "top_missing_skills": top_missing,
        }
