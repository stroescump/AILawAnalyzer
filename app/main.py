from fastapi import FastAPI

from app.config import load_config
from app.infra.db import DbConfig, connect, migrate
from app.web.analysis import router as analysis_router
from app.web.health import router as health_router
from app.web.ocr import router as ocr_router
from app.web.upload import router as upload_router


def create_app() -> FastAPI:
    cfg = load_config()
    conn = connect(DbConfig(path=cfg.db_path))
    migrate(conn)

    app = FastAPI(title="Civic Sustainability PoC", version="0.1.0")
    app.state.cfg = cfg
    app.state.db = conn
    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(ocr_router)
    app.include_router(analysis_router)
    return app


app = create_app()
