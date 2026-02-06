# SME feedback ingestion orchestration (PoC)

Decision captured
- Primary authoring workflow: Admin UI form
- Approval: single-approver for all templates/packs in PoC
- SME onboarding: pre-vetted SMEs get credentials; we optimize for low-friction authoring.
- Reason: reduce friction for non-technical SMEs; accept higher governance risk short-term, mitigate via strict schemas + versioning + audit logs.

## Goals
- SME input is pristine and machine-usable: no ambiguity, no missing context.
- SMEs can submit **theories/conclusions + supporting evidence** without being overwhelmed.
- Every conclusion is reproducible: references exact pack/template versions.
- No free-form expert text becomes executable knowledge without validation.

## Core objects

Design principle: progressive disclosure
- The UI starts with a minimal “SME claim” form (low friction).
- The system then guides the SME to add the minimum evidence needed to publish.
- Drafts can be saved with missing fields; publishing cannot.

### 1) SME Claim (author-friendly wrapper)
This is what SMEs create first: a theory/conclusion they want the system to be able to use.

Draft fields (minimal)
- claim_id (slug)
- title_ro
- conclusion_ro (free text, but will be converted into a constrained template on publish)
- domain_tags[] (e.g., drug_policy, public_health, criminal_justice)
- applicability_notes (free text)
- created_by, created_at

Publish-time requirements
- Must be linked to at least 1 Evidence Pack version
- Must be converted into a Claim Template (fixed wording + typed slots)

### 2) Evidence Pack
A curated bundle of sources + excerpts that can support one or more claim templates.

Draft fields (minimal)
- pack_id (slug)
- title_ro
- short_summary_ro (1–3 sentences)
- sources[] (can start with just URL + citation)

Publish-time requirements (UI must enforce)
- scope
  - applies_to
  - does_not_apply_to
  - jurisdiction_notes
- strength
  - rating: low|medium|high
  - rationale
- sources[]
  - citation (APA-ish)
  - url
  - license (enum + free text)
  - excerpt_text
  - excerpt_location (page/section)
  - notes
- counterevidence[] (same schema as sources) OR explicit “none found” + justification
- tags[]
- created_by, created_at

### 3) Claim Template
Defines what the LLM is allowed to conclude (fixed wording + typed slots).

Draft fields (minimal)
- template_id (slug)
- title_ro
- allowed_conclusion_ro (string with slots)

Publish-time requirements
- slots_schema (typed)
- applicability_tests (deterministic predicates over extracted facts)
- required_citations
  - min_bill_quotes
  - min_pack_excerpts
- risk_notes
- created_by, created_at

### 3) Publication snapshot
A published, immutable version of a pack/template.

Required fields
- version (integer)
- content_hash (sha256 of canonical JSON)
- status: draft|published|deprecated
- approved_by, approved_at
- changelog

## Storage model (SQLite PoC)
Tables (new)
- sme_claims
  - id (pk)
  - claim_id (unique)
  - status (draft|published|deprecated)
  - created_by
  - created_at
- sme_claim_versions
  - id (pk)
  - claim_id (fk)
  - version
  - content_json
  - content_hash
  - status
  - created_by
  - approved_by
  - created_at
  - approved_at

- knowledge_packs
  - id (pk)
  - pack_id (unique)
  - current_version
  - status
  - created_at
- knowledge_pack_versions
  - id (pk)
  - pack_id (fk)
  - version
  - content_json
  - content_hash
  - status
  - created_by
  - approved_by
  - created_at
  - approved_at

- claim_templates
  - id (pk)
  - template_id (unique)
  - current_version
  - status
  - created_at
- claim_template_versions
  - id (pk)
  - template_id (fk)
  - version
  - content_json
  - content_hash
  - status
  - created_by
  - approved_by
  - created_at
  - approved_at

- knowledge_audit_log
  - id (pk)
  - actor
  - action (create_draft|update_draft|publish|deprecate)
  - object_type (claim|pack|template)
  - object_id
  - object_version
  - diff_json (optional)
  - created_at

Analysis linkage
- analysis_runs should store:
  - knowledge_snapshot_hash (hash of all pack/template versions used)
- outputs should store:
  - conclusions_v1 (JSON) referencing pack_id@version and template_id@version

## Admin UI workflow (PoC)
### Screens
1) SME Claims list
- filter by status/tag
- show linked packs/templates

2) SME Claim editor (low-friction)
- fields: title, conclusion, applicability notes, tags
- actions: Save draft
- CTA: “Add supporting evidence”

3) Evidence Packs list
- filter by status/tag
- show current version + last approved

4) Pack editor (progressive)
- start with: title + short summary + sources (url + citation)
- advanced section (required for publish): scope, strength, excerpts, counterevidence, licensing
- live validation errors
- preview canonical JSON + computed hash
- actions: Save draft, Publish

5) Templates list
- filter by status/tag

6) Template editor
- start with: allowed_conclusion_ro
- advanced (required for publish): slot schema builder + applicability tests DSL + required citations + risk notes
- preview canonical JSON + computed hash
- actions: Save draft, Publish

7) Publish wizard (claim → template)
- takes an SME Claim draft and guides conversion into a constrained template:
  - identify slots
  - define applicability tests
  - link required evidence packs
  - set required citations

### Validation gates (must-have)
- Schema validation (server-side) on every save
- Publish requires:
  - at least 1 source excerpt
  - at least 1 counterevidence excerpt (can be “none found” with justification field)
  - license present for each source
  - allowed_conclusion_ro only uses declared slots

## Constrained LLM integration (B)
### Deterministic pre-filter
- Evaluate applicability_tests against extracted facts (change_list_v1 + mechanisms_v1)
- Only eligible templates are passed to the LLM

### LLM output contract (strict JSON)
- selected_template_id
- selected_template_version
- filled_slots
- citations
  - bill: [{page_number, quote, chunk_id?}]
  - pack: [{pack_id, version, citation, excerpt_location, excerpt_text}]
- confidence

### Post-checks (reject if)
- template not in eligible set
- missing required citations
- slot types invalid
- citations not present in provided context

Caching key
- (document_version_hash, eligible_template_versions_hash, pack_versions_hash)

## Threat model + mitigations (PoC)
- Poisoning: require identity for approver; immutable versions; audit log.
- Bias: mandatory counterevidence section; scope limits; show uncertainty.
- Licensing: require license field; block unknown/forbidden licenses.
- Prompt injection via packs: never feed raw pack text without quoting; treat pack excerpts as data; enforce JSON-only LLM output.

## Next implementation steps (todo)
- Add DB tables for packs/templates + versions + audit log.
- Add FastAPI admin endpoints (CRUD drafts + publish).
- Add server-side schema validation + canonical JSON hashing.
- Add 1 pack + 1 template for drug-penalty escalation.
- Add conclusions_v1 output generation (LLM constrained reasoner) behind a feature flag.
