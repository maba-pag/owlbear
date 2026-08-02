---
id: 157
title: Create E2E smoke test script for real Copilot CLI
status: archived
priority: medium
created: 2026-03-29 19:34:05.215049+02:00
updated: 2026-04-02 16:43:57.634341+02:00
started: 2026-04-02 16:43:57.169984+02:00
completed: 2026-04-02 16:43:57.169984+02:00
tags:
- phase-2
- scope:orchestrator
- type:test
depends_on:
- 20
- 22
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Manual smoke test script that validates the full stack with real Copilot CLI.

## Acceptance Criteria

### Script Structure
- [ ] Script at `scripts/e2e_smoke.py` (standalone -- no owlbear package imports)
- [ ] Script header documents: purpose, prerequisites, and manual invocation steps
- [ ] Invocation: `python scripts/e2e_smoke.py [timeout_seconds]` with `E2E_TIMEOUT` env var override (default 300s)
- [ ] Exit codes: 0=PASS, 1=FAIL, 2=prerequisite error

### Prerequisites (exit code 2 on any failure)
- [ ] Checks `shutil.which(gh)` -- gh CLI on PATH
- [ ] Checks `subprocess.run([gh, copilot, --help])` exits 0 -- Copilot extension installed
- [ ] Checks `kanban/kanban-md.exe` exists -- kanban-md binary available
- [ ] Checks `shutil.which(owlbear)` -- owlbear CLI installed in env
- [ ] Each prerequisite failure prints descriptive message to stderr before exit 2

### Task Lifecycle
- [ ] Creates temp kanban task with UUID-isolated title `fE2E-smoke-{uuid.uuid4()}` and tag `e2e-smoke`
- [ ] Resolves created task ID by matching both tag `e2e-smoke` AND UUID title substring from `kanban-md list --json`
- [ ] Invokes `owlbear dispatch <id>` via `subprocess.run()` with configured timeout, capturing stdout+stderr
- [ ] Verifies board state: task status advanced past `todo` via `kanban-md show <id> --json`
- [ ] Prints PASS or FAIL with task ID, final status to stdout; on FAIL includes captured dispatch output

### Cleanup and Safety
- [ ] try/finally cleanup (no atexit): removes temp task with `kanban-md delete <id> --yes` then `os.remove()` on the task file path (from `kanban-md show --json` `file` field)
- [ ] Timeout handling: catches `subprocess.TimeoutExpired`, prints FAIL with captured output, still cleans up

### Known Limitations (documented in script header)
- Process tree: timeout kills `owlbear dispatch` but grandchild Copilot CLI process may survive
- Orphan recovery: tag `e2e-smoke` enables manual discovery via `kanban-md list --tag e2e-smoke` if cleanup fails

## Context
See docs/research/e2e-smoke-test-script.md for implementation patterns.
See docs/research/e2e-dispatch-test.md S3.3 (Layer 2) for architectural context.

[[2026-04-02]] Thu 07:10
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- T1 classification per both research docs (.85 confidence)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Script at scripts/e2e_smoke.py | Clear, verifiable | Kept |
| Creates temp task on kanban board | Vague -- no isolation pattern | Rewritten: UUID title + e2e-smoke tag |
| Runs owlbear dispatch targeting temp task | Missing invocation detail | Rewritten: subprocess.run() with timeout, stdout+stderr capture |
| Waits for completion with configurable timeout | Missing config mechanism | Rewritten: E2E_TIMEOUT env var, sys.argv fallback, default 300s |
| Checks board state and prints PASS/FAIL | Vague checks | Rewritten: status advanced past todo, includes dispatch output on FAIL |
| Cleans up temp task on exit | Missing strategy | Rewritten: try/finally, kanban-md delete + os.remove file |
| Documents prerequisites | Missing depth | Rewritten: 4 prerequisite checks (gh, copilot ext, kanban-md, owlbear) with exit 2 |
| Script header documents manual steps | Fine as-is | Kept |
| (missing) Exit codes | Not specified | Added: 0=PASS, 1=FAIL, 2=prereq error |
| (missing) ID resolution | Ambiguous | Added: tag + UUID title match |
| (missing) Known limitations | Not documented | Added: process tree, orphan recovery |

### Architecture Notes
Module placement: scripts/e2e_smoke.py -- standalone script, no package imports. Consistent with existing scripts/ convention (setup.py, validate_agents.py). Not a package module.

Pattern source: test_e2e_dispatch.py provides UUID isolation, subprocess dispatch, try/finally cleanup patterns per e2e-smoke-test-script.md S3.4.

TDD: tagged type:test -- test-writer pass-through. This IS the test artifact.

### Changes Made
- Rewrote AC: 8 vague lines replaced with 17 verifiable lines grouped by concern
- Added prerequisite checks section (4 checks per challenger feedback)
- Added title+tag resolution (per challenger -- tag-only filter is ambiguous)
- Added output capture on FAIL (per challenger)
- Added Known Limitations section documenting process tree and orphan recovery
- Added exit code semantics

### Dependencies
- Verified: #20 (dispatch planner) archived
- Verified: #22 (CLI trigger commands) archived

### Challenge Results
- Challenger: reconsider
- Confidence in original: .65
- Key challenges: (1) kanban-md delete is soft-delete, (2) prerequisite check too shallow, (3) title-match missing from ID resolution, (4) owlbear CLI not documented as prerequisite, (5) kanban-md.exe not validated
- Architect response: accepted challenges 1-5. Revised AC adds os.remove() file cleanup, deeper prerequisite checks (gh copilot ext, kanban-md.exe, owlbear CLI), title+tag ID resolution. Rebutted pytest-marker alternative (YAGNI -- Layer 2 is a distinct manually-invocable tool, not a pytest fixture). Process tree orphan risk documented as known limitation.

[[2026-04-02]] Thu 08:12
## Test-Writer Notes
- Non-implementation task (tagged type:test) -- no tests applicable.
- This task IS the test artifact: scripts/e2e_smoke.py (standalone E2E smoke script).
- Architect confirmed: test-writer pass-through. This IS the test artifact.
- Passing through to builder.

[[2026-04-02]] Thu 12:24
## Builder Notes
- Files changed: scripts/e2e_smoke.py (new, 201 lines)
- This task IS the test artifact; test-writer passed through, builder created the script
- All AC items satisfied: 4 prereq checks, UUID task isolation, tag+title ID resolution, subprocess dispatch with timeout, try/finally cleanup, kanban-md delete + Path.unlink(), PASS/FAIL/timeout output
- Lint: ruff clean (noqa: S603/S607 for validated subprocess calls, contextlib.suppress, Path.unlink)
- No tests to run (standalone script, no package imports)
- Commit: 76d0184

[[2026-04-02]] Thu 15:54
## Docs Gate
All 5 checklist items evaluated. Updated copilot-instructions.md and README.md to list e2e_smoke.py in the scripts/ directory. Docstrings complete. sources/overview.md already updated by builder. Research doc exists and linked. No scratch files. Commit: e625669

[[2026-04-02]] Thu 16:43
## Audit
### AC Verification
| AC Group | Evidence | Status |
|----------|----------|--------|
| Script at scripts/e2e_smoke.py (standalone) | File exists, 201 lines, no owlbear imports | PASS |
| Script header (purpose, prereqs, invocation) | Lines 1-37, full RST docstring | PASS |
| Invocation with E2E_TIMEOUT/argv/default 300s | _resolve_timeout() L139-152 | PASS |
| Exit codes 0/1/2 | Documented in header, sys.exit calls match | PASS |
| Prereq: shutil.which(gh) | L62 | PASS |
| Prereq: gh copilot --help exits 0 | L67-73 | PASS |
| Prereq: kanban-md.exe exists | L78-80 | PASS |
| Prereq: shutil.which(owlbear) | L82-84 | PASS |
| Prereq failure prints to stderr, exit 2 | _print_err + sys.exit(2) per check | PASS |
| UUID title E2E-smoke-{uuid4()} + tag e2e-smoke | L158, _create_task L101-112 | PASS |
| Tag+title ID resolution from kanban-md list --json | _create_task filters both tag and title | PASS |
| owlbear dispatch via subprocess with timeout | L163-170 subprocess.run with timeout | PASS |
| Board state: status advanced past todo | L172-178 checks final_status != todo | PASS |
| PASS/FAIL output with dispatch output on FAIL | L175-178 prints captured output | PASS |
| try/finally cleanup: kanban-md delete + Path.unlink | _cleanup L127-133 in finally block | PASS |
| Timeout handling: catches TimeoutExpired, cleans up | L180-185 except block, finally runs | PASS |
| Known Limitations documented in header | Lines 28-37 process tree + orphan recovery | PASS |

### Test Results
- pytest: 2807 passed, 338 failed, 8 skipped (0 failures in task scope, all pre-existing)
- ruff: clean on scripts/e2e_smoke.py (2 pre-existing issues in unrelated test file)

### AC Quality Score: 5/5
Architect rewrote 8 vague AC lines into 17 verifiable lines grouped by concern. Challenger feedback (5 challenges) integrated. Clean, specific, led to clean implementation.

### Deduction breakdown
- -.02 missing reviewer evidence section (no Review Evidence in task body)

### Confidence: .98
### Action: archive
