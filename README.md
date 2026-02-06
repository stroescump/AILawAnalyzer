# CeMuncescParlamentarii — Civic Sustainability PoC (Romania)

## Business context (brief)
This is a civic-tech PoC for Romania: ingest proposed bills/laws (PDF/HTML, including messy scans) and produce:
1) a short citizen-friendly summary, and
2) a Sustainability Index (A/B/C/D) with confidence.

The product goal is **high trust**: every claim must be backed by exact source excerpts (document version hash + page + offsets/bbox when available). Outputs are reproducible and versioned (no overwrites).

## Run locally
### 1) Create venv + install deps
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn[standard] pydantic-settings python-multipart pypdf pillow pytesseract
```

### 2) Start the API
```bash
. .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `GET http://127.0.0.1:8000/health`

### 3) Upload a PDF (creates bill + document + version)
```bash
curl -X POST "http://127.0.0.1:8000/bills/upload?title=Test%20bill" \
  -F "file=@sample.pdf;type=application/pdf"
```

Artifacts:
- SQLite DB: `data/app.sqlite3`
- Stored uploads: `data/blobs/{sha256}/original.pdf`

## Current API surface (PoC)
- `GET /health`
- `POST /bills/upload?title=...` (multipart file upload)

## Architecture (current + near-term)

### Clean-ish layering (minimal ceremony)
- **Web/API**: request handling, validation, response shaping
- **Infra**: SQLite, repositories, blob storage
- **Domain-ish**: enums and small data structures

### Mermaid: current data flow
```mermaid
flowchart TD
  U[User] -->|POST /bills/upload (PDF)| API[FastAPI]
  API -->|store bytes by sha256| BS[Blob store on disk]
  API -->|migrate + write rows| DB[(SQLite)]
  DB --> B[bills]
  DB --> D[documents]
  DB --> DV[document_versions]
  BS --> FS[(data/blobs/{sha256}/original.pdf)]
```

### Mermaid: target PoC pipeline (next milestones)
```mermaid
flowchart TD
  subgraph Ingest
    S[Scrape/Upload] --> V[Versioned document bytes]
  end

  subgraph Parse
    V --> Q[Quality triage Q1-Q4]
    Q -->|Q1/Q2| TXT[Extract text]
    Q -->|Q3| OCR[OCR per page]
    TXT --> PAGES[Persist pages + page images]
    OCR --> PAGES
  end

  subgraph Analyze
    PAGES --> CH[Chunk by legal structure]
    CH --> XREF[Cross-reference graph]
    XREF --> EXT[Extractor (structured facts + evidence)]
    EXT --> IDX[Sustainability index + confidence]
    EXT --> EXP[Explainer (summary from extracted facts)]
  end

  PAGES --> DB[(SQLite/Postgres later)]
  CH --> DB
  EXT --> DB
  IDX --> DB
  EXP --> DB
```

## Repo rules
See [`agent-guidelines.md`](agent-guidelines.md) for constraints (SOLID/DRY/KISS, type safety, error handling, no magic strings, <150 LOC/file).
