---
id: 33
title: Extract entity extraction + graph builders
status: archived
priority: medium
created: 2026-03-26 18:33:48.389441+01:00
updated: 2026-03-31 07:52:43.329923+02:00
started: 2026-03-31 07:52:23.751466+02:00
completed: 2026-03-31 07:52:23.751466+02:00
tags:
- phase-1
- scope:knowledge
- type:build
depends_on:
- 32
- 203
claimed_by: auditor
claimed_at: 2026-03-31 07:52:43.328905+02:00
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Replace no-op stubs in packages/knowledge/ with protocol-backed entity extraction and graph building. Uses a pluggable StructuredExtractor protocol so the MCP server or orchestrator can inject the LLM provider.

## Acceptance Criteria

- [ ] protocol.py â€” add StructuredExtractor protocol: @runtime_checkable, single method sync def extract(self, prompt: str) -> ExtractionResult, following the existing EmbeddingProvider / VectorStoreProtocol pattern
- [ ] extractor.py â€” replace no-op stub: EntityExtractor(extractor: StructuredExtractor) constructor; extract(text: str, metadata: dict | None = None) -> ExtractionResult optionally prefixes metadata key-value pairs to the prompt before delegating to the injected extractor; empty/whitespace input returns empty ExtractionResult without calling the extractor
- [ ] graph_builder.py â€” replace no-op stub: IntraDocGraphBuilder(extractor: StructuredExtractor) constructor; uild(entities, scope, document_id) -> GraphBuildResult; <2 entities returns empty result; >80 entities batches by entity_type (one extractor call per type); all inferred edges stamped with weight=0.5 and metadata={source: intra_doc_inference}
- [ ] inter_doc_graph_builder.py â€” separate file (move InterDocGraphBuilder out of graph_builder.py): InterDocGraphBuilder(extractor: StructuredExtractor, vector_store: VectorStoreProtocol, graph_store: GraphStore, top_k: int = 10, cosine_threshold: float = 0.70) constructor; vector pre-filtering via get_embedding + search_similar per entity; cross-doc filter (skip same document_id); dedup existing inter-doc edges via list_edges; batches candidate pairs in groups of 40; all inferred edges stamped with weight=0.4 and metadata={source: inter_doc_inference}
- [ ] Prompt constants (EXTRACTION_PROMPT, GRAPH_BUILDER_PROMPT, INTER_DOC_PROMPT) preserved as module-level string constants matching v1 content
- [ ] Zero PydanticAI imports in any knowledge package module (verified by grep -r pydantic_ai packages/knowledge/)
- [ ] ExtractionResult and GraphBuildResult models preserved: frozen Pydantic BaseModel, same field schema as current v2 stubs
- [ ] All tests from preceding test task #203 pass; ruff clean

## Context

Depends on #32 (vector store, shared protocol.py). Depends on #203 (TDD RED â€” failing tests). Subtask 3/4 of knowledge engine extraction. Downstream: #158 (intake/ingest pipeline) depends on this task's StructuredExtractor protocol.

Research doc: docs/research/extract-entity-extraction-graph-builders.md

### Design decisions
- **StructuredExtractor** (narrow protocol, Option C from research) at .85 confidence â€” matches existing EmbeddingProvider pattern, all 3 modules return ExtractionResult, system prompt is caller-owned
- **intake/ingest split** into #158 per research S4 â€” ingest depends on DocumentStore extensions and #135 (CancelSignal, sandbox_path)

[[2026-03-30]] Mon 08:12

## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| StructuredExtractor protocol in protocol.py | Follows EmbeddingProvider/VectorStoreProtocol pattern. Added @runtime_checkable spec. | Tightened |
| extractor.py EntityExtractor with injected StructuredExtractor | Clarified constructor signature, metadata-prefix behavior, empty-input guard. | Tightened |
| graph_builder.py IntraDocGraphBuilder | Clarified constructor, batch threshold (80), edge stamp (weight=0.5, source=intra_doc_inference). Matches v1 _BATCH_THRESHOLD. | Tightened |
| inter_doc_graph_builder.py separate file | Clarified full constructor (extractor + vector_store + graph_store + top_k + cosine_threshold). Matches v1 DI pattern. | Tightened |
| Prompt constants preserved | Added as explicit AC line. V1 has EXTRACTION_PROMPT, GRAPH_BUILDER_PROMPT, INTER_DOC_PROMPT. | Added |
| Zero PydanticAI imports | Clear, verifiable by grep. | Kept |
| ExtractionResult/GraphBuildResult preserved | Frozen Pydantic, same schema as v2 stubs. Verifiable. | Kept |
| Unit tests (original AC) | REMOVED from impl task. Moved to preceding test task #203 for TDD compliance. | Moved |
| All tests pass; ruff clean | Builder gate condition. | Kept |

### Architecture Notes
Module layering is clean. All modules stay within owlbear_knowledge/ with no upward imports. StructuredExtractor follows the established Protocol pattern (EmbeddingProvider, VectorStoreProtocol) with @runtime_checkable. DI via constructor matches existing codebase convention. InterDocGraphBuilder needs GraphStore (for get_entity/list_edges dedup) and VectorStoreProtocol (for embedding pre-filter) per v1 pattern. System prompts are caller-owned per research recommendation (Option C, .85 confidence). intake/ingest scope correctly split into #158 per research S4.

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handling | User Impact |
|----------|-------------|-----------|----------|-------------|
| EntityExtractor.extract() | LLM call fails | From StructuredExtractor | Catch, return empty ExtractionResult | Silent degradation |
| IntraDocGraphBuilder.build() | Batch LLM call fails | From StructuredExtractor | Catch per-batch, continue | Partial graph edges |
| InterDocGraphBuilder._find_candidate_pairs() | Vector lookup fails | From VectorStoreProtocol | Catch, skip entity | Fewer cross-doc candidates |
| InterDocGraphBuilder.build() | Batch LLM call fails | From StructuredExtractor | Catch per-batch, continue | Partial cross-doc edges |

### Changes Made
- Rewrote AC: 8 precise lines (was 7 with mixed test/impl concerns)
- Added constructor signatures with DI types for all 3 classes
- Added InterDocGraphBuilder full constructor params (vector_store, graph_store, top_k, cosine_threshold)
- Added prompt constants as explicit AC line
- Removed unit test AC (moved to #203)
- Added depends_on #203 (TDD RED pair)
- Created #203 (Test: Entity extraction and graph builders) at backlog

### Dependencies
- Verified: #32 (vector store, todo) provides shared protocol.py types
- Added: #203 (preceding test task, backlog)
- Downstream: #158 depends on #33 (StructuredExtractor protocol)

[[2026-03-30]] Mon 23:25
## Test-Writer Notes
- Pre-existing test task #203 completed the TDD RED phase for this task
- Test files: tests/test_extractor.py, tests/test_graph_builder.py, tests/test_inter_doc_graph_builder.py, tests/test_structured_extractor_protocol.py
- Classes: TestFromAC_EntityExtractor, TestFromAC_IntraDocGraphBuilder, TestFromAC_InterDocGraphBuilder, TestFromAC_StructuredExtractorProtocol
- Total: 52 tests (47 TestFromAC + 5 TestBuilderDiscovered) all PASS (implementation already done in #203 pipeline)
- ruff: clean
- Advancing to in-progress: implementation + tests complete via #203; builder pass-through.

[[2026-03-31]] Tue 03:56
## Builder Notes
- Pass-through: implementation completed in #203 pipeline
- Files: packages/knowledge/src/ (extractor.py, graph_builder.py, inter_doc_graph_builder.py, protocol.py)
- Tests: 52 passed (47 TestFromAC + 5 TestBuilderDiscovered), 0 failures
- Lint: ruff clean
- Evidence: `uv run pytest tests/test_extractor.py tests/test_graph_builder.py tests/test_inter_doc_graph_builder.py tests/test_structured_extractor_protocol.py -q` → 52 passed in 0.63s

[[2026-03-31]] Tue 04:37
## Review Evidence
See docs/scratch/33-reviewer.md for full evidence.

[[2026-03-31]] Tue 05:13
## Test-Writer Notes (retry)
- Retry: reviewer FAIL — 2 MISSING AC rows
- Added: 7 new failing tests (TestFromAC_PromptConstants x3, TestFromAC_InterDocGraphBuilderConstructorParams x4)
- Preserved: 52 existing tests PASS
- ruff clean, committed 86756f5

[[2026-03-31]] Tue 06:08
## Builder Notes (retry)
- Files changed: extractor.py, graph_builder.py, inter_doc_graph_builder.py
- Tests: 59 passed (7 previously failing now pass), 0 failures
- Lint: ruff clean (extracted _collect_candidates helper to fix C901 complexity)
- Coverage: extractor.py 92%, graph_builder.py 100%, inter_doc_graph_builder.py 98%, protocol.py 100%
- Fixes: EXTRACTION_PROMPT, GRAPH_BUILDER_PROMPT, INTER_DOC_PROMPT added; InterDocGraphBuilder.__init__ accepts top_k=10 and cosine_threshold=0.70; filtering applied in _collect_candidates
- Commit: 488963a

[[2026-03-31]] Tue 06:49
## Review Evidence (retry 2)
See docs/scratch/33-reviewer.md for full evidence.

[[2026-03-31]] Tue 07:52
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| StructuredExtractor @runtime_checkable, sync extract | protocol.py L82-99; 8 protocol tests pass | PASS |
| EntityExtractor DI constructor + empty guard + metadata prefix | extractor.py L53-100; 14 tests pass | PASS |
| IntraDocGraphBuilder DI, <2 empty, >80 batch by type, w=0.5/intra_doc_inference | graph_builder.py L72-120; 18 tests pass | PASS |
| InterDocGraphBuilder separate file, full DI (top_k=10, cosine=0.70) | inter_doc_graph_builder.py L80-92; 19 tests pass | PASS |
| Vector prefilter, cross-doc filter, dedup list_edges, batch 40, w=0.4 | inter_doc_graph_builder.py L97-135 | PASS |
| Prompt constants (EXTRACTION, GRAPH_BUILDER, INTER_DOC) | extractor.py L24, graph_builder.py L28, inter_doc L30 | PASS |
| Zero PydanticAI imports | Select-String confirms no matches | PASS |
| ExtractionResult/GraphBuildResult frozen Pydantic | ConfigDict(frozen=True) in both | PASS |
| All tests pass; ruff clean | 59/59 passed; ruff all checks passed | PASS |

### Test Results
- pytest (task scope): 59 passed, 0 failed (0.73s)
- pytest (full suite): 1939 passed, 242 failed (all failures are pre-existing TDD RED from other tasks)
- ruff: All checks passed

### Architect Quality
- AC specificity: 5/5 - precise constructor signatures, thresholds, edge stamps, batching limits, prompt names
- Edge cases covered in AC (empty input, <2 entities, >80 batch threshold)
- Design notes led to clean implementation matching existing protocol patterns

### Deduction breakdown: none - all AC lines verified with evidence, lint clean, reviewer evidence thorough
### Confidence: 1.0
### Action: archived
