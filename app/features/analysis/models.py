from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkCandidate:
    label: str
    text: str


@dataclass(frozen=True)
class Evidence:
    page_number: int
    quote: str


@dataclass(frozen=True)
class Finding:
    kind: str
    label: str
    evidence: list[Evidence]


@dataclass(frozen=True)
class CitizenSummary:
    bullets: list[str]
    limitations: list[str]
