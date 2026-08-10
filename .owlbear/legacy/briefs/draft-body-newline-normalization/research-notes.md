# Research Notes — Body Newline Normalization

## Verified Findings

### Guidance system infrastructure
- `SingleTaskResponse.guidance: list[str]` field exists and is returned to agents on all mutation responses
- `collect_guidance(operation, before, after, **kwargs)` is the extension point — already handles operation-specific messages
- Current guidance examples: block DR reminders, commit reminders, status-skip warnings
- All guidance injection uses `contextlib.suppress(Exception)` + null-check pattern
- `create_dr` returns `dict[str, object]` (no guidance field) — normalization feedback would need alternative approach there

### Normalization surface
- 5 parameters across 4 tools: `body` (create_task, edit_task, create_dr), `append_body` (edit_task), `note` (end_work)
- Existing normalization precedent: `body_parser.py` already normalizes CRLF → LF at parse time
- No existing input sanitization at the MCP server layer — body text passes through as-is
- Body size validation (500 KB max) exists in engine, not MCP

### Testing infrastructure
- Test fixtures: `_make_board()`, `_make_ctx()`, `_make_single_task_response()`
- Integration pattern: real board + real engine; check persisted task state
- Error routing: mocked side effects on view methods
- Key test files: `tests/test_mcp_kanban.py`, `tests/test_mcp_kanban_1451.py`

### The double-escape problem at byte level
- LLM sends JSON `"body": "line1\\nline2"` → JSON parse → `line1\nline2` (two chars: backslash, n)
- Correct would be: `"body": "line1\nline2"` → JSON parse → `line1` + newline + `line2`
- An intentional literal `\n` uses the SAME encoding as the bug — indistinguishable

## Candidate Implications

- The normalize-and-notify approach maps cleanly onto existing `collect_guidance()` — add a kwarg like `normalization_applied=True` or track replacements in a pre-processing step
- `create_dr` is a special case — returns `dict`, not `SingleTaskResponse` — may need the guidance message in a different response key, or could be skipped (DR bodies are short, less likely to have bulk double-escaping)
- The CRLF precedent in `body_parser.py` validates the "normalize at ingress" pattern — it's already done for a different whitespace normalization
- Triple-escape convention (for intentional literal `\n`) would need documentation in tool descriptions — that's where agents learn parameter contracts
- The existing `_coerce_to_str()` pattern shows the server already handles agent misbehavior at the boundary (int→str coercion for stale schemas)

## Open Research Questions

1. **What should the triple-escape convention actually be?** If `\\n` → newline, what encoding preserves literal `\n`? Options: `\\\n` in JSON (→ `\\n` after parse → `\n` after normalization? No, that's circular), or a dedicated escape like `{{newline_literal}}` placeholder, or just accept the trade-off.
2. **Should `create_dr` get normalization?** It returns `dict` without guidance — the agent won't get feedback. Worth it anyway for correctness?
3. **Is `\t` or `\\` corruption also occurring?** First-principles challenger raised this. A quick grep of existing task files would answer whether this is newline-specific or broader.
4. **Should the tool description document the normalization behavior?** Agents read tool descriptions — adding "literal \\n sequences are normalized to newlines" would set correct expectations.
