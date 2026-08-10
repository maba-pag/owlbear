# Brief — Body Newline Normalization

## Problem

LLM agents frequently double-escape newlines in MCP tool call JSON arguments. The JSON string `"\\n"` deserializes to the literal two-character sequence `\n` (0x5C, 0x6E) instead of an actual newline (0x0A). This corrupts 16.5% of kanban task files, breaking search/grep tooling that expects newline-delimited markdown.

The problem is ongoing, newline-specific (`\t`/`\\` corruption does not occur), and cannot be fixed upstream because LLM tool-calling serialization is non-deterministic.

## Solution

Three-step escape-protected normalization at the MCP kanban server ingress boundary, applied to all text body parameters. When normalization occurs, the response includes a guidance message referencing the documented escape convention.

### Normalization Function

```python
_SENTINEL = "\x00ESCAPED_NEWLINE\x00"

def _normalize_escaped_newlines(text: str) -> tuple[str, bool]:
    """Normalize literal \\n to actual newlines. Protect \\\\n escape convention."""
    protected = text.replace("\\\\n", _SENTINEL)
    normalized = protected.replace("\\n", "\n")
    result = normalized.replace(_SENTINEL, "\\n")
    return result, result != text
```

### Affected Parameters

| Tool | Parameter |
|------|-----------|
| `create_task` | `body` |
| `edit_task` | `body` |
| `edit_task` | `append_body` |
| `end_work` | `note` |
| `create_dr` | `body` |

### Escape Convention

| Agent intent | JSON encoding | After parse | After normalization |
|---|---|---|---|
| Newline (correct) | `\n` | newline (0x0A) | Unchanged |
| Newline (bugged) | `\\n` | `\n` (0x5C, 0x6E) | Newline (0x0A) — fixed |
| Literal `\n` | `\\\\n` | `\\n` (0x5C, 0x5C, 0x6E) | `\n` (0x5C, 0x6E) — preserved |

### Guidance Integration

- For `create_task`, `edit_task`, `end_work`: append to `result.guidance` AFTER the existing `if not result.guidance` block (preserving existing DR/commit reminders)
- For `create_dr`: add optional `guidance` key to the dict response
- Message: `"Body contained literal \\n sequences — normalized to actual newlines. Use \\\\n in JSON to preserve intentional literal \\n."`

### Tool Metadata

Add normalization behavior + escape convention to the affected tool descriptions (docstrings and/or parameter descriptions).

## Scope

- **In scope:** Prevention — normalize text inputs at MCP server ingress
- **Out of scope:** Archive remediation, `\r\n` normalization, non-body parameters, engine/storage changes

## Constraints

1. Helper lives in `server.py` alongside `_coerce_to_str()` — boundary-level input fix, not shared utility
2. Normalization applied exactly once per tool invocation (at the handler level)
3. Guidance append MUST be positionally after the existing `if not result.guidance` block — ordering violation suppresses existing reminders
4. Non-idempotent by design — re-edit by unaware agents may degrade preserved literals (documented limitation, not a bug)
5. Sentinel collision risk is near-zero (null bytes cannot arrive through JSON MCP transport)

## Acceptance Criteria

1. `_normalize_escaped_newlines()` exists in `server.py`, implements three-step protect/normalize/restore, returns `(text, changed)` tuple
2. All 5 text body parameters are normalized before engine calls
3. When `changed=True`, guidance message is appended to the response (all 4 tools)
4. `create_dr` response dict includes optional `guidance` key when normalization occurs
5. Guidance append is positionally after existing guidance wiring (test: existing DR/commit reminders still fire when normalization also occurs)
6. Escape convention works: `\\\\n` in JSON → `\\n` after parse → preserved as `\n` in stored file
7. Tool descriptions document normalization behavior and escape convention
8. Existing MCP kanban tests pass without modification (except pinned body assertions that now receive normalized content)

## Known Limitations

- **Non-idempotent lifecycle:** Intentional `\n` preserved on first write degrades if an unaware agent later full-rewrites the body via `edit_task`. This is accepted — the escape convention provides first-write fidelity only.
- **Convention depends on agent cooperation:** Agents that don't read tool descriptions won't use the escape convention. The normalization still fixes the 16.5% corruption rate regardless.

## Implementation Notes

- Single file change: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- Test file: `tests/test_mcp_kanban.py` (or new file for normalization-specific tests)
- Estimated diff: ~40 lines (helper + 5 call sites + guidance appends + create_dr key)
- No dependency changes
