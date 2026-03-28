# AcpClient Test Strategy — RED Phase Mocking Approach

> **Owning task:** #94 — Test: AcpClient wrapper with timeouts and error classification
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #94 defines RED phase tests for AcpClient (#59). The AcpClient wraps the ACP
SDK's `ClientSideConnection` with per-method timeouts, error classification, and
cancellation. This research validates the AC, identifies a mocking approach, and flags
gaps. AcpClient does not exist yet — tests must fail on import.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | ACP SDK `client/connection.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/client/connection.py> | .95 |
| 2 | ACP SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | .90 |
| 3 | ACP SDK `examples/gemini.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | .85 |
| 4 | OwlBear `test_process_supervisor.py` | Local: `tests/test_process_supervisor.py` | .95 |
| 5 | OwlBear `test_error_classification.py` | Local: `v1/tests/test_error_classification.py` | .90 |
| 6 | OwlBear error handling research | Local: `docs/research/acp-error-handling-strategy.md` §3.3–3.5 | .95 |
| 7 | OwlBear decomposition research | Local: `docs/research/acp-client-library-decomposition.md` §3.3–3.5 | .85 |

## 3. Analysis

### 3.1 ClientSideConnection API Surface (Source 1)

The SDK's `ClientSideConnection` exposes these async methods relevant to AcpClient:

| Method | Signature (simplified) | Returns |
|--------|----------------------|---------|
| `initialize` | `(protocol_version, client_capabilities, client_info)` | `InitializeResponse` |
| `new_session` | `(cwd, mcp_servers)` | `NewSessionResponse` |
| `prompt` | `(prompt, session_id, message_id)` | `PromptResponse` |
| `cancel` | `(session_id)` | `None` (notification) |
| `close` | `()` | `None` |

All methods delegate to `Connection.send_request()` or `send_notification()`. They are
pure async — no I/O beyond the underlying JSON-RPC pipe. This makes mocking trivial.

### 3.2 Mocking Approach — AsyncMock with side_effect

**Strategy (.90 confidence):** Create `AsyncMock(spec=ClientSideConnection)` — every
method becomes an `AsyncMock` automatically. Test behavior via `side_effect`:

| Test scenario | Mock setup | Assertion |
|--------------|------------|-----------|
| Timeout on method X | `side_effect=asyncio.TimeoutError` on patched `wait_for` | Verify exception / cancel call |
| RequestError classification | `side_effect=RequestError(code, msg)` | Verify error mapped correctly |
| BrokenPipeError | `side_effect=BrokenPipeError()` | Verify TRANSIENT classification |
| EOF on stdout | `side_effect=ConnectionError("EOF")` or empty read | Verify TRANSIENT classification |
| Successful call | `return_value=MagicMock()` | Verify return value passed through |

This follows the established test_process_supervisor.py pattern (Source 4):
`_patch_spawn()` uses `patch()` with `AsyncMock(return_value=proc)`.

### 3.3 Timeout Verification — Two Approaches

| Approach | Pros | Cons | Source |
|----------|------|------|--------|
| Patch `asyncio.wait_for` | Fast, deterministic, no real delays | Tests the patch, not real timeout | Source 4 |
| Inject short timeouts (0.01s) | Tests real `asyncio.wait_for` flow | Slower, timing-sensitive | gemini.py (Source 3) |

**Recommendation (.85 confidence):** Use the patch approach for consistency with
test_process_supervisor.py (Source 4), which already patches `asyncio.wait_for` with
`side_effect=asyncio.TimeoutError`. The timeout _values_ (30s/15s/300s) can be verified
by asserting the `timeout` kwarg passed to the patched `wait_for`.

### 3.4 Cancel Verification

After `asyncio.TimeoutError` on `prompt`, AcpClient should call `conn.cancel(session_id)`.
Test pattern:

```
mock_conn.prompt.side_effect = asyncio.TimeoutError  # via patched wait_for
client.prompt(...)  # wrapped call
mock_conn.cancel.assert_awaited_once_with(session_id=session_id)
```

The SDK's `cancel()` method sends a JSON-RPC notification (Source 1) — no response
expected. This makes the assertion straightforward.

### 3.5 AC Gap Analysis

| AC Item | Status | Gap? |
|---------|--------|------|
| Test: initialize wrapped with 30s timeout | Valid | No |
| Test: new_session wrapped with 15s timeout | Valid | No |
| Test: prompt wrapped with 300s timeout | Valid | No |
| Test: RequestError caught and classified | Valid | No |
| Test: session/cancel sent on TimeoutError | Valid | No |
| Test: BrokenPipeError as TRANSIENT | Valid | No |
| Test: EOF on stdout as TRANSIENT | Valid | **See below** |
| All tests use mocked ClientSideConnection | Valid | No |

**EOF detection gap:** The AC says "EOF on stdout detected as TRANSIENT." At the
AcpClient wrapper level, EOF manifests as either `ConnectionError` from the SDK's
receive loop or an empty read on the stream reader. The AcpClient catches this at
the method call boundary. The test should raise `ConnectionError("EOF")` as the
`side_effect` — this matches Python's exception hierarchy where EOF conditions on
sockets/pipes surface as `ConnectionError` subclasses (Sources 1, 6).

**Missing AC item:** Task #59 AC includes "Sends session/cancel on timeout **or
external CancelSignal**." No corresponding test in #94 AC for external CancelSignal.
This should be added.

### 3.6 Module Path

The decomposition research (Source 7, §3.5) noted that `packages/orchestrator/`
builds as package `owlbear`, not `owlbear_orchestrator`. The test import should match
the actual module structure. Current `test_process_supervisor.py` uses
`owlbear_orchestrator.process_supervisor`, which is inconsistent — the test-writer
should verify the actual package name when writing tests.

## 4. Recommendation (.85 confidence)

The AC for #94 is well-specified and achievable. Two refinements:

1. **Add test for external CancelSignal** — #59 AC covers this but #94 AC omits it.
   Pattern: set a `CancelSignal` before calling `prompt`, verify `cancel()` called.
2. **EOF test approach** — use `side_effect=ConnectionError("EOF")` on mock methods
   to simulate SDK behavior on pipe close.

No new components or dependencies needed. All tests use `unittest.mock` + `pytest-asyncio`.

## 5. Follow-up Tasks

No new tasks beyond the AC refinement noted above. Task #94 is ready for architect
review with the suggested AC addition for CancelSignal testing.
