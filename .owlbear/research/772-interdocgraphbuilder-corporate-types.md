# InterDocGraphBuilder for Corporate Types — Phase 3 Research

> **Owning task:** #772 — P3-00: Phase 3 — InterDocGraphBuilder for corporate types
> **Date:** 2026-04-13 **Status:** Complete

## 1. Context and Question

Task #772 is a Phase 3 placeholder under the Authenticated Content Pipeline (#751). The brief's Outcome 4 states: "Cross-source concepts are linked in the knowledge graph. The entity extraction pipeline recognizes corporate knowledge types and creates cross-source edges when entities from different sources refer to the same concept."

**Research question:** What concrete work does Phase 3 require, given that InterDocGraphBuilder and corporate entity types already exist?

## 2. Sources Studied

| Source | Relevance | What |
|--------|-----------|------|
| `inter_doc_graph_builder.py` (codebase) | .95 | Current DI-based builder: embedding pre-filter, batch LLM, edge stamping |
| `models.py` (codebase) | .90 | EntityType/RelationType enums — corporate types already present |
| `llm_extractor.py` (codebase) | .90 | LLM_EXTRACTION_PROMPT — corporate guidance exists, dynamic enum join |
| Brief: data-person voice | .85 | Gaps 3-4: canonicalization, list_edges() scale, re-ingest churn |
| Prior research #256 | .80 | Original InterDocGraphBuilder design: embedding pre-filter approach |
| Brief context.md Outcome 4 | .85 | Success criterion: SharePoint→Confluence concept linking |

## 3. Analysis

### 3.1 What's Already Done (Phase 1 deliverables in #751)

- Corporate EntityType values: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
- Corporate RelationType values: GOVERNS, SUPERSEDES_VERSION
- LLM_EXTRACTION_PROMPT with corporate-type-specific guidance
- InterDocGraphBuilder with DI pattern, embedding pre-filter, batch LLM
- Schema v9: source_pages + source_id FK on documents

### 3.2 Gap Analysis — What Phase 3 Actually Needs

| # | Gap | Severity | Evidence |
|---|-----|----------|----------|
| G1 | `INTER_DOC_PROMPT` is dead code — defined but never used | High | Only reference is line 31 definition; no `.format()` call |
| G2 | `_build_inter_prompt` sends names only, not types/descriptions | High | Line 60: `f"({a.name}, {b.name})"` — LLM lacks context for GOVERNS/SUPERSEDES_VERSION |
| G3 | No source-level awareness in candidate filtering | Medium | Filters by `document_id` only; brief's Outcome 4 requires cross-*source* linking |
| G4 | No entity name canonicalization | Medium | Data-person Gap 3: "Data Classification" vs "data classification" |
| G5 | `list_edges()` fetches ALL edges for dedup | Low | Data-person Gap 4: O(N) memory at corporate scale |
| G6 | Builder not wired into refresh/ingest pipeline | Medium | Standalone class; no call site in refresh.py or ingest.py |
| G7 | No corporate-type-specific relationship guidance in inter-doc prompt | High | Extraction prompt has corporate guidance; inter-doc prompt does not |

### 3.3 Approach Comparison

| Criterion | A: Prompt-only fix (.65) | B: Prompt + source-aware filter (.80) | C: Full extension with canonicalization (.85) |
|-----------|--------------------------|----------------------------------------|-----------------------------------------------|
| Fixes G1-G2 (prompt gaps) | Yes | Yes | Yes |
| Fixes G3 (source awareness) | No | Yes — add source_id join | Yes |
| Fixes G4 (canonicalization) | No | No | Yes — canonical_name field |
| Fixes G5 (scale) | No | Partial — targeted queries | Yes — set-based lookup |
| Fixes G6 (pipeline wiring) | No | Yes | Yes |
| Fixes G7 (corporate guidance) | Yes | Yes | Yes |
| LOC estimate | ~30 | ~80 | ~150 |
| KISS | High | Medium | Medium |
| YAGNI risk | Low | Low | Low — all gaps identified by brief voices |

### 3.4 Dependency Gate

The task body states: "Depends on Phase 1 entity model being proven via real ingestion."

**Current state:** Entity model is code-complete (#751). But real corporate content ingestion has NOT occurred — Phase 0 CDP spike (#753) is blocked on user action; Phase 1 browser tasks (#787, #788) are in review but blocked. Until corporate content flows through the pipeline, the entity model is untested on real data.

**Implication:** Follow-up implementation tasks should remain at `research` status with the `deferred` tag until Phase 1 ingestion produces real corporate entities.

## 4. Recommendation (confidence: .78)

**Approach B: Prompt fix + source-aware filtering + pipeline wiring.** Defer canonicalization (Approach C) until real data shows entity name drift is a problem.

Rationale:
- G1/G2/G7 are correctness issues — the builder's LLM prompt is non-functional for corporate types today
- G3 directly addresses Outcome 4's cross-*source* requirement
- G6 is required for the builder to actually run
- G4/G5 are optimization — YAGNI until proven on real corporate corpus

**Risk:** Without canonicalization, "Data Classification Framework" (policy) and "data classification" (concept) may not link. Mitigation: embedding similarity at 0.70 threshold should catch high-similarity variants; monitor after first ingestion.

Challenge: FALLBACK — challenger subagent not available in agent list.

## 5. Follow-up Tasks

1. Fix inter-doc prompt integration — activate INTER_DOC_PROMPT with corporate guidance, include entity types/descriptions in user prompt (G1, G2, G7)
2. Source-aware candidate filtering — join to document.source_id, prioritize cross-source pairs (G3)
3. Wire InterDocGraphBuilder into refresh pipeline — trigger after intra-doc build per new document (G6)
4. Entity name canonicalization — canonical_name field, pre-filter alongside vector similarity (G4, deferred)
