from pathlib import Path

from app.infra.storage import BlobStore


def test_put_bytes_is_idempotent(tmp_path: Path) -> None:
    store = BlobStore(root=tmp_path)

    payload = b"hello"

    ref1 = store.put_bytes(data=payload, ext=".pdf")
    ref2 = store.put_bytes(data=payload, ext=".pdf")

    assert ref1 == ref2
    assert ref1.original_path.exists()
    assert ref1.original_path.read_bytes() == payload

    assert ref1.pages_dir.exists()
    assert ref1.pages_dir.is_dir()
