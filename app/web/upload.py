from fastapi import APIRouter, HTTPException, Request, UploadFile

from app.infra.pdf_render import render_pdf_to_pages
from app.infra.repo_bills import BillRepo
from app.infra.repo_documents import DocumentRepo, DocumentVersionRepo
from app.infra.repo_pages import PageRepo
from app.infra.storage import BlobStore

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("/upload")
async def upload_bill(request: Request, title: str, file: UploadFile) -> dict[str, object]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty_file")

    cfg = request.app.state.cfg
    conn = request.app.state.db

    bill = BillRepo(conn).create(source="manual", title=title)
    doc = DocumentRepo(conn).create(bill_id=bill.id, doc_type="proiect", source_url=None)

    ext = ".pdf" if (file.filename or "").lower().endswith(".pdf") else ""
    blob = BlobStore(cfg.blobs_dir).put_bytes(data, ext=ext)

    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="only_pdf_supported")

    rendered = render_pdf_to_pages(blob.original_path, blob.pages_dir)

    ver = DocumentVersionRepo(conn).create(
        document_id=doc.id,
        version_hash=blob.sha256,
        mime_type=file.content_type or "application/pdf",
        file_path=str(blob.original_path),
        page_count=len(rendered),
        quality_level=None,
        ocr_applied=False,
        notes=None,
    )

    pages = PageRepo(conn)
    for p in rendered:
        pages.upsert(
            document_version_id=ver.id,
            page_number=p.page_number,
            text=p.text,
            ocr_text=None,
            quality_level=None,
            has_handwriting=False,
            image_path=str(p.image_path),
        )

    return {
        "bill_id": bill.id,
        "document_id": doc.id,
        "document_version_id": ver.id,
        "sha256": blob.sha256,
        "page_count": len(rendered),
    }
