import re

from app.features.analysis.models import ChunkCandidate, CitizenSummary, Evidence, Finding

_ART_RE = re.compile(r"^\s*Art\.?\s*(\d+[A-Za-z]?)\b", re.IGNORECASE)
_PENALTY_RE = re.compile(r"\b(amend[ăa]|contraven\w+|sanc\w+|pedeaps\w+)\b", re.IGNORECASE)


def chunk_by_article(text: str) -> list[ChunkCandidate]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []

    for i, line in enumerate(lines):
        m = _ART_RE.match(line)
        if m:
            starts.append((i, f"Art. {m.group(1)}"))

    if not starts:
        return [ChunkCandidate(label="FULL_TEXT", text=text.strip())]

    chunks: list[ChunkCandidate] = []
    for idx, (start_i, label) in enumerate(starts):
        end_i = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start_i:end_i]).strip()
        if body:
            chunks.append(ChunkCandidate(label=label, text=body))

    return chunks


def extract_findings(pages: list[tuple[int, str]], chunks: list[ChunkCandidate]) -> list[Finding]:
    findings: list[Finding] = []

    for ch in chunks:
        if _PENALTY_RE.search(ch.text):
            ev = _best_effort_evidence(pages=pages, needle=ch.text[:200])
            findings.append(Finding(kind="PENALTY_OR_SANCTION", label=ch.label, evidence=ev))

    return findings


def explain(findings: list[Finding]) -> CitizenSummary:
    bullets: list[str] = []
    limitations: list[str] = []

    if not findings:
        bullets.append("Nu am detectat automat modificări clare pe baza regulilor PoC.")
        limitations.append("Rezultatul este incomplet: extractorul PoC caută doar câteva tipare simple.")
        return CitizenSummary(bullets=bullets, limitations=limitations)

    kinds = {f.kind for f in findings}
    if "PENALTY_OR_SANCTION" in kinds:
        bullets.append("Documentul pare să introducă sau să modifice sancțiuni/amenzi (detectare automată).")

    limitations.append("Rezumatul este generat strict din tipare detectate; poate rata nuanțe juridice.")
    return CitizenSummary(bullets=bullets, limitations=limitations)


def _best_effort_evidence(pages: list[tuple[int, str]], needle: str) -> list[Evidence]:
    needle = needle.strip()
    if not needle:
        return []

    for page_no, page_text in pages:
        if needle in page_text:
            return [Evidence(page_number=page_no, quote=needle)]

    if pages:
        page_no, page_text = pages[0]
        return [Evidence(page_number=page_no, quote=page_text[:200].strip())]

    return []
