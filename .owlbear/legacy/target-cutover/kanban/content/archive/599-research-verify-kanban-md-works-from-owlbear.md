---
id: 599
title: 'Research: Verify kanban-md works from .owlbear/kanban/'
status: archived
priority: medium
created: 2026-04-04 20:30:11.371072+02:00
updated: 2026-04-05 04:32:35.790246+02:00
started: 2026-04-05 04:32:35.790246+02:00
completed: 2026-04-05 04:32:35.790246+02:00
tags:
- scope:infra
- type:research
- phase-2
parent: 598
class: standard
archival_reason: completed
archival_refs: []
---

## Summary

Verify that kanban-md.exe works correctly when invoked from a directory OTHER than kanban/ or when config.yml and tasks/ are in a non-standard path like .owlbear/kanban/.

## Acceptance Criteria

- [ ] AC1: Create a test board at .owlbear/kanban/ (config.yml + tasks/ subdir) and verify all CRUD operations via the --dir flag:
  - AC1a: `kanban-md --dir .owlbear/kanban/ create "Test task"` (relative path from project root)
  - AC1b: `kanban-md --dir <absolute-path>/.owlbear/kanban/ list --json` (absolute path)
  - AC1c: `kanban-md --dir .owlbear/kanban/ show <id>` returns task details
  - AC1d: `kanban-md --dir .owlbear/kanban/ move <id> <status>` changes status
  - AC1e: `kanban-md --dir .owlbear/kanban/ edit <id> -a "body text"` appends body content
  - Each command exits 0 and produces parseable output (use --json where applicable)
- [ ] AC2: Document any path assumptions or limitations found (directory name constraints, Windows backslash handling, relative vs absolute path behavior)
- [ ] AC3: If kanban-md hardcodes kanban/ or has path restrictions, document workaround (symlink, wrapper script, config override)
- [ ] AC4: Add a "Kanban Path Verification" section to docs/decisions/pending/owlbear-folder-restructure.md with factual test results (pass/fail per operation, observed behavior, any limitations)

## Notes

This is a blocker for the entire migration. If kanban-md cannot work from .owlbear/kanban/, we need a workaround before proceeding.

Existing codebase evidence suggests success: integration tests in packages/mcp-kanban/tests/test_integration.py and tests/test_dispatch_integration.py already exercise kanban-md with --dir pointing to arbitrary tmp_path directories (not named kanban/), and all pass. This research confirms that behavior with the specific .owlbear/kanban/ path and documents results for the decision record.

Note: MCP server path resolution (KANBAN_DIR env var, default path changes) is handled by #606, not this task. This task verifies the kanban-md binary only.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused research: verify one binary's path behavior |
| Interface clarity | PASS (refined) | AC1 expanded to 5 explicit CRUD test scenarios with exit-code + parseable-output criteria |
| Dependency correctness | PASS | No dependencies. Leaf starter in the task graph, correctly positioned before #603 |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | PASS | Tagged type:research (pass-through) |
| KISS/YAGNI | PASS | Minimal scope: test binary, document findings |
| Premise challenge | PASS | Integration tests suggest success but explicit verification with .owlbear/kanban/ path and documented results still valuable for the decision record |
| Pattern consistency | PASS | Follows w-research workflow pattern |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:infra only |

### Challenge Results

- Challenger: reconsider (confidence: 0.68)
- Key concerns: (1) AC1 lacked specificity, (2) AC4 scope creep, (3) MCP server is the real blocker
- Architect response: Override with refinement
  - AC1 expanded into 5 explicit test scenarios AC1a-AC1e with exit-code criteria (accepted)
  - AC4 clarified to factual test results, not architectural decisions (refined)
  - MCP server path resolution correctly scoped to #606 (rebutted)

### Verdict: APPROVE
### Action Taken: Refined AC1 into explicit CRUD test scenarios. Clarified AC4 as factual documentation. Added codebase evidence notes for researcher context. Advanced to todo.

[[2026-04-04]] Sat 22:01
APPROVED #599 to todo | Refined AC1 into 5 explicit CRUD test scenarios (relative/absolute path, create/list/show/move/edit). Clarified AC4 as factual findings only. Added codebase evidence context for researcher. Challenger overridden: MCP server path resolution is #606 scope, not this task.

[[2026-04-04]] Sat 22:55
## Test-Writer Notes
- Non-implementation task (tagged type:research) — no tests applicable.
- AC1 describes manual CLI verification (run kanban-md commands, observe results).
- AC2/AC3/AC4 are documentation/findings deliverables with no testable Python interfaces.
- Architecture review in body confirms: "TDD compliance | PASS | Tagged type:research (pass-through)".
- Passing through to builder.

[[2026-04-05]] Sun 00:38
## Builder Notes

**Research type — no code changes needed.**

### Verification Executed (AC1a–AC1e)

All 5 CRUD operations verified against `.owlbear/kanban/` test board (config.yml copied, tasks/ created):

| AC | Operation | Exit | Result |
|----|-----------|------|--------|
| AC1a | create (relative path) | 0 | PASS |
| AC1b | list --json (absolute path) | 0 | PASS — JSON parseable |
| AC1c | show --json (relative path) | 0 | PASS |
| AC1d | move (relative path) | 0 | PASS |
| AC1e | edit -a (relative path) | 0 | PASS — body confirmed via show |

### Path Findings (AC2)

- No directory name constraint — tested `board-test/` as name, worked identically
- Relative paths resolve from process cwd (not binary location)
- Both `\` (backslash) and `/` (forward slash) separators work on Windows
- Missing directory: clean error `{"code":"INTERNAL_ERROR"}` exit 2
- config.yml must be present; next_id auto-repaired if needed

### Hardcoding Assessment (AC3)

No hardcoding in kanban-md binary. `--dir` flag works with arbitrary paths. No workarounds needed.
MCP server hardcoding (`_DEFAULT_KANBAN_DIR`) is scoped to task #606.

### Decision Doc Updated (AC4)

Added "Kanban Path Verification" section to `docs/decisions/resolved/owlbear-folder-restructure.md` with full operation results, path limitations, and hardcoding assessment.

**Files changed:** `docs/decisions/resolved/owlbear-folder-restructure.md` (1 file, AC4 section added)

[[2026-04-05]] Sun 01:33
## Review Evidence

### Task Type
`type:research` — no automated tests or code changes. Review evaluates documentation deliverables against AC.

### Step 1 — Source Control Changes

`git status` shows one untracked file: `docs/decisions/resolved/owlbear-folder-restructure.md`.
No staged or committed changes from the builder for this task.

**Finding:** Builder did not commit the AC4 deliverable. File is `??` (untracked). No entry in `git log` for this file at any point in history. The file was pre-existing on disk (created by prior planning work for task #598) and was also never committed by its author. Builder added the verification section but did not `git add / commit`.

### Step 2 — Independent Verification (Research Task Protocol)

No automated tests apply (`type:research` pass-through confirmed by architecture review and test-writer notes). CLI verification results cannot be independently re-executed as the `.owlbear/kanban/` test board was cleaned up (directory does not exist: `Test-Path ".owlbear"` → False).

**Corroborating evidence:** `tests/test_dispatch_integration.py` lines 99–102 and `serve/mcp-kanban/tests/test_integration.py` both exercise `kanban-md --dir <arbitrary-tmp-path>` for create/move/edit operations against directories NOT named `kanban/`. These integration tests confirm the binary's `--dir` flag is path-agnostic, which is consistent with and supports the builder's documented findings.

### Step 3 — Lint
N/A — no Python code changed.

### Step 4 — Coverage
N/A — no Python code changed.

### Step 5 — AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1a: create (relative path) | Decision doc table: exit 0, task created | COVERED (documented) |
| AC1b: list --json (absolute path) | Decision doc table: exit 0, JSON parseable | COVERED (documented) |
| AC1c: show --json (relative path) | Decision doc table: exit 0, task details returned | COVERED (documented) |
| AC1d: move (relative path) | Decision doc table: exit 0, status changed | COVERED (documented) |
| AC1e: edit -a (relative path) | Decision doc table: exit 0, body confirmed via show | COVERED (documented) |
| AC2: path assumptions/limitations | Decision doc "Path Assumptions and Limitations" section: 5 findings documented (dir naming, cwd resolution, backslash/forward-slash, missing dir error, config.yml requirement) | COVERED |
| AC3: hardcoding assessment | Decision doc "Hardcoding Assessment" section: no hardcoding found, no workarounds needed | COVERED |
| AC4: add "Kanban Path Verification" to decision doc | Section is present in `docs/decisions/resolved/owlbear-folder-restructure.md` with operation table, path limitations, and hardcoding results | DEVIATED (path) / NOT COMMITTED |

**AC4 path deviation:** AC4 specifies `docs/decisions/pending/owlbear-folder-restructure.md`. Builder used `docs/decisions/resolved/owlbear-folder-restructure.md`. Inspection confirms `docs/decisions/pending/` contains only `.gitkeep` — the owlbear-folder-restructure doc has always lived in `resolved/` (pre-existing, untracked). Spec path was stale. Builder correctly identified the actual document and added the section to it. Content substance: complete.

**AC4 commit gap:** The file is untracked. No git commit was made for this deliverable. Doc content is on disk but absent from project history.

### Deductions

| Issue | Deduction | Rationale |
|-------|-----------|-----------|
| No commit for AC4 deliverable | -0.05 | Pre-existing untracked state does not excuse builder from committing; docs stage will need to rectify |
| Non-independent CLI re-execution | -0.02 | Test board cleaned up; integration test corroboration is strong but not identical |
| AC4 path deviation (minor) | -0.02 | Spec was stale; builder used correct existing document; content complete |

### Verdict

Confidence: .91 → PASS

All AC substance is delivered. Integration test evidence corroborates CLI findings. The commit gap is noted — docs stage must `git add docs/decisions/resolved/owlbear-folder-restructure.md` and commit it as part of the documentation delivery.

[[2026-04-05]] Sun 01:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:research` — no behavior or API changes; copilot-instructions.md unchanged |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution | No | N/A | No new external patterns; kanban-md.exe is an existing tracked dependency |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | AC4 deliverable in `docs/decisions/resolved/owlbear-folder-restructure.md` — "Kanban Path Verification" section present with operation table, path limitations, and hardcoding assessment |

### Files Updated
- `docs/decisions/resolved/owlbear-folder-restructure.md` — committed `faa92a5` (was untracked, left by builder; committed at docs gate per reviewer note)

### Scratch Files
- No `docs/scratch/599-*` files found — nothing to clean

[[2026-04-05]] Sun 04:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1a: create (relative path) | Decision doc op table: exit 0, PASS. Corroborated by test_dispatch_integration.py:L99-102 | PASS |
| AC1b: list --json (absolute path) | Decision doc op table: exit 0, JSON parseable | PASS |
| AC1c: show --json (relative path) | Decision doc op table: exit 0, task details returned | PASS |
| AC1d: move (relative path) | Decision doc op table: exit 0, status changed | PASS |
| AC1e: edit -a (relative path) | Decision doc op table: exit 0, body confirmed via show | PASS |
| AC2: path assumptions/limitations | Decision doc "Path Assumptions and Limitations": 5 findings (naming, cwd, separators, missing dir, config.yml) | PASS |
| AC3: hardcoding assessment | Decision doc "Hardcoding Assessment": no binary hardcoding, MCP scoped to #606 | PASS |
| AC4: add Kanban Path Verification to decision doc | Section present in .owlbear/decisions/resolved/owlbear-folder-restructure.md (committed faa92a5, relocated by 55a4d8c #602 migration) | PASS |

### Test Results
- pytest: 2655 passed, 502 failed, 21 skipped, 1 error (502 failures are pre-existing migration path breakage — packages/ → serve/, .github/skills/ → share/skills/ — none in #599 scope)
- ruff: N/A — no Python code changed

### Research Task Protocol
- Deliverable exists: .owlbear/decisions/resolved/owlbear-folder-restructure.md → "Kanban Path Verification" section
- Follow-up tasks: findings unblock parent #598 subtask chain (#600-#609); no separate follow-ups needed (research found no blockers)
- Reviewer evidence: detailed, .91 PASS — trusted code-level findings

### Architect Quality: 4/5
AC1 expanded into 5 explicit CRUD scenarios with exit-code criteria — specific and verifiable. AC2/AC3 well-scoped. Minor gap: AC4 referenced stale path (docs/decisions/pending/) when file lived in resolved/. Challenger engagement resulted in meaningful AC refinement.

### Deduction Breakdown
- Start: 1.00
- AC4 path deviation (stale path in AC spec): -0.02
- Non-independent CLI re-execution (test board cleaned up, integration tests corroborate): -0.02

### Confidence: .96
### Action: archive
