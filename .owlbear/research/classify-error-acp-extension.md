# Extending classify_error for ACP RequestError Codes

> **Owning task:** #60 — Extend classify_error for ACP RequestError codes
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #60 extends the existing `classify_error()` function in `v1/src/owlbear/core/errors.py`
to handle ACP SDK `RequestError` exceptions. The error code-to-category mapping was
designed in `docs/research/acp-error-handling-strategy.md` §3.1/§3.5 (task #47). This
research validates the implementation approach against the existing codebase and SDK.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | JSON-RPC 2.0 specification | <https://www.jsonrpc.org/specification> | .95 |
| 2 | ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | .95 |
| 3 | MCP Python SDK `exceptions.py` | <https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/shared/exceptions.py> | .80 |
| 4 | OwlBear v1 `errors.py` | `v1/src/owlbear/core/errors.py` | .95 |
| 5 | OwlBear ACP error strategy | `docs/research/acp-error-handling-strategy.md` §3.1, §3.5 | .95 |
| 6 | OwlBear architecture standards | `.github/skills/architecture-standards/SKILL.md` | .85 |

## 3. Analysis

### 3.1 RequestError Interface (Sources 2, 3)

Both ACP and MCP SDKs expose `code: int` on their error classes (Sources 2, 3).
The ACP SDK's `RequestError(code, message, data=None)` constructor stores `code` as
an instance attribute. Factory methods map to standard JSON-RPC codes (Source 1):

| Factory method | Code | JSON-RPC name |
|---------------|------|---------------|
| `parse_error()` | -32700 | Parse error |
| `invalid_request()` | -32600 | Invalid Request |
| `method_not_found()` | -32601 | Method not found |
| `invalid_params()` | -32602 | Invalid params |
| `internal_error()` | -32603 | Internal error |
| `auth_required()` | -32000 | Auth required (ACP-specific) |
| `resource_not_found()` | -32002 | Resource not found (ACP-specific) |

### 3.2 Code-to-Category Mapping

| Code | ErrorCategory | Rationale | Sources |
|------|---------------|-----------|---------|
| -32700 | PERMANENT | Malformed JSON — SDK/process bug | 1, 5 |
| -32600 | PERMANENT | Invalid RPC structure — SDK bug | 1, 5 |
| -32601 | PERMANENT | Wrong method name — code bug | 1, 5 |
| -32602 | PERMANENT | Wrong params — code bug | 1, 5 |
| -32603 | TRANSIENT | Agent internal failure — may recover | 1, 5 |
| -32000 | AUTH | Copilot CLI needs re-authentication | 2, 5 |
| -32002 | TOOL_SEMANTIC | Stale session/resource — model can retry | 2, 5 |
| Unknown | PERMANENT | Safe default for undefined codes | 1 |

**Note:** The AC lists `-32700/-32601/-32602: PERMANENT` but omits `-32600`. The SDK
has `invalid_request(-32600)` which should also map to PERMANENT per JSON-RPC spec
(Source 1). The builder should include -32600 in the implementation for completeness.

### 3.3 BrokenPipeError — Already Handled

`BrokenPipeError` inherits from `ConnectionError` in Python's exception hierarchy:
`BrokenPipeError -> ConnectionError -> OSError -> Exception`. The existing
`classify_error` already classifies `ConnectionError` as TRANSIENT (Source 4, line ~100).
No code change needed — just an explicit test to document this behavior.

### 3.4 Dependency: acp Package Not Installed

The `acp` package is **not** in `v1/pyproject.toml` dependencies (checked all groups).
The existing codebase uses conditional imports for optional deps (e.g., `openai` at the
module level with `try/except ImportError`, Source 4). The same pattern applies here:

```python
try:
    from acp.exceptions import RequestError as AcpRequestError
except ImportError:
    AcpRequestError = None
```

When `acp` is not installed, the `isinstance` check is skipped and `RequestError`
exceptions fall through to the default PERMANENT classification.

**Decision needed:** Should `acp` be added as an optional dependency (e.g., `acp` extra
group), or remain purely conditional? Since the v2 orchestrator will require `acp`, it
should be an optional dep under a new extras group (e.g., `orchestrator`).

### 3.5 Implementation Approach

Insert the `RequestError` branch in `classify_error` **after** `HTTPStatusError` and
**before** the transient network block. Use a dict lookup for code mapping:

```python
_ACP_ERROR_CODES: dict[int, ErrorCategory] = {
    -32700: ErrorCategory.PERMANENT,  # Parse error
    -32600: ErrorCategory.PERMANENT,  # Invalid Request
    -32601: ErrorCategory.PERMANENT,  # Method not found
    -32602: ErrorCategory.PERMANENT,  # Invalid params
    -32603: ErrorCategory.TRANSIENT,  # Internal error
    -32000: ErrorCategory.AUTH,  # Auth required
    -32002: ErrorCategory.TOOL_SEMANTIC,  # Resource not found
}
```

Unknown codes default to PERMANENT (safe — don't retry undefined errors).
Architecture standards (Source 6) require extending the existing taxonomy, not
creating parallel hierarchies.

### 3.6 Testing Strategy

| Test case | Input | Expected |
|-----------|-------|----------|
| Parse error | `RequestError(-32700, "...")` | PERMANENT |
| Invalid request | `RequestError(-32600, "...")` | PERMANENT |
| Method not found | `RequestError(-32601, "...")` | PERMANENT |
| Invalid params | `RequestError(-32602, "...")` | PERMANENT |
| Internal error | `RequestError(-32603, "...")` | TRANSIENT |
| Auth required | `RequestError(-32000, "...")` | AUTH |
| Resource not found | `RequestError(-32002, "...")` | TOOL_SEMANTIC |
| Unknown ACP code | `RequestError(-32099, "...")` | PERMANENT |
| BrokenPipeError | `BrokenPipeError()` | TRANSIENT |
| acp not installed | Mock `AcpRequestError = None` | Falls through |

Tests should use real `RequestError` objects (the constructor is trivial: no I/O,
no network). Add a `TestAcpErrors` class to `v1/tests/test_error_classification.py`.

## 4. Recommendation (.90 confidence)

Implement as a ~30 LOC change to `v1/src/owlbear/core/errors.py`:

1. Conditional import of `acp.exceptions.RequestError` (like `openai` pattern)
2. Module-level `_ACP_ERROR_CODES` dict mapping codes to categories
3. Single `isinstance` branch in `classify_error` with dict lookup + PERMANENT default
4. Add `acp` as optional dependency under new `orchestrator` extras group

Low risk: the `RequestError.code` integer interface follows JSON-RPC 2.0 standard
(Source 1), which is stable. The conditional import means no breakage when `acp`
is absent.

## 5. Follow-up Tasks

No new follow-up tasks needed — task #60 already has concrete AC covering the full
implementation scope. The additional finding (include -32600 in the mapping) is a
refinement to the existing AC, not a separate task.
