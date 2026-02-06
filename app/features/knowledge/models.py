from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


KnowledgeStatus = Literal["draft", "published", "archived"]


@dataclass(frozen=True)
class KnowledgeObject:
    object_id: str
    current_version: int | None
    status: KnowledgeStatus
    created_by: str
    created_at: str


@dataclass(frozen=True)
class KnowledgeVersion:
    object_id: str
    version: int
    content: dict[str, Any]
    content_hash: str
    status: KnowledgeStatus
    created_by: str
    approved_by: str | None
    created_at: str
    approved_at: str | None
