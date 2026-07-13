---
id: 1929
title: Enforce pipeline-owned commits at task closure
status: verify
priority: high
created: 2026-07-14T00:44:01.023216+02:00
updated: 2026-07-14T01:02:28.048112+02:00
tags:
  - agent
  - kanban
  - type:build
parent:
depends_on: []
ac:
  - Final Kanban state and task-owned durable changes are committed together or 
    closure fails explicitly
  - Unrelated dirty and staged paths remain untouched and excluded
  - Collector archive moves are included in the owned commit
  - All pipeline agents load and follow the same commit contract
  - Focused tests cover dirty-worktree advancement and archival
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Ensure every pipeline agent commits its task-owned durable changes and final Kanban task state, including collector archive moves, without staging or committing unrelated dirty work.

## Context
Current protocol requires commits before `end_work`, but `end_work` itself appends the agent note, changes status, and archives collect tasks. This makes it impossible for a pre-transition commit to include the final task record. Core pipeline agents also do not guarantee-load `r-workspace-governance`.

## Acceptance Criteria
- Pipeline closure has one authoritative ordering that includes final task state in the task-owned commit.
- Dirty unrelated tracked, staged, and untracked paths are preserved and excluded.
- Collector archive transitions are committed, including task-to-archive path movement.
- Commit failure cannot be reported as successful task closure without an explicit recoverable state.
- Pipeline agent loading and documentation match the enforced behavior.
- Focused regression tests cover ordinary advancement and collector archival with a dirty worktree.

[[2026-07-14T00:49:49+02:00]]
## Builder Notes

- Change envelope: pipeline governance loading, closure ordering, collector archive path handling, and focused regression coverage.
- Files changed: four core pipeline agent definitions; `r-workspace-governance`; `r-pipeline-protocol`; `h-mcp-kanban`; `share/WIRING.md`; authority wiring tests; scoped commit helper tests.
- Root cause: commit governance was optional for core pipeline roles; protocol required commits before `end_work` even though `end_work` creates the final note/status/archive record; lifecycle docs encouraged stopping immediately after `end_work`; collector inherited no former auditor commit-integrity check.
- Behavior: all core pipeline roles guarantee-load governance; successful closure requires an immediate explicit-path commit after `end_work`, always including final task state and both sides of archive moves; dirty unrelated paths remain excluded; no success verdict precedes commit success.
- Durable test justification: one static authority/order regression prevents instruction drift; one real-Git rename test protects collector archival with unrelated staged and untracked dirt.
- Proof: `uv run pytest tests/test_skill_authority_wiring.py serve/tools/tests/test_commit_owned.py -q` -> 8 passed; `uv run ruff check tests/test_skill_authority_wiring.py serve/tools/tests/test_commit_owned.py` -> clean; `uv run python .owlbear/scripts/validate_agents.py` -> all 23 pass; VS Code diagnostics -> none.
- Builder challenger: pass; no concrete blocker.

[[2026-07-14T00:56:06+02:00]]
## Verify Notes

- Builder commit reviewed: `de3687a7b22840a9b0ba8c4ead2099fa74ede663`.
- Initial verification found commit-failure containment missing after `end_work`; follow-up draft added `COMMIT_FAILED` blocking/recovery semantics.
- Second verification found ordinary dirty-worktree advancement proof incomplete; follow-up draft added a real-Git task-record test preserving unrelated tracked, staged, and untracked changes.
- Current proof: 9 focused tests pass; Ruff clean; all 23 agent files validate; diagnostics none.
- Verifier challenger final result: fail because these follow-up changes include durable regression tests, which verifier patch-pass cannot own.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Adopt the drafted COMMIT_FAILED contract and ordinary dirty-worktree regression as builder-owned changes; validate and commit them before returning to verify. | `share/agents/{builder,verifier,collector}.agent.md`, `share/skills/{r-workspace-governance,r-pipeline-protocol,h-mcp-kanban}/SKILL.md`, `tests/test_skill_authority_wiring.py`, `serve/tools/tests/test_commit_owned.py` | Verifier challenger rejected patch-pass ownership; current focused suite has 9 passing tests. |

[[2026-07-14T01:02:28+02:00]]
## Builder Notes

- Repair adopted from verifier follow-up: defined `COMMIT_FAILED` containment and recovery for post-`end_work` commit failures; restored final-task closure ordering and required-reader wiring.
- On-board failure state: retry scoped commit, then block with a `COMMIT_FAILED` recovery reason before returning so orchestrator cannot redispatch. Archived tasks remain off-board and report `COMMIT_FAILED` without false archival success.
- Recovery: complete the original owned commit, clear an on-board block, and commit the unblock task record separately.
- Added ordinary advancement proof: final task status and owned implementation commit together while unrelated tracked, staged, and untracked changes survive. Existing archive proof covers both sides of the task-to-archive move.
- Proof: `uv run pytest tests/test_skill_authority_wiring.py serve/tools/tests/test_commit_owned.py -q` -> 9 passed; Ruff -> clean; agent validator -> 23/23 pass; diff check -> clean.
- Builder challenger: pass; no concrete blocker.
