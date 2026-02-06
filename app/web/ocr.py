from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.infra.ocr import ocr_image
from app.infra.repo_pages import PageRepo

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/{document_version_id}/ocr")
def ocr_document_version(request: Request, document_version_id: int) -> dict[str, object]:
    conn = request.app.state.db
    pages_repo = PageRepo(conn)
    pages = pages_repo.list_for_version(document_version_id)
    if not pages:
        raise HTTPException(status_code=404, detail="document_version_not_found")

    updated = 0
    skipped_missing_image = 0

    for p in pages:
        if p.ocr_text and p.ocr_text.strip():
            continue
        if not p.image_path:
            skipped_missing_image += 1
            continue

        img_path = Path(p.image_path)
        if not img_path.is_absolute():
            # `image_path` is stored relative to repo root (e.g., data/blobs/...)
            img_path = img_path
        if not img_path.exists():
            skipped_missing_image += 1
            continue

        res = ocr_image(path=img_path)
        pages_repo.upsert(
            document_version_id=document_version_id,
            page_number=p.page_number,
            text=p.text,
            ocr_text=res.text,
            quality_level=p.quality_level,
            has_handwriting=p.has_handwriting,
            image_path=p.image_path,
        )
        updated += 1

    return {
        "document_version_id": document_version_id,
        "pages_ocr_updated": updated,
        "pages_skipped_missing_image": skipped_missing_image,
    }
