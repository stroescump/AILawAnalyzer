import json
from dataclasses import asdict

from app.features.analysis.artifacts_v1 import SpanRef, StructureNode
from app.infra.repo_chunks import ChunkRow


def build_structure_nodes_v1(
    *,
    document_version_id: int,
    chunks: list[ChunkRow],
) -> list[StructureNode]:
    """Build `StructureNode` rows from persisted `chunks`.

    Note: our v1 `StructureNode` dataclass is *flat* (no children field). We store
    parent/child relationships via `parent_id`.

    Pareto v1:
    - Root node + ARTICLE + ALIN
    - Evidence is best-effort: page range + excerpt; no offsets/bbox.
    """

    nodes: list[StructureNode] = []

    root_id = f"dv:{document_version_id}:root"
    nodes.append(
        StructureNode(
            node_id=root_id,
            node_type="ROOT",
            label=None,
            parent_id=None,
            page_start=min((c.page_start for c in chunks), default=1),
            page_end=max((c.page_end for c in chunks), default=1),
            text="",
            spans=[],
        )
    )

    for ch in chunks:
        parent_id: str | None
        if ch.parent_chunk_id is None:
            parent_id = root_id
        else:
            parent_id = f"chunk:{ch.parent_chunk_id}"

        excerpt = (ch.text or "").strip()[:400]
        spans = [SpanRef(page_number=ch.page_start, quote=excerpt)] if excerpt else []

        nodes.append(
            StructureNode(
                node_id=f"chunk:{ch.id}",
                node_type=ch.chunk_type,
                label=ch.label,
                parent_id=parent_id,
                page_start=ch.page_start,
                page_end=ch.page_end,
                text=ch.text,
                spans=spans,
            )
        )

    return nodes


def structure_nodes_to_json(nodes: list[StructureNode]) -> str:
    return json.dumps([asdict(n) for n in nodes], ensure_ascii=False)
