# Civic-tech PoC (Romania): AI-backed bill ingestion + citizen summary + Sustainability Index (A–D)

## 1) PRODUCT OVERVIEW

### Business idea + user value (1 paragraph)
A high-trust civic-tech platform for Romania that ingests proposed bills/laws (PDF/HTML, including messy scans) and produces two outputs: (1) a short citizen-friendly summary and (2) a Sustainability Index (A/B/C/D) with confidence. The core value is trust: every claim is backed by exact source excerpts (document + page + legal label like art./alin. when possible), uncertainty is explicit, and outputs are reproducible and versioned so users can see what changed between document versions.

### Main user flows
- **List**: browse bills (manual uploads + scraped from [`cdep.ro`](https://www.cdep.ro) and [`senat.ro`](https://www.senat.ro)), filter by status/date/source, see analysis status + document quality (Q1–Q4) + last run.
- **View**: open a bill detail page with:
  - documents and versions
  - extracted legal structure (articles/paragraphs) and detected changes
  - Sustainability Index grade + confidence + dimension breakdown
  - citizen summary (strictly derived from extracted structure)
- **Evidence**: click any claim in summary or any score component to open:
  - exact excerpt(s) with page number and bounding box/offsets
  - link to source URL and document hash/version
  - “why this matters” explanation tied to rubric
- **Compare**:
  - compare two versions of the same bill (or bill vs amended law text if available)
  - show diff at article/alin level
  - show how index and confidence changed, with evidence deltas

### Sustainability Index definition (PoC)
**Scope (per your choice):** use bill text + cited laws it amends (follow cross-references). **Index is ESG-lite + economic**.

#### Dimensions (PoC)
Each dimension is scored on a **-2 to +2** ordinal scale based on *textual signals* and *extracted obligations/permissions/penalties*, not on political actors.
- **E: Environment** (climate, air/water/soil pollution, biodiversity, land use, waste, energy efficiency)
- **S: Social** (public health, safety, labor, vulnerable groups, access/affordability)
- **G: Governance** (transparency, enforcement clarity, institutional capacity, anti-corruption controls, reporting/audit)
- **Ec: Economic** (cost burden, competitiveness, administrative load, fiscal impact signals)

#### Evidence-driven scoring rubric (deterministic-first)
For each dimension, compute a **dimension score** from extracted “impact statements” and “mechanisms”:
- **Mechanisms extracted** (deterministic):
  - new/changed obligations, prohibitions, permissions
  - enforcement mechanisms (sanctions, inspections, reporting)
  - scope (who/what/where), thresholds, dates
  - exceptions/derogations
  - references to other laws/articles
- **Impact signals** (deterministic):
  - explicit objectives (e.g., reduce emissions, protect habitats)
  - explicit risk/cost statements (e.g., budget impact, compliance costs)
  - measurable targets/thresholds

**Dimension score aggregation (simple Pareto):**
- Start at 0.
- Add/subtract points based on rule-based patterns tied to extracted mechanisms (e.g., introducing stricter limits on pollutants → +1 E; removing reporting obligations → -1 G).
- Cap to [-2, +2].
- If evidence is insufficient or contradictory, keep score near 0 and reduce confidence.

#### Mapping to A/B/C/D
Compute **overall index score** as weighted sum (default equal weights; configurable later):
- `overall = mean(E, S, G, Ec)` in [-2, +2]
- Map to grade:
  - **A**: overall ≥ +1.0
  - **B**: +0.25 to +0.99
  - **C**: -0.24 to +0.24 (net neutral/unclear)
  - **D**: ≤ -0.25

#### Confidence scoring (separate from grade)
Confidence is **not** “model confidence”; it is **evidence + document quality + completeness**.
- **Inputs**:
  - Document quality Q1–Q4 (see section 4)
  - Coverage: % of detected legal structure with usable text
  - Cross-reference resolution rate: % of references successfully retrieved
  - Numeric sanity: % of numeric constraints parsed without ambiguity
  - Contradiction flags: presence of conflicting clauses or missing annexes
- **Output**: `confidence ∈ [0, 1]` and a label:
  - High (≥0.75), Medium (0.5–0.74), Low (0.25–0.49), Very low (<0.25)
- **Rule**: if confidence < 0.25, show grade as **provisional** and UI must emphasize “insufficient evidence”.

## 2) SYSTEM ARCHITECTURE (PoC)

### High-level components
- **Ingestion**
  - Manual upload (PDF/HTML/DOCX optional)
  - Scrapers for cdep.ro + senat.ro (metadata + document URLs)
- **Parsing / OCR**
  - PDF text extraction (native)
  - OCR only when needed (scanned pages)
  - Layout capture (page images, bounding boxes)
- **Chunking (legal-structure aware)**
  - segment by article/alin/letter where possible
  - store chunk provenance (page + offsets)
- **Analysis (two-stage pipeline)**
  - **Extractor**: deterministic structured extraction + evidence
  - **Explainer**: citizen summary generated strictly from extracted structure
- **API (FastAPI)**
  - CRUD for bills/docs
  - trigger analysis runs
  - serve outputs + evidence
- **Storage (SQLite PoC)**
  - versioned documents, chunks, runs, outputs, errors
- **Frontend (thin PoC)**
  - list + bill detail + evidence viewer + compare

### Two-stage pipeline (recommended)
#### a) Extractor (deterministic, structured)
Goal: produce a **machine-checkable JSON** of what the text says, with pointers to evidence.
- Detect legal structure (titlu/capitol/secțiune/art./alin./lit.)
- Extract:
  - amendments: “se modifică”, “se completează”, “se abrogă”, “se introduce”
  - definitions: “în sensul prezentei legi”, “se definește”
  - obligations/prohibitions/permissions
  - penalties/sanctions (contravenție/infracțiune, cuantum, unități)
  - dates/entry into force
  - cross-references to other laws/articles
- Output includes evidence anchors for every extracted item.

#### b) Explainer (constrained generation)
Goal: produce citizen summary **only** by rewriting extracted items.
- Input: extractor JSON + selected evidence snippets
- Output: summary sections (What changes, Who is affected, When, Enforcement, Potential impacts) with claim-to-evidence links.
- Guardrail: no new entities/numbers not present in extractor JSON.

### Data flow diagram (step-by-step)
1. Ingest bill metadata (manual upload or scrape) → create bill + document records.
2. Download/store raw documents → compute content hash → create document version.
3. Quality triage (Q1–Q4) per document/page.
4. Parse text:
   - if Q1/Q2: extract text + layout
   - if Q3: OCR selected pages
   - if Q4: mark blocked/partial
5. Normalize + segment into legal-structure chunks (art./alin) → store chunks with provenance.
6. Build cross-reference graph from chunks.
7. Extractor run:
   - detect changes/obligations/penalties/definitions
   - resolve references (multi-hop retrieval)
   - compute dimension scores + confidence + quality flags
   - store structured output + evidence map
8. Explainer run:
   - generate citizen summary from structured output
   - attach claim-level evidence links
9. API serves bill view, outputs, and evidence excerpts.
10. Compare view uses versioned outputs + chunk diffs.

## 3) DATA MODEL (PoC) — SQLite schema

### Tables (minimum viable)
- **bills**
  - id (PK)
  - source (enum: manual, cdep, senat)
  - source_bill_id (nullable)
  - title
  - status (nullable)
  - introduced_at (nullable)
  - created_at, updated_at

- **documents** (logical document)
  - id (PK)
  - bill_id (FK)
  - doc_type (e.g., proiect, expunere_motive, raport, aviz, forma_adoptata, anexă, html_page)
  - source_url (nullable)
  - created_at

- **document_versions** (immutable)
  - id (PK)
  - document_id (FK)
  - version_hash (sha256 of bytes)
  - fetched_at
  - mime_type
  - file_path (or blob ref)
  - page_count (nullable)
  - quality_level (Q1–Q4 overall)
  - ocr_applied (bool)
  - notes (nullable)

- **pages** (optional but useful for OCR + evidence)
  - id (PK)
  - document_version_id (FK)
  - page_number
  - text (nullable)
  - ocr_text (nullable)
  - quality_level (Q1–Q4)
  - has_handwriting (bool)
  - image_path (nullable)

- **chunks** (legal-structure aware)
  - id (PK)
  - document_version_id (FK)
  - chunk_type (title/capitol/sectiune/articol/alin/litera/annex)
  - label (e.g., art. 5, alin. 2)
  - parent_chunk_id (nullable FK)
  - page_start, page_end
  - text
  - char_start, char_end (offsets within concatenated page text or within page)
  - bbox_json (nullable; per-page bounding boxes)
  - created_at

- **analysis_runs**
  - id (PK)
  - bill_id (FK)
  - input_fingerprint (hash of document_version hashes + pipeline version)
  - pipeline_version (git sha or semantic)
  - status (queued/running/succeeded/failed/partial/blocked)
  - started_at, finished_at
  - quality_summary_json (coverage, missing_pages, unresolved_refs)

- **outputs** (one per run)
  - id (PK)
  - analysis_run_id (FK)
  - output_type (extractor_json, explainer_summary, sustainability_index)
  - content_json (or content_text for summary)
  - created_at

- **evidence** (claim-to-source mapping)
  - id (PK)
  - analysis_run_id (FK)
  - claim_id (stable id within output)
  - document_version_id (FK)
  - page_number
  - chunk_id (nullable)
  - article_label (nullable)
  - alin_label (nullable)
  - char_start, char_end
  - bbox_json (nullable)
  - excerpt_text

- **errors**
  - id (PK)
  - analysis_run_id (FK)
  - stage (ingest/parse/ocr/chunk/extract/explain)
  - error_code
  - message
  - details_json
  - created_at

### Traceability requirements (must-have fields)
- doc_type, source_url
- version_hash per document version
- page_number + offsets (char_start/end) and bbox when available
- article/alin labels when detected
- pipeline_version + input_fingerprint
- never overwrite outputs; create new analysis_run

### Migration path to Postgres
- Keep schema relational and avoid SQLite-specific features.
- Use integer PKs + explicit FKs.
- Store JSON in text columns initially; later migrate to Postgres JSONB.

## 4) DOCUMENT HANDLING STRATEGY

### Quality triage levels Q1–Q4
- **Q1 Native digital**: selectable text, consistent encoding, pages present.
- **Q2 Digital but messy**: selectable text but broken layout, hyphenation, missing diacritics, copy/paste artifacts.
- **Q3 Scanned/OCR-needed**: image-based pages; OCR required for most content.
- **Q4 Unreadable/unsafe**: severe blur, missing pages, heavy handwriting overprint, or OCR confidence too low.

### Decision rules
- **When to run OCR**
  - If PDF text extraction yields low text density per page (e.g., < N chars) OR high ratio of non-letter glyphs.
  - If page is image-only.
  - Run OCR per-page (not whole doc) to minimize cost.
- **When to block analysis**
  - Missing critical pages (first page with title/scope, amendment articles, annex referenced but absent).
  - Q4 for pages containing detected amendment clauses.
  - Cross-reference resolution fails for key amended provisions and no fallback text is available.
- **When to provide partial analysis**
  - Some pages Q3/Q4 but amendment clauses are readable.
  - Provide “partial” status with explicit missing sections list.
- **When to provide intent-only summary**
  - If only objectives/explanatory memo is readable but normative text is not.
  - UI must label as “intent-only (non-normative)” and exclude scoring or set confidence very low.

### Handwritten notes policy
- Detect handwriting (heuristic: OCR engine handwriting flag or image classifier later).
- Store handwriting regions separately as annotations.
- Treat as **non-binding** unless the document explicitly states it is an official amendment and is confirmed in typed normative text.
- Never score sustainability impacts from handwriting.

## 5) CONTEXT PRESERVATION / RAG MITIGATION

### Chunking strategy
- Chunk by **legal structure** (art./alin./lit./annex), not by tokens.
- Preserve hierarchy: title → chapter → section → article → paragraph.

### Cross-reference graph
- Parse mentions like `art. 5 alin. (2)`, `Legea nr. X/YYYY`, `Codul ...`.
- Build a graph:
  - nodes: chunks (and external law provisions when available)
  - edges: references (type: amends, cites, defines, exception)

### Multi-hop retrieval (deterministic)
1. Seed chunk (where claim originates).
2. Add parent + siblings (same article) to preserve local context.
3. Follow explicit references to other articles/alin.
4. If range reference detected (e.g., art. 2–10), fetch all in range and check completeness.
5. Add annexes if referenced.

### Guardrails
- **Negation preservation**: detect `nu`, `fără`, `se interzice`, `se exceptează` and keep clause polarity.
- **Numeric sanity checks**: parse amounts, units, thresholds; flag ambiguous separators and missing units.
- **Missing annex detection**: if text references “Anexa” but annex chunk absent → block/partial.
- **Range completeness checks**: if art. 2–10 referenced but only subset present → reduce confidence + flag.

### Preventing context loss and false clarity
- Every generated sentence must link to at least one excerpt.
- If extractor cannot resolve a reference, explainer must state uncertainty (“Textul face trimitere la… dar nu am putut recupera prevederea completă”).
- Avoid summarizing beyond extracted structure; no speculative impacts.

## 6) API DESIGN (FastAPI)

### Endpoints (PoC)
- `GET /health`
- `GET /bills` (filters: source, status, date range, has_analysis)
- `POST /bills` (manual create)
- `GET /bills/{id}`
- `GET /bills/{id}/documents`
- `POST /bills/{id}/documents` (upload or attach URL)
- `POST /bills/{id}/analysis` (trigger run; returns run id)
- `GET /bills/{id}/analysis` (latest + list of runs)
- `GET /bills/{id}/evidence?claim_id=...` (or `GET /analysis_runs/{run_id}/evidence`)

### Minimal async/background processing
Pareto option: **job table + worker loop**.
- `jobs` table: id, type, payload_json, status, attempts, scheduled_at, locked_at.
- A single worker process (or thread) polls and executes.
- Justification: avoids Redis/Celery for PoC; still supports retries and observability.
- Deviate to a queue (RQ/Celery) only if concurrency/throughput becomes a bottleneck.

## 7) DEPLOYMENT (FREE-FIRST)

### Local dev workflow
- Run FastAPI + SQLite locally.
- Store documents on disk under a versioned directory keyed by hash.
- Run worker loop as separate process.

### Free hosting options (PoC)
- Backend:
  - Fly.io free/low tier (simple container) OR Render free tier (if available) with SQLite caveats.
  - If SQLite persistence is risky on free tiers, store DB in a mounted volume or switch to managed Postgres free tier early.
- Frontend:
  - Vercel/Netlify free tier.
- Storage:
  - Prefer object storage free tier if needed; otherwise keep small PoC docs in repo releases is not recommended.

### Plan B: single cheap VPS
- One small VPS running:
  - FastAPI + worker
  - Postgres (optional upgrade)
  - file storage on disk

### Scheduled ingestion
- GitHub Actions cron:
  - run scrapers nightly
  - enqueue new documents for processing
  - store scrape logs as artifacts

## 8) PITFALLS & THREATS (with mitigations)

### A) Data quality
1. **Scanned PDFs with OCR noise**
   - Impact: wrong extraction → wrong claims/scores
   - Likelihood: high
   - Detection: low OCR confidence, low text density, high garbage char ratio
   - Mitigation: Q-level triage, per-page OCR, block/partial modes, require evidence links, reduce confidence
2. **Missing pages / missing annexes**
   - Impact: false completeness
   - Likelihood: medium
   - Detection: page count mismatch, “Anexa” references without annex chunks
   - Mitigation: completeness checks, explicit missing list, block scoring if annex is normative
3. **Multiple versions with subtle changes**
   - Impact: outdated analysis
   - Likelihood: high
   - Detection: version_hash changes, source URL updated
   - Mitigation: immutable document_versions, input_fingerprint, compare view, never overwrite outputs

### B) Legal nuance
1. **Cross-references and delegated legislation**
   - Impact: misinterpretation of effect
   - Likelihood: high
   - Detection: unresolved reference rate, reference graph depth
   - Mitigation: multi-hop retrieval, confidence penalty, show unresolved refs prominently
2. **Ambiguous wording / exceptions**
   - Impact: polarity errors (e.g., exceptions flip meaning)
   - Likelihood: medium
   - Detection: negation/exception keywords, conflicting clauses
   - Mitigation: negation guardrails, require sibling/parent context, highlight exceptions in summary

### C) Trust & ethics
1. **Bias accusations / perceived political ranking**
   - Impact: reputational
   - Likelihood: medium
   - Detection: user feedback, media scrutiny
   - Mitigation: analyze texts not actors, no party/person scoring, publish rubric, show evidence for every claim
2. **False authority from AI phrasing**
   - Impact: users over-trust
   - Likelihood: high
   - Detection: low confidence but assertive language
   - Mitigation: constrained explainer, uncertainty templates, confidence label always visible

### D) Security & abuse
1. **Prompt injection via documents**
   - Impact: corrupted outputs
   - Likelihood: medium
   - Detection: presence of instruction-like text, anomalies in output
   - Mitigation: extractor-first design, treat docs as data, strict schema, no tool execution from text
2. **DoS via massive PDFs / zip bombs**
   - Impact: downtime/cost
   - Likelihood: medium
   - Detection: file size/page count thresholds
   - Mitigation: upload limits, page limits, timeouts, queue backpressure
3. **Data poisoning (malicious uploads)**
   - Impact: degraded trust
   - Likelihood: low-medium
   - Detection: source allowlist, anomaly checks
   - Mitigation: label source provenance, separate manual uploads, moderation flagging

## 9) PARETO DECISION LOG

| Decision | Default (Pareto) option | When to deviate | Tradeoff summary | Not now alternatives |
|---|---|---|---|---|
| Background processing | Job table + worker loop | Need high concurrency | Simple, observable, no extra infra | Celery + Redis |
| Storage | SQLite + file system | Multi-instance deploy | Minimal ops, easy dev | Postgres + S3 |
| OCR | Per-page OCR only when needed | Mostly scanned corpus | Cost control, faster | Full-doc OCR pipeline |
| Summarization | Explainer constrained to extractor JSON | Need richer narrative | High trust, fewer hallucinations | Free-form LLM summary |
| Retrieval | Legal-structure chunks + reference graph | Complex amendments | Better context, fewer errors | Token chunking |
| Scoring | Rule-based rubric + confidence | Need domain calibration | Explainable, cheap | ML/LLM scoring |

## 10) MILESTONES (deliverables + relative effort)

- **Milestone 1 (S/M)**: single PDF upload → analysis → evidence UI
  - Upload PDF, versioning, Q1–Q4 triage
  - Chunking by art./alin (best-effort)
  - Extractor JSON + evidence mapping
  - Citizen summary constrained to extractor
  - Minimal UI: bill page + clickable evidence

- **Milestone 2 (M/L)**: batch scraping (50–200 bills) + nightly runs
  - Scrapers for cdep.ro + senat.ro
  - Document download/versioning
  - Job queue + worker reliability
  - Dashboard for run status + errors

- **Milestone 3 (M/L)**: evaluation suite + confidence + compare view
  - Gold set of annotated bills (structure + key claims)
  - Automated checks (missing annex, negation, numeric parsing)
  - Compare view across versions
  - Confidence calibration + reporting
