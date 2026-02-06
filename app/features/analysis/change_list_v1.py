import json
import re
from dataclasses import asdict, dataclass

from app.features.analysis.artifacts_v1 import SpanRef
from app.infra.repo_chunks import ChunkRow


@dataclass(frozen=True)
class ChangeItem:
    change_id: str
    action: str  # modifies/completes/repeals/unknown
    target: str  # normalized target like "art:2" or "art:2 alin:1"
    target_raw: str
    new_text_excerpt: str
    evidence: list[SpanRef]
    confidence: float


_ACTION_RE = re.compile(r"\b(se\s+modific\w+|se\s+completeaz\w+|se\s+abrog\w+)\b", re.IGNORECASE)
_TARGET_RE = re.compile(
    r"\bArt\.?\s*(?P<art>\d+[A-Za-z]?)\b(?:[^\n]{0,80}?\b(?:alin\.?\s*\(?\s*(?P<alin>\d+)\s*\)?)\b)?",
    re.IGNORECASE,
)


def extract_change_list_v1(*, chunks: list[ChunkRow]) -> list[ChangeItem]:
    """Extract a deterministic, evidence-linked list of amendments.

    Pareto v1:
    - Works on ARTICLE/ALIN chunks.
    - Detects action (modifică/completează/abrogă) and target (Art./alin).
    - Captures a short excerpt of the proposed new wording (best-effort).

    Does NOT:
    - Fetch base law text (future work).
    - Produce a true diff.
    """

    items: list[ChangeItem] = []

    for ch in chunks:
        if ch.chunk_type not in {"ARTICLE", "ALIN"}:
            continue
        text = (ch.text or "").strip()
        if not text:
            continue

        action = _detect_action(text)
        if action == "unknown":
            continue

        target_raw, target_norm, target_conf = _detect_target(text)
        if target_norm is None:
            continue

        excerpt = _extract_new_wording_excerpt(text)
        evidence = [SpanRef(page_number=ch.page_start, quote=text[:700])]

        conf = min(0.95, 0.55 + 0.25 * target_conf + (0.15 if excerpt else 0.0))

        items.append(
            ChangeItem(
                change_id=f"chg:{ch.id}",
                action=action,
                target=target_norm,
                target_raw=target_raw,
                new_text_excerpt=excerpt,
                evidence=evidence,
                confidence=conf,
            )
        )

    return items


def _detect_action(text: str) -> str:
    m = _ACTION_RE.search(text)
    if not m:
        return "unknown"
    s = m.group(1).lower()
    if "modific" in s:
        return "modifies"
    if "completeaz" in s:
        return "completes"
    if "abrog" in s:
        return "repeals"
    return "unknown"


def _detect_target(text: str) -> tuple[str, str | None, float]:
    m = _TARGET_RE.search(text)
    if not m:
        return ("", None, 0.0)

    art = m.group("art")
    alin = m.group("alin")

    raw = m.group(0).strip()
    if alin:
        return (raw, f"art:{art} alin:{alin}", 1.0)
    return (raw, f"art:{art}", 0.8)


_CUPRINS_RE = re.compile(r"(va\s+avea\s+urm[aă]torul\s+cuprins\s*:?)", re.IGNORECASE)


def _extract_new_wording_excerpt(text: str) -> str:
    """Best-effort: return the part after 'va avea următorul cuprins'."""
    m = _CUPRINS_RE.search(text)
    if not m:
        return ""
    tail = text[m.end() :].strip()
    # Keep it short and UI-friendly.
    return tail[:600]


def change_list_to_json(items: list[ChangeItem]) -> str:
    return json.dumps([asdict(i) for i in items], ensure_ascii=False)
