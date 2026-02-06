import json
import re
from dataclasses import dataclass, asdict

from app.infra.repo_chunks import ChunkRow


@dataclass(frozen=True)
class SegmentationQualityV1:
    article_count: int
    alin_count: int
    has_full_text_fallback: bool
    article_labels: list[str]
    article_label_duplicates: list[str]
    article_label_non_monotonic: bool
    page_coverage_ratio: float
    warnings: list[str]


def compute_segmentation_quality_v1(
    *,
    chunks: list[ChunkRow],
    page_numbers_present: list[int],
) -> SegmentationQualityV1:
    articles = [c for c in chunks if c.chunk_type == "ARTICLE"]
    alins = [c for c in chunks if c.chunk_type == "ALIN"]
    full = [c for c in chunks if c.chunk_type == "FULL_TEXT"]

    labels = [c.label for c in articles if c.label]
    dups: list[str] = []
    seen: set[str] = set()
    for l in labels:
        if l in seen and l not in dups:
            dups.append(l)
        seen.add(l)

    # Monotonicity check: extract first integer from labels like "Art. 10A".
    nums: list[int] = []
    for l in labels:
        m = re.search(r"(\d+)", l)
        if m:
            nums.append(int(m.group(1)))

    non_monotonic = any(nums[i] < nums[i - 1] for i in range(1, len(nums))) if nums else False

    # Page coverage: how many pages are covered by at least one chunk.
    covered: set[int] = set()
    for c in chunks:
        for p in range(c.page_start, c.page_end + 1):
            covered.add(p)

    present = set(page_numbers_present)
    coverage_ratio = (len(covered & present) / len(present)) if present else 0.0

    warnings: list[str] = []
    if not articles and not full:
        warnings.append("no_structure_detected")
    if full:
        warnings.append("used_full_text_fallback")
    if dups:
        warnings.append("duplicate_article_labels")
    if non_monotonic:
        warnings.append("non_monotonic_article_numbers")
    if coverage_ratio < 0.8:
        warnings.append("low_page_coverage")

    return SegmentationQualityV1(
        article_count=len(articles),
        alin_count=len(alins),
        has_full_text_fallback=bool(full),
        article_labels=labels,
        article_label_duplicates=dups,
        article_label_non_monotonic=non_monotonic,
        page_coverage_ratio=coverage_ratio,
        warnings=warnings,
    )


def quality_to_json(q: SegmentationQualityV1) -> str:
    return json.dumps(asdict(q), ensure_ascii=False)
