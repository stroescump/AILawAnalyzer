import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ChunkRow:
    id: int
    document_version_id: int
    chunk_type: str
    label: str | None
    parent_chunk_id: int | None
    page_start: int
    page_end: int
    text: str
    char_start: int | None
    char_end: int | None
    bbox_json: str | None
    created_at: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChunkRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        document_version_id: int,
        chunk_type: str,
        label: str | None,
        parent_chunk_id: int | None,
        page_start: int,
        page_end: int,
        text: str,
        char_start: int | None,
        char_end: int | None,
        bbox_json: str | None,
    ) -> ChunkRow:
        now = utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO chunks(
              document_version_id, chunk_type, label, parent_chunk_id,
              page_start, page_end, text, char_start, char_end, bbox_json, created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_version_id,
                chunk_type,
                label,
                parent_chunk_id,
                page_start,
                page_end,
                text,
                char_start,
                char_end,
                bbox_json,
                now,
            ),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create chunk: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, chunk_id: int) -> ChunkRow:
        row = self._conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        if row is None:
            raise KeyError(f"Chunk not found: {chunk_id}")
        return ChunkRow(
            id=int(row["id"]),
            document_version_id=int(row["document_version_id"]),
            chunk_type=str(row["chunk_type"]),
            label=row["label"],
            parent_chunk_id=row["parent_chunk_id"],
            page_start=int(row["page_start"]),
            page_end=int(row["page_end"]),
            text=str(row["text"]),
            char_start=row["char_start"],
            char_end=row["char_end"],
            bbox_json=row["bbox_json"],
            created_at=str(row["created_at"]),
        )

    def list_for_version(self, document_version_id: int) -> list[ChunkRow]:
        rows = self._conn.execute(
            "SELECT * FROM chunks WHERE document_version_id = ? ORDER BY id ASC",
            (document_version_id,),
        ).fetchall()
        return [
            ChunkRow(
                id=int(r["id"]),
                document_version_id=int(r["document_version_id"]),
                chunk_type=str(r["chunk_type"]),
                label=r["label"],
                parent_chunk_id=r["parent_chunk_id"],
                page_start=int(r["page_start"]),
                page_end=int(r["page_end"]),
                text=str(r["text"]),
                char_start=r["char_start"],
                char_end=r["char_end"],
                bbox_json=r["bbox_json"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def delete_for_version(self, document_version_id: int) -> None:
        self._conn.execute("DELETE FROM chunks WHERE document_version_id = ?", (document_version_id,))
        self._conn.commit()
