from fastapi import HTTPException, Request


def require_admin(request: Request) -> None:
    cfg = request.app.state.cfg
    expected = getattr(cfg, "admin_secret", None)
    provided = request.headers.get("X-Admin-Secret")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="admin_unauthorized")
