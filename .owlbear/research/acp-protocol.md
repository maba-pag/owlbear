# ACP Protocol Deep-Dive

> **Owning task:** #1 — ACP protocol deep-dive
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

OwlBear v2 replaces the PydanticAI daemon with an on-demand orchestrator that spawns `copilot --acp --stdio` as a subprocess and communicates via JSON-RPC 2.0 over stdin/stdout (NDJSON). This research documents the ACP specification, key message types, error handling, and the official Python SDK that can accelerate implementation.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | ACP specification (official) | https://agentclientprotocol.com/ | .95 — authoritative spec |
| 2 | ACP GitHub (schema + repo) | https://github.com/agentclientprotocol/agent-client-protocol | .95 — JSON schema, v0.11.3 |
| 3 | ACP Python SDK | https://github.com/agentclientprotocol/python-sdk | .90 — official client/agent library, v0.9.0 |
| 4 | mcp-copilot-acp (TypeScript bridge) | https://github.com/bsmi021/mcp-copilot-acp | .75 — real-world ACP client impl |
| 5 | rest-acp (OpenAI-compat wrapper) | https://github.com/iot2020/rest-acp | .70 — session management patterns |

## 3. Analysis

### 3.1 Protocol Overview

ACP is a JSON-RPC 2.0 protocol between a **client** (code editor / orchestrator) and an **agent** (Copilot CLI). Transport is stdio (stdin/stdout) with NDJSON framing. One connection supports multiple concurrent sessions.

### 3.2 Key Message Types (Client → Agent)

| Method | Purpose | Required |
|--------|---------|----------|
| `initialize` | Negotiate protocol version + capabilities | Yes |
| `authenticate` | Auth via agent-advertised method | Optional |
| `session/new` | Create session (cwd, MCP servers) | Yes |
| `session/load` | Resume existing session | If `loadSession` cap |
| `session/list` | List known sessions | If `list` cap |
| `session/prompt` | Send user message (text, image, audio, resource) | Yes |
| `session/cancel` | Cancel ongoing prompt turn | Yes (notification) |
| `session/set_mode` | Switch agent modes (ask/code/architect) | Optional |
| `session/set_config_option` | Set session config (model, thought level) | Optional |

### 3.3 Key Message Types (Agent → Client)

| Method | Purpose | Required |
|--------|---------|----------|
| `session/update` | Stream updates (agent_message_chunk, tool_call, plan, etc.) | Yes (notification) |
| `session/request_permission` | Ask user to approve a tool call | Yes (if permission needed) |
| `fs/write_text_file` | Write file on client's filesystem | If `fs.writeTextFile` cap |
| `fs/read_text_file` | Read file on client's filesystem | If `fs.readTextFile` cap |
| `terminal/create` | Execute command in terminal | If `terminal` cap |
| `terminal/output` | Get terminal output | If `terminal` cap |
| `terminal/wait_for_exit` | Wait for command to finish | If `terminal` cap |
| `terminal/kill` / `release` | Terminate / release terminal | If `terminal` cap |

### 3.4 Session Update Types (via `session/update` notification)

| Update Discriminator | Purpose |
|---------------------|---------|
| `user_message_chunk` | Streamed user message chunk |
| `agent_message_chunk` | Streamed agent response text |
| `agent_thought_chunk` | Streamed internal reasoning |
| `tool_call` | New tool call initiated |
| `tool_call_update` | Status/content update on tool call |
| `plan` | Execution plan (entries with status + priority) |
| `available_commands_update` | Agent's available slash commands changed |
| `current_mode_update` | Session mode changed |
| `config_option_update` | Session config changed |
| `session_info_update` | Session metadata changed |

### 3.5 Lifecycle Flow

```
Client                              Agent (Copilot CLI)
  |-- initialize ------------------>|
  |<-------------- InitializeResponse (caps, auth methods)
  |-- session/new (cwd, mcp) ------>|
  |<-------------- NewSessionResponse (sessionId, modes)
  |-- session/prompt (text) -------->|
  |<-- session/update (agent_message_chunk) -- (streamed)
  |<-- session/update (tool_call) ----------- (streamed)
  |<-- session/request_permission ----------- (if needed)
  |-- RequestPermissionResponse ---->|
  |<-- session/update (tool_call_update) ---- (streamed)
  |<-------------- PromptResponse (stopReason)
```

### 3.6 Error Handling Patterns

| Scenario | ACP mechanism |
|----------|--------------|
| Invalid JSON | Error code -32700 (parse error) |
| Unknown method | Error code -32601 (method not found) |
| Auth required | Error code -32000 + `authMethods` in init response |
| Process crash | Subprocess exits; detect via process.returncode != None |
| Timeout | No built-in timeout; client must implement (mcp-copilot-acp uses 300s default) |
| Cancellation | Client sends `session/cancel` notification; agent replies with `stopReason: "cancelled"` |
| Permission denied | `RequestPermissionOutcome::Cancelled` or user selects reject option |

Stop reasons: `end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled`.

### 3.7 Python SDK Assessment

| Criterion | Assessment | Score |
|-----------|-----------|-------|
| Schema parity | Auto-generated Pydantic models from official schema (v0.11.2) | .95 |
| Transport | asyncio stdio JSON-RPC plumbing built-in | .90 |
| API ergonomics | `connect_to_agent()`, `conn.initialize()`, `conn.new_session()`, `conn.prompt()` | .90 |
| Deps (KISS) | pip install: `agent-client-protocol` (Pydantic-based, minimal) | .85 |
| Maturity | v0.9.0, 204 stars, 13 contributors, Apache-2.0 | .70 |
| Examples | 5 runnable examples (client, agent, echo, duet, gemini bridge) | .85 |

## 4. Recommendation (.85 confidence)

**Use the official Python SDK (`agent-client-protocol`)** rather than building a raw JSON-RPC client.

Rationale: The SDK provides auto-generated Pydantic models tracking every ACP release, async stdio transport, and lifecycle helpers that reduce our client to ~50 lines (matching the v2 architecture target). The `examples/client.py` demonstrates exactly the spawn-and-talk pattern v2 needs.

Risk: SDK is v0.9.0 (pre-1.0). Mitigation: pin version, vendor types if needed. The ACP spec itself is at v0.11.3 with 2.6k stars and 90 contributors — active and well-maintained.

**For the hello-world task:** spawn `copilot --acp --stdio --allow-all-tools`, use `connect_to_agent()` + `conn.initialize()` + `conn.new_session()` + `conn.prompt()`. The rest-acp and mcp-copilot-acp projects confirm the `--yolo` / `--allow-all-tools` flags auto-approve permissions.

## 5. Follow-up Tasks

1. #45 - Build ACP hello-world script.
  Priority rationale: `needed` because v2 orchestration requires a verified ACP client bootstrap path before broader integration.
  Dependencies: #7, #46.
  One-line AC: add a minimal Python example that initializes ACP, creates a session, sends one prompt, prints streamed output, and cleans up the subprocess.
  Created:

  ```powershell
  kanban\kanban-md.exe create "Build ACP hello-world script" --priority needed --status ideation --tags "phase-1,scope:orchestrator" --depends-on 7,46 --body "See docs/research/acp-protocol.md §5 for context. AC: add a minimal Python example that initializes ACP, creates a session, sends one prompt, prints streamed output, and cleans up the subprocess."
  ```

  Created task ID after execution: #45.

2. #46 - Add agent-client-protocol to orchestrator deps.
  Priority rationale: `needed` because task #45 and all ACP client work depend on the SDK being available in orchestrator dependencies.
  Dependencies: #7.
  One-line AC: add `agent-client-protocol >=0.9.0,<1.0.0` to orchestrator dependencies, validate lock resolution, and confirm import of `Client` and `connect_to_agent`.
  Created:

  ```powershell
  kanban\kanban-md.exe create "Add agent-client-protocol to orchestrator deps" --priority needed --status ideation --tags "phase-1,scope:orchestrator,config" --depends-on 7 --body "See docs/research/acp-protocol.md §5 for context. AC: add agent-client-protocol >=0.9.0,<1.0.0 to orchestrator dependencies, validate lock resolution, and confirm import of Client and connect_to_agent."
  ```

  Created task ID after execution: #46.

3. #47 - Document ACP error handling strategy.
  Priority rationale: `important` because transport failures and cancellation semantics need explicit implementation guidance for reliable orchestrator behavior.
  Dependencies: none.
  One-line AC: document process crash handling, JSON parse/method errors, timeout/cancellation behavior, and ACP error-code mapping for orchestrator flows.
  Created:

  ```powershell
  kanban\kanban-md.exe create "Document ACP error handling strategy" --priority important --status ideation --tags "phase-1,scope:orchestrator,docs" --body "See docs/research/acp-protocol.md §5 for context. AC: document process crash handling, JSON parse or method errors, timeout and cancellation behavior, and ACP error-code mapping for orchestrator flows."
  ```

  Created task ID after execution: #47.
