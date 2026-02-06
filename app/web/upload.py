from fastapi import APIRouter, Request, UploadFile

from app.infra.repo_bills import BillRepo
from app.infra.repo_documents import DocumentRepo, DocumentVersionRepo
from app.infra.storage import BlobStore

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("/upload")
async def upload_bill(request: Request, title: str, file: UploadFile) -> dict[str, object]:
    data = await file.read()
    if not data:
        return {"error": "empty_file"}

    cfg = request.app.state.cfg
    conn = request.app.state.db

    bill = BillRepo(conn).create(source="manual", title=title)
    doc = DocumentRepo(conn).create(bill_id=bill.id, doc_type="proiect", source_url=None)

    ext = ".pdf" if (file.filename or "").lower().endswith(".pdf") else ""
    blob = BlobStore(cfg.blobs_dir).put_bytes(data, ext=ext)

    ver = DocumentVersionRepo(conn).create(
        document_id=doc.id,
        version_hash=blob.sha256,
        mime_type=file.content_type or "application/octet-stream",
        file_path=str(blob.original_path),
        page_count=None,
        quality_level=None,
        ocr_applied=False,
        notes=None,
    )

    return {
        "bill_id": bill.id,
        "document_id": doc.id,
        "document_version_id": ver.id,
        "sha256": blob.sha256,
    }
