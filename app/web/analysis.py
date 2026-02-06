import json

from fastapi import APIRouter, HTTPException, Request

from app.analysis.chunker import chunk_by_article
from app.analysis.explainer_v0 import explain
from app.analysis.extractor_v0 import extract_findings
from app.infra.repo_pages import PageRepo

router = APIRouter(prefix="/bills", tags=["analysis"])


@router.post("/{bill_id}/analysis")
async def analyze_bill(request: Request, bill_id: int) -> dict[str, object]:
    conn = request.app.state.db

    row = conn.execute(
        """
        SELECT dv.id AS document_version_id
        FROM document_versions dv
        JOIN documents d ON d.id = dv.document_id
        WHERE d.bill_id = ?
        ORDER BY dv.id DESC
        LIMIT 1
        """,
        (bill_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="bill_or_document_not_found")

    document_version_id = int(row["document_version_id"])
    pages = PageRepo(conn).list_for_version(document_version_id=document_version_id)
    if not pages:
        raise HTTPException(status_code=409, detail="no_pages_for_document_version")

    page_texts: list[tuple[int, str]] = []
    for p in pages:
        text = (p.ocr_text or p.text or "").strip()
        if text:
            page_texts.append((p.page_number, text))

    full_text = "\n\n".join(t for _, t in page_texts)
    chunks = chunk_by_article(full_text)
    findings = extract_findings(pages=page_texts, chunks=chunks)
    summary = explain(findings)

    return {
        "bill_id": bill_id,
        "document_version_id": document_version_id,
        "chunk_count": len(chunks),
        "finding_count": len(findings),
        "findings": [
            {
                "kind": f.kind,
                "label": f.label,
                "evidence": [
                    {"page_number": e.page_number, "quote": e.quote} for e in f.evidence
                ],
            }
            for f in findings
        ],
        "citizen_summary": {
            "bullets": summary.bullets,
            "limitations": summary.limitations,
        },
        "raw": json.loads(json.dumps({"chunks": [c.label for c in chunks]})),
    }
