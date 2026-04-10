# Data Person — Authenticated Content Pipeline

## Data Quality Stance

The pipeline has **six data quality gaps**, three critical and three moderate, that must be resolved before corporate content can produce trustworthy knowledge graph entities. The core issue is that the pipeline was built for code-centric markdown/text files and has no validation boundary between raw web content and the chunker. Everything downstream — entity extraction, embedding, graph building, delta detection — inherits the corruption introduced at intake.

**Priority order: (1) HTML cleaning boundary, (2) content hash on wrong input, (3) entity name canonicalization, (4) source attribution, (5) entity model + prompt extension, (6) extraction quality monitoring.**

## Schema and Validation Reasoning

### Gap 1 (Critical): No HTML-to-Text Cleaning Boundary

`read_url()` returns raw `response.text`. The `TextChunker` uses markdown separators (`\n## `, `\n### `, `\n\n`, `\n`, ` `). Feeding HTML into a markdown chunker will:

- Create chunks that split mid-tag
- Include SharePoint nav bars, footers, breadcrumbs, and chrome as "content"
- Cause entity extraction to produce noise entities ("Navigation", "Home", "Settings")
- Make content hashes unstable — dynamic SharePoint boilerplate changes on every render

Even if the v1 BrowserToolset's `read_text` tool returns pre-cleaned text via accessibility tree parsing, the pipeline itself has no validation gate. The chunker should **never** receive HTML. Defense-in-depth requires a cleaning/validation step at pipeline entry.

**Prescription:** Insert a content normalizer between intake and chunking. Strip `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`. Extract main content area. Convert structural headings to markdown (`h1`→`# `, `h2`→`## `). Output clean text that the existing `TextChunker` separator hierarchy can handle. This is a validation boundary — enforce it with a contract check (reject content containing `<script>` or `<style>` tags after cleaning).

### Gap 2 (Critical): Content Hash Computed on Raw Input

`compute_content_hash()` hashes `content.strip()` — the raw intake content. For browser-extracted HTML:

- Dynamic page elements (timestamps, session avatars, "last modified" footers) change the hash every render
- Every refresh cycle re-ingests unchanged content → old document cascade-deleted → new entities created → InterDocGraphBuilder loses cross-document edges because entity IDs changed
- Re-ingestion churn wastes LLM tokens on unchanged corporate pages

**Prescription:** Hash the **cleaned** text, not the raw intake content. If meaningful content didn't change, skip re-ingestion. Optionally store a raw content hash for audit purposes, but the skip decision must use the cleaned hash. This means the cleaning step must run BEFORE `check_content_changed()` in `ingest()`.

### Gap 3 (High): Entity Name Canonicalization Missing

`InterDocGraphBuilder` uses embedding cosine similarity (threshold 0.70) to find cross-document entity pairs. No name normalization exists:

- "Data Classification" (SharePoint) and "data classification" (Confluence) become separate entities with separate embeddings
- Cosine similarity might catch them, but there's no guarantee — it depends on embedding model and context
- Even when detected as candidates, LLM inference creates a RELATED_TO edge rather than merging them
- Result: duplicate entity nodes accumulate over time, graph quality degrades

**Prescription:** Add a `canonical_name` derived field: lowercase, collapse whitespace, strip leading/trailing articles and punctuation. Use canonical_name for pre-filtering candidates in `InterDocGraphBuilder._collect_candidates()` alongside vector similarity. Do NOT use aggressive stemming or word removal — "Data Classification Framework" (a policy document) must remain distinct from "data classification" (a concept). Conservative normalization only.

### Gap 4 (High): Minimal Source Attribution

`IntakeResult.metadata` carries only `source_type` and `fetched_at`. For corporate content provenance, agents need:

- `source_system`: "sharepoint" | "confluence" | "github" | "web"
- `page_url`: canonical URL (distinct from `IntakeResult.source` which may vary by session)
- `site_name`: SharePoint site or Confluence space identifier
- `content_last_modified`: extracted from page content if available (no HTTP headers for browser extraction)
- `parent_page_url`: for hierarchy tracking

The `Entity.metadata` dict and `Document.metadata` dict already exist and accept arbitrary keys — no schema migration needed. The metadata just needs to be populated at intake and flowed through.

### Gap 5 (Medium): Entity Model and Prompt Extension

`EntityType` is code-centric: FILE, FUNCTION, CLASS_, DECISION, PATTERN, CONCEPT. Corporate content needs: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD.

`LLM_EXTRACTION_PROMPT` dynamically includes enum values — adding new types to the enum will automatically appear in the prompt. But the prompt's **guidance text** says "files, functions, classes, decisions, patterns, and concepts." Without corporate-type examples and guidance, the LLM will classify everything as CONCEPT (the catch-all).

**Prescription:** Add the 5 new EntityType values. Update `LLM_EXTRACTION_PROMPT` guidance to include corporate examples: "requirements (mandated constraints), solutions (implementation approaches), procedures (step-by-step processes), policies (organizational rules), standards (normative references)." Add SUPERSEDES_VERSION to RelationType but park its implementation until source identity across refreshes is solved (document_id changes on re-ingest today).

### Gap 6 (Medium): Silent Extraction Failure — No Quality Monitoring

`LLMExtractor.extract()` catches all exceptions and returns `ExtractionResult()` — zero entities, zero edges, no error signal. If the prompt doesn't match corporate content structure, every chunk silently produces nothing. The pipeline reports `status="ok"` with `entity_count=0`, and nobody notices.

**Prescription:** Log at WARNING level when a non-trivial prompt produces zero entities. Track entity-per-chunk yield rates. Alert when a document with significant chunk count produces zero or near-zero entities — this indicates the extraction prompt doesn't match the content type. This is the "NaN propagation" analog for knowledge graphs: empty extraction results propagate silently through the pipeline.

## Key Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| Clean before hash | Stable delta detection, no churn | Raw content changes invisible to skip logic |
| Conservative name canonicalization | Catches case/whitespace variants | Won't catch synonym-level drift ("infosec" vs "information security") |
| Validation gate at chunker entry | Prevents garbage-in-garbage-out | Additional processing step, needs maintenance per source type |
| Rich metadata on IntakeResult | Full provenance chain for agents | Browser extraction must parse/extract metadata from page DOM |
| Extraction quality monitoring | Catches silent failures | Adds logging/alerting infrastructure |

## Warnings

1. **Re-ingest churn will corrupt the graph if hash-on-raw isn't fixed.** Every weekly refresh will cascade-delete and rebuild all SharePoint content. InterDocGraphBuilder edges will be destroyed and recreated with new entity IDs. Cross-source links are ephemeral under this regime.

2. **The `ingest()` path doesn't call `delete_document_data()` before re-ingesting.** When `check_content_changed()` returns `(True, existing_document_id)`, the pipeline creates a NEW document with a new ID. The old document's entities and edges become orphans. Either cascade-delete the old document first, or implement an update-in-place strategy.

3. **CONCEPT is going to be the junk drawer.** Without specific prompt guidance for corporate types, extractors will dump everything into CONCEPT. Monitor CONCEPT entity counts — if they dominate, the prompt needs work.

4. **InterDocGraphBuilder.build() fetches ALL existing edges for deduplication.** At corporate scale (thousands of documents, tens of thousands of edges), `self._graph_store.list_edges()` becomes a bottleneck. Needs pagination or set-based lookup.

5. **Entity metadata carries `pipeline_name` but not `source_system`.** Store_extractions stamps `pipeline_name` into entity metadata, but the source system identity (SharePoint vs Confluence) doesn't reach the entity. It's in Document.metadata but not propagated to Entity.metadata. Agents querying entities won't know the source system without joining back to the document.

## Confidence

0.85 — High confidence in the gap identification and prioritization. The HTML cleaning boundary and hash-on-cleaned-content are clear correctness issues. Entity canonicalization direction is sound but the specific threshold/algorithm needs empirical tuning on actual corporate content. The extraction monitoring gap is real but the severity depends on how well the LLM adapts to corporate content with just enum additions.
