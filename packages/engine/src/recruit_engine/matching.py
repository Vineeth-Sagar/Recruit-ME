"""
Job ↔ résumé scoring.

``batch_match`` scores every job against every résumé (keeping the best), in
batches, through an injected ``LLMClient``. It never sleeps and never builds a
client — the caller owns pacing and concurrency (a semaphore here bounds
in-flight LLM calls; the per-site rate limiting happens in the worker).
"""

from __future__ import annotations

import asyncio
import json
import logging

from .ai import AI_UNAVAILABLE_MARKER, _extract_json, _fallback_keyword_score, _resume_skills
from .ports import LLMClient
from .types import JobPosting, MatchedJob, ResumeParse

logger = logging.getLogger(__name__)

BATCH_JOB_MATCH_PROMPT = """
You are a professional talent-acquisition expert. Evaluate how well this candidate's résumé
matches the given batch of jobs. Return ONLY a valid JSON object (no markdown, no extra text):
a dictionary mapping the string index of each job to its evaluation.

{{
  "0": {{
    "match_percentage": <integer 0-100>,
    "matched_skills": ["skills from the résumé that match the job"],
    "missing_skills": ["important job skills not in the résumé"],
    "why_good_fit": "1-2 sentence explanation",
    "urgency": "HIGH | MEDIUM | LOW",
    "recommended_action": "Apply immediately | Apply this week | Optional | Skip"
  }},
  "1": {{ ... }}
}}

Scoring guide: 80-100 strong · 60-79 good · 40-59 partial · 20-39 weak · 0-19 poor.

Candidate:
- Skills: {skills}
- Branch: {branch}
- Projects/experience: {projects}
- Summary: {summary}

Jobs:
{jobs_json}
"""

_DEFAULT_RESULT = {
    "match_percentage": 0,
    "matched_skills": [],
    "missing_skills": [],
    "why_good_fit": "",
    "urgency": "LOW",
    "recommended_action": "Skip",
}


def _job_for_prompt(idx: int, job: JobPosting) -> dict:
    return {
        "index": str(idx),
        "title": job.title,
        "company": job.company,
        "description": (job.description or "")[:1000],
    }


async def _score_batch(
    batch: list[JobPosting], resume: ResumeParse, llm: LLMClient
) -> dict[str, dict]:
    parsed = resume.parsed
    prompt = BATCH_JOB_MATCH_PROMPT.format(
        skills=", ".join(_resume_skills(parsed)[:40]),
        branch=parsed.get("branch", ""),
        projects="; ".join(
            (parsed.get("projects", []) or []) + (parsed.get("internships", []) or [])
        )[:800],
        summary=str(parsed.get("summary", ""))[:400],
        jobs_json=json.dumps([_job_for_prompt(i, j) for i, j in enumerate(batch)], indent=2),
    )
    try:
        raw = await llm.complete(prompt, temperature=0.0)
    except Exception as e:  # noqa: BLE001
        logger.warning("batch match LLM call failed: %s", e)
        raw = ""

    result = _extract_json(raw)
    if not isinstance(result, dict):
        result = {}
    for i, job in enumerate(batch):
        key = str(i)
        if key not in result or "match_percentage" not in result.get(key, {}):
            result[key] = _fallback_keyword_score(
                {"title": job.title, "description": job.description}, parsed
            )
    return result


def _to_matched(job: JobPosting, res: dict, profile_id: str) -> MatchedJob:
    return MatchedJob(
        job=job,
        match_percentage=int(res.get("match_percentage", 0) or 0),
        matched_skills=list(res.get("matched_skills", []) or []),
        missing_skills=list(res.get("missing_skills", []) or []),
        why_fit=str(res.get("why_good_fit", "")),
        urgency=str(res.get("urgency", "LOW")).upper(),
        recommended_action=str(res.get("recommended_action", "Skip")),
        matched_profile_id=profile_id,
    )


async def batch_match(
    jobs: list[JobPosting],
    resumes: list[ResumeParse],
    llm: LLMClient,
    *,
    batch_size: int = 20,
    max_concurrency: int = 1,
) -> tuple[list[MatchedJob], dict[str, int], bool]:
    """Return (best match per job, missing-skill tally, ai_degraded)."""
    if not jobs or not resumes:
        return [], {}, False

    sem = asyncio.Semaphore(max(1, max_concurrency))

    async def run_batch(
        resume: ResumeParse, start: int
    ) -> tuple[int, ResumeParse, dict[str, dict]]:
        async with sem:
            return start, resume, await _score_batch(jobs[start : start + batch_size], resume, llm)

    tasks = [
        run_batch(resume, start) for resume in resumes for start in range(0, len(jobs), batch_size)
    ]

    best: dict[int, MatchedJob] = {}
    for start, resume, scored in await asyncio.gather(*tasks):
        for offset in range(len(jobs[start : start + batch_size])):
            job_idx = start + offset
            res = scored.get(str(offset), dict(_DEFAULT_RESULT))
            candidate = _to_matched(jobs[job_idx], res, resume.resume_id)
            if job_idx not in best or candidate.match_percentage > best[job_idx].match_percentage:
                best[job_idx] = candidate

    matched = [best[i] for i in sorted(best)]
    tally: dict[str, int] = {}
    for m in matched:
        for skill in m.missing_skills:
            tally[skill] = tally.get(skill, 0) + 1

    degraded = bool(matched) and all(m.why_fit == AI_UNAVAILABLE_MARKER for m in matched)
    return matched, tally, degraded
