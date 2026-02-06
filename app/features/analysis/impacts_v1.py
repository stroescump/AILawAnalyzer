import json
from dataclasses import asdict

from app.features.analysis.artifacts_v1 import ImpactStatement, Mechanism, SpanRef


def derive_impacts_v1(*, mechanisms: list[Mechanism]) -> list[ImpactStatement]:
    """Derive impact statements from mechanisms (Pareto v1).

    This is intentionally conservative:
    - Only emits impacts for a small set of mechanism kinds.
    - Uses coarse dimensions (E/S/G) and low confidence.
    - Evidence is inherited from mechanisms.

    This is a bridge step before mechanism-delta scoring replaces the current index.
    """

    impacts: list[ImpactStatement] = []

    for i, m in enumerate(mechanisms):
        dim: str | None = None
        polarity = 0
        rationale = ""
        conf = 0.35

        if m.kind == "sanction":
            dim = "G"
            polarity = +1
            rationale = "Introduces/mentions sanctions; may improve enforceability (governance)."
            conf = 0.4
        elif m.kind == "obligation":
            dim = "G"
            polarity = +1
            rationale = "Introduces/mentions obligations; may increase compliance requirements (governance)."
            conf = 0.35
        elif m.kind == "prohibition":
            dim = "E"
            polarity = +1
            rationale = "Introduces/mentions prohibitions; may reduce harmful activities (environment)."
            conf = 0.35
        elif m.kind == "definition":
            dim = "G"
            polarity = 0
            rationale = "Adds/mentions definitions; may clarify scope but impact is uncertain."
            conf = 0.25

        if dim is None:
            continue

        evidence: list[SpanRef] = list(m.evidence)
        impacts.append(
            ImpactStatement(
                impact_id=f"imp:{m.mechanism_id}:{i}",
                dimension=dim,
                polarity=polarity,
                rationale=rationale,
                mechanism_ids=[m.mechanism_id],
                evidence=evidence,
                confidence=conf,
            )
        )

    return impacts


def impacts_to_json(impacts: list[ImpactStatement]) -> str:
    return json.dumps([asdict(i) for i in impacts], ensure_ascii=False)
