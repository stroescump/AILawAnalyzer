import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.enums import OutputType, RunStatus


@dataclass(frozen=True)
class AnalysisRun:
    id: int
    bill_id: int
    input_fingerprint: str
    pipeline_version: str
    status: RunStatus
    started_at: str | None
    finished_at: str | None
    quality_summary_json: str | None


@dataclass(frozen=True)
class Output:
    id: int
    analysis_run_id: int
    output_type: OutputType
    content_json: str | None
    content_text: str | None
    created_at: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, bill_id: int, input_fingerprint: str, pipeline_version: str) -> AnalysisRun:
        cur = self._conn.execute(
            """
            INSERT INTO analysis_runs(
              bill_id, input_fingerprint, pipeline_version, status,
              started_at, finished_at, quality_summary_json
            )
            VALUES(?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (bill_id, input_fingerprint, pipeline_version, RunStatus.queued.value),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create analysis run: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, run_id: int) -> AnalysisRun:
        row = self._conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"Analysis run not found: {run_id}")
        return AnalysisRun(
            id=int(row["id"]),
            bill_id=int(row["bill_id"]),
            input_fingerprint=str(row["input_fingerprint"]),
            pipeline_version=str(row["pipeline_version"]),
            status=RunStatus(str(row["status"])),
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            quality_summary_json=row["quality_summary_json"],
        )

    def mark_running(self, run_id: int) -> None:
        self._conn.execute(
            "UPDATE analysis_runs SET status = ?, started_at = ? WHERE id = ?",
            (RunStatus.running.value, utc_now_iso(), run_id),
        )
        self._conn.commit()

    def mark_finished(self, run_id: int, status: RunStatus, quality_summary_json: str | None) -> None:
        self._conn.execute(
            """
            UPDATE analysis_runs
            SET status = ?, finished_at = ?, quality_summary_json = ?
            WHERE id = ?
            """,
            (status.value, utc_now_iso(), quality_summary_json, run_id),
        )
        self._conn.commit()


class OutputRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        run_id: int,
        output_type: OutputType,
        content_json: str | None,
        content_text: str | None,
    ) -> Output:
        now = utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO outputs(analysis_run_id, output_type, content_json, content_text, created_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (run_id, output_type.value, content_json, content_text, now),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create output: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, output_id: int) -> Output:
        row = self._conn.execute("SELECT * FROM outputs WHERE id = ?", (output_id,)).fetchone()
        if row is None:
            raise KeyError(f"Output not found: {output_id}")
        return Output(
            id=int(row["id"]),
            analysis_run_id=int(row["analysis_run_id"]),
            output_type=OutputType(str(row["output_type"])),
            content_json=row["content_json"],
            content_text=row["content_text"],
            created_at=str(row["created_at"]),
        )

    def list_for_run(self, run_id: int) -> list[Output]:
        rows = self._conn.execute(
            "SELECT * FROM outputs WHERE analysis_run_id = ? ORDER BY id ASC", (run_id,)
        ).fetchall()
        return [
            Output(
                id=int(r["id"]),
                analysis_run_id=int(r["analysis_run_id"]),
                output_type=OutputType(str(r["output_type"])),
                content_json=r["content_json"],
                content_text=r["content_text"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
