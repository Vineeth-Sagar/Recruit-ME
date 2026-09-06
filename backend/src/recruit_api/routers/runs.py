"""/api/v1/runs — trigger (202), list, detail, live events (SSE), cancel."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.responses import StreamingResponse

from ..models.run import RunStatus, RunTrigger
from ..schemas.common import Page
from ..schemas.run import RunCreateIn, RunDetailOut, RunOut, RunSourceOut, RunStepOut
from ..security.deps import CurrentUser, get_run_service
from ..services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])

SvcDep = Annotated[RunService, Depends(get_run_service)]


@router.post("", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    body: RunCreateIn,
    user: CurrentUser,
    svc: SvcDep,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RunOut:
    run, created = await svc.create(
        user.id, body.job_profile_id, trigger=RunTrigger.manual, idempotency_key=idempotency_key
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return RunOut.model_validate(run)


@router.get("", response_model=Page[RunOut])
async def list_runs(
    user: CurrentUser,
    svc: SvcDep,
    run_status: Annotated[RunStatus | None, Query(alias="status")] = None,
    profile: uuid.UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[RunOut]:
    rows, total = await svc.list(
        user.id, status=run_status, profile_id=profile, page=page, page_size=page_size
    )
    return Page[RunOut](
        items=[RunOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=RunDetailOut)
async def get_run(run_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> RunDetailOut:
    run = await svc.get(user.id, run_id)
    out = RunDetailOut.model_validate(run)
    out.steps = [RunStepOut.model_validate(s) for s in await svc.steps(run_id)]
    out.sources = [RunSourceOut.model_validate(s) for s in await svc.sources(run_id)]
    return out


@router.get("/{run_id}/events")
async def run_events(run_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> StreamingResponse:
    await svc.get(user.id, run_id)  # ownership / 404 before streaming
    return StreamingResponse(
        svc.stream_events(user.id, run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{run_id}:cancel", response_model=RunOut)
async def cancel_run(run_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> RunOut:
    return RunOut.model_validate(await svc.cancel(user.id, run_id))
