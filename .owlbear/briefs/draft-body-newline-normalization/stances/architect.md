# Architectural Stance — Body Newline Normalization

## Architectural Position

The normalize-and-notify pattern is **structurally sound** and fits cleanly into the existing MCP server boundary. The design requires one named helper, five call-site additions, an ordering-aware guidance append, and documentation in tool metadata. No engine or storage changes.

The pattern's main weakness is not structural but semantic: there is no clean escape convention for intentional literal `\n` because the corrupted and intentional cases are byte-identical. The guidance message provides transparency, not a functional retry path. This is an acceptable trade-off given the 16%+ corruption rate and the rarity of intentional literal `\n` in practice.

## Structural Reasoning

### 1. Named helper in server.py

```python
def _normalize_escaped_newlines(text: str) -> str:
    return text.replace("\\n", "\n")
```

Lives in `server.py` alongside `_coerce_to_str()`. Both are boundary-level input fixes for agent misbehavior. The function is a one-liner but naming it documents intent and centralizes the operation for all 5 call sites. No tuple return — detect normalization at the call site with `"\\n" in text` before calling the helper.

NOT in `guidance.py`. Normalization is input sanitation, not task-state feedback.

### 2. All 5 parameters, explicitly

The normalization applies to every text body parameter at MCP ingress:

| Tool | Parameter |
|------|-----------|
| `create_task` | `body` |
| `edit_task` | `body` |
| `edit_task` | `append_body` |
| `end_work` | `note` |
| `create_dr` | `body` |

Each call site follows the same pattern:
```python
normalized = "\\n" in body  # or append_body, note
body = _normalize_escaped_newlines(body)
```

### 3. Guidance append ordering is critical

The existing guidance wiring in server.py uses an empty-check guard:
```python
if not result.guidance:
    result.guidance = collect_guidance(...)
```

The normalization append MUST come AFTER this block. If before, it populates the guidance list, which prevents `collect_guidance()` from running — silently suppressing DR reminders and commit reminders.

Correct ordering:
```python
# 1. Engine call (with normalized input)
result = _to_single_task_response(record)
# 2. Existing guidance wiring (unchanged)
with contextlib.suppress(Exception):
    if not result.guidance:
        result.guidance = collect_guidance(...)
# 3. Normalization notice (new — always appended when applicable)
if body_was_normalized:
    result.guidance.append("⚠️ Body contained literal \\n sequences — normalized to actual newlines.")
```

This is not a second guidance assembly path. It is an additional `.append()` after existing sources have already populated the list.

### 4. create_dr: special-case guidance key

`create_dr` returns `dict[str, object]`, not `SingleTaskResponse`. Add a `"guidance"` key:
```python
response = {"created": True, "path": relative_path, "guidance": []}
if body_was_normalized:
    response["guidance"].append("⚠️ Body contained literal \\n sequences — normalized to actual newlines.")
```

This is a new field on the dict — not reuse of the existing guidance contract. Acceptable because: (a) `create_dr` writes human-facing files where silent mutation would be visible, (b) the addition is 3 lines, (c) it aligns the notification story across all 4 tools.

### 5. create_task already has guidance wiring from AgentView

`create_task` in `agent_view.py` already returns guidance (body size warning). The MCP tool passes it through. No new wiring needed — just the append after the engine call. But `create_task` currently lacks the MCP-level `collect_guidance()` fallback that `edit_task`/`move_task`/`end_work` have. For normalization purposes this doesn't matter — the append works on whatever list AgentView returned.

### 6. Documentation in tool metadata

Two surfaces:
- **Tool docstrings** — add a sentence: "Literal \\n sequences in text parameters are normalized to actual newlines."
- **Per-parameter description patches** — the server already has a parameter description patching surface. Add normalization behavior to the affected parameter descriptions.

Without this, agents cannot learn the normalization contract from tool metadata.

## Key Trade-offs

| Dimension | Assessment |
|-----------|------------|
| **Blast radius** | Minimal — one file changed (server.py), one response shape extended (create_dr dict), test expectations updated |
| **False positives** | Real but rare. Intentional literal `\n` in task bodies exists (confirmed in archive). No clean escape convention possible at the string level — the guidance message provides transparency, not a retry mechanism |
| **Guidance ordering** | The append-after pattern is safe but depends on positional discipline. An implementer who puts the append before the empty-check guard will suppress existing reminders |
| **Maintenance** | Future tools with text body params must add normalization. Same maintenance pattern as existing `collect_guidance()` wiring — no worse, no better |
| **Escape convention** | Research-notes.md correctly identified the circularity: triple-escaping produces the same byte sequence after double-unescape. The honest position is that there is no ingress-level escape path. Markdown code fences preserve visual display but not raw bytes. Documenting this limitation is better than promising a mechanism that doesn't work |

## Warnings

1. **Guidance ordering is the implementation landmine.** The append must be positionally after the `if not result.guidance` block. This is not obvious from reading the code and should be called out explicitly in task AC.

2. **Test surface is broader than the diff.** MCP mutation tests pin exact forwarded body strings and exact guidance lists. Tests that send `\\n` in body text will need updating. Tests that assert exact guidance lists will need updating. This should be scoped in the task, not discovered during implementation.

3. **The escape convention question is unresolvable at the string level.** Any attempt to define "triple-escape preserves literal `\n`" will fail because the corrupted case and the escape case produce the same bytes. The task should document this limitation rather than defer it as a "future problem."

4. **`create_dr` dict shape change needs downstream check.** Any consumer that asserts exact dict equality on `create_dr` responses will break.

## Confidence

**0.80** — Strong structural fit. Two Critic cycles hardened the ordering concern and false-positive assessment. The remaining uncertainty is whether the escape convention limitation matters enough in practice to affect the design choice (I believe it doesn't, but the Critic's evidence that intentional `\n` exists in the corpus prevents me from dismissing it entirely).
