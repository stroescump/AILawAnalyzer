import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.features.knowledge.auth import require_admin
from app.infra.repo_knowledge import KnowledgeRepo

router = APIRouter(prefix="/admin/knowledge", tags=["admin-ui"])

templates = Jinja2Templates(directory="app/templates")


def _require_admin_ui(request: Request) -> str:
    """Browser-friendly auth.

    We accept the secret via query param so you can test in a browser without
    custom headers. This is PoC-only; do not use in production.
    """

    cfg = request.app.state.cfg
    expected = getattr(cfg, "admin_secret", None)
    provided = request.query_params.get("secret")
    if not expected or not provided or provided != expected:
        raise HTTPException(
            status_code=401,
            detail="admin_unauthorized",
        )
    return provided


@router.get("/knowledge", response_class=HTMLResponse)
def knowledge_home(request: Request) -> HTMLResponse:
    secret = _require_admin_ui(request)
    return templates.TemplateResponse(
        request,
        "admin/knowledge_home.html",
        {
            "title": "Knowledge Admin",
            "secret": secret,
        },
    )


@router.get("/knowledge/create", response_class=HTMLResponse)
def knowledge_create_get(request: Request) -> HTMLResponse:
    secret = _require_admin_ui(request)
    return templates.TemplateResponse(
        request,
        "admin/knowledge_create.html",
        {
            "title": "Create knowledge object",
            "secret": secret,
            "object_type": "sme_claim",
            "object_id": "",
            "error": None,
        },
    )


@router.post("/knowledge/create")
async def knowledge_create_post(request: Request):
    secret = _require_admin_ui(request)
    form = await request.form()
    object_type = str(form.get("object_type") or "").strip()
    object_id = str(form.get("object_id") or "").strip()

    if object_type not in ("sme_claim", "knowledge_pack", "claim_template"):
        return templates.TemplateResponse(
            request,
            "admin/knowledge_create.html",
            {
                "title": "Create knowledge object",
                "secret": secret,
                "object_type": object_type,
                "object_id": object_id,
                "error": "invalid_object_type",
            },
            status_code=400,
        )

    if not object_id or " " in object_id:
        return templates.TemplateResponse(
            request,
            "admin/knowledge_create.html",
            {
                "title": "Create knowledge object",
                "secret": secret,
                "object_type": object_type,
                "object_id": object_id,
                "error": "invalid_object_id",
            },
            status_code=400,
        )

    # Enforce same admin auth as JSON API by setting header from query param.
    request.headers.__dict__["_list"].append((b"x-admin-secret", secret.encode("utf-8")))  # type: ignore[attr-defined]
    require_admin(request)

    from app.features.knowledge.api import create_object as api_create_object

    try:
        api_create_object(request, object_type=object_type, object_id=object_id)
    except HTTPException as e:
        return templates.TemplateResponse(
            request,
            "admin/knowledge_create.html",
            {
                "title": "Create knowledge object",
                "secret": secret,
                "object_type": object_type,
                "object_id": object_id,
                "error": e.detail,
            },
            status_code=e.status_code,
        )

    return RedirectResponse(
        url=f"/admin/knowledge/knowledge/{object_type}/{object_id}/edit?secret={secret}",
        status_code=303,
    )


@router.get("/knowledge/{object_type}", response_class=HTMLResponse)
def knowledge_list(request: Request, object_type: str) -> HTMLResponse:
    secret = _require_admin_ui(request)
    if object_type not in ("sme_claim", "knowledge_pack", "claim_template"):
        raise HTTPException(status_code=404, detail="invalid_object_type")

    repo = KnowledgeRepo(request.app.state.db)
    items = repo.list_objects(object_type)  # type: ignore[arg-type]

    return templates.TemplateResponse(
        request,
        "admin/knowledge_list.html",
        {
            "title": f"{object_type} list",
            "object_type": object_type,
            "items": items,
            "secret": secret,
        },
    )


@router.get("/knowledge/{object_type}/{object_id}", response_class=HTMLResponse)
def knowledge_detail(request: Request, object_type: str, object_id: str) -> HTMLResponse:
    secret = _require_admin_ui(request)
    if object_type not in ("sme_claim", "knowledge_pack", "claim_template"):
        raise HTTPException(status_code=404, detail="invalid_object_type")

    repo = KnowledgeRepo(request.app.state.db)
    obj = repo.get_object(object_type, object_id)  # type: ignore[arg-type]
    if not obj:
        raise HTTPException(status_code=404, detail="not_found")

    draft = repo.get_version(object_type, object_id, version=0)  # type: ignore[arg-type]
    current = None
    if obj.current_version is not None:
        current = repo.get_version(object_type, object_id, version=int(obj.current_version))  # type: ignore[arg-type]

    draft_json = "{}" if not draft else json.dumps(draft.content, ensure_ascii=False, indent=2)

    versions = repo.list_versions(object_type, object_id, limit=50)  # type: ignore[arg-type]

    return templates.TemplateResponse(
        request,
        "admin/knowledge_detail.html",
        {
            "title": f"{object_type}/{object_id}",
            "object_type": object_type,
            "object_id": object_id,
            "obj": obj,
            "draft": draft,
            "current": current,
            "versions": versions,
            "draft_json": draft_json,
            "secret": secret,
        },
    )


@router.get("/knowledge/{object_type}/{object_id}/edit", response_class=HTMLResponse)
def knowledge_edit_get(request: Request, object_type: str, object_id: str) -> HTMLResponse:
    secret = _require_admin_ui(request)
    if object_type not in ("sme_claim", "knowledge_pack", "claim_template"):
        raise HTTPException(status_code=404, detail="invalid_object_type")

    repo = KnowledgeRepo(request.app.state.db)
    obj = repo.get_object(object_type, object_id)  # type: ignore[arg-type]
    if not obj:
        raise HTTPException(status_code=404, detail="not_found")

    draft = repo.get_version(object_type, object_id, version=0)  # type: ignore[arg-type]
    draft_json = "{}" if not draft else json.dumps(draft.content, ensure_ascii=False, indent=2)

    return templates.TemplateResponse(
        request,
        "admin/knowledge_edit.html",
        {
            "title": f"Edit {object_type}/{object_id}",
            "object_type": object_type,
            "object_id": object_id,
            "draft_json": draft_json,
            "issues": [],
            "error": None,
            "secret": secret,
        },
    )


@router.post("/knowledge/{object_type}/{object_id}/edit")
async def knowledge_edit_post(request: Request, object_type: str, object_id: str):
    secret = _require_admin_ui(request)
    if object_type not in ("sme_claim", "knowledge_pack", "claim_template"):
        raise HTTPException(status_code=404, detail="invalid_object_type")

    form = await request.form()
    action = str(form.get("action") or "save")
    draft_json = str(form.get("draft_json") or "{}")

    try:
        body = json.loads(draft_json)
        if not isinstance(body, dict):
            raise ValueError("draft_json must be a JSON object")
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "admin/knowledge_edit.html",
            {
                "title": f"Edit {object_type}/{object_id}",
                "object_type": object_type,
                "object_id": object_id,
                "draft_json": draft_json,
                "issues": [],
                "error": f"invalid_json:{type(e).__name__}",
                "secret": secret,
            },
            status_code=400,
        )

    # Call the JSON API handlers directly (no HTTP roundtrip), but enforce the same admin header auth.
    # We set the header from the query param secret.
    request.headers.__dict__["_list"].append((b"x-admin-secret", secret.encode("utf-8")))  # type: ignore[attr-defined]

    require_admin(request)

    from app.features.knowledge.api import publish as api_publish
    from app.features.knowledge.api import upsert_draft as api_upsert_draft

    if action == "save":
        api_upsert_draft(request, object_type=object_type, object_id=object_id, body=body)
        return RedirectResponse(
            url=f"/admin/knowledge/knowledge/{object_type}/{object_id}?secret={secret}",
            status_code=303,
        )

    if action == "publish":
        # Always save draft first so publish uses the latest content.
        api_upsert_draft(request, object_type=object_type, object_id=object_id, body=body)
        try:
            api_publish(request, object_type=object_type, object_id=object_id)
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, dict) else {"error": str(e.detail)}
            issues = detail.get("issues") if isinstance(detail, dict) else None
            return templates.TemplateResponse(
                request,
                "admin/knowledge_edit.html",
                {
                    "title": f"Edit {object_type}/{object_id}",
                    "object_type": object_type,
                    "object_id": object_id,
                    "draft_json": draft_json,
                    "issues": issues or [],
                    "error": detail.get("error") if isinstance(detail, dict) else "publish_failed",
                    "secret": secret,
                },
                status_code=409,
            )

        return RedirectResponse(
            url=f"/admin/knowledge/knowledge/{object_type}/{object_id}?secret={secret}",
            status_code=303,
        )

    raise HTTPException(status_code=400, detail="invalid_action")
