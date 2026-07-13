---
id: 1315
title: 'P1-14: Integration test — Full lifecycle (save → curate → approve → recall
  + git commits)'
status: archived
priority: medium
created: 2026-05-04T01:32:27.514360+00:00
updated: 2026-05-07T07:39:31.529654+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
- test
parent: 1301
depends_on:
- 1311
- 1308
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Integration test exercises full lifecycle: save_memory -> list_memories -> read_memory -> curate_memory (with scope_agents) -> approve_memory -> recall_memory (td:2)
- [ ] Verifies persisted state at each step via engine re-read (not just return values): pending -> curated -> approved (td:1)
- [ ] Verifies recall_memory(agent=\"scoped-agent\") returns the approved entry in body-only format (\"## {title}
{content}\") (td:1)
- [ ] Verifies recall_memory(agent=\"other-agent\") returns empty string for non-scoped agents (td:1)
- [ ] Verifies git semantics: no new commit after save_memory; exactly 1 new commit after explicit commit_batch(session_type=\"curation\"); exactly 1 more commit after explicit commit_batch(session_type=\"review\") (td:2)
- [ ] Test uses real async tool handlers from tools.py with MemoryEngine on git-init'd tmp_path (td:1)

## Scope

- In: end-to-end integration test covering tool handler + engine + git layers
- Out: consumer wiring verification (manual), performance testing, MCP transport layer

## Builder Guidance

- Use established pattern: `_make_ctx(engine)` helper wiring `ctx.request_context.lifespan_context.engine`
- `commit_batch` is NOT auto-triggered — call it explicitly between phases
- State check via `engine.get_entry(entry_id).state` after each tool call
- Git commit count via `git rev-list --count HEAD` in tmp_path
- File: `tests/test_memory_lifecycle_1315.py`

[[2026-05-06]]
## Research

Analyzed mcp-memory codebase: tools.py (save/list/read/curate/approve/recall), engine.py (MemoryEngine, MtimeScanCache), git.py (commit_batch), models.py (MemoryEntry, MemoryState lifecycle).

Key findings:
- All tool handlers are async and use MagicMock ctx pattern (established in tests 1272, 1308, 1310)
- commit_batch is NOT auto-triggered by tool handlers — must be called explicitly between phases
- recall_memory filters by scope_agents list membership and returns body-only markdown
- State transitions: pending→curated (via curate_memory with scope_agents), curated→approved (via approve_memory)

Test design: single async integration test with explicit phases exercising all 6 AC. Uses git-init'd tmp_path with real MemoryEngine. Verifies state at each step + git commit count after batch operations.

Doc: .owlbear/research/memory-full-lifecycle-integration-test.md

## Architecture Review

**Verdict:** APPROVED (refined)

| AC line | Assessment | Action |
|---------|-----------|--------|
| Full lifecycle exercise | Clear, names exact tool functions | Refined: added function names |
| State verification | Was ambiguous (return vs persisted) | Refined: requires engine re-read |
| Recall scoped format | Clear | Refined: added expected format |
| Recall scope exclusion | Clear | Refined: added agent param example |
| Git semantics | Was missing explicit commit_batch call | Refined: made batch calls explicit |
| Real tool handlers | Was ambiguous about layer | Refined: specifies tools.py + MemoryEngine + tmp_path |

**Architecture notes:**
- Follows established mcp-memory test patterns (tests 1308, 1310)
- Dependencies #1311, #1308 confirmed done (implementations exist in tools.py, git.py)
- No new abstractions introduced; composition test of existing surfaces
- Builder Guidance section added for implementation clarity

**Challenger result:** reconsider (0.64) — addressed persistence proof gap via AC2 refinement; dismissed recall-visibility concern (already covered by #1308); dismissed layer-boundary concern (established pattern). Override justified: task is a standard composition test.

**Test-writer:** Process normally (AC1, AC5 are td:2; rest td:1).")
</invoke>
[[2026-05-06]]
Architecture review complete. Refined all 6 AC lines for precision: added exact function names, required persisted-state verification via engine re-read, specified expected recall format, made commit_batch calls explicit. Added Builder Guidance section. Challenger override justified (0.64 → proceed): persistence gap addressed, other concerns dismissed with evidence.
[[2026-05-06]]
## Test-Writer Notes
- Test file: tests/test_memory_lifecycle_1315.py
- Classes: TestFromAC_FullLifecycle, TestFromAC_PersistedState, TestFromAC_RecallScopedFormat, TestFromAC_RecallExclusion, TestFromAC_GitSemantics, TestFromAC_RealHandlers
- Tests per category: happy 6, edge 1, error 0, boundary 3
- Total: 10 tests

**Result: all 10 PASS** — all 6 tool handlers (save_memory, list_memories, read_memory, curate_memory, approve_memory, recall_memory) and commit_batch are fully implemented by dependency tasks #1308 and #1311. No builder work required.

**Direct-to-review advance** (Step 1b.1 equivalent): all new tests pass against current implementation, ruff clean. Builder has no implementation work to do.

- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 (td:2) — full lifecycle | test_full_lifecycle_save_to_recall, test_list_memories_reflects_state_change |
| AC2 (td:1) — engine re-read state | test_state_transitions_via_engine_reread |
| AC3 (td:1) — recall scoped format | test_recall_returns_body_only_markdown_format |
| AC4 (td:1) — recall exclusion | test_recall_other_agent_returns_empty_string |
| AC5 (td:2) — git semantics | test_save_memory_does_not_create_commit, test_curation_batch_creates_exactly_one_new_commit, test_review_batch_creates_exactly_one_more_commit, test_no_commit_when_only_pending_entries_present |
| AC6 (td:1) — real handlers on git repo | test_real_tool_handlers_on_git_repo |
[[2026-05-06]]
## Builder Notes
- Non-implementation pass-through confirmed: no source changes required.
- Verification run (independent): `tests/test_memory_lifecycle_1315.py`.
- Tests: 10 passed, 0 failed.
- Coverage: not measured in scoped verification run (no code touched).
- ruff: clean on `tests/test_memory_lifecycle_1315.py`.
- Evidence summary: Test-writer AC coverage map aligns with passing scoped run; all lifecycle, persisted-state, scoped-recall, exclusion, git commit semantics, and real-handler checks are green.
- Files changed: none.
- Commits made by builder: none (no deliverables to commit).

- Post-task reflection:
  - Prior notes already indicated pass-through; independent scoped run prevented false-green risk.
  - No tooling or environment blockers encountered.
  - Task was correctly bounded as test-only integration evidence.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped run on [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py): 10 passed, 0 failed, 0 skipped.
- Passing test names included [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L104), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L179), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L217), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L248), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L279), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L299), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L325), and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L387).

### Lint Results
- Ruff clean on [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py).

### Coverage
- Module coverage from quality-runner was: `owlbear_mcp_memory.tools` 55%, `owlbear_mcp_memory.git` 91%, `owlbear_mcp_memory.engine` 81%, overall 67%.
- Informational only: this is a test-only task with no builder source diff, so module-level percentages are not the gate.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| Integration test exercises full lifecycle: save_memory -> list_memories -> read_memory -> curate_memory -> approve_memory -> recall_memory | Lifecycle flow is exercised in [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L104) with step assertions at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L119), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L123), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L127), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L132), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L137), and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L141). | PASS |
| Verifies persisted state at each step via engine re-read: pending -> curated -> approved | Explicit engine rereads in [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L179) with persisted-state assertions at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L195), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L200), and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L205). | PASS |
| Verifies recall_memory(agent="scoped-agent") returns approved entry in body-only format | Exact equality proof at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L217) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L236), matching the formatter in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L319). | PASS |
| Verifies recall_memory(agent="other-agent") returns empty string for non-scoped agents | Exact empty-string assertion at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L248) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L267), aligned with scoped filtering in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L275). | PASS |
| Verifies git semantics: no new commit after save_memory; exactly 1 new commit after explicit commit_batch("curation"); exactly 1 more after explicit commit_batch("review") | Save-phase proof is strong at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L279). But the curation baseline is captured only after `curate_memory` mutates and persists state at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L316) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L318); review baseline is captured only after `approve_memory` mutates and persists state at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L344) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L346). Those handlers write to disk via [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L380) and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L480) before the explicit git contract in [serve/mcp-memory/src/owlbear_mcp_memory/git.py](serve/mcp-memory/src/owlbear_mcp_memory/git.py#L53) is measured. A hidden auto-commit inside `curate_memory` or `approve_memory` would stay green. | FAIL |
| Test uses real async tool handlers from tools.py with MemoryEngine on git-init'd tmp_path | Direct imports from [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L24), git-init fixture at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L69), and async smoke coverage at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L387). | PASS |

### Deductions
- `-0.13` AC5 proof gap: the current tests do not prove that explicit `commit_batch()` calls are the only commit points in the lifecycle, leaving a concrete false-green path.

### Verdict
- FAIL -> `todo`
- Confidence: `0.84`

### Action
- Route to `todo` for test-writer strengthening. This is a first-cycle proof failure, not an implementation failure: the current source behavior appears correct, but AC5 is not discriminating enough to catch an implicit-commit regression.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC5 by asserting commit counts immediately before and immediately after `curate_memory` and `approve_memory`, proving those handlers do not create commits before the explicit `commit_batch(session_type="curation")` and `commit_batch(session_type="review")` calls. | tests/test_memory_lifecycle_1315.py | False-green path documented in AC5 row: [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L316), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L318), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L344), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L346), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L380), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L480), [serve/mcp-memory/src/owlbear_mcp_memory/git.py](serve/mcp-memory/src/owlbear_mcp_memory/git.py#L53) |
[[2026-05-06]]
## Test-Writer Notes
- Retry (Step 1b): Added 2 new tests to `TestFromAC_GitSemantics` addressing reviewer's AC5 gap.
- New tests:
  - `test_curate_memory_does_not_create_commit` — captures commit count immediately before and after `curate_memory`, asserts no new commit.
  - `test_approve_memory_does_not_create_commit` — captures commit count immediately before and after `approve_memory`, asserts no new commit.
- These directly discriminate against a hidden auto-commit in either handler; the reviewer's false-green path is now closed.
- Test file: tests/test_memory_lifecycle_1315.py
- Total: 12 tests (10 existing + 2 new), all PASS — per Step 1b.1, implementation already correct.
- ruff: clean.
- Commit: 9850c3ab

AC coverage unchanged; AC5 proof strengthened:
| AC | Tests |
|----|-------|
| AC5 (td:2) — git semantics | test_save_memory_does_not_create_commit, test_curate_memory_does_not_create_commit (**new**), test_approve_memory_does_not_create_commit (**new**), test_curation_batch_creates_exactly_one_new_commit, test_review_batch_creates_exactly_one_more_commit, test_no_commit_when_only_pending_entries_present |

**Direct-to-review advance (Step 1b.1):** all new tests pass against current implementation, no implementation work needed.
[[2026-05-06]]
## Builder Notes
- Non-implementation pass-through (Step 1b.1): test-writer added 2 AC5-strengthening tests; all 12 pass; no source changes required.
- Advancing directly to review.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass on [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py): 12 passed, 0 failed, 0 skipped.
- The AC5 retry proofs are present at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L353) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L376), alongside the existing explicit batch assertions at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L299) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L325).

### Lint Results
- Ruff clean on [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py) and the scoped package path [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py).

### Coverage
- `owlbear_mcp_memory.tools`: 55%
- `owlbear_mcp_memory.git`: 91%
- `owlbear_mcp_memory.engine`: 81%
- Overall scoped coverage: 67%
- Informational only: this retry changed test proof, not implementation code, so the gate is AC coverage and discriminating assertions rather than module-wide percentage.

### Source Control Scope
- Reflog evidence confirms the task commits recorded for this work are ancestors of current `dev`, including the retry commit noted at [.owlbear/kanban/tasks/1315-p1-14-integration-test-full-lifecycle-save-curate-approve-recall-git-commits.md](.owlbear/kanban/tasks/1315-p1-14-integration-test-full-lifecycle-save-curate-approve-recall-git-commits.md#L175).
- Current task history also records builder pass-through with no source-file changes at [.owlbear/kanban/tasks/1315-p1-14-integration-test-full-lifecycle-save-curate-approve-recall-git-commits.md](.owlbear/kanban/tasks/1315-p1-14-integration-test-full-lifecycle-save-curate-approve-recall-git-commits.md#L121).
- Exact `git diff-tree` and `git status --porcelain` checks were unavailable from this tool surface, so exact changed-file ownership and dirty-tree overlap could not be mechanically proven in-session.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Full lifecycle exercise across save, list, read, curate, approve, recall | Real handler chain exercised in [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L104); implementation entrypoints are [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L153), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L188), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L223), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L419), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L484), and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L275). | [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L104) | PASS |
| Persisted state verified via engine re-read | State is re-read through [serve/mcp-memory/src/owlbear_mcp_memory/engine.py](serve/mcp-memory/src/owlbear_mcp_memory/engine.py#L121) after save, curate, and approve in [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L179). | [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L179) | PASS |
| Scoped recall returns exact body-only markdown | Exact equality assertion in [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L217) matches the formatter in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L275). | [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L217) | PASS |
| Non-scoped recall returns empty string | Exact empty-string assertion in [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L248) matches the scope filter in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L275). | [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L248) | PASS |
| Git semantics require no implicit commits and exactly one explicit batch commit per phase | Save no-commit proof at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L279), curate no-commit proof at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L353), approve no-commit proof at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L376), explicit curation and review batch proofs at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L299) and [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L325), pending-only no-commit proof at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L400), and the only production commit entrypoint at [serve/mcp-memory/src/owlbear_mcp_memory/git.py](serve/mcp-memory/src/owlbear_mcp_memory/git.py#L53). The prior false-green path is closed. | [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L279), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L353), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L376), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L299), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L325), [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L400) | PASS |
| Real async tool handlers with MemoryEngine on git-init'd tmp_path | Git-backed integration smoke test at [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L434) uses the imported async handlers and a git-initialized repo fixture. | [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L434) | PASS |

### Test Integrity And Quality
- Code-reader found no weakened or removed TestFromAC coverage. Current-file evidence shows additive strengthening on AC5, not a relaxation of prior assertions.
- Assertion specificity is adequate to strong on all AC-critical paths: exact state equality, exact recall format, exact empty-string exclusion, and exact commit-count deltas.
- No security, data-safety, or implementation-aware AC gaps were found in task scope.
- Informational only: [tests/test_memory_lifecycle_1315.py](tests/test_memory_lifecycle_1315.py#L145) proves state-filter membership, not exclusivity, for `list_memories`; that is outside this task’s stated AC and does not block the gate.

### Deductions
- `-0.03` source-control proof limit: reflog and current-file evidence prove task ancestry and deliverable presence, but in-session tooling could not run exact git diff or dirty-tree overlap checks.

### Verdict
- PASS to `docs`
- Confidence: `0.94`

### Action
- Advance to docs. The second-cycle AC5 proof gap is resolved in the current retry, and no further builder or test-writer work is required.
[[2026-05-07]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only task; builder confirmed no source changes; no behavior/API/CLI/config change → no IN-scope prose docs affected |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Research doc (S1–S6) references only internal project files; no external repos or articles used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/memory-full-lifecycle-integration-test.md` exists, linked from task body ("Doc: .owlbear/research/memory-full-lifecycle-integration-test.md"), marked Complete, follow-up section states "No additional follow-up tasks needed" |
| 5 | Diagram maintenance (describes match) | No | N/A | `share/diagrams/memory-layers.excalidraw` describes `serve/mcp-memory/src/**` — changed files are in `tests/` only; no glob match |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_memory_lifecycle_1315.py | OUT | N/A (test file) |
| .owlbear/research/memory-full-lifecycle-integration-test.md | IN | Verified — accurate and complete |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1315-*` scratch files existed)
[[2026-05-07]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Full lifecycle (save/list/read/curate/approve/recall) | test_full_lifecycle_save_to_recall exercises all 6 handlers in sequence with step assertions | PASS |
| AC2: Persisted state via engine re-read | test_state_transitions_via_engine_reread verifies engine.get_entry().state after each op | PASS |
| AC3: Recall scoped format ("## title\ncontent") | test_recall_returns_body_only_markdown_format with exact equality assertion | PASS |
| AC4: Recall exclusion for non-scoped agents | test_recall_other_agent_returns_empty_string with empty-string assertion | PASS |
| AC5: Git semantics (no implicit commits, +1 per batch) | 6 tests: save/curate/approve no-commit proofs + curation/review batch +1 proofs + pending-only no-commit. False-green path closed by retry commit 9850c3ab | PASS |
| AC6: Real async handlers on git-init'd tmp_path | test_real_tool_handlers_on_git_repo uses real imports + git_repo fixture | PASS |

### Test Results
- Task-scoped: 12 passed, 0 failed (verified independently)
- Full suite: 4759 passed, 218 failed, 4 skipped. All failures in unrelated tasks (1285, 1271, 1203, 1015, 1218). Zero regressions from this task.
- ruff: clean in task scope; 12 pre-existing violations in unrelated packages

### Architect Quality: 4/5
AC was refined during architecture review to be specific and verifiable. All 6 lines had clear assertion targets. Minor gap: original AC5 wording didn't explicitly require proving absence of implicit commits from non-batch handlers, requiring one review-cycle iteration. Architect caught and refined this proactively in the review round.

### Deduction Breakdown
- AC lines without evidence: 0 (all PASS)
- Lint in scope: 0
- AC quality <=3: N/A (score 4)
- Missing reviewer evidence: N/A (present, detailed, two cycles)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Commits Verified
- 9850c3ab: test: strengthen AC5 git no-commit proofs (test-writer)
- 97a3f60d: test: add integration lifecycle tests (test-writer)