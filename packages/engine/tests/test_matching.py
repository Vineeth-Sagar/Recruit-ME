"""batch_match: best-of-résumés scoring, keyword fallback, ai_degraded, tally."""

import json

import pytest
from recruit_engine.ai import AI_UNAVAILABLE_MARKER
from recruit_engine.matching import batch_match
from recruit_engine.types import JobPosting, ResumeParse

pytestmark = pytest.mark.asyncio


class FakeLLM:
    def __init__(self, replies: list[str] | None = None, raises: bool = False):
        self._replies = list(replies or [])
        self._raises = raises
        self.calls = 0

    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        self.calls += 1
        if self._raises:
            raise RuntimeError("provider down")
        return self._replies.pop(0) if self._replies else "{}"


def _jobs(n: int) -> list[JobPosting]:
    return [
        JobPosting(
            source="YC",
            company=f"C{i}",
            title=f"Backend Engineer {i}",
            description="Python FastAPI",
        )
        for i in range(n)
    ]


def _resume(rid: str, skills: list[str]) -> ResumeParse:
    return ResumeParse(
        resume_id=rid, parsed={"technical_skills": skills, "summary": "x"}, skills=skills
    )


async def test_scores_from_llm_and_tallies_missing():
    reply = json.dumps(
        {
            "0": {
                "match_percentage": 82,
                "matched_skills": ["Python"],
                "missing_skills": ["Kafka"],
                "why_good_fit": "good",
                "urgency": "HIGH",
            },
            "1": {
                "match_percentage": 40,
                "matched_skills": [],
                "missing_skills": ["Kafka", "Go"],
                "why_good_fit": "meh",
                "urgency": "LOW",
            },
        }
    )
    matched, tally, degraded = await batch_match(
        _jobs(2), [_resume("r1", ["Python"])], FakeLLM([reply])
    )
    assert [m.match_percentage for m in matched] == [82, 40]
    assert matched[0].urgency == "HIGH"
    assert tally == {"Kafka": 2, "Go": 1}
    assert degraded is False


async def test_best_score_across_resumes_wins():
    r1 = json.dumps({"0": {"match_percentage": 30}})
    r2 = json.dumps({"0": {"match_percentage": 75}})
    llm = FakeLLM([r1, r2])
    matched, _, _ = await batch_match(_jobs(1), [_resume("r1", ["A"]), _resume("r2", ["B"])], llm)
    assert matched[0].match_percentage == 75
    assert matched[0].matched_profile_id == "r2"


async def test_llm_failure_falls_back_to_keywords_and_flags_degraded():
    matched, _, degraded = await batch_match(
        _jobs(3), [_resume("r1", ["Python"])], FakeLLM(raises=True)
    )
    assert len(matched) == 3
    assert all(m.why_fit == AI_UNAVAILABLE_MARKER for m in matched)
    assert degraded is True


async def test_empty_inputs():
    assert await batch_match([], [_resume("r1", ["Python"])], FakeLLM()) == ([], {}, False)
    assert await batch_match(_jobs(2), [], FakeLLM()) == ([], {}, False)
