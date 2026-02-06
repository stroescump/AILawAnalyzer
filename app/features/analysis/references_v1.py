import json
import re
from dataclasses import asdict

from app.features.analysis.artifacts_v1 import ReferenceEdge
from app.features.analysis.structure_tree_v1 import build_structure_nodes_v1
from app.infra.repo_chunks import ChunkRow


# Very small, Romanian-legal-ish patterns (Pareto v1)
_ART_MENTION_RE = re.compile(r"\bart\.?\s*(\d+[A-Za-z]?)\b", re.IGNORECASE)
_ALIN_MENTION_RE = re.compile(r"\balin\.?\s*\(?\s*(\d+)\s*\)?", re.IGNORECASE)
_RANGE_RE = re.compile(r"\b(\d+)\s*[–\-]\s*(\d+)\b")


def extract_reference_edges_v1(
    *,
    document_version_id: int,
    chunks: list[ChunkRow],
) -> list[ReferenceEdge]:
    """Extract best-effort reference edges from chunk text.

    Output is conservative:
    - Only emits edges when we see an `art.` mention.
    - `target` is a normalized string like `art:5` or `art:5 alin:2`.
    - `confidence` is heuristic.

    Limitations (accepted for v1):
    - No law identifiers (Legea X/YYYY) yet.
    - No robust range expansion; we store ranges as `art:2-10`.
    """

    # Build nodes so we can map chunk_id -> node_id.
    nodes = build_structure_nodes_v1(document_version_id=document_version_id, chunks=chunks)
    chunk_node_ids = {n.node_id for n in nodes if n.node_id.startswith("chunk:")}

    edges: list[ReferenceEdge] = []

    for ch in chunks:
        source_node_id = f"chunk:{ch.id}"
        if source_node_id not in chunk_node_ids:
            continue

        text = ch.text or ""
        for m in _ART_MENTION_RE.finditer(text):
            art = m.group(1)
            raw = m.group(0)

            # Look ahead a bit for alin mention near the art mention.
            window = text[m.end() : m.end() + 120]
            alin_m = _ALIN_MENTION_RE.search(window)
            if alin_m:
                alin = alin_m.group(1)
                target = f"art:{art} alin:{alin}"
                conf = 0.75
                raw = raw + " " + alin_m.group(0)
            else:
                target = f"art:{art}"
                conf = 0.6

            # Range detection (e.g., "art. 2-10")
            range_m = _RANGE_RE.search(window)
            if range_m and not alin_m:
                target = f"art:{range_m.group(1)}-{range_m.group(2)}"
                conf = 0.55

            edges.append(
                ReferenceEdge(
                    source_node_id=source_node_id,
                    raw_text=raw.strip(),
                    target=target,
                    kind="refers_to",
                    confidence=conf,
                )
            )

    return edges


def reference_edges_to_json(edges: list[ReferenceEdge]) -> str:
    return json.dumps([asdict(e) for e in edges], ensure_ascii=False)
