import json

from fastapi import APIRouter, HTTPException, Request

from app.analysis.chunker import chunk_by_article
from app.analysis.explainer_v0 import explain
from app.analysis.extractor_v0 import extract_findings
from app.domain.enums import OutputType, RunStatus
from app.infra.repo_evidence import EvidenceRepo
from app.infra.repo_pages import PageRepo
from app.infra.repo_runs import OutputRepo, RunRepo

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

    run_repo = RunRepo(conn)
    run = run_repo.create(
        bill_id=bill_id,
        input_fingerprint=f"document_version:{document_version_id}",
        pipeline_version="analysis_v0",
    )
    run_repo.mark_running(run.id)

    pages = PageRepo(conn).list_for_version(document_version_id=document_version_id)
    if not pages:
        run_repo.mark_finished(run.id, status=RunStatus.failed, quality_summary_json=None)
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

    out_repo = OutputRepo(conn)
    ev_repo = EvidenceRepo(conn)

    for i, f in enumerate(findings):
        claim_id = f"finding:{i}:{f.kind}:{f.label}"
        for e in f.evidence:
            ev_repo.create(
                analysis_run_id=run.id,
                claim_id=claim_id,
                document_version_id=document_version_id,
                page_number=e.page_number,
                excerpt_text=e.quote,
                article_label=f.label,
            )

    out_repo.create(
        run_id=run.id,
        output_type=OutputType.extractor_json,
        content_json=json.dumps(
            {
                "chunks": [c.label for c in chunks],
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
            },
            ensure_ascii=False,
        ),
        content_text=None,
    )

    out_repo.create(
        run_id=run.id,
        output_type=OutputType.explainer_summary,
        content_json=json.dumps(
            {"bullets": summary.bullets, "limitations": summary.limitations},
            ensure_ascii=False,
        ),
        content_text=None,
    )

    run_repo.mark_finished(run.id, status=RunStatus.succeeded, quality_summary_json=None)

    return {
        "analysis_run_id": run.id,
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
