from dataclasses import dataclass

from app.analysis.extractor_v0 import Finding


@dataclass(frozen=True)
class CitizenSummary:
    bullets: list[str]
    limitations: list[str]


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
