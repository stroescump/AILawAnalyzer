from __future__ import annotations

import re
from dataclasses import dataclass

from app.features.analysis.artifacts_v1 import Mechanism
from app.infra.repo_knowledge import KnowledgeRepo


@dataclass(frozen=True)
class ClaimMatch:
    claim_id: str
    score: float
    matched_keywords: list[str]


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _mechanism_text(m: Mechanism) -> str:
    parts: list[str] = []
    if m.kind:
        parts.append(m.kind)
    if m.actor:
        parts.append(m.actor)
    if m.action:
        parts.append(m.action)
    if m.obj:
        parts.append(m.obj)
    parts.extend(m.conditions or [])
    parts.extend(m.exceptions or [])
    return _normalize(" ".join(p for p in parts if p))


def suggest_claim_matches_v1(
    *,
    conn,
    mechanisms: list[Mechanism],
    limit_claims: int = 200,
    min_score: float = 0.2,
) -> dict[str, list[ClaimMatch]]:
    """Suggest SME claim matches for mechanisms using deterministic keyword hits.

    - Only uses published SME claims (current_version).
    - Matches against a normalized mechanism text (kind/actor/action/obj/conditions/exceptions).
    - Returns per-mechanism suggestions; does NOT attach or score.
    """

    repo = KnowledgeRepo(conn)
    claims = repo.list_objects("sme_claim", limit=limit_claims)

    # Load current published content for each claim.
    claim_payloads: list[tuple[str, list[str]]] = []
    for c in claims:
        if c.current_version is None:
            continue
        v = repo.get_version("sme_claim", c.object_id, version=int(c.current_version))
        if not v:
            continue
        kws = v.content.get("trigger_keywords") or []
        if not isinstance(kws, list):
            continue
        norm_kws = [_normalize(str(x)) for x in kws if str(x).strip()]
        if not norm_kws:
            continue
        claim_payloads.append((c.object_id, norm_kws))

    out: dict[str, list[ClaimMatch]] = {}

    for m in mechanisms:
        text = _mechanism_text(m)
        matches: list[ClaimMatch] = []

        for claim_id, kws in claim_payloads:
            hit: list[str] = []
            for kw in kws:
                if not kw:
                    continue
                if kw in text:
                    hit.append(kw)
            if not hit:
                continue

            # Simple scoring: fraction of keywords hit, capped.
            score = min(1.0, len(hit) / max(1, len(kws)))
            if score < min_score:
                continue
            matches.append(ClaimMatch(claim_id=claim_id, score=score, matched_keywords=hit))

        matches.sort(key=lambda x: x.score, reverse=True)
        out[m.mechanism_id] = matches[:10]

    return out
