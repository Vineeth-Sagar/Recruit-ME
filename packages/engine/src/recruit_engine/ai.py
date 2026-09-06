"""
ai.py  (← job_hunter/ai_engine.py)

Résumé parsing helpers and the shared JSON-extraction / keyword-fallback logic.
Job–résumé *scoring* lives in :mod:`recruit_engine.matching`.

Phase 4.4: the module-global OpenAI client, the in-request ``time.sleep`` pacing,
and the legacy ``api_key``-taking functions are gone — callers pass an
``LLMClient`` (:mod:`recruit_engine.ports`) instead.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ports import LLMClient

logger = logging.getLogger(__name__)

# Set on a job's ``why_good_fit`` when its LLM score fell back to keyword
# overlap. If *every* job in a run carries this, the AI backend is down and the
# caller reports ``ai_degraded`` instead of a misleading "no matches today".
AI_UNAVAILABLE_MARKER = "Keyword-based match (AI scoring unavailable)"


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from an LLM reply (bare, fenced, or embedded)."""
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, AttributeError):
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def _resume_skills(parsed: dict) -> list[str]:
    return (
        list(parsed.get("technical_skills", []) or [])
        + list(parsed.get("languages", []) or [])
        + list(parsed.get("frameworks", []) or [])
        + list(parsed.get("tools", []) or [])
    )


def _fallback_keyword_score(job: dict, resume_profile: dict) -> dict:
    """Keyword-overlap score used when the LLM call fails for a job."""
    all_skills = {s.lower() for s in _resume_skills(resume_profile)}
    desc_lower = (job.get("description", "") + " " + job.get("title", "")).lower()
    matched = [s for s in all_skills if s in desc_lower]
    pct = min(int((len(matched) / max(len(all_skills), 1)) * 100), 100)
    return {
        "match_percentage": pct,
        "matched_skills": matched[:10],
        "missing_skills": [],
        "why_good_fit": AI_UNAVAILABLE_MARKER,
        "urgency": "MEDIUM" if pct >= 60 else "LOW",
        "recommended_action": "Apply this week" if pct >= 60 else "Optional",
        "job_tags": [],
    }


# ─────────────────────────────────────────────────────────────────
# PDF → text
# ─────────────────────────────────────────────────────────────────


def compute_resume_hash(pdf_path: Path) -> str:
    """SHA-256 of a PDF's bytes — lets callers skip re-parsing an unchanged file."""
    return hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        return extract_text_from_pdf_bytes(Path(pdf_path).read_bytes())
    except Exception as e:  # noqa: BLE001
        logger.error("PDF read error for %s: %s", pdf_path, e)
        return ""


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Plain text from PDF bytes; "" for an image-only / unreadable PDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed.")
        return ""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(pages).strip()
    except Exception as e:  # noqa: BLE001
        logger.error("PDF parse error: %s", e)
        return ""


# ─────────────────────────────────────────────────────────────────
# Résumé parsing
# ─────────────────────────────────────────────────────────────────

RESUME_PARSE_PROMPT = """
You are an expert resume parser. Analyse the resume text below and return ONLY a valid JSON object
(no markdown, no explanation) with this exact schema:

{{
  "name": "string",
  "branch": "string (e.g. CSE, ECE, IT, Mechanical)",
  "graduation_year": "number (e.g. 2027)",
  "college": "string",
  "technical_skills": ["list", "of", "skills"],
  "soft_skills": ["list"],
  "languages": ["Python", "Java", ...],
  "frameworks": ["React", "TensorFlow", ...],
  "tools": ["Git", "Docker", ...],
  "domains": ["Machine Learning", "Web Dev", ...],
  "certifications": ["list"],
  "projects": ["brief project descriptions"],
  "internships": ["brief internship descriptions"],
  "cgpa": "string or null",
  "summary": "3-line professional summary of this candidate"
}}

Resume text:
{resume_text}
"""


def skills_from_parse(parsed: dict) -> list[str]:
    """Flatten a parsed résumé's skill lists into a deduped list."""
    seen: dict[str, None] = {}
    for item in _resume_skills(parsed):
        s = str(item).strip()
        if s and s.lower() not in {k.lower() for k in seen}:
            seen[s] = None
    return list(seen)


async def parse_resume_text(text: str, llm: LLMClient) -> dict:
    """Parse résumé text into structured JSON via an injected LLM client."""
    if not text.strip():
        return {"error": "no extractable text"}
    raw = await llm.complete(RESUME_PARSE_PROMPT.format(resume_text=text[:6000]), temperature=0.0)
    parsed = _extract_json(raw)
    if not parsed:
        logger.warning("resume parse returned no JSON")
        return {"technical_skills": [], "summary": "", "error": "unparseable LLM response"}
    return parsed
