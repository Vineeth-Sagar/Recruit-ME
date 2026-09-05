# recruit-worker

arq workers that run the engine per tenant. Phase 4.3 introduces one task —
`parse_resume` — and reuses `recruit_api`'s config / DB / object-store code
(shared ORM models, one `DATABASE_URL`).

## Run

```bash
# infra up (make up); DATABASE_URL / REDIS_URL / S3_* / OPENROUTER_* in env or .env
uv run arq recruit_worker.settings.WorkerSettings
```

## Task

`parse_resume(ctx, resume_id)` — fetch the PDF from object storage, extract text
(`recruit_engine.ai.extract_text_from_pdf_bytes`), ask the LLM for structured
JSON (`parse_resume_text`), write a `ResumeParse` row, set `Resume.status`.
Image-only / unreadable PDFs are marked `failed` with a reason.

Phase 4.4 builds this out: the `execute_run` task, retry policy, rate limiting.
