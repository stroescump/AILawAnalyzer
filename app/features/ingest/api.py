from fastapi import APIRouter, Request, UploadFile

from app.features.ingest.service import IngestService

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("/upload")
async def upload_bill(request: Request, title: str, file: UploadFile) -> dict[str, object]:
    cfg = request.app.state.cfg
    conn = request.app.state.db
    return await IngestService(conn=conn, blobs_dir=cfg.blobs_dir).upload_bill(title=title, file=file)
