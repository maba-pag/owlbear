---
id: 155
title: Build mock ACP agent for E2E testing
status: archived
priority: medium
created: 2026-03-29 19:33:50.555516+02:00
updated: 2026-03-30 15:29:40.647104+02:00
started: 2026-03-30 15:29:04.911862+02:00
completed: 2026-03-30 15:29:04.911862+02:00
tags:
- phase-2
- scope:orchestrator
- type:test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create a mock ACP agent Python script that receives task IDs via ACP prompt, reads/edits kanban board via kanban-md subprocess, and returns PromptResponse. Used as test double for Copilot CLI in E2E dispatch tests.

## Acceptance Criteria
- [ ] Python script at `tests/fixtures/mock_acp_agent.py` implementing ACP Agent Protocol
- [ ] Entry point: `run_agent(KanbanMockAgent())` Ã¢â‚¬â€ spawnable via `spawn_agent_process()`
- [ ] `initialize()` returns `InitializeResponse` with protocol version
- [ ] `new_session()` returns `NewSessionResponse` with session ID
- [ ] `prompt()` extracts task ID from first `TextContentBlock` via regex `#(\d+)`
- [ ] `prompt()` calls kanban-md subprocess (list args, no `shell=True`): show task, edit body with "Mock agent processed" annotation, move to next status
- [ ] `prompt()` returns `PromptResponse` with `stop_reason="end_turn"`
- [ ] Board dir read from `KANBAN_DIR` env var (test fixture sets this)
- [ ] Kanban binary path read from `KANBAN_BIN` env var or fallback to `kanban/kanban-md.exe`
- [ ] Remaining 11+ Agent Protocol stubs return defaults (no-op)
- [ ] Unit test at `tests/test_mock_acp_agent.py` with mocked `subprocess.run`:
  - Parses task ID correctly from prompt text
  - Calls kanban-md show, edit, move with correct args
  - Returns PromptResponse with stop_reason end_turn
  - Raises or returns error on missing/invalid task ID in prompt
- [ ] All tests pass: `uv run pytest tests/test_mock_acp_agent.py -q --tb=short`

## Architecture Notes
- Follow `examples/agent.py` from ACP SDK (run_agent entry point pattern)
- Follow mcp-kanban `test_integration.py` pattern for KANBAN_BIN/KANBAN_DIR env vars
- Subprocess calls use list args Ã¢â‚¬â€ never `shell=True`
- ~60 LOC estimated (validated against SDK examples)

## Context
See docs/research/mock-acp-agent-e2e.md for full research findings.
See docs/research/e2e-dispatch-test.md S3.4 for the mock agent pattern from ACP SDK.

[[2026-03-30]] Mon 08:39
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Script at tests/fixtures/mock_acp_agent.py | Clear, verifiable path | Kept |
| Entry point: run_agent() | Validated against ACP SDK pattern [S2, S5] | Added (was implicit) |
| initialize() returns InitializeResponse | Clear, verifiable | Added (was implicit) |
| new_session() returns NewSessionResponse | Clear, verifiable | Added (was implicit) |
| prompt() extracts task ID via regex | Precise parsing spec | Tightened (was "parses it") |
| prompt() calls kanban-md subprocess | Three operations specified, security constraint (no shell=True) | Kept + tightened |
| prompt() returns PromptResponse end_turn | Clear, verifiable | Kept |
| KANBAN_DIR env var | Test isolation mechanism from research | Added per research rec |
| KANBAN_BIN env var | Follows mcp-kanban test pattern | Added per research rec |
| Remaining stubs return defaults | Scope-limiting constraint | Added |
| Unit test with mocked subprocess.run | 4 concrete sub-assertions specified | Tightened (was vague) |
| All tests pass | Concrete command | Kept |

### Architecture Notes
- Follows ACP SDK run_agent() entry point (examples/agent.py pattern)
- Follows mcp-kanban test_integration.py pattern for env-var based binary/dir resolution
- No production code changes required (test fixture only)
- subprocess.run with list args (no shell=True) prevents command injection
- Task is standalone: no dependency on #20 (planner). Only downstream #156 depends on this + #20 + #22
- Single domain: scope:orchestrator, type:test

### Changes Made
- Refined AC: 6 items expanded to 12 verifiable items
- Added env var configuration (KANBAN_DIR, KANBAN_BIN) per research recommendation
- Added entry point and protocol method specifications
- Added concrete sub-assertions for unit test AC
- Removed stale duplicate Research sections from original body

### Dependencies
- Verified: no depends_on (standalone mock agent, per research S3.3 recommendation)
- Downstream: #156 depends on this task

[[2026-03-30]] Mon 09:10
## Test-Writer Notes
- Test file: tests/test_mock_acp_agent.py
- Classes: TestFromAC_Initialize, TestFromAC_NewSession, TestFromAC_PromptTaskIdParsing, TestFromAC_PromptSubprocessCalls, TestFromAC_PromptResponse, TestFromAC_EnvVarConfig, TestFromAC_StubMethods
- Tests per category: happy 15, edge 2, error 2, boundary 3
- Total: 22 tests, all FAIL (ModuleNotFoundError: No module named 'tests.fixtures') âœ“
- ruff: clean
- AC coverage summary:
  - initialize() returns InitializeResponse with protocol_version: test_initialize_* (2)
  - new_session() returns NewSessionResponse with session_id: test_new_session_* (2)
  - prompt() extracts task ID via regex: test_prompt_parses_* + first_id_when_multiple (3)
  - prompt() calls show/edit/move subprocesses, list args, no shell=True: test_prompt_calls_* + list_not_shell (5)
  - prompt() returns PromptResponse stop_reason=end_turn: test_prompt_returns_* + stop_reason (2)
  - KANBAN_DIR/KANBAN_BIN env vars and fallback: test_kanban_* (3)
  - 11+ stubs return defaults: test_cancel + test_load_session + test_close_session (3)
  - Raises on missing/invalid task ID: test_prompt_raises_on_* (2)

[[2026-03-30]] Mon 09:35
## Builder Notes
- Files changed: tests/fixtures/__init__.py (new), tests/fixtures/mock_acp_agent.py (new, 121 lines)
- Tests: 22 passed (all TestFromAC_* classes green)
- Lint: ruff clean (ASYNC221 suppressed per AC requirement for subprocess.run with list args)
- Coverage: tests/fixtures not in source_pkgs; no data expected (fixture file, not a registered package)
- Fixes applied: ARG002 for required Protocol stub params via noqa inline; ASYNC221 required since tests patch subprocess.run directly
- Commit: 9ce1331

[[2026-03-30]] Mon 13:55
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test fixture only, no behavior or API change |
| 2 | Docstrings | Yes | Pass | Module docstring present; all 16 public methods documented in mock_acp_agent.py |
| 3 | sources/overview.md | Yes | Pass | ACP SDK entries (lines 5-13) already added for task #155 |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research docs | Yes | Pass | docs/research/mock-acp-agent-e2e.md and e2e-dispatch-test.md exist and linked from task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/155-* files found)

[[2026-03-30]] Mon 13:56
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test fixture only, no behavior or API change |
| 2 | Docstrings | Yes | Pass | Module docstring present; all 16 public methods documented in mock_acp_agent.py |
| 3 | sources/overview.md | Yes | Pass | ACP SDK entries (lines 5-13) already added for task #155 |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research docs | Yes | Pass | docs/research/mock-acp-agent-e2e.md and e2e-dispatch-test.md exist and linked from task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/155-* files found)

[[2026-03-30]] Mon 15:28
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Script at tests/fixtures/mock_acp_agent.py | File exists, 121 lines, KanbanMockAgent class | PASS |
| Entry point: run_agent(KanbanMockAgent()) | L119-121: asyncio.run(run_agent(KanbanMockAgent())) | PASS |
| initialize() returns InitializeResponse | L37-43: returns InitializeResponse(protocol_version=protocol_version) | PASS |
| new_session() returns NewSessionResponse | L45-49: returns NewSessionResponse(session_id=str(uuid.uuid4())) | PASS |
| prompt() extracts task ID via regex | L59-62: _TASK_ID_RE.search(text), raises ValueError on miss | PASS |
| prompt() calls kanban-md subprocess, list args, no shell=True | L65-77: 3x subprocess.run with list args, check=False | PASS |
| prompt() returns PromptResponse end_turn | L78: return PromptResponse(stop_reason=end_turn) | PASS |
| KANBAN_DIR env var | L58: os.environ[KANBAN_DIR] | PASS |
| KANBAN_BIN fallback | L57,L24: os.environ.get(KANBAN_BIN, _DEFAULT_KANBAN_BIN) | PASS |
| 11+ stubs return defaults | 13 async no-op stubs (L80-116) | PASS |
| Unit tests with mocked subprocess.run | 22 tests across 7 classes covering all 4 sub-assertions | PASS |
| All tests pass | 22 passed in 0.44s | PASS |

### Test Results
- pytest (task scope): 22 passed, 0 failed
- pytest (full suite): pre-existing failures in unrelated tests (agent_port_v2, audit_log, voice_process_manager) not caused by #155
- ruff: All checks passed

### AC Quality
- Score: 4/5 (specific, verifiable; minor gap: exact stub count not specified)

### Deduction breakdown
- -.02 missing Review Evidence section in task body
### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 15:29
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 48d5043 | chore | kanban/tasks/155-*.md | #155 |
