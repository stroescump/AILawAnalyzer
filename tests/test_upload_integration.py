from pathlib import Path

from fastapi.testclient import TestClient

from app.config import AppConfig
from app.infra.db import DbConfig
from app.main import create_app


def test_upload_creates_bill_and_pages(tmp_path: Path) -> None:
    app = create_app()

    # Override config for test isolation.
    app.state.cfg = AppConfig(data_dir=tmp_path)

    # Re-init DB in the new location.
    from app.infra import db as db_mod

    app.state.db = db_mod.connect(DbConfig(path=app.state.cfg.db_path))
    db_mod.migrate(app.state.db)

    client = TestClient(app)

    pdf_path = Path("sample.pdf")
    assert pdf_path.exists(), "sample.pdf must exist in repo root for this test"

    with pdf_path.open("rb") as f:
        resp = client.post(
            "/bills/upload",
            params={"title": "Test bill"},
            files={"file": ("sample.pdf", f, "application/pdf")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["bill_id"] > 0
    assert body["document_version_id"] > 0
    assert body["page_count"] > 0
