import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Bill:
    id: int
    source: str
    source_bill_id: str | None
    title: str
    status: str | None
    introduced_at: str | None
    created_at: str
    updated_at: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BillRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, source: str, title: str, source_bill_id: str | None = None) -> Bill:
        now = utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO bills(source, source_bill_id, title, status, introduced_at, created_at, updated_at)
            VALUES(?, ?, ?, NULL, NULL, ?, ?)
            """,
            (source, source_bill_id, title, now, now),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create bill: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, bill_id: int) -> Bill:
        row = self._conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
        if row is None:
            raise KeyError(f"Bill not found: {bill_id}")
        return Bill(
            id=int(row["id"]),
            source=str(row["source"]),
            source_bill_id=row["source_bill_id"],
            title=str(row["title"]),
            status=row["status"],
            introduced_at=row["introduced_at"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list(self, limit: int = 50, offset: int = 0) -> list[Bill]:
        rows = self._conn.execute(
            "SELECT * FROM bills ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [
            Bill(
                id=int(r["id"]),
                source=str(r["source"]),
                source_bill_id=r["source_bill_id"],
                title=str(r["title"]),
                status=r["status"],
                introduced_at=r["introduced_at"],
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"]),
            )
            for r in rows
        ]
