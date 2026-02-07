from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.features.knowledge.errors import PublishValidationError, ValidationIssue
from app.features.knowledge.schemas import (
    ClaimTemplateContent,
    KnowledgePackContent,
    SmeClaimContent,
)


def _to_issues(e: ValidationError) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for err in e.errors():
        loc = err.get("loc") or []
        path = ".".join(str(p) for p in loc)
        issues.append(
            ValidationIssue(
                code=str(err.get("type") or "validation_error"),
                path=path,
                message=str(err.get("msg") or "invalid"),
            )
        )
    return issues


def validate_sme_claim_publish(content: dict[str, Any]) -> None:
    try:
        SmeClaimContent.model_validate(content)
    except ValidationError as e:
        raise PublishValidationError(_to_issues(e))


def validate_knowledge_pack_publish(content: dict[str, Any]) -> None:
    try:
        KnowledgePackContent.model_validate(content)
    except ValidationError as e:
        raise PublishValidationError(_to_issues(e))


def validate_claim_template_publish(content: dict[str, Any]) -> None:
    try:
        ClaimTemplateContent.model_validate(content)
    except ValidationError as e:
        raise PublishValidationError(_to_issues(e))
