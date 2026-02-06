from fastapi import HTTPException


class DocumentsService:
    def __init__(self, *, conn) -> None:
        self._conn = conn

    async def list_evidence(self, *, run_id: int) -> dict[str, object]:
        run = self._conn.execute("SELECT id FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="run_not_found")

        rows = self._conn.execute(
            """
            SELECT id, claim_id, document_version_id, page_number, article_label, excerpt_text
            FROM evidence
            WHERE analysis_run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()

        return {
            "analysis_run_id": run_id,
            "evidence": [
                {
                    "id": int(r["id"]),
                    "claim_id": str(r["claim_id"]),
                    "document_version_id": int(r["document_version_id"]),
                    "page_number": int(r["page_number"]),
                    "article_label": r["article_label"],
                    "excerpt_text": str(r["excerpt_text"]),
                }
                for r in rows
            ],
        }
