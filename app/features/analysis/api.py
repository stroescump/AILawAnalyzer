import json

from fastapi import APIRouter, HTTPException, Request

from app.domain.enums import OutputType, RunStatus
from app.features.analysis.mechanism_validators_v1 import validate_mechanisms_v1
from app.features.analysis.mechanisms_v1 import extract_mechanisms_v1, mechanisms_to_json
from app.features.analysis.references_v1 import extract_reference_edges_v1, reference_edges_to_json
from app.features.analysis.scoring import score_sustainability
from app.features.analysis.segmentation_quality_v1 import compute_segmentation_quality_v1, quality_to_json
from app.features.analysis.segmentation_v1 import segment_pages_to_structure
from app.features.analysis.service import chunk_by_article, explain, extract_findings
from app.features.analysis.structure_tree_v1 import build_structure_nodes_v1, structure_nodes_to_json
from app.infra.repo_chunks import ChunkRepo
from app.infra.repo_evidence import EvidenceRepo
from app.infra.repo_pages import PageRepo
from app.infra.repo_runs import OutputRepo, RunRepo

router = APIRouter(prefix="/bills", tags=["analysis"])


@router.post("/{bill_id}/analysis")
async def analyze_bill(request: Request, bill_id: int) -> dict[str, object]:
    conn = request.app.state.db

    row = conn.execute(
        """
        SELECT dv.id AS document_version_id, dv.quality_level AS quality_level
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
    quality_level = row["quality_level"]

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

    # Segmentation v1: persist structural chunks (ARTICLE/ALIN) for traceability.
    segs = segment_pages_to_structure(page_texts)
    chunk_repo = ChunkRepo(conn)
    chunk_repo.delete_for_version(document_version_id=document_version_id)

    key_to_id: dict[str, int] = {}
    for s in segs:
        parent_id: int | None = None
        if s.parent_key is not None:
            parent_id = key_to_id.get(s.parent_key)
        row = chunk_repo.create(
            document_version_id=document_version_id,
            chunk_type=s.chunk_type,
            label=s.label,
            parent_chunk_id=parent_id,
            page_start=s.page_start,
            page_end=s.page_end,
            text=s.text,
            char_start=None,
            char_end=None,
            bbox_json=None,
        )
        if s.chunk_type == "ARTICLE" and s.label:
            key_to_id[f"ARTICLE::{s.label}"] = row.id

    full_text = "\n\n".join(t for _, t in page_texts)
    chunks = chunk_by_article(full_text)
    findings = extract_findings(pages=page_texts, chunks=chunks)
    summary = explain(findings)

    all_evidence = [e for f in findings for e in f.evidence]
    index = score_sustainability(text=full_text, evidence=all_evidence, quality_level=quality_level)

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

    for c in index.components:
        claim_id = f"sustainability:{c.dimension}:{c.rule_id}"
        for e in c.evidence:
            ev_repo.create(
                analysis_run_id=run.id,
                claim_id=claim_id,
                document_version_id=document_version_id,
                page_number=e.page_number,
                excerpt_text=e.quote,
                article_label=None,
            )

    # Persist structure_tree_v1 artifact from the chunks we just inserted.
    persisted_chunks = chunk_repo.list_for_version(document_version_id=document_version_id)
    structure_nodes = build_structure_nodes_v1(
        document_version_id=document_version_id,
        chunks=persisted_chunks,
    )
    out_repo.create(
        run_id=run.id,
        output_type=OutputType.structure_tree_v1,
        content_json=structure_nodes_to_json(structure_nodes),
        content_text=None,
    )

    # Persist reference_graph_v1 artifact (best-effort extraction from chunk text).
    ref_edges = extract_reference_edges_v1(
        document_version_id=document_version_id,
        chunks=persisted_chunks,
    )
    out_repo.create(
        run_id=run.id,
        output_type=OutputType.reference_graph_v1,
        content_json=reference_edges_to_json(ref_edges),
        content_text=None,
    )

    # Persist mechanisms_v1 artifact (span-grounded, conservative triggers).
    mechs = extract_mechanisms_v1(document_version_id=document_version_id, chunks=persisted_chunks)
    out_repo.create(
        run_id=run.id,
        output_type=OutputType.mechanisms_v1,
        content_json=mechanisms_to_json(mechs),
        content_text=None,
    )

    validation_issues = validate_mechanisms_v1(mechs)
    out_repo.create(
        run_id=run.id,
        output_type=OutputType.mechanism_validation_v1,
        content_json=json.dumps([issue.__dict__ for issue in validation_issues], ensure_ascii=False),
        content_text=None,
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

    out_repo.create(
        run_id=run.id,
        output_type=OutputType.sustainability_index,
        content_json=json.dumps(
            {
                "grade": index.grade,
                "overall": index.overall,
                "confidence": index.confidence,
                "dimensions": index.dimensions,
                "flags": index.flags,
                "components": [
                    {
                        "dimension": c.dimension,
                        "delta": c.delta,
                        "rationale": c.rationale,
                        "rule_id": c.rule_id,
                    }
                    for c in index.components
                ],
            },
            ensure_ascii=False,
        ),
        content_text=None,
    )

    # Segmentation quality summary (v1): stored on the run for observability.
    q = compute_segmentation_quality_v1(
        chunks=persisted_chunks,
        page_numbers_present=[p.page_number for p in pages],
    )
    run_repo.mark_finished(run.id, status=RunStatus.succeeded, quality_summary_json=quality_to_json(q))

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
        "sustainability_index": {
            "grade": index.grade,
            "overall": index.overall,
            "confidence": index.confidence,
            "dimensions": index.dimensions,
            "flags": index.flags,
        },
    }
