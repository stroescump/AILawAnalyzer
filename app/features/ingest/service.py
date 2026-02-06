from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.infra.pdf_render import render_pdf_to_pages
from app.infra.repo_bills import BillRepo
from app.infra.repo_documents import DocumentRepo, DocumentVersionRepo
from app.infra.repo_pages import PageRepo
from app.infra.storage import BlobStore


class IngestService:
    def __init__(self, *, conn, blobs_dir: str) -> None:
        self._conn = conn
        self._blobs_dir = blobs_dir

    async def upload_bill(self, *, title: str, file: UploadFile) -> dict[str, object]:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="empty_file")

        bill = BillRepo(self._conn).create(source="manual", title=title)
        doc = DocumentRepo(self._conn).create(bill_id=bill.id, doc_type="proiect", source_url=None)

        ext = ".pdf" if (file.filename or "").lower().endswith(".pdf") else ""
        blob = BlobStore(Path(self._blobs_dir)).put_bytes(data, ext=ext)

        if ext != ".pdf":
            raise HTTPException(status_code=400, detail="only_pdf_supported")

        rendered = render_pdf_to_pages(blob.original_path, blob.pages_dir)

        ver = DocumentVersionRepo(self._conn).create(
            document_id=doc.id,
            version_hash=blob.sha256,
            mime_type=file.content_type or "application/pdf",
            file_path=str(blob.original_path),
            page_count=len(rendered),
            quality_level=None,
            ocr_applied=False,
            notes=None,
        )

        pages = PageRepo(self._conn)
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
