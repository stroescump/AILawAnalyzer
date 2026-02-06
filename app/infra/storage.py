import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlobRef:
    sha256: str
    original_path: Path
    pages_dir: Path


class BlobStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def put_bytes(self, data: bytes, ext: str) -> BlobRef:
        sha = hashlib.sha256(data).hexdigest()
        base = self._root / "blobs" / sha
        base.mkdir(parents=True, exist_ok=True)
        original = base / f"original{ext}"
        if not original.exists():
            original.write_bytes(data)
        pages_dir = base / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        return BlobRef(sha256=sha, original_path=original, pages_dir=pages_dir)
