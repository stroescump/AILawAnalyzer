from __future__ import annotations

from typing import Any


def _require_str(obj: dict[str, Any], key: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"missing_or_invalid:{key}")
    return v.strip()


def _require_list(obj: dict[str, Any], key: str) -> list[Any]:
    v = obj.get(key)
    if not isinstance(v, list) or len(v) == 0:
        raise ValueError(f"missing_or_invalid:{key}")
    return v


def validate_sme_claim_publish(content: dict[str, Any]) -> None:
    """Minimal publish-time validation.

    Drafts can be incomplete; publishing requires enough structure to be used.
    """

    _require_str(content, "title")
    _require_str(content, "claim")
    _require_str(content, "domain")
    _require_list(content, "supported_by_pack_ids")


def validate_knowledge_pack_publish(content: dict[str, Any]) -> None:
    _require_str(content, "title")
    _require_str(content, "scope")
    sources = _require_list(content, "sources")
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            raise ValueError(f"invalid_source:{i}")
        _require_str(s, "title")
        _require_str(s, "url")


def validate_claim_template_publish(content: dict[str, Any]) -> None:
    _require_str(content, "title")
    _require_str(content, "dimension")
    _require_str(content, "verdict")
    _require_list(content, "required_slots")
    _require_list(content, "allowed_evidence_types")
