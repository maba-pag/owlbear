---
id: 1126
title: Remove dead try/except TypeError fallback chain in MCP server end_work
status: in-progress
priority: important
created: 2026-04-25 17:32:36.614244+00:00
updated: 2026-04-25T21:02:06.215206+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-25]]
## Research
- Research doc: .owlbear/research/dead-typeerror-fallback-chain.md
- Sources: 7 studied, 4 high-relevance (code)
- Recommendation: Remove both TypeError fallback chains in server.py end_work and move_task (confidence: 0.92)
- Follow-up tasks created: none needed — this task IS the follow-up; implementation is the next step
- Decision requests: none (T1 — autonomous cleanup)

## Challenge Results
- Challenger: FALLBACK — trivial cleanup, no trade-off to challenge
- Confidence in original: 0.92

## Scope note
Task title says end_work only, but move_task has identical dead code (lines 285-288). Recommend including both in implementation scope — same root cause, same fix pattern, one commit.
[[2026-04-25]]
## Acceptance Criteria
- [ ] `server.py` `end_work` (~L421-432): Remove `except TypeError:` block and its two nested fallback calls; retain primary `view.end_work(...)` call, `except KanbanError`, and `except NotImplementedError: pass`
- [ ] `server.py` `move_task` (~L285-288): Remove `except TypeError:` block and its nested `contextlib.suppress(NotImplementedError)` fallback call; retain primary `view.move_task(...)` call, `except KanbanError`, and `except NotImplementedError: pass`
- [ ] All existing MCP kanban tests pass without modification — no tests exercise the dead TypeError paths (verified: comments in `test_mcp_guidance_1089.py` describe other tools' fallbacks, not end_work/move_task)

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Dead code removal for one root cause (parameter-stripping shims) in two call sites |
| Interface clarity | PASS | AC specifies exact blocks to remove and what to retain |
| Dependency correctness | PASS | No deps needed; #1124 context is informational, not blocking — parameter alignment holds independently |
| Module layering | PASS | Changes confined to MCP adapter layer (`server.py`), no cross-layer impact |
| TDD compliance | PASS | Existing test suites cover the retained paths; test-writer verifies no regressions |
| KISS/YAGNI | PASS | Removing dead complexity — pure simplification |
| Premise challenge | PASS | Parameter alignment verified: MCP primary calls pass exactly the kwargs AgentView accepts (`end_work`: outcome/move_to/note/block_reason/archival_reason/archival_refs; `move_task`: task_id/status/archival_reason/archival_refs). TypeError unreachable. |
| Pattern consistency | PASS | Post-removal try/except follows same pattern as other tools in server.py |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | MCP adapter domain only |

### Codebase Evidence
- `AgentView.end_work` signature (engine.py ~L1355): accepts `task_id, *, note, outcome, block_reason, move_to, archival_reason, archival_refs` — all 6 kwargs from MCP primary call
- `AgentView.move_task` signature (engine.py ~L1074): accepts `task_id, status, *, archival_reason, archival_refs, expected_updated, source` — MCP passes first 4, all accepted
- `test_mcp_guidance_1089.py` TypeError references are comments about show_task/create_task/edit_task/pick_tasks fallbacks, not end_work/move_task — no test assertions on the dead paths
- `test_mcp_models_1084.py` TypeError usage is for model validation, unrelated to server fallback chains

### Challenge Results
- Challenger: FALLBACK — trivial dead-code removal with verified parameter alignment; no challenger agent available
- Confidence: 0.93

### Verdict: APPROVE
### Action Taken: Added concrete AC, advanced to todo
[[2026-04-25]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1126.py
- Classes: TestFromAC_DeadTypeErrorFallback
- Tests per category: happy 0, edge 1 (null archival args boundary), error 2 (TypeError call_count), boundary 1 (structural source inspection)
- Total: 4 tests, all FAIL
- ruff: clean
- AC coverage:
  | AC | Test(s) |
  |----|---------|
  | AC1 end_work TypeError fallback removed | test_end_work_typeerror_propagates_after_one_call, test_end_work_typeerror_null_archival_args_propagates_after_one_call |
  | AC2 move_task TypeError fallback removed | test_move_task_typeerror_propagates_after_one_call |
  | AC3 structural — except TypeError absent | test_no_except_typeerror_in_server_source |
- Commit: f62268c4