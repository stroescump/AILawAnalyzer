from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpanRef:
    page_number: int
    quote: str
    bbox_json: str | None = None
    char_start: int | None = None
    char_end: int | None = None


@dataclass(frozen=True)
class StructureNode:
    node_id: str
    node_type: str  # title/capitol/sectiune/articol/alin/litera/annex/unknown
    label: str | None
    parent_id: str | None
    page_start: int
    page_end: int
    text: str
    spans: list[SpanRef]


@dataclass(frozen=True)
class ReferenceEdge:
    source_node_id: str
    raw_text: str
    target: str  # normalized target string (e.g., "art:5 alin:2", "lege:123/2012")
    kind: str  # refers_to/amends/repeals/defines/exception_of
    confidence: float


@dataclass(frozen=True)
class Mechanism:
    mechanism_id: str
    kind: str  # obligation/prohibition/permission/definition/sanction/procedure/amendment
    actor: str | None
    action: str | None
    obj: str | None
    conditions: list[str]
    exceptions: list[str]
    effective_date: str | None
    references: list[str]
    source_node_id: str
    evidence: list[SpanRef]
    field_confidence: dict[str, float]


@dataclass(frozen=True)
class ImpactStatement:
    impact_id: str
    dimension: str  # E/S/G/Ec
    polarity: int  # -2..+2
    rationale: str
    mechanism_ids: list[str]
    evidence: list[SpanRef]
    confidence: float
