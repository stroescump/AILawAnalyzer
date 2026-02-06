import json
from dataclasses import dataclass, asdict

from app.features.analysis.artifacts_v1 import ReferenceEdge
from app.infra.repo_chunks import ChunkRow


@dataclass(frozen=True)
class RetrievalTraceStep:
    step: str
    added_chunk_ids: list[int]
    reason: str


@dataclass(frozen=True)
class RetrievalResult:
    seed_chunk_id: int
    selected_chunk_ids: list[int]
    steps: list[RetrievalTraceStep]


def _parse_target(target: str) -> tuple[str, str | None]:
    """Return (kind, value) where kind in {art, art_range, unknown}."""
    if target.startswith("art:"):
        rest = target[len("art:") :]
        if "-" in rest:
            return ("art_range", rest)
        return ("art", rest)
    return ("unknown", None)


def expand_retrieval_v1(
    *,
    seed_chunk_id: int,
    chunks: list[ChunkRow],
    ref_edges: list[ReferenceEdge],
    budget_chunks: int = 12,
) -> RetrievalResult:
    """Multi-hop retrieval expansion (Pareto v1).

    Strategy:
    1) Start with seed chunk.
    2) Add parent and siblings (same parent).
    3) Follow outgoing references from any selected chunk to ARTICLE chunks.

    Notes:
    - This is conservative and bounded by `budget_chunks`.
    - Resolution is best-effort: `art:X` maps to chunk with label `Art. X`.
    """

    by_id = {c.id: c for c in chunks}
    if seed_chunk_id not in by_id:
        return RetrievalResult(seed_chunk_id=seed_chunk_id, selected_chunk_ids=[], steps=[])

    by_parent: dict[int | None, list[ChunkRow]] = {}
    for c in chunks:
        by_parent.setdefault(c.parent_chunk_id, []).append(c)

    # Map article label -> chunk id
    art_label_to_id: dict[str, int] = {}
    for c in chunks:
        if c.chunk_type == "ARTICLE" and c.label:
            art_label_to_id[c.label.strip()] = c.id

    selected: list[int] = []
    selected_set: set[int] = set()
    steps: list[RetrievalTraceStep] = []

    def add(ids: list[int], reason: str, step: str) -> None:
        added: list[int] = []
        for cid in ids:
            if cid in selected_set:
                continue
            if len(selected) >= budget_chunks:
                break
            selected.append(cid)
            selected_set.add(cid)
            added.append(cid)
        if added:
            steps.append(RetrievalTraceStep(step=step, added_chunk_ids=added, reason=reason))

    # 1) seed
    add([seed_chunk_id], reason="seed", step="seed")

    # 2) parent + siblings
    seed = by_id[seed_chunk_id]
    if seed.parent_chunk_id is not None:
        add([seed.parent_chunk_id], reason="parent of seed", step="context")
        sibs = [c.id for c in by_parent.get(seed.parent_chunk_id, [])]
        add(sibs, reason="siblings of seed", step="context")

    # 3) follow references (one hop, then second hop if budget allows)
    def outgoing_from(chunk_id: int) -> list[ReferenceEdge]:
        node_id = f"chunk:{chunk_id}"
        return [e for e in ref_edges if e.source_node_id == node_id]

    frontier = list(selected)
    visited_frontier: set[int] = set()

    while frontier and len(selected) < budget_chunks:
        current = frontier.pop(0)
        if current in visited_frontier:
            continue
        visited_frontier.add(current)

        targets: list[int] = []
        for e in outgoing_from(current):
            kind, val = _parse_target(e.target)
            if kind == "art" and val is not None:
                label = f"Art. {val}".strip()
                tid = art_label_to_id.get(label)
                if tid is not None:
                    targets.append(tid)
            elif kind == "art_range" and val is not None:
                # Keep as best-effort: do not expand; try to include endpoints if present.
                start, end = val.split("-", 1)
                for v in (start.strip(), end.strip()):
                    label = f"Art. {v}".strip()
                    tid = art_label_to_id.get(label)
                    if tid is not None:
                        targets.append(tid)

        before = len(selected)
        add(targets, reason="follow references", step="refs")
        if len(selected) > before:
            # newly added become part of frontier for one more hop
            frontier.extend([cid for cid in selected if cid not in visited_frontier])

    return RetrievalResult(seed_chunk_id=seed_chunk_id, selected_chunk_ids=selected, steps=steps)


def retrieval_result_to_json(r: RetrievalResult) -> str:
    return json.dumps(asdict(r), ensure_ascii=False)
