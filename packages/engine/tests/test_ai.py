"""
Unit tests for recruit_engine.ai  (← job_hunter/ai_engine.py).

These never call the real OpenRouter API — they pin the pure logic around it
(JSON extraction, the keyword fallback, résumé hashing).
"""

import hashlib

from recruit_engine import ai

# ── _extract_json ────────────────────────────────────────────────────────


def test_extract_json_direct():
    assert ai._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_markdown_fence():
    text = 'Sure, here you go:\n```json\n{"a": 1, "b": [1, 2]}\n```'
    assert ai._extract_json(text) == {"a": 1, "b": [1, 2]}


def test_extract_json_embedded_object_with_surrounding_text():
    text = 'Here is the result: {"a": 1} — hope that helps!'
    assert ai._extract_json(text) == {"a": 1}


def test_extract_json_garbage_returns_empty_dict():
    assert ai._extract_json("not json at all") == {}


def test_extract_json_empty_string_returns_empty_dict():
    assert ai._extract_json("") == {}


# ── _fallback_keyword_score ──────────────────────────────────────────────


def test_fallback_keyword_score_marks_itself_as_ai_unavailable():
    result = ai._fallback_keyword_score(
        {"title": "Python Developer", "description": "Looking for a Python engineer."},
        {"technical_skills": ["Python"], "languages": [], "frameworks": [], "tools": []},
    )
    assert result["why_good_fit"] == ai.AI_UNAVAILABLE_MARKER


def test_fallback_keyword_score_finds_matching_skill():
    result = ai._fallback_keyword_score(
        {"title": "Python Developer", "description": "Looking for a Python backend engineer."},
        {"technical_skills": ["Python", "React"], "languages": [], "frameworks": [], "tools": []},
    )
    assert "python" in [s.lower() for s in result["matched_skills"]]
    assert 0 < result["match_percentage"] <= 100


def test_fallback_keyword_score_no_skills_scores_zero_not_error():
    result = ai._fallback_keyword_score({"title": "", "description": ""}, {})
    assert result["match_percentage"] == 0


# ── compute_resume_hash ──────────────────────────────────────────────────


def test_compute_resume_hash_is_stable_for_identical_content(tmp_path):
    pdf_a = tmp_path / "a.pdf"
    pdf_a.write_bytes(b"hello world")
    pdf_b = tmp_path / "b.pdf"
    pdf_b.write_bytes(b"hello world")

    assert ai.compute_resume_hash(pdf_a) == ai.compute_resume_hash(pdf_b)
    assert ai.compute_resume_hash(pdf_a) == hashlib.sha256(b"hello world").hexdigest()


def test_compute_resume_hash_changes_when_content_changes(tmp_path):
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"version one")
    before = ai.compute_resume_hash(pdf)

    pdf.write_bytes(b"version two")
    after = ai.compute_resume_hash(pdf)

    assert before != after
