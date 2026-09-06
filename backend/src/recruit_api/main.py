"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import AppError, app_error_handler
from .middleware import RequestContextMiddleware
from .routers import admin, auth, job_profiles, matches, me, resumes, runs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Recruit-ME API", version="0.1.0", docs_url="/docs", redoc_url=None)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_base_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(me.router, prefix=api_prefix)
    app.include_router(job_profiles.router, prefix=api_prefix)
    app.include_router(resumes.router, prefix=api_prefix)
    app.include_router(runs.router, prefix=api_prefix)
    app.include_router(matches.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
