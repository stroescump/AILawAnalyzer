from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    image_path: Path
    text: str


def render_pdf_to_pages(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list[RenderedPage]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    pages: list[RenderedPage] = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        pix = page.get_pixmap(matrix=mat)
        img_path = out_dir / f"{i+1}.png"
        pix.save(str(img_path))
        pages.append(RenderedPage(page_number=i + 1, image_path=img_path, text=text))

    return pages
