import json
import re
from dataclasses import asdict

from app.features.analysis.artifacts_v1 import Mechanism, SpanRef
from app.infra.repo_chunks import ChunkRow


_OBLIGATION_RE = re.compile(r"\b(are obliga\w+|au obliga\w+|este obligat\w+|sunt obligat\w+)\b", re.IGNORECASE)
_PROHIBITION_RE = re.compile(r"\b(se interzice|este interzis\w+|sunt interzis\w+)\b", re.IGNORECASE)
_DEFINITION_RE = re.compile(r"\b(în sensul prezentei legi|se înțelege prin|înseamnă)\b", re.IGNORECASE)
_SANCTION_RE = re.compile(r"\b(contraven\w+|se sancționeaz\w+|amend\w+|pedeaps\w+)\b", re.IGNORECASE)
_AMENDMENT_RE = re.compile(r"\b(se modific\w+|se completeaz\w+|se abrog\w+)\b", re.IGNORECASE)


def extract_mechanisms_v1(
    *,
    document_version_id: int,
    chunks: list[ChunkRow],
) -> list[Mechanism]:
    """Extract mechanisms from chunk text (Pareto v1).

    This is intentionally conservative and span-grounded:
    - We only emit a mechanism when a strong lexical trigger is present.
    - We do not attempt actor/action/object parsing yet; those fields remain None.
    - Evidence is a short excerpt from the chunk.

    Mechanism IDs are stable-ish within a run: `m:{chunk_id}:{kind}:{i}`.
    """

    mechs: list[Mechanism] = []

    def mk_evidence(ch: ChunkRow) -> list[SpanRef]:
        excerpt = (ch.text or "").strip()
        excerpt = excerpt[:500]
        if not excerpt:
            return []
        return [SpanRef(page_number=ch.page_start, quote=excerpt)]

    for ch in chunks:
        if ch.chunk_type not in {"ARTICLE", "ALIN", "FULL_TEXT"}:
            continue
        text = ch.text or ""
        evidence = mk_evidence(ch)
        if not evidence:
            continue

        kinds: list[str] = []
        if _OBLIGATION_RE.search(text):
            kinds.append("obligation")
        if _PROHIBITION_RE.search(text):
            kinds.append("prohibition")
        if _DEFINITION_RE.search(text):
            kinds.append("definition")
        if _SANCTION_RE.search(text):
            kinds.append("sanction")
        if _AMENDMENT_RE.search(text):
            kinds.append("amendment")

        for i, kind in enumerate(kinds):
            mechs.append(
                Mechanism(
                    mechanism_id=f"m:{ch.id}:{kind}:{i}",
                    kind=kind,
                    actor=None,
                    action=None,
                    obj=None,
                    conditions=[],
                    exceptions=[],
                    effective_date=None,
                    references=[],
                    source_node_id=f"chunk:{ch.id}",
                    evidence=evidence,
                    field_confidence={"kind": 0.7},
                )
            )

    return mechs


def mechanisms_to_json(mechs: list[Mechanism]) -> str:
    return json.dumps([asdict(m) for m in mechs], ensure_ascii=False)
