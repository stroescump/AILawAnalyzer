import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    id: int
    document_version_id: int
    page_number: int
    text: str | None
    ocr_text: str | None
    quality_level: str | None
    has_handwriting: bool
    image_path: str | None


class PageRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self,
        document_version_id: int,
        page_number: int,
        text: str | None,
        ocr_text: str | None,
        quality_level: str | None,
        has_handwriting: bool,
        image_path: str | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO pages(
              document_version_id, page_number, text, ocr_text, quality_level, has_handwriting, image_path
            )
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_version_id, page_number) DO UPDATE SET
              text=excluded.text,
              ocr_text=excluded.ocr_text,
              quality_level=excluded.quality_level,
              has_handwriting=excluded.has_handwriting,
              image_path=excluded.image_path
            """,
            (
                document_version_id,
                page_number,
                text,
                ocr_text,
                quality_level,
                1 if has_handwriting else 0,
                image_path,
            ),
        )
        self._conn.commit()

    def list_for_version(self, document_version_id: int) -> list[Page]:
        rows = self._conn.execute(
            "SELECT * FROM pages WHERE document_version_id = ? ORDER BY page_number ASC",
            (document_version_id,),
        ).fetchall()
        return [
            Page(
                id=int(r["id"]),
                document_version_id=int(r["document_version_id"]),
                page_number=int(r["page_number"]),
                text=r["text"],
                ocr_text=r["ocr_text"],
                quality_level=r["quality_level"],
                has_handwriting=bool(r["has_handwriting"]),
                image_path=r["image_path"],
            )
            for r in rows
        ]
