"""parse_resume — fetch the PDF, extract text, ask the LLM for structured JSON,
write a ResumeParse row. Bad input marks the résumé failed (no retry); the
richer retry policy for transient errors lands in Phase 4.4."""

from __future__ import annotations

import logging
import uuid

from recruit_api.models.resume import Resume, ResumeParse, ResumeStatus
from recruit_engine.ai import (
    extract_text_from_pdf_bytes,
    parse_resume_text,
    skills_from_parse,
)

logger = logging.getLogger("recruit_worker.parse_resume")


def _fail(resume: Resume, reason: str) -> None:
    resume.status = ResumeStatus.failed
    resume.parse_error = reason[:2000]


async def parse_resume(ctx: dict, resume_id: str) -> None:
    sessionmaker = ctx["sessionmaker"]
    store = ctx["object_store"]
    llm = ctx["llm"]
    model_name = ctx["llm_model"]

    async with sessionmaker() as db:
        resume = await db.get(Resume, uuid.UUID(resume_id))
        if resume is None:
            logger.warning("resume %s vanished before parse", resume_id)
            return

        try:
            resume.status = ResumeStatus.parsing
            await db.flush()

            data = await store.get(resume.storage_key)
            text = extract_text_from_pdf_bytes(data)
            if not text:
                _fail(resume, "No extractable text — image-only or corrupt PDF.")
            else:
                parsed = await parse_resume_text(text, llm)
                if parsed.get("error"):
                    _fail(resume, str(parsed["error"]))
                else:
                    db.add(
                        ResumeParse(
                            resume_id=resume.id,
                            model=model_name,
                            parsed_json=parsed,
                            skills=skills_from_parse(parsed),
                            tokens_used=0,
                        )
                    )
                    resume.status = ResumeStatus.parsed
                    resume.parse_error = None
        except Exception as exc:  # noqa: BLE001 — record and move on
            logger.exception("parse_resume failed for %s", resume_id)
            _fail(resume, f"{type(exc).__name__}: {exc}")

        await db.commit()
        logger.info("resume %s -> %s", resume_id, resume.status)
