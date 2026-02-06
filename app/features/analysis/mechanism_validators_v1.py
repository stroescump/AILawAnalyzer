import re
from dataclasses import dataclass

from app.features.analysis.artifacts_v1 import Mechanism


@dataclass(frozen=True)
class MechanismValidationIssue:
    mechanism_id: str
    code: str
    message: str


_NEGATION_RE = re.compile(r"\b(nu|nici|fără)\b", re.IGNORECASE)
_EXCEPTION_RE = re.compile(r"\b(cu excepția|exceptând|prin derogare)\b", re.IGNORECASE)
_SANCTION_AMOUNT_RE = re.compile(r"\b(amend[ăa]\s+de\s+\d+[\d\.]*\s*(lei|ron))\b", re.IGNORECASE)


def validate_mechanisms_v1(mechanisms: list[Mechanism]) -> list[MechanismValidationIssue]:
    """Lightweight validators (Pareto v1).

    We do not mutate mechanisms yet; we only emit issues so the UI/API can show
    "partial/uncertain" flags.
    """

    issues: list[MechanismValidationIssue] = []

    for m in mechanisms:
        # Negation/exception detection: if present, we should later split conditions/exceptions.
        evidence_text = "\n".join(e.quote for e in m.evidence)
        if _NEGATION_RE.search(evidence_text):
            issues.append(
                MechanismValidationIssue(
                    mechanism_id=m.mechanism_id,
                    code="contains_negation",
                    message="Evidence contains negation; mechanism may require exception/condition parsing.",
                )
            )
        if _EXCEPTION_RE.search(evidence_text):
            issues.append(
                MechanismValidationIssue(
                    mechanism_id=m.mechanism_id,
                    code="contains_exception_phrase",
                    message="Evidence contains exception/derogation phrase; mechanism may be conditional.",
                )
            )

        # Sanction completeness: if kind is sanction, try to detect an amount.
        if m.kind == "sanction":
            if not _SANCTION_AMOUNT_RE.search(evidence_text):
                issues.append(
                    MechanismValidationIssue(
                        mechanism_id=m.mechanism_id,
                        code="sanction_amount_missing",
                        message="Sanction detected but no clear fine amount pattern found (may be incomplete OCR or different phrasing).",
                    )
                )

    return issues
