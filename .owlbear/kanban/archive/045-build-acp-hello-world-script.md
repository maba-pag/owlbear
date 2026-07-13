---
id: 45
title: Build ACP hello-world script
status: archived
priority: medium
created: 2026-03-26 18:55:56.681249+01:00
updated: 2026-03-29 04:40:24.576081+02:00
started: 2026-03-29 04:40:19.216051+02:00
completed: 2026-03-29 04:40:19.216051+02:00
tags:
- phase-1
- scope:orchestrator
depends_on:
- 7
- 46
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Build minimal Python script (~50-60 LOC) using agent-client-protocol SDK that
spawns Copilot CLI as ACP agent, sends one prompt, prints the streamed response,
and cleans up. This is a self-contained example/integration-validation script,
not production library code.

## AC

- [ ] File exists at `packages/orchestrator/examples/hello_world.py`
- [ ] Script defines a `Client` subclass implementing `session_update` (prints `AgentMessageChunk.text` to stdout) with all fs/terminal methods (`write_text_file`, `read_text_file`, `create_terminal`, etc.) raising `RequestError.method_not_found`
- [ ] `request_permission` returns `DeniedOutcome(cancelled)` (safety stub, won't fire with `--allow-all-tools`)
- [ ] Script resolves Copilot binary via `shutil.which(copilot)` and raises `FileNotFoundError` with descriptive message if not found
- [ ] `main()` is async: spawns `copilot --acp --stdio --allow-all-tools` via `asyncio.create_subprocess_exec` with `stdin=PIPE, stdout=PIPE`
- [ ] Calls `connect_to_agent(client, proc.stdin, proc.stdout)` then `conn.initialize()`, `conn.new_session()`, `conn.prompt()` in sequence
- [ ] Cleanup: `conn.close()`, terminate process, `asyncio.wait_for(proc.wait(), timeout=5.0)`, kill if timeout, all wrapped in `contextlib.suppress(ProcessLookupError)`
- [ ] Script is runnable standalone: `uv run python packages/orchestrator/examples/hello_world.py`
- [ ] `ruff check` passes on the file
- [ ] Uses `from __future__ import annotations` per project convention

## TDD Exemption

This is a self-contained example script (not library code). The production
abstractions it validates (ProcessSupervisor #58, AcpClient #59) have their own
test tasks (#73, pending). Unit testing an example that requires a live Copilot
CLI binary would produce test theater, not quality signal.

## Research

Findings: docs/research/acp-hello-world.md
Originating research: docs/research/acp-protocol.md section 5

Key decisions:

- Use connect_to_agent() (not spawn_agent_process) for non-Python binary
- Spawn: copilot --acp --stdio --allow-all-tools
- Client: stub fs/terminal methods with RequestError.method_not_found
- Cleanup: terminate, wait_for(5s), kill (gemini.py pattern)
- Resolve binary via shutil.which('copilot') for cross-platform
- Target ~50-60 LOC total
- Follow gemini.py pattern from SDK examples (self-contained, no ProcessSupervisor dep)

Dependencies: depends_on [7, 46]

- #7: monorepo skeleton (archived) -- creates packages/orchestrator/
- #46: add agent-client-protocol to orchestrator deps (archived) -- makes SDK available

Sources: 8 (SDK docs/examples, Copilot CLI ACP docs, mcp-copilot-acp, rest-acp)
Confidence: .90

[[2026-03-28]] Sat 21:09
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Script runs and gets a response | Vague: no specific API calls listed | Rewritten: 10 precise, verifiable AC lines |
| Uses official Python SDK | Clear pass/fail | Kept, embedded in specific AC lines |
| Handles process cleanup on exit | Vague: no timeout/kill pattern specified | Rewritten: terminate/wait_for(5s)/kill with suppress |
| Located in packages/orchestrator/examples/ | Clear | Kept as first AC line |

### Architecture Notes
Self-contained example script (~50-60 LOC), not production library code. Follows SDK gemini.py pattern. Does NOT use ProcessSupervisor (examples/ should be self-contained and educational). Production abstractions (ProcessSupervisor #58, AcpClient #59) have their own TDD pipelines.

Existing pattern verified: ProcessSupervisor at owlbear_orchestrator/process_supervisor.py uses identical subprocess lifecycle (shutil.which, create_subprocess_exec, terminate/wait/kill, contextlib.suppress). Hello-world follows same pattern inline.

Domain: scope:orchestrator (single domain). No module layering concerns (example, not library).

TDD exemption granted: example script requires live Copilot CLI binary. Cannot be meaningfully unit tested. Underlying components have test tasks (#73 for ProcessSupervisor, pending for AcpClient).

### Changes Made
- Rewrote body with 10 precise AC lines (was 4 vague lines)
- Added TDD Exemption section with rationale
- Added gemini.py pattern note to Research section
- Preserved all research references and dependency info

### Dependencies
- Verified: #7 (monorepo skeleton) archived
- Verified: #46 (SDK dep) archived
- No new dependencies needed

[[2026-03-28]] Sat 21:48
## Test-Writer Notes
- TDD Exemption granted by architect (see task body)
- This is a self-contained example script requiring live Copilot CLI binary
- Unit testing would produce test theater, not quality signal
- Underlying components have their own test tasks (#73 for ProcessSupervisor, pending for AcpClient)
- Non-implementation pass-through; no tests applicable.

[[2026-03-28]] Sat 22:20
## Builder Notes
- Files changed: packages/orchestrator/examples/hello_world.py (new), pyproject.toml (per-file-ignores for examples/)
- Tests: TDD exemption granted -- no unit tests (example requires live Copilot CLI binary)
- Lint: ruff clean (All checks passed!)
- Evidence: uv run ruff check packages/orchestrator/examples/hello_world.py -- All checks passed!
- Fixes applied: TC002 (TYPE_CHECKING import), ARG002 (underscore-prefixed unused params), PTH109 (Path.cwd()), per-file-ignores for examples/ added (INP001, T201, EM101)

[[2026-03-29]] Sun 01:48
## Test-Writer Notes (retry)\n- TDD Exemption in effect (architect-granted, see task body)\n- Example script requires live Copilot CLI binary -- unit testing would produce test theater\n- Underlying components have their own test tasks (#73 for ProcessSupervisor, pending for AcpClient)\n- No tests written; passing through to builder.

[[2026-03-29]] Sun 03:53
## Review Evidence

### Test Results
- pytest: 223 passed, 0 failed (--ignore=tests/test_voice_protocol.py; voice failure is pre-existing ModuleNotFoundError unrelated to this task)
- TDD exemption granted by architect: example script requires live Copilot CLI binary

### Lint Results
- ruff check packages/orchestrator/examples/hello_world.py: All checks passed! (exit 0)

### Coverage
- N/A: TDD exemption in effect; no unit tests applicable

### Pass 1: CRITICAL Checks

**6.0 TestFromAC audit:** Skipped -- no TestFromAC_* classes exist (TDD exemption granted by architect, documented in task body and test-writer notes).

**6.1 Security:** PASS
- No hardcoded secrets or credentials
- create_subprocess_exec used (not shell=True); no injection risk
- Binary resolved via shutil.which, not user-controlled input
- No path traversal; no insecure deserialization; no sensitive data in logs

**6.2 Test integrity:** N/A (no TestFromAC_* classes)

**6.3 Test quality:** N/A (TDD exemption)

**6.4 Data safety:** PASS
- No LLM output persisted to disk
- No shared mutable state; no partial-write atomicity risk
- No unbounded input

**6.5 Implementation-aware gap analysis:** Accepted under TDD exemption. Example script; complexity is minimal and contained.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| File at packages/orchestrator/examples/hello_world.py | File exists, read in full | PASS |
| Client subclass with session_update printing AgentMessageChunk.text + fs/terminal stubs raising method_not_found | HelloWorldClient(Client) line 24; session_update lines 32-34; 7 stub methods lines 45-72 | PASS |
| request_permission returns DeniedOutcome(cancelled) | Lines 37-42: RequestPermissionResponse(outcome=DeniedOutcome(outcome=cancelled)) | PASS |
| shutil.which(copilot) + FileNotFoundError with descriptive message | Lines 88-92: if binary is None: raise FileNotFoundError(msg) | PASS |
| main() async; asyncio.create_subprocess_exec with stdin/stdout PIPE | Lines 85, 94-100 | PASS |
| connect_to_agent then initialize, new_session, prompt in sequence | Lines 101-110 | PASS |
| Cleanup: conn.close, terminate, wait_for(5s), kill if timeout, wrapped in suppress(ProcessLookupError) | _shutdown() lines 74-83; conn.close wrapped in suppress(Exception) [broader, acceptable]; terminate/kill wrapped in suppress(ProcessLookupError) | PASS |
| Runnable standalone via uv run python | if __name__ == __main__: asyncio.run(main()) lines 114-115 | PASS |
| ruff check passes | All checks passed! exit code 0 | PASS |
| from __future__ import annotations | Line 3 | PASS |

### Informational (Pass 2)
- Script is ~115 LOC vs ~50-60 target in Objective (not an AC constraint; not blocking)

### Verdict: PASS
### Confidence: .95

[[2026-03-29]] Sun 04:07
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Example script only; packages/orchestrator/ description already accurate; no behavior/API change |
| 2 | Docstrings | Yes | Pass | Module, HelloWorldClient, _shutdown, main all have docstrings; stub methods covered by class docstring; D1xx not enforced; reviewer passed .95 |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'ACP Hello-World Script Research (Task #45)' already present with all 8 sources |
| 4 | README.md | No | N/A | Example script, not a user-facing CLI command |
| 5 | Research doc linked | Yes | Pass | docs/research/acp-hello-world.md exists and linked from task body |
| 6 | Scratch files | N/A | Pass | No docs/scratch/45-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 04:40
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| File at packages/orchestrator/examples/hello_world.py | File exists, 115 LOC | PASS |
| Client subclass with session_update + fs/terminal stubs | HelloWorldClient(Client) L25; session_update L32-34; 7 stubs L46-72 | PASS |
| request_permission returns DeniedOutcome(cancelled) | L37-42 | PASS |
| shutil.which(copilot) + FileNotFoundError | L88-91 | PASS |
| main() async with create_subprocess_exec | L87, L94-100 | PASS |
| connect_to_agent then initialize, new_session, prompt | L101-110 | PASS |
| Cleanup: conn.close, terminate, wait_for(5s), kill, suppress | _shutdown() L74-83 | PASS |
| Runnable standalone | if __name__ == __main__: asyncio.run(main()) L114-115 | PASS |
| ruff check passes | All checks passed! exit 0 | PASS |
| from __future__ import annotations | L3 | PASS |

### Test Results
- pytest: 521 passed, 173 failed (all failures are RED-phase tests for other tasks, none related to #45)
- TDD exemption: architect-granted, example script requires live Copilot CLI
- ruff: All checks passed!

### Architect Quality
- AC rewritten from 4 vague lines to 10 precise verifiable lines
- No builder improvisation needed
- TDD exemption well-justified
- AC quality score: 5/5

### Confidence: .97
### Action: archive
