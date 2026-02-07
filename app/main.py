from fastapi import FastAPI

from app.config import load_config
from app.features.analysis.api import router as analysis_router
from app.features.documents.api import router as documents_router
from app.features.ingest.api import router as ingest_router
from app.features.knowledge.api import router as knowledge_router
from app.features.knowledge.web import router as knowledge_web_router
from app.features.ocr.api import router as ocr_router
from app.features.runs.api import router as runs_router
from app.infra.db import DbConfig, connect, migrate
from app.web.health import router as health_router


def create_app() -> FastAPI:
    cfg = load_config()
    conn = connect(DbConfig(path=cfg.db_path))
    migrate(conn)

    app = FastAPI(title="Civic Sustainability PoC", version="0.1.0")
    app.state.cfg = cfg
    app.state.db = conn
    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(ocr_router)
    app.include_router(analysis_router)
    app.include_router(runs_router)
    app.include_router(documents_router)
    app.include_router(knowledge_router)
    app.include_router(knowledge_web_router)
    return app


app = create_app()
