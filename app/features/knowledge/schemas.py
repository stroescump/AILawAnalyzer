from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceRef(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    url: HttpUrl
    license: str | None = Field(default=None, max_length=200)


class KnowledgePackContent(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    scope: str = Field(min_length=10, max_length=2000)
    sources: list[SourceRef] = Field(min_length=1, max_length=50)


Domain = Literal["E", "S", "G"]


class SmeClaimContent(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    domain: Domain
    claim: str = Field(min_length=10, max_length=4000)
    supported_by_pack_ids: list[str] = Field(min_length=1, max_length=20)
    trigger_keywords: list[str] = Field(default_factory=list, max_length=50)


Verdict = Literal["positive", "negative", "mixed", "unclear"]


class ClaimTemplateContent(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    dimension: str = Field(min_length=2, max_length=80)
    verdict: Verdict
    required_slots: list[str] = Field(min_length=1, max_length=30)
    allowed_evidence_types: list[str] = Field(min_length=1, max_length=30)
