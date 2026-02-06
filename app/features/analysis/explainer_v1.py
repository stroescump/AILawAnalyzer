import re

from app.features.analysis.artifacts_v1 import Mechanism
from app.features.analysis.models import CitizenSummary


def explain_v1(*, mechanisms: list[Mechanism]) -> CitizenSummary:
    """Generate a citizen summary strictly from extracted v1 mechanisms.

    Guardrails:
    - No new facts: we only restate what was detected as a mechanism kind.
    - Conservative language: "pare să" / "posibil".
    - No actor ranking; no party/person mentions.

    This is Pareto v1: it summarizes *types* of changes, not full legal meaning.
    """

    bullets: list[str] = []
    limitations: list[str] = []

    if not mechanisms:
        bullets.append("Nu am detectat automat mecanisme clare pe baza regulilor PoC.")
        limitations.append(
            "Rezultatul este incomplet: extractorul PoC folosește declanșatori lexicali conservatori și poate rata modificări."
        )
        return CitizenSummary(bullets=bullets, limitations=limitations)

    kinds = {m.kind for m in mechanisms}

    if "amendment" in kinds:
        bullets.append("Documentul pare să modifice/complecteze/abroge prevederi (detectare automată).")
    if "sanction" in kinds:
        bullets.append("Documentul pare să introducă sau să modifice sancțiuni/pedepse/amenzi (detectare automată).")
    if "obligation" in kinds:
        bullets.append("Documentul pare să introducă obligații pentru anumite entități (detectare automată).")
    if "prohibition" in kinds:
        bullets.append("Documentul pare să introducă interdicții (detectare automată).")
    if "definition" in kinds:
        bullets.append("Documentul pare să definească termeni sau să clarifice sensuri legale (detectare automată).")

    # Small extra: highlight numeric thresholds if present in evidence excerpts.
    if _has_numeric_threshold(mechanisms):
        bullets.append("Sunt prezente praguri/valori numerice (ex.: cantități, termene), care pot schimba aplicarea prevederilor.")

    limitations.extend(
        [
            "Rezumatul este generat strict din tipare detectate; nu interpretează intenția legislativă și poate rata excepții/negări.",
            "Pentru încredere, fiecare mecanism are citate scurte în artefactul mechanisms_v1; UI trebuie să afișeze citatele ca sursă.",
        ]
    )

    return CitizenSummary(bullets=bullets, limitations=limitations)


_NUM_RE = re.compile(r"\b\d+[\d\.,]*\b")


def _has_numeric_threshold(mechanisms: list[Mechanism]) -> bool:
    for m in mechanisms:
        for ev in m.evidence:
            if _NUM_RE.search(ev.quote or ""):
                return True
    return False
