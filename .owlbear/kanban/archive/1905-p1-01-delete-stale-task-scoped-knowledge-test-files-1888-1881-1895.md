---
id: 1905
title: 'P1-01: Delete stale task-scoped knowledge test files (1888, 1881, 1895)'
status: archived
priority: medium
created: 2026-05-28T00:34:20.691200+02:00
updated: 2026-05-28T05:07:19.819600+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - tests/test_mcp_knowledge_lifespan_1888.py deleted from workspace
  - tests/test_mcp_knowledge_read_tools_1881.py deleted from workspace
  - tests/test_knowledge_tool_rename_1895.py deleted from workspace
  - "pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch'
    --ignore=tests/test_search_provenance.py --ignore=tests/test_persistence_source_wiring.py
    --ignore=tests/test_mcp_kanban_newline_norm_1531.py passes (0 failures, 0 errors)
    — deleted files are NOT ignored (proves clean removal); pre-existing failures
    excluded (remediation: #1906, #1907); collection error excluded (unrelated import
    breakage in kanban test)"
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Delete three task-scoped test files that assert legacy symbols removed by #1900. Their AC is fully covered by `tests/test_mcp_knowledge_legacy_removal_1900.py` and the durable v2-era test suites.

## Supersession Evidence
- `test_mcp_knowledge_lifespan_1888.py` (~31 tests): constructs AppContext with `query_service`, `graph_store`, `ingest_pipeline` fields removed by #1900 AC1. Lifespan wiring now covered by #1900 AC3/AC5 tests.
- `test_mcp_knowledge_read_tools_1881.py` (~67 tests): imports `init_db`, patches `BgeM3EmbeddingProvider`, constructs legacy context objects. Read-tool wiring now validated by v2-era tool tests.
- `test_knowledge_tool_rename_1895.py` (~12 tests): asserts `_legacy_graph_stats` exists via `hasattr()`/`callable()` — that function was deleted by #1900 AC4. The rename verification (AC1, AC3, AC4) is now inherent in the codebase state.

## Scope
- In-scope: delete the three files listed above
- Out-of-scope: updating durable module-level tests (separate tasks), modifying test_server.py (separate task)

Existing proof scope: tests/test_mcp_knowledge_legacy_removal_1900.py, pytest knowledge selector without --ignore flags

[[2026-05-28T01:34:43+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One action: delete 3 broken task-scoped test files |
| Interface clarity | PASS | AC1-3 = file absence; AC4 = pytest pass gate |
| Dependency correctness | PASS | #1900 archived (completed); symbols confirmed removed |
| Module layering | N/A | File deletion, no module interaction |
| TDD compliance | PASS | Bundle `existing`; test-writer SKIP |
| KISS/YAGNI | PASS | Minimal action |
| Premise challenge | PASS | All 3 files are broken: init_db import removed, AppContext fields removed, _legacy_graph_stats deleted |
| Pattern consistency | PASS | Task-scoped file naming convention; deletion follows cleanup pattern |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: reconsider (0.26 confidence)
- Finding: "live v2 coverage" in files being deleted; `knowledge_entity_lookup` has no other test coverage
- Architect response: REBUTTED. Verified all 3 files are BROKEN — `_make_ctx` imports deleted `init_db`, AppContext constructor uses removed fields, `_legacy_graph_stats` assertion targets deleted symbol. No test in these files can pass. The coverage gap for `knowledge_entity_lookup` is pre-existing (caused by #1900 removing infrastructure these tests depend on), not caused by this deletion. Follow-up durable test updates are explicitly out-of-scope per task body.

### Proof-Bundle Validation
- Planner assignment: existing
- Final bundle: existing
- Existing proof scope: tests/test_mcp_knowledge_legacy_removal_1900.py, pytest knowledge selector without --ignore flags
- Test-writer: SKIP (bundle `existing`)

### Design Diverge
- Skipped: single obvious approach (delete broken files), no competing alternatives

### Verdict: APPROVE
### Action Taken: Advanced to todo. Non-impl tag `test` already present for pass-through.

[[2026-05-28T01:51:57+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `test`, `proof_bundle: existing`) — no tests applicable.
- AC1-3 are file-deletion assertions; AC4 is a pytest gate on existing test infrastructure.
- Architecture review explicitly marks test-writer SKIP for this bundle.
- Passing through to builder.

[[2026-05-28T02:31:44+02:00]]
## Builder Notes
- Implementation attempt: deleted `tests/test_mcp_knowledge_lifespan_1888.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, and `tests/test_knowledge_tool_rename_1895.py` locally to satisfy AC1-AC3, then restored all three because AC4 proof gate failed and task is being rejected.
- Required existing proof 1 (named file): quality-runner scoped run on `tests/test_mcp_knowledge_legacy_removal_1900.py` passed (`44 passed, 0 failed, 0 skipped`; ruff clean).
- Required existing proof 2 (selector intent): quality-runner scoped keyword-set run failed with pre-existing legacy-suite errors outside task scope (`288 passed, 28 failed`, all from `tests/test_search_provenance.py`, `TypeError: object MagicMock can't be used in 'await' expression`).
- Additional selector-style run also reported pre-existing failures in `tests/test_persistence_source_wiring.py`; this reinforces that AC4 currently cannot pass from this task's deletion-only scope.
- Lint status on proof runs: clean.
- Evidence summary: AC4 (`pytest tests/ -k 'knowledge or enrichment or search_provenance or ingest_document or get_next_batch'` passes with 0 failures) is not currently reachable without updating/removing failing durable tests that are explicitly out-of-scope in this task body.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC4 or add prerequisite dependency so the proof gate matches task scope; current selector includes failing legacy suite outside this task. | .owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md, tests/test_search_provenance.py | quality-runner task_id=1905 scoped keyword-set run: 288 passed, 28 failed (all in tests/test_search_provenance.py) |
| 2 | architect | If AC4 must remain unchanged, add prerequisite routing to complete provenance test remediation before redispatch (candidate: #1906). | .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md, .owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md | Kanban status check: #1906 is in backlog while AC4 currently fails. |

[[2026-05-28T02:50:27+02:00]]
## Architecture Review (re-review after builder rejection)

### AC4 Refinement
- **Problem:** Original AC4 keyword selector included `search_provenance` (explicitly pulling in broken `test_search_provenance.py`, 28 pre-existing failures) and matched `test_persistence_source_wiring.py` via `knowledge` keyword (also pre-existing failures). Both files have dedicated remediation tasks (#1906, #1907).
- **Fix:** Removed `search_provenance` from `-k` filter; added `--ignore` for both pre-existing failing files. The 3 deleted files are NOT ignored — their absence from collection proves clean removal.
- **Proof-bundle unchanged:** `existing` with named proof `tests/test_mcp_knowledge_legacy_removal_1900.py` + the refined selector command.

### Existing Proof Scope (updated)
- `tests/test_mcp_knowledge_legacy_removal_1900.py` (named file, 44 tests)
- `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_search_provenance.py --ignore=tests/test_persistence_source_wiring.py` (selector gate)

### Verdict: APPROVE
Re-approved with narrowed AC4. Test-writer: SKIP (bundle `existing`, tagged `test`).

[[2026-05-28T03:12:36+02:00]]
## Test-Writer Notes
- Proof bundle: `existing` — no new test writing required.
- Tagged `test`; architecture review explicitly marks test-writer SKIP.
- AC1–AC3 are file-deletion assertions; AC4 is a pytest gate on existing infrastructure (refined selector after re-review).
- Passing through to builder.

[[2026-05-28T03:47:56+02:00]]
## Builder Notes
- Scope handled: deletion-only task under `proof_bundle: existing` with required proof checks.
- Implementation attempt: removed `tests/test_mcp_knowledge_lifespan_1888.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, and `tests/test_knowledge_tool_rename_1895.py` locally and verified absence; restored all three before reject because AC4 gate remained failing.
- Existing proof 1 (named): quality-runner scoped run on `tests/test_mcp_knowledge_legacy_removal_1900.py` passed (`44 passed, 0 failed, 0 skipped`; ruff clean).
- Existing proof 2 (AC4 selector): quality-runner exact command `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_search_provenance.py --ignore=tests/test_persistence_source_wiring.py` returned `304 passed, 0 failed, 1 error` with `ImportError: cannot import name 'create_dr' from 'owlbear_mcp_kanban.server'` in `tests/test_mcp_kanban_newline_norm_1531.py`.
- Lint status on proof runs: clean.
- Evidence summary: AC4 requires `0 failures, 0 errors`; current selector command is not reachable within this task scope because pytest collection fails on an unrelated import error not covered by current ignores.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC4 gate command to avoid unrelated collection-time import errors (for example by narrowing discovery scope or extending explicit ignore list). | .owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md, tests/test_mcp_kanban_newline_norm_1531.py | quality-runner AC4 selector gate: `304 passed, 0 failed, 1 error`; ImportError `cannot import name 'create_dr'` |
| 2 | architect | Create/route a prerequisite remediation task for the `create_dr` import breakage, then re-dispatch #1905 after that prerequisite is complete. | tests/test_mcp_kanban_newline_norm_1531.py, serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | same AC4 selector evidence; collection abort prevents `0 errors` gate |

### Post-task Reflection
- Problem faced: AC4 selector-gate still collected an unrelated test file with import-time failure, blocking a deletion-only task.
- Workaround applied: verified both required proofs through quality-runner and isolated blocker to a single collection error with exact file/symbol evidence.
- Pattern discovered: pytest `-k` gates are brittle when collection contains unrelated import errors; ignore/narrowing needs explicit architect ownership.
- Quality gap: no existing backlog item was found for the `create_dr` import breakage, leaving AC4 without a declared prerequisite path.

[[2026-05-28T03:58:40+02:00]]
## Architecture Review (re-review #3 after second builder rejection)

### AC4 Refinement
- **Problem:** AC4 selector gate collected `tests/test_mcp_kanban_newline_norm_1531.py` which has a broken import (`create_dr` removed from `owlbear_mcp_kanban.server`). Pytest collection errors fire before `-k` filtering, blocking the 0-errors gate.
- **Fix:** Added `--ignore=tests/test_mcp_kanban_newline_norm_1531.py` to AC4 command — same pattern already used by predecessor #1900's own AC7 gate.
- **Proof-bundle unchanged:** `existing` with named proof + refined selector.

### Existing Proof Scope (updated)
- `tests/test_mcp_knowledge_legacy_removal_1900.py` (named file, 44 tests)
- `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_search_provenance.py --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py` (selector gate)

### Challenge
- Skipped: trivial refinement (adding one ignore for a known broken file already excluded by predecessor task). No architectural change.

### Verdict: APPROVE
Re-approved with extended ignore list. Test-writer: SKIP (bundle `existing`, tagged `test`).

[[2026-05-28T04:04:25+02:00]]
## Test-Writer Notes
- Proof bundle: `existing` — no new test writing required.
- Tagged `test`; architecture review (re-review #3) explicitly marks test-writer SKIP.
- AC1–AC3 are file-deletion assertions; AC4 is a pytest gate on existing infrastructure (refined selector with three `--ignore` flags after re-review #3).
- Passing through to builder.

[[2026-05-28T04:29:28+02:00]]
## Builder Notes
- Implementation: deleted `tests/test_mcp_knowledge_lifespan_1888.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, and `tests/test_knowledge_tool_rename_1895.py`.
- Proof bundle: `existing` (no new tests authored; deletion-only execution).
- Existing proof 1 (named): quality-runner scoped run on `tests/test_mcp_knowledge_legacy_removal_1900.py` -> `44 passed, 0 failed, 0 skipped`; ruff clean (`ruff: 0`).
- Existing proof 2 (AC4 selector): `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_search_provenance.py --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py` -> `304 passed, 0 failed, 0 errors`.
- Coverage: N/A for this deletion-only `existing` proof task.
- Lint status: clean on proof runs.
- Commit: `ad7dbfe2` (`chore: delete stale task-scoped knowledge tests (#1905, builder)`).
- Evidence summary: AC1-AC3 satisfied by file deletion; AC4 satisfied by passing selector gate without ignoring the deleted files.

### Post-task Reflection
- Problem faced: patch-based delete operations initially reported success but did not persist on disk.
- Workaround applied: switched to direct `rm -f` with immediate `git status -- <paths>` verification before re-running proofs.
- Pattern discovered: for deletion-only tasks, filesystem + git-status verification should happen before invoking expensive proof commands.
- Time sink: one extra quality-runner cycle was consumed while stale files were still present.
- Quality gap: none in current task scope after corrected deletion flow; required proofs are now green.

[[2026-05-28T04:37:50+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1905 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence sufficiency: existing-bundle proof is complete and internally consistent. Local workspace checks confirmed all three target files are absent, consistent with the delete summary in [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L171-L178).
- Safety & security: deletion-only task; no new runtime boundary or input-handling surface was introduced.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | Authoritative AC at [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L16). Local workspace file search returned no path for tests/test_mcp_knowledge_lifespan_1888.py. | Legacy AppContext field removal remains directly asserted in [tests/test_mcp_knowledge_legacy_removal_1900.py](tests/test_mcp_knowledge_legacy_removal_1900.py#L33), [tests/test_mcp_knowledge_legacy_removal_1900.py](tests/test_mcp_knowledge_legacy_removal_1900.py#L40), and [tests/test_mcp_knowledge_legacy_removal_1900.py](tests/test_mcp_knowledge_legacy_removal_1900.py#L47). | PASS |
| AC2 | Authoritative AC at [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L17). Local workspace file search returned no path for tests/test_mcp_knowledge_read_tools_1881.py. | Legacy init_db removal remains asserted in [tests/test_mcp_knowledge_legacy_removal_1900.py](tests/test_mcp_knowledge_legacy_removal_1900.py#L222). Durable v2 entity-lookup coverage remains in [tests/test_query_facade_1880.py](tests/test_query_facade_1880.py#L179-L367). | PASS |
| AC3 | Authoritative AC at [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L18). Local workspace file search returned no path for tests/test_knowledge_tool_rename_1895.py. | Deleted legacy graph-stats surface remains asserted in [tests/test_mcp_knowledge_legacy_removal_1900.py](tests/test_mcp_knowledge_legacy_removal_1900.py#L187). Adjacent live-registry and allowlist coverage remains in [tests/test_enrichment_tools_registry_1901.py](tests/test_enrichment_tools_registry_1901.py#L127-L184). | PASS |
| AC4 | Authoritative gate is the frontmatter AC at [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L19-L24). | Builder recorded the named proof pass at [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L173) and the selector gate pass at [.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md](.owlbear/kanban/tasks/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md#L174). The ignore list excludes only unrelated pre-existing failures, not the three deleted files. | PASS |

## Observations
- No non-blocking follow-up from review. Historical rejected attempts in the task body are superseded by the final AC and builder evidence.

[[2026-05-28T04:49:05+02:00]]
## Docs Gate

**Verdict: PASS — no docs impact**

### Item 1: README Verification
N/A — changed files are root `tests/` deletions (`tests/test_mcp_knowledge_lifespan_1888.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, `tests/test_knowledge_tool_rename_1895.py`). Convention mapping: root-level test files do not map to any `serve/{pkg}/README.md` target. No source code, public interface, CLI flags, or entry points changed.

### Item 2: External Attribution
N/A — no external sources influenced this deletion-only task.

### Item 3: Research Doc
N/A — no research document was authored for this task. Pre-existing research files (`.owlbear/research/knowledge-phase-c-sweep-v2.md`, `mcp-knowledge-legacy-removal-b2.md`) reference the deleted files in historical context; these are internal tracking artifacts, not public docs, and were created under predecessor tasks.

### Item 4: Deletion Detection
No README references orphaned — grep across all `**/*.md` README files for all three deleted filenames returned zero matches. The references in `.owlbear/kanban/tasks/1906-*.md` are internal kanban task bodies; task #1906 has a declared #1905 dependency and its arch review already accounts for the deletion.

### Scratch Cleanup
No `.owlbear/scratch/1905-*` files found — nothing to clean.

### Files Modified
None.

[[2026-05-28T05:07:19+02:00]]
## Audit

### Regression Detection
Quality-runner full suite: 5902 passed, 6 failed. All 6 failures are in `tests/test_mcp_knowledge_server_1911.py` — TDD RED tests committed by test-writer for in-progress task #1911 (`61b0faba`). Not regressions from #1905. Lint violations (3x TC001/ARG002 in `serve/knowledge/`) are pre-existing, not introduced by this deletion-only task. Collection error in `test_mcp_kanban_newline_norm_1531.py` is pre-existing (known broken import).

### Intent Verification
Changed files: 3 task-scoped test files deleted from `tests/` (knowledge domain). Matches stated purpose exactly — remove broken test files superseded by #1900. No extraneous scope.

### Architect Quality
AC1-3: crystal clear file-deletion assertions (5/5). AC4: final form is adequate but required 3 architect iterations — initial selector collected unrelated broken tests twice, costing 2 full builder rejection cycles. Score: **3/5** — notable gaps requiring significant builder improvisation.

### Commit Integrity
Builder commit `ad7dbfe2` present: `chore: delete stale task-scoped knowledge tests (#1905, builder)`. 3 files deleted, 2691 lines removed. Correct format and attribution.

### Deductions
- AC quality score 3: -.03

### Confidence: 0.97
### Action: ARCHIVE

ARCHIVED #1905 -> archived | confidence .97
