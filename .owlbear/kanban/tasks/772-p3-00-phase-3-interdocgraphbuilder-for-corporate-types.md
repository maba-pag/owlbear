---
id: 772
title: 'P3-00: Phase 3 — InterDocGraphBuilder for corporate types'
status: in-progress
priority: nice-to-have
created: '2026-04-10T10:56:34.377861+00:00'
updated: '2026-04-13T20:52:19.504575+00:00'
tags:
- phase-3
- scope:knowledge
- deferred
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Placeholder — needs decomposition when Phase 1 is complete.

InterDocGraphBuilder extension for corporate entity types (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD). Cross-source edge creation when entities from different sources reference the same concept.

Depends on Phase 1 entity model being proven via real ingestion.

Parent: #751

[[2026-04-13]]
## Research
- Research doc: .owlbear/research/772-interdocgraphbuilder-corporate-types.md
- Sources: 6 studied, 4 high-relevance (all codebase + brief voices)
- Recommendation: Approach B — prompt fix + source-aware filtering + pipeline wiring. Defer canonicalization until real data. (confidence: .78)
- Follow-up tasks created: #862 (P3-01: prompt integration), #863 (P3-02: source-aware filtering), #864 (P3-03: pipeline wiring), #865 (P3-04: canonicalization, deferred)
- Decision requests: none — T1 autonomous (incremental extensions to existing builder)
- Challenge: FALLBACK — challenger subagent not available

### Key Findings
1. InterDocGraphBuilder already handles all entity types generically — corporate types work without code changes
2. INTER_DOC_PROMPT is dead code (defined line 31, never used) — builder delegates to shared LLMExtractor
3. _build_inter_prompt() sends only entity names, not types/descriptions — LLM lacks context for GOVERNS/SUPERSEDES_VERSION inference
4. No source-level awareness — filters by document_id only; brief Outcome 4 requires cross-source linking
5. Builder not wired into refresh/ingest pipeline — standalone class with no call site
6. All follow-ups tagged `deferred` — dependency gate: Phase 1 entity model must be proven via real corporate ingestion first
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tracking epic for Phase 3 InterDocGraphBuilder. Children #862-#865 carry single-responsibility implementation. |
| Interface clarity | PASS | Parent defines the feature scope. Children have concrete AC with affected files identified. |
| Dependency correctness | PASS/FLAG | Parent has no deps (correct). **#864 body says "Depends on P3-01 and P3-02" but `depends_on` is empty** — must be set to `[862, 863]` before #864 leaves research. |
| Module layering | PASS | All changes scoped to `owlbear_knowledge.inter_doc_graph_builder` and its callers in `refresh.py`/`ingest.py`. No cross-package violations. |
| TDD compliance | PASS | Children will go through RED/GREEN phases when promoted from research. |
| KISS/YAGNI | PASS | Phased delivery + deferred gate prevents over-investment. #865 (canonicalization) correctly deferred to `someday` priority with "until real data shows drift" gate. |
| Premise challenge | PASS | Verified: `INTER_DOC_PROMPT` is dead code, `_build_inter_prompt()` sends only names (no types/descriptions), `_collect_candidates()` filters by document_id not source_id, builder has no call site. All 4 gaps are real and code-verified. |
| Pattern consistency | PASS | Children follow existing DI patterns (StructuredExtractor, VectorStoreProtocol, GraphStore). #864 config toggle follows existing pattern (default: disabled). |
| Security surface | PASS | No new system boundaries. LLM prompt changes are internal; no user-facing input surfaces added. |
| Single domain | PASS | All children scoped to `scope:knowledge` domain. #864 touches refresh pipeline wiring but within same package. |

### Codebase Evidence

- `INTER_DOC_PROMPT`: `inter_doc_graph_builder.py:31-52` — defined with `{relation_types}` placeholder, never imported or called
- `_build_inter_prompt()`: `inter_doc_graph_builder.py:59-61` — `f"({a.name}, {b.name})"`, no types/descriptions
- `_collect_candidates()`: `inter_doc_graph_builder.py:99-120` — `entity.document_id == other.document_id` filter only, no `source_id`
- No call site: grep for `InterDocGraphBuilder` usage outside of graph_builder.py (legacy stub) and its own module — no call in refresh.py or ingest.py
- Entity model: `models.py` has `Entity.document_id` field; `source_id` FK added by Phase 1 schema v9 to documents table

### Children AC Assessment

| Task | AC Quality | Flags |
|------|-----------|-------|
| #862 (P3-01: prompt) | Concrete: INTER_DOC_PROMPT usage, type+description in prompt, corporate relationship guidance, test preservation | Clean |
| #863 (P3-02: source-aware) | Concrete: source_id join, cross-source priority, source_pair metadata, tests | Clean |
| #864 (P3-03: pipeline wiring) | Concrete: trigger point, async, skip logic, config toggle, integration test | **Missing `depends_on: [862, 863]`** |
| #865 (P3-04: canonicalization) | Concrete: canonical_name derivation rules, conservative normalization with distinctness example | Clean, correctly `someday` priority |

### Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge; high confidence based on codebase evidence verification

### Action Items
1. **#864 dependency fix**: `depends_on` must be set to `[862, 863]` — orchestrator or next agent touching #864 should fix this
2. **Pass-through tag**: `quality` added — #772 is a non-implementation tracking epic

### Verdict: APPROVE
### Action Taken: Advanced #772 to todo as tracking epic. Flagged #864 dependency gap (needs depends_on: [862, 863]).
[[2026-04-13]]
## Test-Writer Notes
- Non-implementation task (tracking epic / placeholder) — no tests applicable.
- Task body is a research summary + architecture review with no concrete AC or testable Python interfaces.
- Architecture review (also in body) confirms: "#772 is a non-implementation tracking epic."
- All testable implementation is carried by children #862 (P3-01: prompt), #863 (P3-02: source-aware filtering), #864 (P3-03: pipeline wiring), #865 (P3-04: canonicalization).
- Passing through to builder.