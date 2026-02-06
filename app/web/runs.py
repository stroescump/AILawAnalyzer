from fastapi import APIRouter, HTTPException, Request

from app.infra.repo_runs import OutputRepo, RunRepo

router = APIRouter(prefix="/bills", tags=["runs"])


@router.get("/{bill_id}/runs/latest")
async def get_latest_run(request: Request, bill_id: int) -> dict[str, object]:
    conn = request.app.state.db
    row = conn.execute(
        "SELECT id FROM analysis_runs WHERE bill_id = ? ORDER BY id DESC LIMIT 1",
        (bill_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="run_not_found")
    return await get_run(request, int(row["id"]))


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: int) -> dict[str, object]:
    conn = request.app.state.db
    try:
        run = RunRepo(conn).get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run_not_found")

    return {
        "id": run.id,
        "bill_id": run.bill_id,
        "input_fingerprint": run.input_fingerprint,
        "pipeline_version": run.pipeline_version,
        "status": run.status.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "quality_summary_json": run.quality_summary_json,
    }


@router.get("/runs/{run_id}/outputs")
async def list_outputs(request: Request, run_id: int) -> dict[str, object]:
    conn = request.app.state.db
    try:
        RunRepo(conn).get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run_not_found")

    outs = OutputRepo(conn).list_for_run(run_id)
    return {
        "analysis_run_id": run_id,
        "outputs": [
            {
                "id": o.id,
                "output_type": o.output_type.value,
                "content_json": o.content_json,
                "content_text": o.content_text,
                "created_at": o.created_at,
            }
            for o in outs
        ],
    }
