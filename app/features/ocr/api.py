from fastapi import APIRouter, Request

from app.features.ocr.service import OcrService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/{document_version_id}/ocr")
def ocr_document_version(request: Request, document_version_id: int) -> dict[str, object]:
    conn = request.app.state.db
    return OcrService(conn=conn).ocr_document_version(document_version_id=document_version_id)
