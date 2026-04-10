# Data Person — Critic Debate Log

## Cycle 1

**Position:** 6 data quality gaps in priority order: (1) HTML cleaning boundary, (2) content hash on wrong input, (3) entity name canonicalization, (4) extended source attribution, (5) entity model extension, (6) entity/concept drift.

**Critic challenges:**

### Challenge 1: Browser extraction may already return clean text

"You assume browser extraction returns raw HTML, but v1 `ContentExtractor` used JavaScript injection and accessibility tree parsing (`AXNodeInfo`). If the browser toolset already extracts text content, your #1 gap might be solved at the extraction layer."

**Response: Partially accepted.** If the browser extraction step returns pre-cleaned text, the HTML cleaning burden shifts there. But the pipeline itself has no validation gate — the chunker accepts whatever string it's given. A validation boundary at pipeline entry is defense-in-depth regardless of upstream extraction quality. SharePoint pages with embedded PowerBI dashboards, iframes, or complex web parts may produce garbage even from AX tree parsing. Updated position to frame it as "validation boundary" rather than "HTML parser insertion."

### Challenge 2: Aggressive name normalization destroys distinctions

"'Data Classification Framework' (a specific policy document) is different from 'data classification' (a general concept). Aggressive normalization collapses these into the same key."

**Response: Partially accepted.** Canonicalization must be conservative: lowercase + whitespace collapse only. No stemming, no word removal. The `canonical_name` is a derived matching key, not a replacement for the original `name` field. Updated position to emphasize conservative normalization and distinct-from-original semantics.

### Challenge 3: Hashing cleaned content loses raw change detection

"If you hash the cleaned version, you lose the ability to detect when the raw content changed — maybe you want to re-extract if boilerplate changed, in case cleaning heuristics improved."

**Response: Rejected.** The purpose of delta detection is to skip unchanged meaningful content. If a SharePoint nav bar changes but the policy text didn't, re-ingesting wastes LLM tokens and churns entity IDs. If cleaning heuristics improve, that's a pipeline-version event — handle it with a forced re-ingest flag, not by hashing raw content. Optionally store both hashes for audit, but the skip decision must use cleaned content hash.

---

## Cycle 2

**Updated position:** Same 6 gaps with nuance — (1) cleaning as validation boundary even if browser pre-cleans; (2) hash cleaned content, optionally store raw hash for audit; (3) conservative canonicalization only.

**Critic challenges:**

### Challenge 4: Entity drift (#6) is the same problem as canonicalization (#3)

"If you solve canonicalization, drift is handled. Listing them separately inflates your gap count."

**Response: Rejected.** They're related but distinct. Canonicalization prevents name-variant duplicates ("Data Classification" vs "data classification"). Drift is temporal — the same concept evolving across source versions. "Data classification requirements v1.2" (2024 policy) vs the updated 2025 edition. Canonicalization handles naming; drift handling requires temporal awareness and version tracking. Different solutions.

### Challenge 5: SUPERSEDES_VERSION becomes viable with content_last_modified

"If you're already adding `content_last_modified` metadata in gap #4, SUPERSEDES_VERSION can use it for ordering."

**Response: Accepted.** `content_last_modified` provides the temporal ordering. However, the document_id changes on every re-ingest (new UUID per `ingest()` call). Version chains require stable source identity across refreshes. This is a prerequisite dependency — noted in final position. SUPERSEDES_VERSION is still parked until source identity is solved.

### Challenge 6: Silent extraction failure is a real and unaddressed gap

"The LLMExtractor has `except Exception: return ExtractionResult()`. If the prompt doesn't match corporate content, every chunk silently produces zero entities. The pipeline reports status='ok' with entity_count=0 and nobody notices."

**Response: Accepted.** Promoted to a new gap (#6 — extraction quality monitoring). The "empty result on failure" catch-all is the knowledge-graph equivalent of NaN propagation. The pipeline reports success while producing nothing useful. This is particularly dangerous because it's invisible — no error, no warning, just an empty graph.

---

## Cycle 3

**Updated position:** 6 gaps, reordered with extraction quality monitoring replacing entity drift (drift folded into canonicalization as a temporal dimension).

**Critic response:** "Position is solid. The 6 gaps are well-identified and the prioritization makes sense. The nuances from previous challenges have been properly integrated. One minor observation: the Entity model's `metadata` dict is already the right extension point for source attribution — no schema migration needed, just metadata population at intake time."

**Accepted as addendum.** Noted in final position.

---

## Final Assessment

- **Cycles completed:** 3
- **Challenges accepted:** 3 (browser pre-cleaning nuance, conservative canonicalization, extraction monitoring as new gap, SUPERSEDES_VERSION dependency)
- **Challenges rejected:** 2 (hash raw content, drift = canonicalization)
- **Key refinements:** Gap #1 reframed as validation boundary rather than HTML parser. Gap #3 narrowed to conservative normalization. Gap #6 replaced entity drift with extraction quality monitoring (more actionable, drift partially addressed by canonicalization).
- **Position stability:** Core gaps unchanged across all cycles. Prioritization unchanged. Nuance added to implementation guidance.
