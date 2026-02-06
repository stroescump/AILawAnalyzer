import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceRow:
    id: int
    analysis_run_id: int
    claim_id: str
    document_version_id: int
    page_number: int
    excerpt_text: str
    article_label: str | None


class EvidenceRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        analysis_run_id: int,
        claim_id: str,
        document_version_id: int,
        page_number: int,
        excerpt_text: str,
        article_label: str | None,
    ) -> EvidenceRow:
        cur = self._conn.execute(
            """
            INSERT INTO evidence(
              analysis_run_id, claim_id, document_version_id, page_number,
              chunk_id, article_label, alin_label, char_start, char_end, bbox_json, excerpt_text
            )
            VALUES(?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, NULL, ?)
            """,
            (analysis_run_id, claim_id, document_version_id, page_number, article_label, excerpt_text),
        )
        self._conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("Failed to create evidence: missing lastrowid")
        return self.get(int(cur.lastrowid))

    def get(self, evidence_id: int) -> EvidenceRow:
        row = self._conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
        if row is None:
            raise KeyError(f"Evidence not found: {evidence_id}")
        return EvidenceRow(
            id=int(row["id"]),
            analysis_run_id=int(row["analysis_run_id"]),
            claim_id=str(row["claim_id"]),
            document_version_id=int(row["document_version_id"]),
            page_number=int(row["page_number"]),
            excerpt_text=str(row["excerpt_text"]),
            article_label=row["article_label"],
        )
