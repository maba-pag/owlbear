# ACP Hello-World Script Implementation Guide

> **Owning task:** #45 — Build ACP hello-world script
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #45 asks for a minimal Python script (~50 LOC) that spawns the Copilot CLI
as an ACP agent via stdio, creates a session, sends a prompt, prints the streamed
response, and cleans up. This research validates technical feasibility and
documents the exact API patterns the builder should follow.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | ACP Python SDK (v0.9.0) | https://pypi.org/project/agent-client-protocol/ | .95 |
| 2 | SDK examples/client.py | https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py | .95 |
| 3 | SDK examples/gemini.py | https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py | .90 |
| 4 | SDK quickstart guide | https://agentclientprotocol.github.io/python-sdk/quickstart/ | .85 |
| 5 | Copilot CLI ACP server docs | https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server | .95 |
| 6 | Copilot CLI about page | https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli | .85 |
| 7 | rest-acp (OpenAI wrapper) | https://github.com/iot2020/rest-acp | .70 |
| 8 | mcp-copilot-acp (TS bridge) | https://github.com/bsmi021/mcp-copilot-acp | .75 |

## 3. Analysis

### 3.1 API Choice: `connect_to_agent` vs `spawn_agent_process`

| Criterion | `connect_to_agent` (.90) | `spawn_agent_process` (.60) |
|-----------|--------------------------|----------------------------|
| Works with non-Python binaries | Yes — accepts stdin/stdout pipes | No — expects `sys.executable` + script path |
| Process lifecycle control | Manual (caller manages subprocess) | Automatic (context manager) |
| Used by SDK for Copilot/Gemini | Yes (client.py, gemini.py) | No (duet.py only, Python-to-Python) |
| Complexity | ~10 more LOC for spawn+cleanup | Simpler, but wrong fit |

**Verdict:** Use `connect_to_agent()` — it's the only option that works with
the `copilot` binary. Both SDK examples targeting external CLIs (client.py,
gemini.py) use this pattern.

### 3.2 Copilot CLI Invocation

Confirmed by GitHub docs (source 5) and rest-acp (source 7):

```
copilot --acp --stdio --allow-all-tools
```

- `--acp` enables ACP server mode
- `--stdio` selects stdio transport (default with `--acp`, explicit for clarity)
- `--allow-all-tools` auto-approves all permission requests (no interactive prompts)

**Windows note:** Resolve via `shutil.which("copilot")` to handle `.exe` and
PATH variations; gemini.py uses this pattern for `gemini` binary resolution.

### 3.3 Implementation Pattern (from gemini.py + client.py)

| Step | API Call | Notes |
|------|----------|-------|
| 1. Spawn | `asyncio.create_subprocess_exec("copilot", ...)` | stdin=PIPE, stdout=PIPE |
| 2. Connect | `connect_to_agent(client, proc.stdin, proc.stdout)` | Wires JSON-RPC over stdio |
| 3. Initialize | `conn.initialize(protocol_version=PROTOCOL_VERSION, ...)` | Negotiates capabilities |
| 4. Session | `conn.new_session(cwd=os.getcwd(), mcp_servers=[])` | Returns session_id |
| 5. Prompt | `conn.prompt(session_id=..., prompt=[text_block("...")])` | Streams via session_update |
| 6. Cleanup | `_shutdown(proc, conn)` | close conn, terminate, wait(5s), kill |

### 3.4 Client Implementation (minimal)

The `Client` interface requires these methods. For the hello-world script:

| Method | Implementation |
|--------|---------------|
| `session_update` | Print `AgentMessageChunk` text content; ignore other update types |
| `request_permission` | Return `DeniedOutcome(cancelled)` — shouldn't fire with `--allow-all-tools` |
| `write_text_file` | Raise `RequestError.method_not_found` |
| `read_text_file` | Raise `RequestError.method_not_found` |
| `create_terminal` | Raise `RequestError.method_not_found` |
| Others (5 terminal methods) | Raise `RequestError.method_not_found` |

### 3.5 Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| ACP support is public preview | Medium | Pin SDK version; wrap breaking changes in adapter |
| `copilot` not on PATH | Low | `shutil.which()` with clear error message |
| `copilot` not authenticated | Medium | Detect init error code, print auth instructions |
| Process hangs on exit | Low | `wait_for(timeout=5)` then `kill()` (gemini.py pattern) |
| Windows process cleanup | Low | `contextlib.suppress(ProcessLookupError)` on wait |

## 4. Recommendation (.90 confidence)

Follow the gemini.py pattern with these adaptations:

1. **Simple one-shot mode** — send a single hardcoded prompt, print response, exit.
   No interactive loop needed for hello-world.
2. **~50-60 LOC** — Client class (~25 LOC), main function (~25 LOC), shutdown
   helper (~10 LOC). Matches the v2 architecture target.
3. **Resolve the Copilot binary** via `shutil.which("copilot")` for cross-platform.
4. **Stub all fs/terminal methods** with `RequestError.method_not_found` — they
   won't fire for a simple text prompt with `--allow-all-tools`.

**Dependency chain:** #7 (monorepo skeleton) must be done first to create
`packages/orchestrator/examples/`. #46 (add SDK dep) must be done to make
`from acp import ...` available. Set `depends_on: [7, 46]` on task #45.

## 5. Follow-up Tasks

No new tasks needed — #45, #46, and #47 (from ACP research #1) cover the scope.
Task #45 needs `depends_on` updated to `[7, 46]` so the pipeline respects the
dependency chain.
