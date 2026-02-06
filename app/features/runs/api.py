from fastapi import APIRouter, Request

from app.features.runs.service import RunsService

router = APIRouter(prefix="/bills", tags=["runs"])


@router.get("/{bill_id}/runs/latest")
async def get_latest_run(request: Request, bill_id: int) -> dict[str, object]:
    conn = request.app.state.db
    return await RunsService(conn=conn).get_latest_run(bill_id=bill_id)


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: int) -> dict[str, object]:
    conn = request.app.state.db
    return await RunsService(conn=conn).get_run(run_id=run_id)


@router.get("/runs/{run_id}/outputs")
async def list_outputs(request: Request, run_id: int) -> dict[str, object]:
    conn = request.app.state.db
    return await RunsService(conn=conn).list_outputs(run_id=run_id)
