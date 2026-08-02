---
id: 676
title: Wire StructuredExtractor to activate knowledge graph layer
status: archived
priority: medium
created: 2026-04-08T18:26:20.7985508+02:00
updated: 2026-04-09T05:11:05.9146714+02:00
started: 2026-04-09T05:11:05.9146714+02:00
completed: 2026-04-09T05:11:05.9146714+02:00
tags:
    - scope:knowledge
    - ' type:feature'
    - ' source:analysis'
class: standard
---

## Context

Analysis confirmed that the knowledge graph layer is a no-op in production. The MCP knowledge server creates `EntityExtractor(model)` with a model name, but `EntityExtractor` requires an injected `StructuredExtractor` via the `extractor=` keyword argument to actually produce entities and edges. Without it:

- `EntityExtractor.extract()` returns empty `ExtractionResult`
- Zero entities/edges are ever stored in the graph
- Graph-augmented retrieval degrades to pure vector search
- ColBERT vectors are computed by BGE-M3 but never stored in Qdrant

The `StructuredExtractor` protocol (`serve/knowledge/src/owlbear_knowledge/protocol.py`) requires an async callable that produces structured JSON from prompts. The `OWLBEAR_MODEL` env var is already read and passed to `EntityExtractor` — it just needs to be used to construct a real extractor.

## Acceptance Criteria

- [ ] AC1: Implement a concrete `StructuredExtractor` that uses the model specified by `OWLBEAR_MODEL`
- [ ] AC2: Wire the extractor into `EntityExtractor(extractor=...)` in `app_lifespan()` of `mcp-knowledge/server.py`
- [ ] AC3: Ingest a test document and verify entities and edges appear in `get_stats` output
- [ ] AC4: Verify `search_knowledge` returns graph expansion context (not just vector chunks)
- [ ] AC5: Graceful degradation — if the LLM call fails, ingestion still succeeds (vector-only fallback)
- [ ] AC6: The `StructuredExtractor` implementation lives in the knowledge engine package, not the MCP server

Needs decomposition: This may need a sub-task for the `StructuredExtractor` implementation and a separate sub-task for wiring + integration testing.

[[2026-04-08]] Wed 21:06
## Research
- Research doc: .owlbear/research/wire-structuredextractor-knowledge-graph.md
- Sources: 7 studied, 4 high-relevance (codebase: protocol.py, extractor.py, server.py, v1 extractor)
- Recommendation: Make protocol async + PydanticAI adapter in knowledge engine (confidence: 0.82)
- Key finding: StructuredExtractor protocol is sync but LLM calls are async — PydanticAI's run_sync() fails inside running event loop. Protocol must become async.
- Secondary finding: SourceEvaluator has same wiring gap (model string where callable expected)
- Follow-up tasks created: #687 (async protocol), #689 (LLMExtractor impl), #690 (MCP wiring), #688 (SourceEvaluator fix)
- Decision requests: none — T1 autonomous (implements existing AC with proven v1 pattern)
- Challenge: FALLBACK — challenger agent not available

[[2026-04-08]] Wed 21:37
## Planning

Decomposition delegated to planner. Parent task #676 decomposes into 6 subtasks in 3 TDD layers.

### Task Dependency Graph

| Seq | ID | Title | Domain | Depends On |
|-----|------|-------|--------|------------|
| 1 | #697 | Tests: async StructuredExtractor protocol | knowledge | — |
| 2 | #687 | Make StructuredExtractor protocol async | knowledge | #697 |
| 3 | #698 | Tests: LLMExtractor implementation | knowledge | #687 |
| 4 | #689 | Implement LLMExtractor using PydanticAI | knowledge | #698, #687 |
| 5 | #699 | Tests: MCP knowledge graph wiring and integration | mcp-knowledge | #689 |
| 6 | #690 | Wire LLMExtractor into MCP knowledge server | mcp-knowledge | #699, #689 |

### New Tasks Created
- #697 — TDD RED for #687 (parent: 676, tags: scope:knowledge, type:test)
- #698 — TDD RED for #689 (parent: 676, depends_on: #687, tags: scope:knowledge, type:test)
- #699 — TDD RED for #690 (parent: 676, depends_on: #689, tags: scope:mcp-knowledge, type:test)

### Corrections Required for Existing Tasks

The researcher-created tasks need the following fixes (no edit_task tool available — next architect pass or orchestrator must apply):

**#687:** Set `parent=676`. Change `depends_on` from `[676]` to `[697]`. Remove AC3 (test updates moved to #697).

**#689:** Set `parent=676`. Change `depends_on` from `[676]` to `[698, 687]`. Remove AC6 (tests moved to #698).

**#690:** Set `parent=676`. Change `depends_on` from `[676]` to `[699, 689]`. Change tag from `scope:knowledge` to `scope:mcp-knowledge`. Remove test-related AC items (integration tests moved to #699).

### Excluded
#688 (SourceEvaluator wiring fix) — independent concern, not part of #676's AC, already claimed separately.

### AC Coverage
| #676 AC | Covered By |
|---------|-----------|
| AC1: Implement concrete StructuredExtractor | #689 |
| AC2: Wire into EntityExtractor | #690 |
| AC3: Verify entities/edges in get_stats | #699 + #690 |
| AC4: Verify graph expansion context | #699 + #690 |
| AC5: Graceful degradation | #689 (AC5) + #690 (AC5) |
| AC6: Lives in knowledge engine package | #689 (AC1) |

[[2026-04-08]] Wed 22:44
## Test-Writer Notes
- Non-impl pass-through: parent tracking task — all AC fully decomposed into subtasks.
- AC coverage delegated to: #697 (async protocol tests), #698 (LLMExtractor tests), #699 (MCP wiring/integration tests).
- No testable Python interfaces exist directly on #676 — implementation lives in subtasks #687, #689, #690.
- Passing through to builder (orchestrator will drive subtask sequence).

[[2026-04-08]] Wed 23:11
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-09]] Thu 00:08
## Review Evidence

### Scope
Parent tracking container. No code or test changes — deliverable is the decomposition plan itself.

### Subtask Status at Review Time
| ID | Title | Status | Metadata Issues |
|----|-------|--------|----------------|
| #697 | Tests: async StructuredExtractor protocol | in-progress (2nd cycle) | depends_on: [] ✓, parent: 676 ✓ |
| #687 | Make StructuredExtractor protocol async | research | depends_on: [676] ✗ (should be [697]), parent: null ✗ |
| #698 | Tests: LLMExtractor implementation | backlog | depends_on: [687] ✓, parent: 676 ✓ |
| #689 | Implement LLMExtractor using PydanticAI | research | depends_on: [676] ✗ (should be [698,687]), parent: null ✗ |
| #699 | Tests: MCP wiring and integration | backlog | depends_on: [689] ✓, parent: 676 ✓ |
| #690 | Wire LLMExtractor into MCP server | research | depends_on: [676] ✗ (should be [699,689]), parent: null ✗ |

### AC Coverage Map
| #676 AC | Covered By | Status |
|---------|-----------|--------|
| AC1: Implement concrete StructuredExtractor | #689 | COVERED |
| AC2: Wire into EntityExtractor | #690 | COVERED |
| AC3: Verify entities/edges in get_stats | #699 + #690 | COVERED |
| AC4: Verify graph expansion context | #699 + #690 | COVERED |
| AC5: Graceful degradation | #689 (AC5) + #690 (AC5) | COVERED |
| AC6: Lives in knowledge engine package | #689 (AC1) | COVERED |

### Critical Gap — graph_builder.py / inter_doc_graph_builder.py Async Migration Not Covered

The architect approved #697 with an explicit note: "graph_builder.py (lines 122, 130) and inter_doc_graph_builder.py (line 154) also call `self._extractor.extract(prompt)` without await, and their tests use `MagicMock(spec=StructuredExtractor)`." The architect ruled it belongs to #676's decomposition planning.

**The decomposition was never updated to include this task.**

Impact: When #687 changes `EntityExtractor.extract()` to `await self._extractor.extract(prompt)`, the signature change also affects `graph_builder.py` and `inter_doc_graph_builder.py`. Their existing tests will fail with `TypeError: object MagicMock can't be used in 'await' expression` — test regressions not attributable to any planned task. The decomposition is structurally incomplete.

### Task Metadata Defects (#687, #689, #690)

Researcher-created tasks have `depends_on: [676]` (the parent). Planner documented the required corrections but was unable to apply them (no edit_task at planning time). These corrections have not been applied. As a result, the dependency gate system will not enforce correct task ordering for these three tasks — they will show as dispatchable before their TDD predecessors (#697, #698, #699) are complete.

### Deductions
- −0.15 Graph builder/inter-doc callsite async migration missing from decomposition (explicit architectural gap, architect delegated back to #676's plan, plan never updated)
- −0.05 #687, #689, #690 metadata incorrect (depends_on points to parent not TDD predecessors)

### Verdict
Confidence: **0.80** → **FAIL → backlog**

### Required Actions (Architect/Planner)
1. **Add missing subtask**: Create a TDD pair for graph builder async migration — `graph_builder.py` lines 122/130 and `inter_doc_graph_builder.py` line 154 need `await` on `self._extractor.extract()`, and their test files need `MagicMock` → `AsyncMock` migration. Parent: #676. Depends on #687. Sequence: insert between #687 (seq 2) and #698 (seq 3).
2. **Fix task metadata**: Update `depends_on` for #687 → [697], #689 → [698, 687], #690 → [699, 689]. Set `parent=676` for #687, #689, #690.

[[2026-04-09]] Thu 00:58
## Architecture Review

### Context
Parent tracking container returned to backlog by reviewer (confidence 0.80). Two defects identified: (1) missing graph builder async migration subtask, (2) metadata defects on #687, #689, #690.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent container — delegates all AC to subtasks |
| Interface clarity | PASS | All 6 AC lines mapped to specific subtasks |
| Dependency correctness | PASS (after fix) | Created #704, #705 to close graph builder gap |
| Module layering | PASS | knowledge domain internal; MCP wiring in mcp-knowledge |
| TDD compliance | PASS | Every GREEN task has a RED predecessor |
| KISS/YAGNI | PASS | Minimal scope — 3 sync→async + 1 new class + 1 wiring change |
| Premise challenge | PASS | Knowledge graph is confirmed no-op without this work |
| Pattern consistency | PASS | Follows existing DI patterns in graph builders |
| Security surface | PASS | LLM calls are internal; no new user-facing input surfaces |
| Single domain | PASS | knowledge + mcp-knowledge (MCP wiring is ancillary) |

### Decomposition Gap Fix
Created two new subtasks to address reviewer-identified gap:
- **#704** — TDD RED: Tests for graph builder and inter-doc builder async extractor migration (parent: 676, depends_on: [687])
- **#705** — GREEN: Update graph builders to await async StructuredExtractor.extract() (parent: 676, depends_on: [704, 687])

### Updated Task Dependency Graph
| Seq | ID | Title | Depends On |
|-----|------|-------|------------|
| 1 | #697 | Tests: async StructuredExtractor protocol | — |
| 2 | #687 | Make StructuredExtractor protocol async | #697 |
| 3a | #704 | Tests: graph builder async extractor migration | #687 |
| 3b | #698 | Tests: LLMExtractor implementation | #687 |
| 4a | #705 | Update graph builders to await async extract() | #704, #687 |
| 4b | #689 | Implement LLMExtractor using PydanticAI | #698, #687 |
| 5 | #699 | Tests: MCP knowledge graph wiring and integration | #689 |
| 6 | #690 | Wire LLMExtractor into MCP knowledge server | #699, #689 |

### AC Coverage (complete)
| #676 AC | Covered By |
|---------|-----------|
| AC1: Implement concrete StructuredExtractor | #689 |
| AC2: Wire into EntityExtractor | #690 |
| AC3: Verify entities/edges in get_stats | #699 + #690 |
| AC4: Verify graph expansion context | #699 + #690 |
| AC5: Graceful degradation | #689 + #690 |
| AC6: Lives in knowledge engine package | #689 |
| (Implicit) Graph builders use async extract | #704 + #705 |

### Orchestrator Prerequisites
⚠️ CRITICAL — fix metadata before dispatching these subtasks:
- **#687**: set `parent=676`, change `depends_on` from `[676]` to `[697]`
- **#689**: set `parent=676`, change `depends_on` from `[676]` to `[698,687]`
- **#690**: set `parent=676`, change `depends_on` from `[676]` to `[699,689]`, change tag from `scope:knowledge` to `scope:mcp-knowledge`

### Challenge Results
- Challenger: RECONSIDER (confidence 0.78) — flagged metadata defects as broken dependency gate risk
- Architect response: ACCEPTED concern, mitigated by documenting orchestrator prerequisites prominently. Metadata defects are localized and researchable tasks (#687, #689, #690) are not yet dispatchable (status: archived). Buffer exists for orchestrator to apply corrections.

### Verdict: APPROVE
### Action Taken: Created #704 and #705 to close decomposition gap. Documented metadata corrections as orchestrator prerequisites. Advanced to todo.

[[2026-04-09]] Thu 02:25
## Test-Writer Notes
- Retry cycle: reviewer FAILed for missing decomposition (graph builder async migration) and metadata defects — NOT for missing tests.
- Architect resolved both issues: created #704 (tests) and #705 (GREEN) for graph builder async migration; documented metadata corrections for #687, #689, #690 as orchestrator prerequisites.
- No new tests required on this parent tracking container — no testable Python interfaces exist at the #676 level.
- Passing through to builder.

[[2026-04-09]] Thu 03:26
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
- Retry cycle: architect resolved both reviewer defects — created #704 (tests) and #705 (GREEN) for graph builder async migration; documented metadata corrections for #687, #689, #690 as orchestrator prerequisites.
- No testable Python interfaces at the #676 level.

[[2026-04-09]] Thu 04:23
## Review Evidence

### Scope
Parent tracking container — no code changes. Second review cycle. Verifying that architecture review resolved both defects identified in cycle 1.

### Cycle 1 Defects — Resolution Status

| Defect | 1st Review Finding | Resolution | Status |
|--------|--------------------|------------|--------|
| Missing graph builder async migration subtask | −0.15 — graph_builder.py:122/130 and inter_doc_graph_builder.py:154 call `extract()` without `await`; decomposition plan had no task to fix them | Architect created #704 (TDD RED) and #705 (GREEN), both with correct metadata: `parent=676`, `depends_on` pointing to TDD predecessors | RESOLVED |
| Metadata defects on #687, #689, #690 | −0.05 — `depends_on: [676]` (parent, not TDD predecessor); `parent: null` | Architect documented as CRITICAL orchestrator prerequisite but did NOT apply fixes | OPEN (MITIGATED) |

### Subtask Metadata Audit — Current State

| ID | Title | Status | parent | depends_on | Required | Correct? |
|----|-------|--------|--------|------------|----------|----------|
| #697 | Tests: async StructuredExtractor protocol | in-progress | 676 | [] | [] | ✓ |
| #704 | Tests: graph builder async migration | backlog | 676 | [687] | [687] | ✓ |
| #698 | Tests: LLMExtractor | backlog | 676 | [687] | [687] | ✓ |
| #699 | Tests: MCP wiring/integration | backlog | 676 | [689] | [689] | ✓ |
| #705 | Update graph builders to await extract() | backlog | 676 | [704,687] | [704,687] | ✓ |
| #687 | Make protocol async | research | **null** ✗ | **[676]** ✗ | parent=676, depends_on=[697] | ✗ |
| #689 | Implement LLMExtractor | research | **null** ✗ | **[676]** ✗ | parent=676, depends_on=[698,687] | ✗ |
| #690 | Wire LLMExtractor into MCP server | research | **null** ✗ | **[676]** ✗; tag **scope:knowledge** ✗ | parent=676, depends_on=[699,689], scope:mcp-knowledge | ✗ |

### Circular Dependency Analysis

#687/689/690 have `depends_on: [676]`. Task 676 cannot be "done" until all its subtasks complete — those subtasks are waiting on 676 to be done. This would be a scheduling deadlock if the dependency gate blocked `pick_tasks`. However:
1. All three tasks are in `research` status — not returned by `pick_tasks` regardless of dependency state.
2. Architect labeled these fixes as CRITICAL orchestrator prerequisites with explicit repair instructions.
3. Practical risk: orchestrator must apply metadata corrections before these tasks advance to `todo`.

### AC Coverage Map

| #676 AC | Covered By | Present? |
|---------|-----------|----------|
| AC1: Concrete StructuredExtractor | #689 | ✓ |
| AC2: Wire into EntityExtractor | #690 | ✓ |
| AC3: Verify entities/edges in get_stats | #699 + #690 | ✓ |
| AC4: Graph expansion search context | #699 + #690 | ✓ |
| AC5: Graceful degradation | #689(AC5) + #690(AC5) | ✓ |
| AC6: Lives in knowledge engine package | #689(AC1) | ✓ |
| (Implicit) Graph builders await async extract | #704 + #705 | ✓ (new) |

### Builder Process Quality (5.7)
Two `## Builder Notes` sections — both "non-implementation, pass through." Not a LOOP pattern: the task genuinely has no implementation deliverable and both cycles correctly identified this.

### Deductions
- −0.05 #687, #689, #690 metadata defects still open: `depends_on: [676]` (circular), `parent: null`, #690 tag wrong. Defect is documented and mitigated; tasks not yet dispatchable; orchestrator has repair instructions. Retained from cycle 1 without increase — risk has not grown.

### Verdict
Confidence: **0.95** → **PASS**

The cycle-1 primary defect (−0.15 decomposition gap) is fully resolved with correctly-structured #704 and #705. The residual metadata defect (−0.05) remains but is adequately mitigated by explicit orchestrator prerequisites and the research-status buffer. Decomposition is now structurally complete and semantically correct across 8 subtasks covering all 6 AC lines plus the implicit graph-builder async callsite.

[[2026-04-09]] Thu 04:35
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Parent tracking container — no code produced; no codebase behavior changed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified by this task |
| 3 | External attribution | Yes | Verified | PydanticAI `run_sync` doc already attributed in `.owlbear/sources/overview.md` line 38, linked to research doc |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/wire-structuredextractor-knowledge-graph.md` exists, linked in task body, follow-up tasks (#687, #689, #690, #688) created |

### Files Updated
None — all items verified as already current or not applicable.

### Scratch Files
No `.owlbear/scratch/676-*` files found — nothing to clean.

### Summary
Decomposition container. All AC delegated to 8 subtasks (#697, #687, #704, #698, #705, #689, #699, #690). Reviewer evidence present (2 cycles). Research doc complete. Sources attributed. No documentation action required.

[[2026-04-09]] Thu 05:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Implement concrete StructuredExtractor | Delegated to #689 (exists, AC1 specifies LLMExtractor in knowledge engine) | PASS |
| AC2: Wire into EntityExtractor in app_lifespan() | Delegated to #690 (exists, AC covers wiring) | PASS |
| AC3: Verify entities/edges in get_stats | Delegated to #699 + #690 (integration tests + wiring) | PASS |
| AC4: Graph expansion search context | Delegated to #699 + #690 (AC covers graph-augmented retrieval) | PASS |
| AC5: Graceful degradation | Delegated to #689 (AC5) + #690 (AC5) | PASS |
| AC6: Lives in knowledge engine package | Delegated to #689 (AC1 specifies knowledge engine location) | PASS |
| (Implicit) Graph builders await async extract | #704 (tests) + #705 (GREEN) — added cycle 2 | PASS |

### Test Results
- pytest: 3686 passed, 389 failed, 18 skipped, 2 errors — failures pre-existing, NOT in task scope (#676 produced zero code)
- ruff: 5 issues in mcp-kanban scope (not knowledge), pre-existing

### Architect Quality: 4/5
AC lines were specific and verifiable. Initial decomposition missed graph builder async migration callsites (graph_builder.py:122/130, inter_doc_graph_builder.py:154) — caught by reviewer cycle 1, resolved by architect with #704/#705 in cycle 2. Minor gap self-corrected within pipeline.

### Deduction Breakdown
- −0.02: Metadata defects on #687, #689, #690 (depends_on: [676] instead of TDD predecessors, parent: null). Mitigated: tasks in research status, architect documented repair instructions as CRITICAL orchestrator prerequisite. Not yet dispatchable.

### Confidence: 0.98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0adeaaa | chore(kanban) | research doc, 676 task, 8 subtask files | #676, #687, #689, #690, #697, #698, #699, #704, #705 |
