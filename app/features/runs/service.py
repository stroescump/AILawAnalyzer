from fastapi import HTTPException

from app.infra.repo_runs import OutputRepo, RunRepo


class RunsService:
    def __init__(self, *, conn) -> None:
        self._conn = conn

    async def get_latest_run(self, *, bill_id: int) -> dict[str, object]:
        row = self._conn.execute(
            "SELECT id FROM analysis_runs WHERE bill_id = ? ORDER BY id DESC LIMIT 1",
            (bill_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="run_not_found")
        return await self.get_run(run_id=int(row["id"]))

    async def get_run(self, *, run_id: int) -> dict[str, object]:
        try:
            run = RunRepo(self._conn).get(run_id)
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

    async def list_outputs(self, *, run_id: int) -> dict[str, object]:
        try:
            RunRepo(self._conn).get(run_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="run_not_found")

        outs = OutputRepo(self._conn).list_for_run(run_id)
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
