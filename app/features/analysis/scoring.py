import re

from app.features.analysis.models import Evidence


class ScoreComponent:
    def __init__(
        self,
        *,
        dimension: str,
        delta: int,
        rationale: str,
        evidence: list[Evidence],
        rule_id: str,
    ) -> None:
        self.dimension = dimension
        self.delta = delta
        self.rationale = rationale
        self.evidence = evidence
        self.rule_id = rule_id


class SustainabilityIndex:
    def __init__(
        self,
        *,
        grade: str,
        overall: float,
        confidence: float,
        dimensions: dict[str, int],
        components: list[ScoreComponent],
        flags: list[str],
    ) -> None:
        self.grade = grade
        self.overall = overall
        self.confidence = confidence
        self.dimensions = dimensions
        self.components = components
        self.flags = flags


_ENV_RE = re.compile(r"\b(emisi\w+|poluar\w+|de\s*șeuri|deseuri|biodivers\w+|habitat\w+)\b", re.IGNORECASE)
_GOV_RE = re.compile(r"\b(raport\w+|audit\w+|transparen\w+|control\w+|inspec\w+)\b", re.IGNORECASE)
_SOC_RE = re.compile(r"\b(s\s*ăn\w+|sanat\w+|siguran\w+|munc\w+|vulnerab\w+)\b", re.IGNORECASE)
_ECO_RE = re.compile(r"\b(buget\w+|tax\w+|cost\w+|tarif\w+|competitiv\w+|administrativ\w+)\b", re.IGNORECASE)


def score_sustainability(*, text: str, evidence: list[Evidence], quality_level: str | None) -> SustainabilityIndex:
    dims = {"E": 0, "S": 0, "G": 0, "Ec": 0}
    comps: list[ScoreComponent] = []
    flags: list[str] = []

    def add(dim: str, delta: int, rationale: str, rule_id: str) -> None:
        dims[dim] = max(-2, min(2, dims[dim] + delta))
        comps.append(
            ScoreComponent(
                dimension=dim,
                delta=delta,
                rationale=rationale,
                evidence=evidence[:1],
                rule_id=rule_id,
            )
        )

    if _ENV_RE.search(text):
        add("E", +1, "Textul conține termeni de mediu (semnal PoC).", "E.KEYWORDS")
    if _SOC_RE.search(text):
        add("S", +1, "Textul conține termeni sociali/sănătate (semnal PoC).", "S.KEYWORDS")
    if _GOV_RE.search(text):
        add("G", +1, "Textul conține termeni de guvernanță/raportare (semnal PoC).", "G.KEYWORDS")
    if _ECO_RE.search(text):
        add("Ec", -1, "Textul conține termeni de cost/buget (semnal PoC, direcție incertă).", "EC.KEYWORDS")
        flags.append("economic_direction_uncertain")

    overall = sum(dims.values()) / 4.0
    grade = _grade_from_overall(overall)

    confidence = _confidence_from_quality(quality_level)
    if not text.strip():
        confidence = 0.0
        flags.append("no_text")

    return SustainabilityIndex(
        grade=grade,
        overall=overall,
        confidence=confidence,
        dimensions=dims,
        components=comps,
        flags=flags,
    )


def _grade_from_overall(overall: float) -> str:
    if overall >= 1.0:
        return "A"
    if overall >= 0.25:
        return "B"
    if overall <= -0.25:
        return "D"
    return "C"


def _confidence_from_quality(quality_level: str | None) -> float:
    if quality_level == "Q1":
        return 0.85
    if quality_level == "Q2":
        return 0.65
    if quality_level == "Q3":
        return 0.4
    if quality_level == "Q4":
        return 0.1
    return 0.5
