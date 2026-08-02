---
id: 1328
title: 'P2-12: Phase 1 enrichment tools (get_next_batch, store_enrichment)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.122372+00:00
updated: 2026-05-05T23:42:34.205901+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1327
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] get_next_batch(limit=N): SELECT pending chunks, IMMEDIATE transaction, UPDATE to claimed + set claimed_at (td:0)
- [ ] Returns: chunk_id, text, doc_title, section_path, source_name (td:0)
- [ ] Claimed chunks excluded from subsequent get_next_batch calls (td:0)
- [ ] Lease expiry: on-demand during get_next_batch, resets stale claims (>10 min) to pending (td:0)
- [ ] store_enrichment(chunk_id, entities, edges): UPSERT entities, INSERT OR IGNORE edges with UNIQUE(src, tgt, rel, doc_id) (td:0)
- [ ] store_enrichment updates chunk enrichment_state to 'enriched' (O4) (td:0)
- [ ] Per-source enrich flag respected: chunks from enrich=false sources not queued (O8) (td:0)
- [ ] All #1327 tests pass green (td:0)

## Scope

- **In scope:** Add `@mcp.tool()` decorators to `get_next_batch` and `store_enrichment` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- **Out of scope:** Phase 2 consolidation tools, agent worker loop, behavioral changes (implementation already complete)

## Builder Guidance

Implementation is already complete (L223–349 in server.py). The ONLY work is adding `@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))` decorator to both functions. Pattern: see L674, L779, L855 for matching non-read-only tool examples.

[[2026-05-05]]
## Research

**Key finding:** Implementation of `get_next_batch` and `store_enrichment` is already complete (L223–349 in server.py) and passes all 28 #1327 tests. The ONLY remaining work is adding `@mcp.tool()` decorators — both functions currently exist as unregistered helper functions.

**Gap:** No `@mcp.tool` decorator on either function → not exposed on MCP surface.
**Fix:** 2-line addition (one decorator per function, matching existing `ToolAnnotations(readOnlyHint=False, destructiveHint=False)` pattern).

**Classification:** T1 — Autonomous (mechanical wiring, no decisions needed).
**Confidence:** 0.95
**Doc:** `.owlbear/research/phase1-enrichment-tools.md`
**Follow-ups:** None — task itself is the follow-up; builder adds decorators.
[[2026-05-05]]
## Architecture Review

### Verdict: APPROVED → todo

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| get_next_batch: IMMEDIATE txn + claimed | Verified in server.py L234–272 | td:0 — covered by #1327 suite |
| Returns: chunk_id, text, doc_title, section_path, source_name | Verified L274–283 | td:0 |
| Claimed excluded from subsequent calls | Verified L246 WHERE clause | td:0 |
| Lease expiry >10 min | Verified L250–253 strftime diff | td:0 |
| store_enrichment: UPSERT entities, INSERT OR IGNORE edges | Verified L305–332 | td:0 |
| Updates enrichment_state to 'enriched' | Verified L334–337 | td:0 |
| Per-source enrich flag | Verified L247 COALESCE(ks.enrich, 1) | td:0 |
| All #1327 tests pass | Test file exists (28 tests), #1327 archived/done | td:0 |

### Architecture Notes

- Both functions already fully implemented (L223–349). Only gap: no `@mcp.tool()` decorator.
- Pattern matches 14 existing registrations (L624–1025). Annotation: `ToolAnnotations(readOnlyHint=False, destructiveHint=False)`.
- SQL uses parameterized queries throughout — no injection risk.
- IMMEDIATE transactions prevent concurrent claim races.
- No new modules, interfaces, or abstractions introduced.

### Dependency Analysis

- #1327 (tests): archived/done, test file exists at tests/test_mcp_knowledge_enrichment_tools_1327.py
- Parent #1316: in-progress container, provides brief context

### Challenge Results

Challenge: SKIPPED — all AC lines td:0, mechanical 2-decorator wiring.

### Test-writer: SKIP

All AC lines are td:0 (behavior fully covered by existing #1327 test suite). Builder adds decorators only.
[[2026-05-05]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Behavior fully covered by existing #1327 test suite (28 tests).
- Passing through to builder.
[[2026-05-05]]
## Builder Notes
- Implementation: registered existing Phase 1 enrichment functions as MCP tools in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L597).
- Fix applied: bound `get_next_batch` and `store_enrichment` with `mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))` immediately after `mcp = FastMCP(...)`, preserving existing function implementations and signatures.
- Tests: 28 passed, 0 failed (`tests/test_mcp_knowledge_enrichment_tools_1327.py`).
- Coverage: `owlbear_mcp_knowledge.server` reported 37% in scoped run (existing baseline from task-owned suite).
- Lint: clean (ruff violations: 0).
- Commit: `9cf30f97` with message `feat: register enrichment MCP tools (#1328, builder)`.

## Post-task Reflection
- Problem faced: target functions were defined before `mcp` initialization, so direct decorator syntax at definition site would fail at import time.
- Workaround applied: used equivalent post-definition registration via `mcp.tool(...)(func)` right after `mcp` creation.
- Pattern discovered: this module mixes early helper definitions with later MCP bindings; post-init registration is the safe approach for predeclared functions.
- Quality gap noted: task suite validates behavior but not MCP registration exposure directly; this build closes that wiring gap without behavioral changes.
[[2026-05-05]]
## Review Evidence
### Test Results
- pytest: 28 passed, 0 failed (`quality-runner`: `uv run pytest tests/test_mcp_knowledge_enrichment_tools_1327.py -q --tb=short`)
- Scope verification: `get_next_batch` and `store_enrichment` are registered on the MCP surface via `mcp.tool(...)` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:597-601`.

### Lint: clean
- ruff: 0 violations on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_enrichment_tools_1327.py`
- VS Code diagnostics: no errors in either file

### Coverage: skipped
- td:0 review path; no coverage gate applied.
- Builder-reported module coverage (`37%`) was not used as a pass/fail input because this task changes two registration lines, not behavior.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| get_next_batch(limit=N): SELECT pending chunks, IMMEDIATE transaction, UPDATE to claimed + set claimed_at | `test_uses_immediate_transaction` (`tests/test_mcp_knowledge_enrichment_tools_1327.py:185`), `test_select_and_update_within_single_immediate_transaction` (`tests/test_mcp_knowledge_enrichment_tools_1327.py:219`) | Yes — asserts `BEGIN IMMEDIATE` and rejects any `COMMIT` between `SELECT` and `UPDATE` | COVERED |
| Returns: chunk_id, text, doc_title, section_path, source_name | `test_returns_chunk_id_field` (`:285`), `test_returns_text_field_with_chunk_content` (`:300`), `test_returns_doc_title_from_documents_join` (`:317`), `test_returns_source_name_from_knowledge_sources_join` (`:334`), `test_section_path_round_trip_from_metadata_json` (`:397`) | Yes — exact field/value assertions would fail on missing or wrong return fields | COVERED |
| Claimed chunks excluded from subsequent get_next_batch calls | `test_claimed_chunks_not_returned_in_second_call` (`:448`) | Yes — exact absence check on second call | COVERED |
| Lease expiry: on-demand during get_next_batch, resets stale claims (>10 min) to pending | `test_stale_claimed_chunk_returned_after_lease_expiry` (`:486`), `test_exactly_10_min_boundary_not_expired` (`:532`) | Yes — proves both stale-claim inclusion and boundary exclusion | COVERED |
| store_enrichment(chunk_id, entities, edges): UPSERT entities, INSERT OR IGNORE edges with UNIQUE(src, tgt, rel, doc_id) | `test_upsert_replaces_existing_entity_on_same_id` (`:644`), `test_duplicate_edge_results_in_single_row` (`:733`), `test_duplicate_edge_does_not_raise_error` (`:708`) | Yes — exact row-count/value assertions fail on non-upsert or duplicate-edge insertion | COVERED |
| store_enrichment updates chunk enrichment_state to 'enriched' (O4) | `test_store_enrichment_sets_state_to_enriched` (`:765`), `test_enriched_chunk_not_returned_by_get_next_batch` (`:787`) | Yes — exact DB state and follow-on exclusion checks | COVERED |
| Per-source enrich flag respected: chunks from enrich=false sources not queued (O8) | `test_excludes_chunks_from_non_enrich_sources` (`:580`), `test_includes_chunks_from_enrich_true_sources` (`:597`) | Yes — exact inclusion/exclusion assertions on mixed source states | COVERED |
| All #1327 tests pass green | Independent quality-runner pytest pass (28/28 green) | Yes — any failing inherited regression breaks this AC directly | COVERED |

#### Security Review
- No issues. The task change is limited to MCP registration lines at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:597-601`; it introduces no new SQL, shell, path, secret, or deserialization surface. The underlying helper SQL remains parameterized at `server.py:239-343`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_GetNextBatch` / `TestFromAC_StoreEnrichment` in `tests/test_mcp_knowledge_enrichment_tools_1327.py` | No weakening or removal observed in the live suite; exact commit diff was unavailable in this session | PRESERVED (partial-confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact-value/state assertions at `:285`, `:317`, `:397`, `:733`, `:765` |
| Negative/error-path coverage | STRONG | Boundary and exclusion paths at `:448`, `:486`, `:532`, `:580` |
| Manual mutation reasoning | STRONG | Split-transaction mutation is caught by `:219`; duplicate-edge mutation is caught by `:733` |
| Test independence | STRONG | Fresh DB fixtures/helpers; no shared mutable state across tests |
| Descriptive test names | STRONG | Test names state the exact contract under proof throughout both TestFromAC classes |

#### Data Safety
- No issues. Transaction boundaries for both write-affecting helpers remain explicit at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:235` and `:299`.

#### Implementation-Aware Gaps
- No untested behavioral gaps within task scope. The inherited suite proves helper behavior; the task-specific structural change (MCP exposure) is verified directly by source inspection at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:597-601`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Commit presence was verified via `.git/logs` grep for `9cf30f97` (`feat: register enrichment MCP tools (#1328, builder)`), but exact `git show`/`git status` evidence was unavailable in this session. I therefore could not fully reconstruct the changed-file set or prove dirty-tree cleanliness and applied a small confidence deduction.
- No prior `## Review Evidence` section was present; this is the first review cycle for #1328.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| get_next_batch(limit=N): SELECT pending chunks, IMMEDIATE transaction, UPDATE to claimed + set claimed_at | `server.py:235`, `:239`, `:250`, `:267`; green pytest on transactional tests | `test_uses_immediate_transaction`, `test_select_and_update_within_single_immediate_transaction` | PASS |
| Returns: chunk_id, text, doc_title, section_path, source_name | `server.py:277-281`; green pytest on return-field tests | `test_returns_chunk_id_field`, `test_returns_text_field_with_chunk_content`, `test_returns_doc_title_from_documents_join`, `test_returns_source_name_from_knowledge_sources_join`, `test_section_path_round_trip_from_metadata_json` | PASS |
| Claimed chunks excluded from subsequent get_next_batch calls | `server.py:250`, `:267`; green pytest on second-call exclusion | `test_claimed_chunks_not_returned_in_second_call` | PASS |
| Lease expiry: on-demand during get_next_batch, resets stale claims (>10 min) to pending | `server.py:253-254`; green pytest on stale and boundary cases | `test_stale_claimed_chunk_returned_after_lease_expiry`, `test_exactly_10_min_boundary_not_expired` | PASS |
| store_enrichment(chunk_id, entities, edges): UPSERT entities, INSERT OR IGNORE edges with UNIQUE(src, tgt, rel, doc_id) | `server.py:304`, `:325`; green pytest on replace and duplicate-edge dedupe | `test_upsert_replaces_existing_entity_on_same_id`, `test_duplicate_edge_does_not_raise_error`, `test_duplicate_edge_results_in_single_row` | PASS |
| store_enrichment updates chunk enrichment_state to 'enriched' (O4) | `server.py:343`; green pytest on state transition and follow-on exclusion | `test_store_enrichment_sets_state_to_enriched`, `test_enriched_chunk_not_returned_by_get_next_batch` | PASS |
| Per-source enrich flag respected: chunks from enrich=false sources not queued (O8) | `server.py:248`; green pytest on enrich flag inclusion/exclusion | `test_excludes_chunks_from_non_enrich_sources`, `test_includes_chunks_from_enrich_true_sources` | PASS |
| All #1327 tests pass green | `quality-runner` report: 28 passed, 0 failed; lint clean | `tests/test_mcp_knowledge_enrichment_tools_1327.py` | PASS |

### Confidence: 0.94
### Verdict: PASS

## Post-task Reflection
- Problem faced: no direct terminal/git tool was available in this review session.
- Workaround applied: verified commit presence via `.git/logs` grep and carried an explicit confidence deduction instead of overstating diff cleanliness.
- Pattern discovered: td:0 wiring tasks can still require substantive inherited test verification when the AC explicitly carries a prior suite forward.
- Quality gap noted: the inherited suite proves helper behavior, but MCP registration exposure still depends on direct source inspection rather than an executable registration test.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-knowledge/README.md` Tools table was missing `get_next_batch` and `store_enrichment` — added two rows with descriptions from function docstrings |
| 2 | Module docstrings | Yes | N/A (accurate) | Both `get_next_batch` (L223) and `store_enrichment` (L287) in `server.py` already have accurate docstrings; no edit needed |
| 3 | External attribution | No | N/A | Task body references no external repos or articles |
| 4 | Research doc | Yes | Verified | `.owlbear/research/phase1-enrichment-tools.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` `describes: serve/mcp-*/src/**` matches `server.py`; footer updated from `2026-05-05 (30298a83)` → `2026-05-06 (6a8c3ded)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | IN (docstrings) | Docstrings verified accurate; no edit needed |
| tests/test_mcp_knowledge_enrichment_tools_1327.py | OUT (test file) | N/A |

### Files Updated
- `serve/mcp-knowledge/README.md` — added `get_next_batch` and `store_enrichment` to Tools table
- `share/diagrams/mcp-topology.excalidraw` — footer updated to `2026-05-06 (6a8c3ded)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1328-ruff.json`
- `.owlbear/scratch/1328-qr-ruff.json`
- `.owlbear/scratch/1328-pytest.txt`
- `.owlbear/scratch/1328-qr-pytest.txt`

Commit: `3feb1afc` — `docs: add enrichment tools to mcp-knowledge README, update diagram footer (#1328, doc-writer)`
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| get_next_batch: IMMEDIATE txn, claimed_at | server.py:597 registration + test_uses_immediate_transaction PASS | PASS |
| Returns: chunk_id, text, doc_title, section_path, source_name | 5 field-specific tests PASS (28/28) | PASS |
| Claimed chunks excluded from subsequent calls | test_claimed_chunks_not_returned_in_second_call PASS | PASS |
| Lease expiry resets stale claims (>10 min) | test_stale_claimed_chunk_returned + boundary test PASS | PASS |
| store_enrichment: UPSERT entities, INSERT OR IGNORE edges | test_upsert_replaces + duplicate_edge tests PASS | PASS |
| store_enrichment updates enrichment_state to enriched | test_store_enrichment_sets_state_to_enriched PASS | PASS |
| Per-source enrich flag respected | test_excludes_chunks_from_non_enrich_sources PASS | PASS |
| All #1327 tests pass green | 28 passed in 0.68s | PASS |

### Test Results
- pytest (task scope): 28 passed, 0 failed
- pytest (full suite): 199 failures, all in unrelated domains (kanban engine accessor migration, mcp-memory, cockpit react, migrations)
- ruff: 0 violations

### Architect Quality: 5/5
Specific, measurable AC lines. Clear td:0 references. Precise builder guidance with line numbers and pattern examples. Minimal-scope wiring task with no ambiguity.

### Deduction Breakdown
- AC lines without evidence: 0 (all 8 verified) - no deduction
- Lint violations: 0 - no deduction
- AC quality: 5/5 - no deduction
- Missing reviewer evidence: not missing (detailed) - no deduction
- Full-suite task-scope failures: 0 - no deduction

### Confidence: 0.98
(0.02 deduction: full suite has pre-existing unrelated failures preventing a clean green baseline proof, though none are in task scope)

### Action: archive

### Commits Verified
- 9cf30f97 feat: register enrichment MCP tools (#1328, builder)
- 3feb1afc docs: add enrichment tools to mcp-knowledge README, update diagram footer (#1328, doc-writer)