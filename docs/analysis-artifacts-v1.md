# Analysis artifacts v1 — how the pieces fit together

This doc explains **why the v1 artifact models exist**, how they connect to the DB, and how they flow through the pipeline.

## 0) The core idea (why models at all)

We want **high-trust outputs**:

- Every claim must be backed by **exact source excerpts** (page + best-effort article/alin).
- We must be able to say **what we know vs what we’re guessing**.
- We must be able to **re-run** and compare results without overwriting history.

To do that, we treat analysis as producing **immutable artifacts** per run:

- `structure_tree_v1`: “How the document is organized” (Art./alin/lit tree)
- `reference_graph_v1`: “What cites what” (art/alin references)
- `mechanisms_v1`: “What the text *does*” (obligations, prohibitions, sanctions, definitions, amendments)
- `impacts_v1`: “So what?” (sustainability-relevant impact statements derived from mechanisms)

These artifacts are stored as JSON in the `outputs` table, keyed by `analysis_run_id`.

## 1) Where artifacts live in the database

### 1.1 Immutable run boundary

- A bill can have multiple documents and versions.
- Each analysis execution creates a new `analysis_runs` row.
- Each run writes one or more `outputs` rows.

This is the reproducibility guarantee: **no overwrites**.

### 1.2 Tables involved (PoC)

- `bills` — the bill entity
- `documents` — a logical document (e.g., “expunere de motive”, “proiect de lege”)
- `document_versions` — a specific file/version (sha256 hash)
- `pages` — per-page extracted text + OCR text + image path
- `chunks` — extracted structural chunks (will become the structure tree backing store)
- `analysis_runs` — one execution (status, timestamps, quality summary)
- `outputs` — JSON artifacts per run (typed by `OutputType`)
- `evidence` — normalized evidence snippets (page + excerpt + optional anchors)
- `errors` — structured errors per run

## 2) The two-stage pipeline (Extractor → Explainer)

### Stage A: Extractor (deterministic, structured)

Input:
- `document_version_id`
- `pages.text` and/or `pages.ocr_text`

Output artifacts:
1) `structure_tree_v1`
2) `reference_graph_v1`
3) `mechanisms_v1`

Plus:
- `chunks` rows (tree-ish representation with provenance)
- `evidence` rows (snippets referenced by mechanisms)

### Stage B: Explainer (constrained narrative)

Input:
- `mechanisms_v1` (+ optionally `impacts_v1`)

Output:
- citizen summary that **only rephrases extracted mechanisms**
- sustainability index (A/B/C/D) derived from `impacts_v1` + confidence gates

Rule: the explainer is not allowed to introduce new facts; it can only:
- reorder
- simplify language
- add “unknown/uncertain” disclaimers based on confidence

## 3) Why these specific models exist

The models in [`SpanRef`](../app/features/analysis/artifacts_v1.py) and friends are there to enforce one thing:

> Every extracted item must be able to point back to the source.

### 3.1 `SpanRef` (the most important type)

A `SpanRef` is a pointer to “where this came from”. It is intentionally flexible because PDFs are messy.

It can include:
- `document_version_id`
- `page`
- `article_label` / `alin_label` (best-effort)
- `text_excerpt` (the actual evidence snippet)
- optional offsets/bbox later

If we can’t reliably compute offsets, we still have page + excerpt.

### 3.2 `StructureNode`

Represents the legal structure tree:

- root
  - Art. 1
    - (1)
    - (2)
  - Art. 2

Why it matters:
- chunking by structure prevents context loss
- it’s the backbone for reference resolution (art/alin mentions)

### 3.3 `ReferenceEdge`

Represents a citation like:
- “art. 5 alin. (2) din Legea 123/2012”

Why it matters:
- legal meaning often lives in referenced text
- we need multi-hop retrieval: seed chunk → follow refs → include definitions

### 3.4 `Mechanism`

A mechanism is a structured “legal effect” extracted from text.

Examples:
- obligation: “Operatorii economici **au obligația** să …”
- prohibition: “Se **interzice** …”
- sanction: “Constituie contravenție … și se sancționează cu amendă …”
- definition: “În sensul prezentei legi, … înseamnă …”
- amendment: “La art. X se modifică …”

Why it matters:
- sustainability scoring should be based on mechanisms, not keywords
- mechanisms can be validated (negation, exceptions, numeric ranges)

### 3.5 `ImpactStatement`

An impact statement is a *derived* interpretation:
- dimension: e.g., climate, pollution, biodiversity, circularity, governance
- polarity: positive/negative/mixed/unknown
- rationale: short explanation referencing mechanism ids

Why it matters:
- it’s the bridge from “what the law says” → “what it likely changes”
- it can be conservative and confidence-gated

## 4) How this ties to the current code

### 4.1 Current state (today)

- Upload creates `document_versions` + `pages`.
- OCR endpoint fills `pages.ocr_text`.
- Analysis endpoint currently does v0 chunking + v0 extraction.

We added:
- new output types in [`OutputType`](../app/domain/enums.py)
- v1 artifact dataclasses in [`app/features/analysis/artifacts_v1.py`](../app/features/analysis/artifacts_v1.py)

### 4.2 Next implementation steps (what will make this feel real)

1) **Segmentation v1** writes:
   - `chunks` rows with parent/child relationships
   - `outputs.structure_tree_v1` JSON

2) **Reference extraction v1** writes:
   - `outputs.reference_graph_v1`

3) **Mechanism extraction v1** writes:
   - `outputs.mechanisms_v1` + `evidence` rows

Once those exist, the models stop feeling abstract because you can:
- open a run
- fetch `structure_tree_v1`
- click a mechanism
- see its evidence excerpt + page

## 5) Minimalism guardrails (to avoid abstraction creep)

We will keep this strict:

- Artifacts are **data**, not behavior.
- No deep class hierarchies.
- No “domain services” explosion.
- If a model isn’t used by an endpoint or persisted output within 1–2 milestones, we delete it.

If you want, we can also collapse structure/refs to plain JSON dicts and keep only `SpanRef` + `Mechanism` + `ImpactStatement` as typed objects.
