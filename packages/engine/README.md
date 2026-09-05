# recruit-engine

The Recruit-ME core engine. A pure library: it scrapes job sources, scores
postings against a parsed résumé, and builds a report. It has **no** database,
reads **no** environment for configuration, does **no** auth, and owns **no**
scheduling.

Everything a run needs arrives as an `EngineInput` plus injected ports
(`recruit_engine.ports`); everything it produces returns as an `EngineResult`.
The same engine build runs for every tenant — all per-user variation is data.

## Layout

| Module | Role |
| :--- | :--- |
| `types.py` | `EngineInput` / `EngineResult` and their parts — the typed contract |
| `ports.py` | `SeenStore`, `RateLimiter`, `LLMClient`, `Clock` — Protocols the engine depends on |
| `engine.py` | `run_engine(...)` — the single entry point (implemented in Phase 4.4) |
| `ai.py` | résumé parsing + job–résumé matching prompts and fallback |
| `dedupe.py` | seen-job hashing (storage moves behind `SeenStore` in Phase 4.4) |
| `report.py` | the 4-sheet Excel workbook, as bytes |
| `email_templates.py` | report email subject + HTML body (no transport) |
| `scrapers/` | `SCRAPERS` registry: `jobspy`, `wellfound`, `yc`, `hackernews` |

## Develop

```bash
uv sync --all-packages          # from the repo root
uv run pytest packages/engine
```

Optional heavy scraper deps: `uv sync --extra jobspy`.

See `PORTING.md` for what still needs to move from EZ-Recruit.
