import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Document:
    id: int
    bill_id: int
    doc_type: str
    source_url: str | None
    created_at: str


@dataclass(frozen=True)
class DocumentVersion:
    id: int
    document_id: int
    version_hash: str
    fetched_at: str
    mime_type: str
    file_path: str
    page_count: int | None
    quality_level: str | None
    ocr_applied: bool
    notes: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, bill_id: int, doc_type: str, source_url: str | None) -> Document:
        now = utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO documents(bill_id, doc_type, source_url, created_at)
            VALUES(?, ?, ?, ?)
            """,
            (bill_id, doc_type, source_url, now),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create document: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, document_id: int) -> Document:
        row = self._conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            raise KeyError(f"Document not found: {document_id}")
        return Document(
            id=int(row["id"]),
            bill_id=int(row["bill_id"]),
            doc_type=str(row["doc_type"]),
            source_url=row["source_url"],
            created_at=str(row["created_at"]),
        )

    def list_for_bill(self, bill_id: int) -> list[Document]:
        rows = self._conn.execute(
            "SELECT * FROM documents WHERE bill_id = ? ORDER BY id ASC", (bill_id,)
        ).fetchall()
        return [
            Document(
                id=int(r["id"]),
                bill_id=int(r["bill_id"]),
                doc_type=str(r["doc_type"]),
                source_url=r["source_url"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]


class DocumentVersionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        document_id: int,
        version_hash: str,
        mime_type: str,
        file_path: str,
        page_count: int | None,
        quality_level: str | None,
        ocr_applied: bool,
        notes: str | None,
    ) -> DocumentVersion:
        now = utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO document_versions(
              document_id, version_hash, fetched_at, mime_type, file_path,
              page_count, quality_level, ocr_applied, notes
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                version_hash,
                now,
                mime_type,
                file_path,
                page_count,
                quality_level,
                1 if ocr_applied else 0,
                notes,
            ),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create document version: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, version_id: int) -> DocumentVersion:
        row = self._conn.execute(
            "SELECT * FROM document_versions WHERE id = ?", (version_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Document version not found: {version_id}")
        return DocumentVersion(
            id=int(row["id"]),
            document_id=int(row["document_id"]),
            version_hash=str(row["version_hash"]),
            fetched_at=str(row["fetched_at"]),
            mime_type=str(row["mime_type"]),
            file_path=str(row["file_path"]),
            page_count=row["page_count"],
            quality_level=row["quality_level"],
            ocr_applied=bool(row["ocr_applied"]),
            notes=row["notes"],
        )

    def list_for_document(self, document_id: int) -> list[DocumentVersion]:
        rows = self._conn.execute(
            "SELECT * FROM document_versions WHERE document_id = ? ORDER BY id DESC",
            (document_id,),
        ).fetchall()
        return [
            DocumentVersion(
                id=int(r["id"]),
                document_id=int(r["document_id"]),
                version_hash=str(r["version_hash"]),
                fetched_at=str(r["fetched_at"]),
                mime_type=str(r["mime_type"]),
                file_path=str(r["file_path"]),
                page_count=r["page_count"],
                quality_level=r["quality_level"],
                ocr_applied=bool(r["ocr_applied"]),
                notes=r["notes"],
            )
            for r in rows
        ]
