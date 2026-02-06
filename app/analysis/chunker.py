import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkCandidate:
    label: str
    text: str


_ART_RE = re.compile(r"^\s*Art\.?\s*(\d+[A-Za-z]?)\b", re.IGNORECASE)


def chunk_by_article(text: str) -> list[ChunkCandidate]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []

    for i, line in enumerate(lines):
        m = _ART_RE.match(line)
        if m:
            starts.append((i, f"Art. {m.group(1)}"))

    if not starts:
        return [ChunkCandidate(label="FULL_TEXT", text=text.strip())]

    chunks: list[ChunkCandidate] = []
    for idx, (start_i, label) in enumerate(starts):
        end_i = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start_i:end_i]).strip()
        if body:
            chunks.append(ChunkCandidate(label=label, text=body))

    return chunks
