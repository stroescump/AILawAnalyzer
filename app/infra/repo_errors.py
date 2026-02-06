import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.enums import ErrorStage


@dataclass(frozen=True)
class RunError:
    id: int
    analysis_run_id: int
    stage: ErrorStage
    error_code: str
    message: str
    details_json: str | None
    created_at: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ErrorRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        run_id: int,
        stage: ErrorStage,
        error_code: str,
        message: str,
        details_json: str | None,
    ) -> RunError:
        now = utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO errors(analysis_run_id, stage, error_code, message, details_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (run_id, stage.value, error_code, message, details_json, now),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create error: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, error_id: int) -> RunError:
        row = self._conn.execute("SELECT * FROM errors WHERE id = ?", (error_id,)).fetchone()
        if row is None:
            raise KeyError(f"Error not found: {error_id}")
        return RunError(
            id=int(row["id"]),
            analysis_run_id=int(row["analysis_run_id"]),
            stage=ErrorStage(str(row["stage"])),
            error_code=str(row["error_code"]),
            message=str(row["message"]),
            details_json=row["details_json"],
            created_at=str(row["created_at"]),
        )

    def list_for_run(self, run_id: int) -> list[RunError]:
        rows = self._conn.execute(
            "SELECT * FROM errors WHERE analysis_run_id = ? ORDER BY id ASC", (run_id,)
        ).fetchall()
        return [
            RunError(
                id=int(r["id"]),
                analysis_run_id=int(r["analysis_run_id"]),
                stage=ErrorStage(str(r["stage"])),
                error_code=str(r["error_code"]),
                message=str(r["message"]),
                details_json=r["details_json"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
