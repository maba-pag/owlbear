---
id: 1330
title: 'P2-14: Phase 2 + stats tools (get_consolidation_candidates, get_stats)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.144282+00:00
updated: 2026-05-07T13:34:00.528281+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1329
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] get_consolidation_candidates(limit=N): deterministic SQL, entity names in 2+ sources, excludes reviewed_pairs and existing cross-source edges (O4)
- [ ] Returns: entity_name + relevant chunks from both sources inline
- [ ] store_enrichment with consolidation: writes cross-source edges
- [ ] store_enrichment with empty edges: marks pair in reviewed_pairs (dismissal, D14)
- [ ] New sources generate new candidate pairs; old dismissals preserved
- [ ] get_stats: total sources, total chunks, chunks enriched/total, consolidation candidates remaining (D18)
- [ ] All #1329 tests pass green

## Scope

- **In scope:** MCP tool implementations for get_consolidation_candidates, get_stats
- **Out of scope:** Per-source health breakdown in get_stats (D18 — deferred)
[[2026-05-07]]
## Research

Implementation already complete — all 7 ACs verified passing.

### Evidence
- `get_consolidation_candidates`: deterministic SQL (L185–265), returns dicts with entity_name + source chunks (L274–284), excludes cross-source edges and reviewed_pairs via canonical OR pattern
- `store_enrichment` Phase 2: candidate_id branch (L448–479) writes edges or reviewed_pairs dismissal
- `get_stats`: expanded with total_sources, total_chunks, chunks_enriched_ratio, consolidation_candidates_remaining (L940–969)
- Test suite: 36/36 passed in 1.33s (`tests/test_mcp_knowledge_phase2_tools_1329.py`)

### Classification: T1 — Autonomous
Implementation was built in a prior session (likely alongside #1329). No design decisions, no architecture changes, no follow-ups needed. Ready for review pipeline.

### Note
`get_consolidation_candidates` is not yet registered as an MCP tool or added to `__all__` — that's scoped to #1334/#1335 (Tool Surface Cleanup, Layer 4).
[[2026-05-07]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Logic-layer implementation of Phase 2 consolidation + stats expansion |
| Interface clarity | PASS | Each AC specifies concrete function, inputs, outputs, and behaviors |
| Dependency correctness | PASS | #1329 (test task) done/archived; parent decomposition chain valid |
| Module layering | PASS | All changes in serve/mcp-knowledge/server.py; no upward imports |
| TDD compliance | PASS | Tests exist in tests/test_mcp_knowledge_phase2_tools_1329.py (36 tests) |
| KISS/YAGNI | PASS | Minimal scope per Brief §4.4; registration deferred to Layer 4 |
| Premise challenge | PASS | Implementation already exists and passes; valid Layer 2 work |
| Pattern consistency | PASS | Follows existing FastMCP handler patterns (async, Context, AppContext) |
| Security surface | PASS | Parameterized SQL; no new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Core concern: scope mismatch between "MCP tool implementations" wording and missing `@mcp.tool` registration for `get_consolidation_candidates`
- Architect response: OVERRIDE — `get_stats` IS registered (L939); only `get_consolidation_candidates` registration is explicitly deferred to #1334/#1335 (Layer 4 Tool Surface Cleanup) per parent #1316 decomposition. The task note documents this. AC lines test function logic, not MCP surface exposure. Challenger conflated Layer 2 (logic) with Layer 4 (registration).

### Test Depth
- AC1: get_consolidation_candidates deterministic SQL (td:2)
- AC2: Returns entity_name + chunks (td:1)
- AC3: store_enrichment consolidation writes edges (td:1)
- AC4: store_enrichment empty edges → dismissal (td:1)
- AC5: New sources + preserved dismissals (td:2)
- AC6: get_stats fields (td:2)
- AC7: All #1329 tests pass green (td:0)
- Max depth: 2
- Test-writer: PROCEED (tests already written by #1329; verify GREEN)

### Verdict: APPROVE
### Action Taken: Advanced to todo. Tests pre-written by #1329. Builder verifies GREEN pass.
[[2026-05-07]]
Architecture review complete. All 10 criteria PASS. Challenger override justified — scope wording is slightly ambiguous but AC lines are precise and testable as function-level assertions. MCP registration deferred to Layer 4 by design. Implementation pre-built; test suite pre-written by #1329.
[[2026-05-07]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_knowledge_phase2_tools_1330.py`

**Context:** Implementation was pre-built before this pipeline stage reached #1330. The primary RED-phase suite (`test_mcp_knowledge_phase2_tools_1329.py`, 36 tests) was written by the #1329 test-writer task to cover all 7 ACs. Per architect directive: "Tests pre-written by #1329. Builder verifies GREEN."

**1330-specific additions** — error paths and boundary conditions not in #1329:

| Class | Tests | Categories |
|---|---|---|
| `TestFromAC_GetConsolidationCandidates` | 2 | edge (empty DB → []), boundary (NULL chunk_id → "") |
| `TestFromAC_StoreEnrichmentPhase2` | 4 | error (invalid candidate_id → ToolError ×3), boundary (multiple edges, idempotent dismissal) |
| `TestFromAC_GetStatsExpansion` | 5 | boundary (all 7 fields present, ratio=1.0, zero-chunk guard ×2, zero-candidate) |

**Total:** 12 tests, all PASS (implementation pre-complete).

**Note:** Because implementation already exists, all new tests are GREEN at write time. This is the expected outcome per architect guidance. Builder task: run full suite and confirm GREEN before advancing to review.

**AC coverage (via #1329 + #1330 combined):**

| AC | Status | File |
|---|---|---|
| AC1: get_consolidation_candidates deterministic SQL (td:2) | ✓ | #1329 (4 tests) + #1330 (1 test) |
| AC2: Returns entity_name + chunks (td:1) | ✓ | #1329 (3 tests) + #1330 (1 test) |
| AC3: store_enrichment consolidation → edges (td:1) | ✓ | #1329 (1 test) + #1330 (3 tests) |
| AC4: store_enrichment empty edges → reviewed_pairs (td:1) | ✓ | #1329 (2 tests) + #1330 (1 test) |
| AC5: New sources + preserved dismissals (td:2) | ✓ | #1329 (4 tests) |
| AC6: get_stats fields (td:2) | ✓ | #1329 (9 tests) + #1330 (4 tests) |
| AC7: All #1329 tests pass green (td:0) | skip | no tests needed |

**Ruff:** clean
[[2026-05-07]]
## Builder Notes
- Implementation: no code changes required in this build pass; implementation for AC1-AC6 was already present in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`.
- Interface check: `tests/test_mcp_knowledge_phase2_tools_1330.py` TestFromAC classes match existing function signatures/behavior (`get_consolidation_candidates`, `store_enrichment`, `get_stats`).
- Tests: 12/12 passed in `tests/test_mcp_knowledge_phase2_tools_1330.py`.
- AC7 verification: 36/36 passed in `tests/test_mcp_knowledge_phase2_tools_1329.py`.
- Coverage: 38.9% on `owlbear_mcp_knowledge.server` in scoped quality-runner runs.
- ruff: clean for scoped source/test paths.
- Module-level durable file check: no `tests/test_mcp_knowledge_phase2_tools.py` present; skipped per workflow.
- Approach: verification-only GREEN pass because implementation was pre-completed upstream; confirmed no regressions and AC7 green gate.
[[2026-05-07]]
## Review Evidence
### Test Results
- pytest: 48 passed, 0 failed across `tests/test_mcp_knowledge_phase2_tools_1329.py` + `tests/test_mcp_knowledge_phase2_tools_1330.py` (independent reviewer quality-runner run)
- pytest: 36 passed, 0 failed for `tests/test_mcp_knowledge_phase2_tools_1329.py` alone (AC7 verification)

### Lint: clean
- ruff: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_mcp_knowledge_phase2_tools_1329.py`, `tests/test_mcp_knowledge_phase2_tools_1330.py`

### Coverage: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`: 38.88%
- 1329-only run reported 37.97%
- Module-level percentage is below 90%, but the task-owned paths at `server.py:266-283`, `server.py:434-479`, and `server.py:940-969` are directly exercised by exact assertions. Per review policy, the hard gate is changed-line proof, not whole-module coverage on this large server module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| get_consolidation_candidates(limit=N): deterministic SQL, entity names in 2+ sources, excludes reviewed_pairs and existing cross-source edges (O4) | `test_entity_in_two_sources_appears_as_candidate`, `test_candidates_ordered_alphabetically_by_entity_name`, `test_entity_in_single_source_excluded_from_candidates`, `test_entity_with_cross_source_edge_excluded_from_candidates`, `test_entity_with_reviewed_pairs_entry_excluded_from_candidates`, `test_ac2_reversed_reviewed_pair_still_excludes_candidate`, `test_ac2_reversed_edge_direction_still_excludes_candidate` | Yes — these assertions prove inclusion, ordering, single-source exclusion, reviewed-pair exclusion, and both edge-direction branches | COVERED |
| Returns: entity_name + relevant chunks from both sources inline | `test_candidate_chunk_payloads_are_exact_source_content`, `test_entity_with_no_chunk_id_yields_empty_chunk_fields` | Yes — exact chunk payload equality and NULL-chunk boundary would fail on wrong/missing inline content | COVERED |
| store_enrichment with consolidation: writes cross-source edges | `test_phase2_non_empty_edges_writes_edge_to_db`, `test_ac4_exact_edge_row_content_after_phase2_store`, `test_phase2_multiple_edges_writes_all_edges` | Yes — exact DB-row and multi-edge count assertions would fail on dropped/miswritten edges | COVERED |
| store_enrichment with empty edges: marks pair in reviewed_pairs (dismissal, D14) | `test_phase2_empty_edges_inserts_reviewed_pair_dismissal`, `test_ac5_exact_reviewed_pairs_row_content_after_dismissal`, `test_phase2_dismissal_is_idempotent` | Yes — reviewed_pairs count/content and idempotency assertions would fail | COVERED |
| New sources generate new candidate pairs; old dismissals preserved | `test_new_source_generates_new_candidate_pair_for_same_entity`, `test_old_dismissal_preserved_in_reviewed_pairs_after_new_source`, `test_dismissed_pair_remains_excluded_after_new_source_added`, `test_exact_candidate_pairs_after_dismissal_and_new_source` | Yes — pair-generation, persistence, and exact pair-set assertions would fail | COVERED |
| get_stats: total sources, total chunks, chunks enriched/total, consolidation candidates remaining (D18) | `test_stats_returns_total_sources_field`, `test_stats_returns_total_chunks_field`, `test_stats_returns_chunks_enriched_ratio_field`, `test_stats_consolidation_candidates_remaining_exact_count`, `test_stats_returns_all_required_fields_in_single_call`, `test_stats_total_chunks_zero_and_ratio_zero_when_no_chunks`, `test_stats_total_sources_zero_when_no_sources`, `test_stats_consolidation_candidates_zero_on_empty_db` | Yes — field presence and exact numeric assertions would fail on wrong counts or missing fields | COVERED |
| All #1329 tests pass green | quality-runner scoped run on `tests/test_mcp_knowledge_phase2_tools_1329.py` | Yes — reviewer-run evidence was 36 passed / 0 failed | COVERED |

#### Security Review
- No issues found. Candidate ID parsing rejects malformed input via `ToolError` at `server.py:167-180`, and SQL in the reviewed paths is parameterized (`server.py:258-262`, `server.py:457-479`, `server.py:950-959`).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` coverage in `tests/test_mcp_knowledge_phase2_tools_1329.py` | No weakening visible in current file; exact proofs for reverse reviewed-pair, reverse edge direction, exact chunk mapping, exact edge row, and exact reviewed_pairs row are present | PRESERVED |
| `TestFromAC_*` coverage in `tests/test_mcp_knowledge_phase2_tools_1330.py` | No weakening visible in current file; error-path and boundary assertions remain discriminating | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---------|--------|---------|
| Assertion specificity | STRONG | Exact chunk equality, exact edge-row content, exact reviewed_pairs content, and exact candidate-count assertions (`1329.py:457`, `1329.py:952`, `1329.py:1010`, `1329.py:1056`) |
| Negative/error-path coverage | STRONG | Malformed `candidate_id` cases and zero-source/zero-chunk stats boundaries (`1330.py:217-248`, `1330.py:395-427`) |
| Manual mutation reasoning | ADEQUATE | Removing reviewed-pair reverse handling, reverse-edge handling, exact chunk mapping, edge writes, dismissal writes, or exact candidate count would fail targeted tests (`1329.py:706`, `1329.py:1109`, `1329.py:1262`) |
| Test independence | STRONG | Both suites use isolated in-memory SQLite fixtures |
| Descriptive names | STRONG | Test names are behavior-specific throughout both `TestFromAC_*` suites |

#### Data Safety
- No AC-blocking issue found. Phase-2 writes are transaction-wrapped with `BEGIN IMMEDIATE` / commit / rollback (`server.py:451-483`), and phase-1 writes retain the same pattern (`server.py:494-543`).
- Informational only: the implementation treats omitted `edges` the same as `edges=[]` because of `edge_rows = edges or []`. The briefed contract is explicit `store_enrichment(candidate_id, edges=[...])` and `edges=[]` for dismissal (`brief.md:97`), so I did not count the omission path against this task.

#### Implementation-Aware Gaps
- No significant untested task-owned paths remain in scope. Query ordering/exclusion, exact inline chunk payloads, phase-2 edge writes, dismissal writes, new-source pair generation, and stats expansion all have direct proof.
- Code-reader flagged missing FastMCP registration for `get_consolidation_candidates`, but the current task history and sibling tasks `#1334` / `#1335` assign tool-surface registration to Phase 4, not this Layer 2 logic task. I treated that as scoped out rather than a blocker.

#### Builder Process Quality
| Metric | Value |
|-------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `get_consolidation_candidates` is still not registered in the live FastMCP block (`server.py:792-799` only registers `get_next_batch` and `store_enrichment`), but sibling tasks `#1334` and `#1335` explicitly own tool-surface validation/cleanup.
- Whole-module coverage on `server.py` remains low because this file carries unrelated MCP endpoints. The task-owned paths are still directly proven by exact tests.
- I could verify task-related commits exist in `.git/logs/HEAD` (`4ba08abcbb95428027b646a76900256c926b7265` for `#1329` builder and `565200544604ab7149da7b866787b1c28974a862` for `#1330` test-writer), but this session did not expose a git-status/git-diff surface, so dirty-tree contamination and TestFromAC immutability could not be proven mechanically. Small confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| get_consolidation_candidates(limit=N): deterministic SQL, entity names in 2+ sources, excludes reviewed_pairs and existing cross-source edges (O4) | Query logic at `server.py:185-262`, return shape at `server.py:266-283`; inclusion/order/exclusion proofs at `1329.py:235`, `1329.py:253`, `1329.py:299`, `1329.py:318`, `1329.py:340`, `1329.py:1109`, `1329.py:1262` | see AC coverage row 1 | PASS |
| Returns: entity_name + relevant chunks from both sources inline | Return payload at `server.py:274-283`; exact and boundary proofs at `1329.py:457` and `1330.py:174` | see AC coverage row 2 | PASS |
| store_enrichment with consolidation: writes cross-source edges | Candidate branch insert path at `server.py:447-474`; proofs at `1329.py:509`, `1329.py:1010`, `1330.py:253` | see AC coverage row 3 | PASS |
| store_enrichment with empty edges: marks pair in reviewed_pairs (dismissal, D14) | Dismissal insert path at `server.py:475-479`; proofs at `1329.py:551`, `1329.py:1056`, `1330.py:295` | see AC coverage row 4 | PASS |
| New sources generate new candidate pairs; old dismissals preserved | Reviewed-pair exclusion logic at `server.py:248-255`; proofs at `1329.py:609`, `1329.py:637`, `1329.py:668`, `1329.py:706` | see AC coverage row 5 | PASS |
| get_stats: total sources, total chunks, chunks enriched/total, consolidation candidates remaining (D18) | Stats logic at `server.py:940-969`; proofs at `1329.py:795`, `1329.py:814`, `1329.py:835`, `1329.py:952`, `1330.py:346`, `1330.py:395`, `1330.py:413`, `1330.py:427` | see AC coverage row 6 | PASS |
| All #1329 tests pass green | reviewer-run quality-runner scoped pass: 36 passed, 0 failed | `tests/test_mcp_knowledge_phase2_tools_1329.py` | PASS |

### Confidence: 0.94
### Verdict: PASS
[[2026-05-07]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified — no update needed | `serve/mcp-knowledge/README.md` Tools table already has accurate entries for `get_consolidation_candidates`, `get_stats`, and `store_enrichment` — descriptions match implementation |
| 2 | Module docstrings | Yes | Verified — accurate | `get_consolidation_candidates` (L271): "Return unresolved cross-source consolidation candidates." ✓; `store_enrichment` (L440): "Persist enrichment results for phase-1 chunks or phase-2 candidates." ✓; `get_stats` (L944): "Get knowledge base statistics." ✓ |
| 3 | External attribution | No | N/A | No external patterns used; pure SQL and FastMCP conventions already attributed |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc produced; task body contains inline research section only |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — footer updated from `d875a5e4` to `56520054` (2026-05-07) |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | IN | Docstrings verified accurate — no edit needed |
| `tests/test_mcp_knowledge_phase2_tools_1329.py` | OUT | Test file — not an IN-scope doc |
| `tests/test_mcp_knowledge_phase2_tools_1330.py` | OUT | Test file — not an IN-scope doc |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated to `56520054` |

### Files Updated
- `share/diagrams/mcp-topology.excalidraw` (footer date/hash update)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1330-*` scratch files existed)
[[2026-05-07]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| get_consolidation_candidates(limit=N): deterministic SQL, excludes reviewed_pairs and cross-source edges | server.py:185-262 ORDER BY + NOT EXISTS clauses; 7 tests in 1329.py + 1 in 1330.py | PASS |\n| Returns: entity_name + relevant chunks inline | server.py:274-283 dict comprehension; 1329.py:457, 1330.py:174 | PASS |\n| store_enrichment consolidation writes edges | server.py:447-474; 1329.py:509, 1330.py:253 | PASS |\n| store_enrichment empty edges marks reviewed_pairs | server.py:475-479; 1329.py:551, 1330.py:295 | PASS |\n| New sources generate pairs; old dismissals preserved | server.py:248-255; 1329.py:609-706 (4 tests) | PASS |\n| get_stats fields | server.py:940-969; 1329.py:795-952, 1330.py:346-427 | PASS |\n| All 1329 tests pass green | 36/36 passed (auditor-run) | PASS |\n\n### Test Results\n- pytest (task-scoped): 48 passed, 0 failed (1.33s)\n- pytest (full suite): 4780 passed, 232 failed (all failures in unrelated modules: memory, kanban, cockpit, decisions)\n- ruff: clean\n\n### Architect Quality: 4/5\nAC lines are specific and testable. Minor ambiguity on \"MCP tool implementations\" wording (function logic vs registration) resolved by pipeline coordination with Layer 4 tasks. No improvisation required by builder.\n\n### Deduction Breakdown\n- AC lines with no evidence: 0 (all 7 PASS)\n- Lint violations: 0\n- AC quality score: 4 (no deduction)\n- Missing reviewer evidence: 0 (comprehensive section present)\n- Full-suite task-scope failures: 0\n- Total deductions: 0.00\n\n### Confidence: 0.98\n### Action: archive\n\n### Commits Verified\n- 56520054 test: add complementary phase-2 tests (test-writer)\n- 5db3f356 docs: update mcp-topology diagram footer (doc-writer)