# Porting status — EZ-Recruit → recruit-engine

Source of truth for the originals: <https://github.com/Vineeth-Sagar/EZ-Recruit>
(`job_hunter/`).

## Moved in Phase 4.1 (this phase)

| From (`job_hunter/`) | To (`recruit_engine/`) | Change |
| :--- | :--- | :--- |
| `ai_engine.py` | `ai.py` | verbatim |
| `deduplicator.py` | `dedupe.py` | verbatim; `DB_PATH` default localised |
| `excel_builder.py` | `report.py` | `build_report(...) -> bytes` added |
| `emailer.py` | `email_templates.py` | SMTP send functions dropped; templating kept |
| `scrapers/{jobspy,wellfound,yc,hn}_scraper.py` | `scrapers/` | logic unchanged; registered in `SCRAPERS` |
| `scrapers/serpapi_scraper.py` | `scrapers/` | logic unchanged; **unregistered** (opt-in, user key) |

All moved files were style-normalized by `ruff` (import order, `List`→`list`,
whitespace) — no behaviour change. The EZ-Recruit originals remain the reference
for logic diffs.

## Deleted (not carried over)

`scrapers/{naukri,unstop,internshala}_scraper.py` and the `scrape_cutshort`
helper — undocumented endpoints / HTML scraping, dropped for the SaaS.

## Not moved — replaced in later phases

| Original | Replaced by | Phase |
| :--- | :--- | :--- |
| `config_loader.py` (JSON-in-repo) | DB-backed per-tenant loader → `EngineInput` | 4.3 |
| `main.py :: run()` (orchestrator: `sys.exit`, git commit, SMTP) | `run_engine()` + the `execute_run` arq task | 4.4 |

## Phase 4.4 work inside this package

- `run_engine()` full implementation, sequencing `scrapers → dedupe → ai → report`
  against the injected ports, emitting `on_step` progress.
- `ai.py`: remove the module-global `_client`; drop the in-request `time.sleep`
  pacing (concurrency + rate limiting become the caller's job).
- `scrapers/*`: reshape to the `Scraper` protocol in `scrapers/base.py`
  (`ProfileSpec` in, `list[JobPosting]` out, per-call `RateLimiter`); remove the
  hardcoded India / batch-2027 assumptions; thread `spec.big3_optin` through
  jobspy.
- `dedupe.py`: storage moves behind the `SeenStore` port; the SQLite default goes.
