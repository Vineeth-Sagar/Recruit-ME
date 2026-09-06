"""The engine contract: types build, ports are Protocols, run_engine keeps the
agreed signature. Its behaviour is covered in test_engine.py."""

import inspect

from recruit_engine import (
    EngineInput,
    EngineResult,
    ProfileSpec,
    ResumeParse,
    SourceCredential,
)
from recruit_engine.engine import run_engine
from recruit_engine.ports import Clock, LLMClient, RateLimiter, SeenStore


def _make_input() -> EngineInput:
    return EngineInput(
        run_id="run-1",
        tenant_id="tenant-1",
        profile=ProfileSpec(
            profile_id="p1",
            target_roles=["Backend Engineer"],
            locations=["Bengaluru"],
        ),
        resumes=[
            ResumeParse(resume_id="r1", parsed={"technical_skills": ["Python"]}, skills=["Python"])
        ],
        enabled_sources=["wellfound", "yc"],
        credentials=[SourceCredential(site="wellfound", auth_type="none")],
    )


def test_engine_input_assembles_and_defaults_apply():
    inp = _make_input()
    assert inp.profile.big3_optin is False
    assert inp.limits.match_batch_size == 20


def test_result_is_constructible_with_defaults():
    res = EngineResult(run_id="run-1")
    assert res.matched == []
    assert res.ai_degraded is False


def test_run_engine_signature_is_the_agreed_contract():
    sig = inspect.signature(run_engine)
    assert list(sig.parameters) == [
        "inp",
        "seen",
        "rate_limiter",
        "llm",
        "clock",
        "on_step",
    ]
    assert inspect.iscoroutinefunction(run_engine)


def test_ports_are_runtime_checkable_protocols():
    for proto in (SeenStore, RateLimiter, LLMClient, Clock):
        assert hasattr(proto, "_is_runtime_protocol")
