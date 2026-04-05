# ACP Client Library — Decomposition Validation

> **Owning task:** #19 — Build ACP client library
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #19 defines an ACP client library with 11 AC items. Prior research (#1,
#45, #47, #60) organically decomposed this into subtasks. This research validates
whether the decomposition is complete, identifies gaps, and recommends disposition.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | ACP Python SDK `interfaces.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/interfaces.py> | .95 |
| 2 | ACP Python SDK `core.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/core.py> | .90 |
| 3 | ACP Python SDK `gemini.py` example | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | .90 |
| 4 | OwlBear ACP protocol research | `docs/research/acp-protocol.md` | .95 |
| 5 | OwlBear ACP error handling research | `docs/research/acp-error-handling-strategy.md` | .95 |
| 6 | OwlBear ACP hello-world research | `docs/research/acp-hello-world.md` | .90 |
| 7 | OwlBear classify-error extension research | `docs/research/classify-error-acp-extension.md` | .90 |

## 3. Analysis

### 3.1 AC-to-Subtask Coverage Map

| # | AC Item | Covering Task | Status | Gap? |
|---|---------|---------------|--------|------|
| 1 | Module in `packages/orchestrator/src/owlbear/acp/` | #58 + #59 (files land here) | todo/ideation | No |
| 2 | `spawn_copilot()` | #58 ProcessSupervisor (`ensure_running()`) | todo | No |
| 3 | `send_initialize()` | #59 AcpClient (wraps `conn.initialize()`) | ideation | No |
| 4 | `send_new_session()` | #59 AcpClient (wraps `conn.new_session()`) | ideation | No |
| 5 | `send_prompt()` streams updates | #59 AcpClient (wraps `conn.prompt()`) | ideation | No |
| 6 | Process lifecycle | #58 ProcessSupervisor (spawn/health/shutdown/kill) | todo | No |
| 7 | NDJSON parsing with error recovery | SDK handles internally (Sources 2, 3) | N/A | **See §3.2** |
| 8 | Async interface (asyncio subprocess) | #58 + #59 (both async) | todo/ideation | No |
| 9 | Timeout handling per message exchange | #59 AcpClient (30s/15s/300s) | ideation | No |
| 10 | Unit tests with mocked subprocess | #73 (ProcessSupervisor tests) | in-progress | **See §3.3** |
| 11 | Integration test with real Copilot CLI | #45 hello-world script | backlog | No |

### 3.2 NDJSON Parsing — SDK-Handled

AC item 7 requests "NDJSON parsing with error recovery (malformed lines)." The SDK's
`connect_to_agent()` (Source 2) wires a `ClientSideConnection` over asyncio stdin/stdout
streams with JSON-RPC framing and a 50MB buffer. The `Connection` base class handles
NDJSON read/write, method dispatch, and malformed-line handling internally (Sources 2, 3).

**Conclusion:** No custom NDJSON parser needed. AC item 7 is satisfied by SDK adoption.
The SDK raises `RequestError(-32700)` for parse errors, which #60 maps to PERMANENT.

### 3.3 Missing Test Task for AcpClient (#59)

Task #73 provides RED tests for #58 (ProcessSupervisor). The TDD pipeline requires a
matching RED test task for #59 (AcpClient wrapper), but none exists. This is a gap.

Required tests (from #59 AC):
- `conn.initialize()` wrapped with 30s timeout
- `conn.new_session()` wrapped with 15s timeout
- `conn.prompt()` wrapped with 300s timeout
- `RequestError` caught and classified by code
- `session/cancel` sent on timeout or external cancel
- `BrokenPipeError` / EOF detected as TRANSIENT

### 3.4 Missing Dependency: #59 on #46

Task #59 wraps `ClientSideConnection` from the `agent-client-protocol` SDK. Task #46
adds the SDK to orchestrator dependencies. Currently #59 `depends_on: [58]` but should
also depend on #46. Without the SDK installed, #59 cannot import `acp.*`.

### 3.5 Package Path Inconsistency

Task #58 AC references `owlbear_orchestrator/process_supervisor.py` but the
orchestrator's `pyproject.toml` builds as package `owlbear` (not `owlbear_orchestrator`):
`[tool.hatch.build.targets.wheel] packages = ["src/owlbear"]`. The correct module
path is `packages/orchestrator/src/owlbear/acp/process_supervisor.py`. This is a
minor AC cleanup for the architect.

### 3.6 Subtask Dependency Chain

```
#46 (SDK dep) ─────────────────────────────┐
#73 (PS tests) ──► #58 (ProcessSupervisor) ──┤──► #59 (AcpClient) ──► #45 (hello-world)
#60 (classify_error) ◄── archived ──────────┘
                            ▲
                   New: AcpClient test task ─┘
```

### 3.7 Disposition of #19 as Parent Task

Task #19 is fully decomposed into: #45, #46, #58, #59, #60 (done), #73. No custom
code remains for #19 itself. Options:

| Option | Pros | Cons |
|--------|------|------|
| A: Archive #19 as decomposed (.75) | Clean board, no orphan tracker | Loses linkage context |
| B: Keep as tracker, add subtask deps (.80) | Clear parent-child chain | Board clutter |

**Recommendation (.80):** Keep #19 as a tracker task at backlog. Add `depends_on`
for all leaf tasks (#45, #59) so it auto-resolves when children complete. The
architect can decide final disposition.

## 4. Recommendation (.85 confidence)

Task #19's AC is **fully covered** by existing subtasks. The only research gap was
the SDK handling NDJSON internally (AC item 7 — no custom code needed). Two pipeline
gaps require fixes: missing AcpClient test task and missing dependency on #46.

KISS/YAGNI assessment: the decomposition correctly uses the official ACP SDK rather
than building a custom JSON-RPC client, keeping total implementation to ~160 LOC
across ProcessSupervisor (~80) and AcpClient (~80).

## 5. Follow-up Tasks

### New tasks

```powershell
kanban\kanban-md.exe create "Test: AcpClient wrapper with timeouts and error classification" --priority needed --status ideation --tags "phase-1,scope:orchestrator,type:test,test" --body "## Objective`nRED phase tests for AcpClient (task #59).`n`n## AC`n- [ ] Test: initialize wrapped with 30s asyncio.wait_for timeout`n- [ ] Test: new_session wrapped with 15s timeout`n- [ ] Test: prompt wrapped with 300s timeout`n- [ ] Test: RequestError caught and classified by error code`n- [ ] Test: session/cancel sent on asyncio.TimeoutError during prompt`n- [ ] Test: BrokenPipeError detected as TRANSIENT, triggers respawn`n- [ ] Test: EOF on stdout detected as TRANSIENT`n- [ ] All tests use mocked ClientSideConnection (no real Copilot CLI)`n`nPrecedes: #59. See docs/research/acp-error-handling-strategy.md SS3.3-SS3.5."
```

### Dependency fixes (kanban-md edit)

```powershell
kanban\kanban-md.exe edit 59 --add-dep 46
```
