# AcpClient Parameter Forwarding

> **Owning task:** #147 — Fix AcpClient wrapper API to forward required SDK parameters
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #147 addresses the critical gap identified in `acp-client-wrapper-validation.md`
§3.3: the AcpClient wrapper's three core methods (`initialize`, `new_session`,
`prompt`) accept no SDK-required parameters, meaning they would raise `TypeError`
at runtime. This research validates the AC, determines the correct forwarding
pattern, and specifies the testing approach.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | ACP SDK `connection.py` (v0.11.2) | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/client/connection.py> | .95 |
| 2 | ACP SDK `examples/gemini.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | .90 |
| 3 | ACP SDK `meta.py` (`PROTOCOL_VERSION`) | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/meta.py> | .85 |
| 4 | ACP SDK `helpers.py` (`text_block`) | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/helpers.py> | .80 |
| 5 | Prior research §3.3 | `docs/research/acp-client-wrapper-validation.md` | .95 |

## 3. Analysis

### 3.1 Exact SDK Signatures (Source 1)

| Method | Required params | Optional params |
|--------|----------------|-----------------|
| `initialize()` | `protocol_version: int` | `client_capabilities: ClientCapabilities \| None`, `client_info: Implementation \| None` |
| `new_session()` | `cwd: str` | `mcp_servers: list[HttpMcpServer \| SseMcpServer \| McpServerStdio] \| None` |
| `prompt()` | `prompt: list[ContentBlock]`, `session_id: str` | `message_id: str \| None` |

`ContentBlock` = `TextContentBlock | ImageContentBlock | AudioContentBlock | ResourceContentBlock | EmbeddedResourceContentBlock` (Source 4, `helpers.py`).

`PROTOCOL_VERSION = 1` (Source 3). The `gemini.py` example imports and passes this
constant directly (Source 2, L244).

### 3.2 Forwarding Pattern Comparison

| Criterion | Explicit params (.85) | `**kwargs` pass-through (.55) |
|-----------|-----------------------|-------------------------------|
| Type safety | Full — IDE autocomplete, mypy checks | None — callers must know SDK internals |
| Self-documenting | Yes — wrapper signature shows API | No — must read SDK docs |
| SDK coupling | Moderate — param names tied to SDK | Low — forwards blindly |
| Bug prevention | High — catches mismatches at dev time | Low — defers to runtime |
| KISS alignment | Yes — 3 methods, ~5 required params | N/A — simpler code but shifts complexity to callers |
| Maintenance cost | Low — SDK pre-1.0 but core params are stable | Lower — auto-forwards new params |

**Verdict:** Explicit params (Approach A). The wrapper is a core interface used by the
orchestrator dispatch loop — type safety at the boundary prevents the exact class of
bug we found (Source 5 §3.3). Only 3 methods with ~5 required params total; not
onerous. Optional SDK params use `**kwargs` for forward-compatibility.

Usage from `gemini.py` (Source 2) confirms the pattern:
```python
await conn.initialize(protocol_version=PROTOCOL_VERSION, client_capabilities=...)
await conn.new_session(cwd=os.getcwd(), mcp_servers=[])
await conn.prompt(session_id=session_id, prompt=[text_block(line)])
```

### 3.3 Testing Strategy

Current tests patch `asyncio.wait_for`, which bypasses the actual SDK call and
cannot verify parameter forwarding. New tests must:

1. **Not patch `wait_for`** — let the call flow through to the mock `conn`
2. **Set mock return values** — `conn.initialize.return_value = MagicMock()`
3. **Assert mock called with expected params** — `conn.initialize.assert_awaited_once_with(protocol_version=1, ...)`

This tests the forwarding path end-to-end through the wrapper, not just the
timeout wrapping. Existing 13 tests (timeout + error classification) remain valid
and should continue passing unchanged.

### 3.4 AC Validation

| AC line | Valid? | Notes |
|---------|--------|-------|
| `initialize()` accepts and forwards `protocol_version` | Yes | Required by SDK (Source 1). Add optional `client_capabilities`, `client_info` via `**kwargs` |
| `new_session()` accepts and forwards `cwd`, `mcp_servers` | Yes | `cwd` required, `mcp_servers` optional with `None` default (Source 1) |
| `prompt()` accepts and forwards prompt content blocks | Yes | `prompt: list[ContentBlock]` is required. `session_id` already forwarded. Add optional `message_id` via `**kwargs` |
| Existing 13 tests still pass | Yes | Signature additions are backwards-compatible (all new params have defaults or are appended) |
| New tests verify params forwarded to conn methods | Yes | Tests must NOT patch `wait_for` — verify mock conn calls directly |

**One refinement:** AC line 2 should clarify that `mcp_servers` is optional (`None` default).
The wrapper should match the SDK default, not force callers to always pass it.

## 4. Recommendation (.90 confidence)

Use explicit required params + `**kwargs` for optional. Estimated ~15 LOC change
in `acp_client.py` + ~30 LOC for 3 new forwarding tests. The AC is correct and
complete. No blocking issues.

**Risk:** SDK schema v0.11.2 is recent (4 days old per commit). The `>=0.9.0,<1.0.0`
pin in `pyproject.toml` may need updating if param names change. Mitigated: core
params (`protocol_version`, `cwd`, `prompt`) are protocol-fundamental.

## 5. Follow-up Tasks

Task #147 AC is already well-defined — no new tasks needed. The task is ready for
the architect gate at `backlog`.
