from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.features.knowledge.auth import require_admin
from app.features.knowledge.errors import PublishValidationError
from app.features.knowledge.validation import (
    validate_claim_template_publish,
    validate_knowledge_pack_publish,
    validate_sme_claim_publish,
)
from app.infra.repo_knowledge import KnowledgeRepo, ObjectType

router = APIRouter(prefix="/api/admin/knowledge", tags=["admin-knowledge"])


def _actor(request: Request) -> str:
    # PoC: no auth yet; keep an explicit actor field for auditability.
    return request.headers.get("X-Actor", "anonymous")


def _parse_object_type(s: str) -> ObjectType:
    if s not in ("sme_claim", "knowledge_pack", "claim_template"):
        raise HTTPException(status_code=400, detail="invalid_object_type")
    return s  # type: ignore[return-value]


@router.post("/{object_type}/{object_id}")
def create_object(request: Request, object_type: str, object_id: str) -> dict[str, Any]:
    require_admin(request)
    repo = KnowledgeRepo(request.app.state.db)
    ot = _parse_object_type(object_type)
    try:
        repo.create_object(ot, object_id=object_id, actor=_actor(request))
    except Exception as e:  # sqlite integrity
        raise HTTPException(status_code=409, detail=f"create_failed:{type(e).__name__}")
    return {"object_type": ot, "object_id": object_id, "status": "draft"}


@router.get("/{object_type}")
def list_objects(request: Request, object_type: str) -> dict[str, Any]:
    require_admin(request)
    repo = KnowledgeRepo(request.app.state.db)
    ot = _parse_object_type(object_type)
    objs = repo.list_objects(ot)
    return {
        "object_type": ot,
        "items": [
            {
                "object_id": o.object_id,
                "current_version": o.current_version,
                "status": o.status,
                "created_by": o.created_by,
                "created_at": o.created_at,
            }
            for o in objs
        ],
    }


@router.get("/{object_type}/{object_id}")
def get_object(request: Request, object_type: str, object_id: str) -> dict[str, Any]:
    require_admin(request)
    repo = KnowledgeRepo(request.app.state.db)
    ot = _parse_object_type(object_type)
    obj = repo.get_object(ot, object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not_found")
    draft = repo.get_version(ot, object_id, version=0)
    current = None
    if obj.current_version is not None:
        current = repo.get_version(ot, object_id, version=int(obj.current_version))
    return {
        "object_type": ot,
        "object": {
            "object_id": obj.object_id,
            "current_version": obj.current_version,
            "status": obj.status,
            "created_by": obj.created_by,
            "created_at": obj.created_at,
        },
        "draft": None
        if not draft
        else {
            "version": draft.version,
            "content": draft.content,
            "content_hash": draft.content_hash,
            "status": draft.status,
            "created_by": draft.created_by,
            "created_at": draft.created_at,
        },
        "current": None
        if not current
        else {
            "version": current.version,
            "content": current.content,
            "content_hash": current.content_hash,
            "status": current.status,
            "created_by": current.created_by,
            "approved_by": current.approved_by,
            "created_at": current.created_at,
            "approved_at": current.approved_at,
        },
    }


@router.put("/{object_type}/{object_id}/draft")
def upsert_draft(
    request: Request, object_type: str, object_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    require_admin(request)
    repo = KnowledgeRepo(request.app.state.db)
    ot = _parse_object_type(object_type)
    try:
        res = repo.upsert_draft_version(ot, object_id=object_id, content=body, actor=_actor(request))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"draft_failed:{type(e).__name__}")
    return {
        "object_type": ot,
        "object_id": res.object_id,
        "version": res.version,
        "content_hash": res.content_hash,
    }


@router.post("/{object_type}/{object_id}/publish")
def publish(request: Request, object_type: str, object_id: str) -> dict[str, Any]:
    require_admin(request)
    repo = KnowledgeRepo(request.app.state.db)
    ot = _parse_object_type(object_type)
    actor = _actor(request)

    def _validator(content: dict[str, Any]) -> None:
        if ot == "sme_claim":
            validate_sme_claim_publish(content)
        elif ot == "knowledge_pack":
            validate_knowledge_pack_publish(content)
        elif ot == "claim_template":
            validate_claim_template_publish(content)
        else:
            raise ValueError("invalid_object_type")

    try:
        res = repo.publish(ot, object_id=object_id, actor=actor, validate_fn=_validator)
    except PublishValidationError as e:
        issues = [i.__dict__ for i in e.issues]
        repo.audit_validation_failure(actor=actor, object_type=ot, object_id=object_id, issues=issues)
        raise HTTPException(
            status_code=409,
            detail={"error": "publish_validation_failed", "issues": issues},
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"error": str(e)})

    return {
        "object_type": ot,
        "object_id": res.object_id,
        "version": res.version,
        "content_hash": res.content_hash,
    }
