---
id: 62
title: Implement voice process manager
status: todo
priority: nice-to-have
created: 2026-03-26T19:33:42.8168161+01:00
updated: 2026-03-29T15:40:50.4402252+02:00
tags:
    - phase-3
    - scope:voice
depends_on:
    - 61
    - 141
class: standard
---

## Objective

Build the owlbear-side subprocess manager for the voice addon.

## Acceptance Criteria

### Public API contract
- [ ] Class `VoiceProcessManager` with `__aenter__` / `__aexit__` (async context manager)
- [ ] `__init__(command: list[str], max_restarts: int = 3, init_timeout: float = 30.0, shutdown_timeout: float = 5.0, kill_timeout: float = 2.0)`
- [ ] `send(msg: VoiceInMessage) -> None` async write method
- [ ] `receive() -> VoiceOutMessage` async read from internal message queue
- [ ] `is_alive` property returns `bool`
- [ ] `shutdown() -> None` explicit graceful shutdown (also called by `__aexit__`)

### Spawn
- [ ] Spawns via `asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=None)`
- [ ] Verifies `proc.stdin` and `proc.stdout` are not None after spawn
- [ ] Starts background `asyncio.Task` read loop after spawn

### Read loop (background task)
- [ ] Background `asyncio.Task` reads lines from stdout
- [ ] Parses each line with `out_adapter.validate_json(line)` into `VoiceOutMessage`
- [ ] Pushes parsed messages to `asyncio.Queue`
- [ ] Malformed JSON lines: log warning via `logging.getLogger(__name__)` and skip
- [ ] EOF on stdout: detect as process crash, trigger restart

### Write method (send)
- [ ] Serializes via `msg.model_dump_json() + \n`, writes to `proc.stdin`, awaits `drain()`
- [ ] `BrokenPipeError` on write: treat as crash, trigger restart

### Init handshake
- [ ] After spawn + read loop start, wait for `StatusMsg(state=ready)` within `init_timeout`
- [ ] Non-ready messages received during wait are queued normally
- [ ] Timeout: kill process and raise `VoiceInitTimeout`
- [ ] Successful init resets restart counter

### Shutdown (6-phase)
- [ ] Phase 1: Send `ShutdownMsg` to stdin (skip on `BrokenPipeError`)
- [ ] Phase 2: Close stdin
- [ ] Phase 3: `asyncio.wait_for(proc.wait(), timeout=shutdown_timeout)`
- [ ] Phase 4: `proc.terminate()`
- [ ] Phase 5: `asyncio.wait_for(proc.wait(), timeout=kill_timeout)`
- [ ] Phase 6: `proc.kill()`
- [ ] Suppress `ProcessLookupError` during phases 4-6 (race-safe)
- [ ] Cancel read loop task during shutdown

### Restart budget
- [ ] Max 3 auto-restarts (configurable via `max_restarts`)
- [ ] Raises `VoiceRestartBudgetExhausted(OwlBearError)` when budget exceeded
- [ ] Counter resets after successful init handshake (ready received)

### Custom exceptions (defined in same module)
- [ ] `VoiceProcessError(OwlBearError)` base for voice process errors
- [ ] `VoiceInitTimeout(VoiceProcessError)` init handshake timeout
- [ ] `VoiceRestartBudgetExhausted(VoiceProcessError)` restart budget exhausted

### Module location
- [ ] `packages/orchestrator/src/owlbear/voice/process.py`

### Patterns to follow
- ProcessSupervisor (process_supervisor.py) for spawn, is_alive, restart budget
- MCP SDK stdio.py for background read/write loop architecture
- Import protocol types from `owlbear.voice.protocol` (VoiceOutMessage, VoiceInMessage, out_adapter, ShutdownMsg, StatusMsg)
- Import base error from `owlbear.errors` (OwlBearError)

## Test task
#141 (todo) tests at tests/test_voice_process_manager.py

## Context

See docs/research/voice-stdio-protocol.md S3.4-S3.5 and docs/research/voice-process-manager.md. Follow MCP SDK shutdown pattern.

[[2026-03-29]] Sun 15:40
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Spawn via create_subprocess_exec | Correct but lacked pipe verification and read loop start | Refined |
| Async read loop parse NDJSON | Vague: missing Task/Queue architecture, malformed JSON handling | Refined |
| Async write method | Vague: missing BrokenPipeError handling | Refined |
| Three-phase shutdown | Wrong: research documents 6-phase sequence | Rewritten to 6-phase |
| Health check returncode/EOF | Correct but implicit in read loop EOF detection | Kept, integrated |
| Auto-restart up to 3 attempts | Correct but missing restart counter reset on healthy init | Refined |
| Init timeout 30s | Correct but missing non-ready message queuing and VoiceInitTimeout | Refined |
| Unit tests with mocked subprocess | TDD violation: belongs in separate test task | Removed, created #141 |

### Architecture Notes
- Single domain: scope:voice. VoiceProcessManager at packages/orchestrator/src/owlbear/voice/process.py
- Independent from ProcessSupervisor (#58): different package scope, voice needs typed NDJSON I/O + init handshake + app-level shutdown. KISS per research (.85 confidence)
- 6-phase shutdown is protocol-specific: ShutdownMsg notifies voice process to flush audio before stdin close. ProcessSupervisor has 2-phase (terminate/kill)
- Error hierarchy: VoiceProcessError(OwlBearError) with two subtypes. Follows taxonomy rule (no parallel hierarchies)
- Pattern consistency: spawn/is_alive/restart from ProcessSupervisor, read/write loop from MCP SDK stdio.py
- Interface: async context manager + send/receive/shutdown/is_alive. Queue decouples reader from VoiceChannel (#63)
- Security: stdin/stdout pipes to owned subprocess, no user input boundary. No additional validation needed

### Changes Made
- Rewrote AC body with 30 verifiable lines across 9 subsections
- Replaced vague 3-phase shutdown with exact 6-phase sequence
- Added public API contract (class, constructor params, methods)
- Added read loop architecture (background Task, Queue, malformed JSON handling)
- Added write error handling (BrokenPipeError triggers restart)
- Added custom exception hierarchy (3 types)
- Added module location
- Removed test AC line, created #141 (Test: Voice process manager) at todo
- Added depends_on: #141 (TDD ordering) alongside existing #61

### Dependencies
- Verified: #61 (voice protocol models) in-progress, correct dependency
- Created: #141 (test task) at todo, added as dependency
