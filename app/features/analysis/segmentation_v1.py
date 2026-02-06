import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    chunk_type: str
    label: str | None
    parent_key: str | None
    page_start: int
    page_end: int
    text: str


# Accept both:
# - canonical headings: "Art. 12"
# - amendment list items: "11. Art.12 se modifică..."
_ART_RE = re.compile(r"^\s*(?:\d+\.)?\s*Art\.?\s*(\d+[A-Za-z]?)\b", re.IGNORECASE)
_ALIN_RE = re.compile(r"^\s*\((\d+)\)\s+", re.IGNORECASE)


def segment_pages_to_structure(pages: list[tuple[int, str]]) -> list[Segment]:
    """Best-effort legal-structure segmentation.

    Pareto v1:
    - Works on per-page text (OCR or native).
    - Detects `Art.` headings and simple `(1)` alineat starts.
    - Produces a flat list of segments with stable keys via (chunk_type,label,parent_key).

    Known limitations (explicitly accepted for PoC v1):
    - No bbox/offsets.
    - No robust header/footer removal.
    - No 2-column reconstruction.
    """

    # Build a single stream with page markers so we can map segments back to page ranges.
    stream_lines: list[tuple[int, str]] = []
    for page_no, page_text in pages:
        for line in page_text.splitlines():
            stream_lines.append((page_no, line.rstrip("\n")))

    # Find article starts.
    art_starts: list[tuple[int, int, str]] = []  # (line_idx, page_no, art_label)
    for i, (page_no, line) in enumerate(stream_lines):
        m = _ART_RE.match(line)
        if m:
            art_starts.append((i, page_no, f"Art. {m.group(1)}"))

    if not art_starts:
        # Single fallback segment.
        if not stream_lines:
            return []
        page_start = stream_lines[0][0]
        page_end = stream_lines[-1][0]
        text = "\n".join(l for _, l in stream_lines).strip()
        return [
            Segment(
                chunk_type="FULL_TEXT",
                label="FULL_TEXT",
                parent_key=None,
                page_start=page_start,
                page_end=page_end,
                text=text,
            )
        ]

    segments: list[Segment] = []

    for idx, (start_i, start_page, art_label) in enumerate(art_starts):
        end_i = art_starts[idx + 1][0] if idx + 1 < len(art_starts) else len(stream_lines)
        art_lines = stream_lines[start_i:end_i]
        if not art_lines:
            continue

        art_page_start = art_lines[0][0]
        art_page_end = art_lines[-1][0]
        art_text = "\n".join(l for _, l in art_lines).strip()
        art_key = f"ARTICLE::{art_label}"

        segments.append(
            Segment(
                chunk_type="ARTICLE",
                label=art_label,
                parent_key=None,
                page_start=art_page_start,
                page_end=art_page_end,
                text=art_text,
            )
        )

        # Alineat segmentation inside the article.
        alin_starts: list[tuple[int, str]] = []  # (relative_line_idx, alin_label)
        for rel_i, (_, line) in enumerate(art_lines):
            m = _ALIN_RE.match(line)
            if m:
                alin_starts.append((rel_i, f"({m.group(1)})"))

        if not alin_starts:
            continue

        for aidx, (alin_start_rel, alin_label) in enumerate(alin_starts):
            alin_end_rel = alin_starts[aidx + 1][0] if aidx + 1 < len(alin_starts) else len(art_lines)
            alin_lines = art_lines[alin_start_rel:alin_end_rel]
            if not alin_lines:
                continue
            alin_page_start = alin_lines[0][0]
            alin_page_end = alin_lines[-1][0]
            alin_text = "\n".join(l for _, l in alin_lines).strip()
            segments.append(
                Segment(
                    chunk_type="ALIN",
                    label=alin_label,
                    parent_key=art_key,
                    page_start=alin_page_start,
                    page_end=alin_page_end,
                    text=alin_text,
                )
            )

    return segments
