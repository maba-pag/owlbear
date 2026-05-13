# Body Newline Normalization in MCP Server

## Problem

16% of task files (280/1717) contain literal `\n` characters in their bodies instead of actual newlines. This happens when AI agents double-escape newlines in MCP tool call JSON arguments — sending `\\n` (which JSON deserializes to the two-character string `\n`) instead of `\n` (which JSON deserializes to an actual newline).

The kanban engine correctly passes body strings through without transformation. The problem originates in LLM tool-calling behavior and cannot be fixed upstream.

Total occurrences: 4758 literal `\n` across 280 files (all in archive, zero in active tasks).

## Proposed Fix

Add input normalization at the MCP server boundary (`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`) for text parameters that represent markdown content:

- `body` in `create_task` and `edit_task`
- `append_body` in `edit_task`
- `note` in `end_work`
- `body` in `create_dr`

### Normalization

Replace literal two-character `\n` sequences with actual newline characters. For markdown task bodies, there is no legitimate use case for literal backslash-n.

```python
def _normalize_body(text: str | None) -> str | None:
    if text is None:
        return None
    return text.replace("\\n", "\n")
```

### Scope

- Applied at MCP server layer only (system boundary input sanitization)
- Engine and storage remain untouched
- No schema changes
- Backward-compatible: bodies without literal `\n` are unaffected
- Optional: one-time migration script to fix existing archive files

### Alternatives considered

- Fix in engine: wrong layer — engine shouldn't know about MCP serialization quirks
- Fix in agents: can't control LLM behavior reliably
- Do nothing: 16% corruption rate is too high to ignore
