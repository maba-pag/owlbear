# Voice Process Manager Research

> **Owning task:** #62 — Implement voice process manager
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #62 builds the owlbear-side subprocess manager for the voice addon. It spans subprocess lifecycle (spawn, shutdown, restart) and protocol-aware I/O (NDJSON read/write with typed messages). The key research question: should VoiceProcessManager reuse ProcessSupervisor (#58), be independent, or share a base class?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK stdio client | `github.com/modelcontextprotocol/python-sdk/.../stdio.py` | .95 — gold-standard asyncio subprocess + NDJSON read/write |
| 2 | ACP Python SDK `spawn_stdio_transport` | `v1/.venv/Lib/site-packages/acp/transports.py` | .90 — asyncio subprocess, graceful shutdown pattern |
| 3 | ProcessSupervisor task #58 | `kanban/tasks/058-*.md` + `tests/test_process_supervisor.py` | .95 — our own ACP subprocess lifecycle manager |
| 4 | Voice stdio protocol design | `docs/research/voice-stdio-protocol.md` S3.4–S3.5 | .95 — authoritative protocol spec for this task |
| 5 | v1 VoiceChannel | `v1/src/owlbear/voice/channel.py` | .85 — prior art adapter pattern |
| 6 | mcp-copilot-acp restart pattern | `docs/research/acp-error-handling-strategy.md` S3.2 | .85 — restart budget (max 3) pattern |

## 3. Analysis

### 3.1 Composition vs Independence vs Shared Base

| Approach | KISS | Coupling | Voice-specific fit | Score |
|----------|------|----------|--------------------|-------|
| **A. Independent class** | High (.90) | None — self-contained | Perfect | .85 |
| **B. Wraps ProcessSupervisor** | Medium (.70) | Cross-package (orchestrator → voice) | Awkward — PS returns raw pipes, voice needs typed messages | .60 |
| **C. Shared abstract base** | Low (.55) | Shared package needed | Over-engineered for 2 users | .45 |

ProcessSupervisor (#58) lives in `packages/orchestrator/`. VoiceProcessManager targets `src/owlbear/voice/process.py` (Source 4, S3.6). Importing across package boundaries adds coupling for ~60 LOC of shared logic. The two managers differ in three ways: (1) voice sends an application-level shutdown message before closing stdin, (2) voice parses NDJSON into typed Pydantic models, (3) voice has an init handshake waiting for `ready` status. Per KISS/DRY-at-third-repetition: copy the pattern, don't abstract it yet (Sources 1, 2 both implement the same pattern independently).

### 3.2 Shutdown Sequence Comparison

| Phase | ProcessSupervisor (#58) | VoiceProcessManager | MCP SDK (Source 1) | ACP SDK (Source 2) |
|-------|------------------------|--------------------|--------------------|---------------------|
| 1. App-level signal | — | Send `ShutdownMsg` | — | — |
| 2. Close stdin | — | Close stdin | Close stdin | write_eof + close |
| 3. Wait graceful | wait(5s) | wait(5s) | wait(2s) | wait(2s) |
| 4. Terminate | terminate | terminate | terminate_tree | terminate |
| 5. Wait again | — | wait(2s) | — | wait(2s) |
| 6. Force kill | kill | kill | kill (via tree) | kill |

Voice has the richest sequence (6 phases). This is protocol-specific — the shutdown message notifies the voice process to flush audio and save state. MCP and ACP only need stdin closure because JSON-RPC has no application-level shutdown message.

### 3.3 Read/Write Architecture

MCP SDK uses anyio task groups with separate `stdout_reader` and `stdin_writer` tasks (Source 1). ACP SDK yields raw pipes (Source 2). For voice:

- **Read loop:** Background `asyncio.Task` reading lines from stdout, parsing with `TypeAdapter(VoiceOutMessage).validate_json(line)`, pushing to `asyncio.Queue`. Malformed JSON lines are logged and skipped (Source 4, S3.5).
- **Write method:** Synchronous serialize via `msg.model_dump_json() + "\n"`, then `stdin.write()` + `drain()`. BrokenPipeError triggers crash detection (Source 4, S3.5).
- **Message buffer:** `asyncio.Queue` decouples read loop from consumer (VoiceChannel). This matches MCP SDK's `MemoryObjectReceiveStream` pattern (Source 1).

### 3.4 Init Handshake

Voice process sends `{"type":"status","state":"ready"}` after model loading. VoiceProcessManager must wait for this within 30s (Source 4, S3.4). Implementation: after spawn, start read loop, then `asyncio.wait_for(queue.get() until ready, timeout=30)`. If timeout, kill process and raise.

### 3.5 Dependency Gap

Task #62 has no `depends_on` set. VoiceProcessManager imports `VoiceOutMessage`/`VoiceInMessage` from #61 (protocol models). Must add `depends_on: [61]`.

## 4. Recommendation (.85 confidence)

**Independent class following MCP SDK patterns** (Source 1), not wrapping ProcessSupervisor. The voice process manager is ~120 LOC with these components:

- Async context manager (`__aenter__` / `__aexit__`)
- Spawn via `asyncio.create_subprocess_exec`, stderr inherited
- Background `asyncio.Task` read loop with `asyncio.Queue` buffer
- Typed write method with BrokenPipeError detection
- 6-phase shutdown (shutdown msg, close stdin, wait, terminate, wait, kill)
- Restart budget: max 3, same pattern as ProcessSupervisor (#58)
- Init handshake: 30s wait for ready status

**AC refinements for architect:**
- Add `depends_on: [61]`
- Add module location: voice package `process.py`
- Clarify read loop runs as background asyncio.Task with Queue buffer
- Add: BrokenPipeError on write triggers crash/restart
- Add: malformed JSON lines logged and skipped
- Specify 6-phase shutdown, not 3-phase

**Risk:** If a 3rd subprocess manager appears, the duplicated lifecycle pattern becomes DRY debt. Mitigation: extract shared base at that point (YAGNI until then).

## 5. Follow-up Tasks

No new tasks needed — #62 AC is architecturally sound, needs refinements only. Dependency fix:

```
kanban\kanban-md.exe edit 62 --add-dep 61
```
