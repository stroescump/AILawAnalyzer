import re
from dataclasses import dataclass

from app.analysis.chunker import ChunkCandidate


@dataclass(frozen=True)
class Evidence:
    page_number: int
    quote: str


@dataclass(frozen=True)
class Finding:
    kind: str
    label: str
    evidence: list[Evidence]


_PENALTY_RE = re.compile(r"\b(amend[ăa]|contraven\w+|sanc\w+|pedeaps\w+)\b", re.IGNORECASE)


def extract_findings(pages: list[tuple[int, str]], chunks: list[ChunkCandidate]) -> list[Finding]:
    findings: list[Finding] = []

    for ch in chunks:
        if _PENALTY_RE.search(ch.text):
            ev = _best_effort_evidence(pages=pages, needle=ch.text[:200])
            findings.append(Finding(kind="PENALTY_OR_SANCTION", label=ch.label, evidence=ev))

    return findings


def _best_effort_evidence(pages: list[tuple[int, str]], needle: str) -> list[Evidence]:
    needle = needle.strip()
    if not needle:
        return []

    for page_no, page_text in pages:
        if needle in page_text:
            return [Evidence(page_number=page_no, quote=needle)]

    # Fallback: return first page excerpt to avoid false precision.
    if pages:
        page_no, page_text = pages[0]
        return [Evidence(page_number=page_no, quote=page_text[:200].strip())]

    return []
