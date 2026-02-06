import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.domain.enums import JobStatus


@dataclass(frozen=True)
class Job:
    id: int
    type: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    scheduled_at: str
    locked_at: str | None
    last_error: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def enqueue(self, job_type: str, payload: dict[str, Any]) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO jobs(type, payload_json, status, attempts, scheduled_at, locked_at, last_error)
            VALUES(?, ?, ?, 0, ?, NULL, NULL)
            """,
            (job_type, json.dumps(payload), JobStatus.queued.value, utc_now_iso()),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to enqueue job: missing lastrowid")
        return int(cur.lastrowid)

    def fetch_next(self) -> Job | None:
        row = self._conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = ? AND (locked_at IS NULL)
            ORDER BY scheduled_at ASC, id ASC
            LIMIT 1
            """,
            (JobStatus.queued.value,),
        ).fetchone()
        if row is None:
            return None
        return Job(
            id=int(row["id"]),
            type=str(row["type"]),
            payload=json.loads(row["payload_json"]),
            status=JobStatus(str(row["status"])),
            attempts=int(row["attempts"]),
            scheduled_at=str(row["scheduled_at"]),
            locked_at=row["locked_at"],
            last_error=row["last_error"],
        )

    def lock(self, job_id: int) -> None:
        self._conn.execute(
            "UPDATE jobs SET status = ?, locked_at = ? WHERE id = ?",
            (JobStatus.running.value, utc_now_iso(), job_id),
        )
        self._conn.commit()

    def mark_succeeded(self, job_id: int) -> None:
        self._conn.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (JobStatus.succeeded.value, job_id),
        )
        self._conn.commit()

    def mark_failed(self, job_id: int, error: str) -> None:
        self._conn.execute(
            """
            UPDATE jobs
            SET status = ?, attempts = attempts + 1, last_error = ?
            WHERE id = ?
            """,
            (JobStatus.failed.value, error, job_id),
        )
        self._conn.commit()
