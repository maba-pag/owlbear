# Switch move/pick to JSON Output, Remove board_context

> **Owning task:** #477 — Switch move/pick to JSON output, remove board_context tool
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

The mcp-kanban server currently returns plain text from `move_task` and `pick_task`, while `show_task` already returns JSON. This inconsistency means callers cannot parse the result of a move or pick structurally. Additionally, `board_context` wraps `kanban-md context` but is unused by any agent, skill, or orchestrator code — it should be removed per YAGNI.

**Decisions:**

1. Can `kanban-md move` and `kanban-md pick` accept `--json`?
2. What does the JSON output look like?
3. Is `board_context` used anywhere?
4. What's the impact of removing it?

## 2. Sources Studied

| # | Source | URL | Relevance | What |
|---|--------|-----|-----------|------|
| 1 | kanban-md v0.33.0 `move --help` | Local CLI | 1.0 | Confirms `--json` is a global flag, supported by `move` |
| 2 | kanban-md v0.33.0 `pick --help` | Local CLI | 1.0 | Confirms `--json` is a global flag, supported by `pick` |
| 3 | kanban-md JSON schemas | `skills/kanban-md/references/json-schemas.md` | .95 | Documents task object shape returned by `--json` |
| 4 | mcp-kanban server.py | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 1.0 | Current implementation; `show_task` already uses `--json` |
| 5 | Codebase grep for `board_context` | Workspace search | 1.0 | Zero usages outside mcp-kanban package + docs/task history |

## 3. Analysis

### 3.1 JSON Support Verification

Both `move` and `pick` accept `--json` as a global flag (kanban-md v0.33.0). Verified by `--help` output and live test.

**`move --json` output:** Returns full task JSON object with `"changed": true` field added. Same schema as `show --json`.

**`pick --json` output:** Returns picked task as JSON object (same schema). No-match returns an error JSON with `"code": "TASK_NOT_FOUND"`.

### 3.2 Implementation Complexity

| Change | LOC | Risk |
|--------|-----|------|
| `move_task`: add `"--json"` to args | 1 | None — `show_task` already does this |
| `pick_task`: add `"--json"` to args | 1 | None — same pattern as `show_task` |
| Remove `board_context` function + `@mcp.tool()` | -7 | None — zero consumers |
| Remove from `__all__` | -1 | None |
| Update tests | ~15 | Remove board_context tests, add JSON assertions for move/pick |
| Update SKILL.md | ~5 | Remove board_context row, update move/pick descriptions |

Total: ~4 LOC changed in server.py, ~20 LOC in tests + docs.

### 3.3 board_context Usage Audit

| Location | Present? | Nature |
|----------|----------|--------|
| Agent files (`agents/`) | No | Not referenced |
| Skill files (`skills/`) | mcp-kanban SKILL.md only | Documentation, not invocation |
| Instructions (`instructions/`) | No | Not referenced |
| Orchestrator (`packages/orchestrator/`) | No | Not referenced |
| `.vscode/mcp.json` | No | Not in tool registration |
| Test files | Yes | test_server.py only — tests the tool itself |
| Historical task/docs | Yes | Task #14 history + old research docs |

**Verdict:** `board_context` has zero runtime consumers. Safe to remove.

### 3.4 Consistency Gain

After this change, all read-producing tools return structured JSON:

| Tool | Before | After |
|------|--------|-------|
| `show_task` | JSON | JSON (unchanged) |
| `move_task` | Plain text | JSON |
| `pick_task` | Plain text | JSON |
| `list_tasks` | Compact text | Compact text (token-efficient, keep as-is) |
| `create_task` | Plain text | Plain text (confirmation, keep as-is) |
| `edit_task` | Plain text | Plain text (confirmation, keep as-is) |

## 4. Recommendation (.95 confidence)

**Proceed as described in AC.** This is a straightforward 2-line change in server.py (add `"--json"` to move/pick args), plus removal of 8 lines for `board_context`. Risk is near-zero:

- `--json` is a stable global flag, not a per-command experiment
- `show_task` already uses the identical pattern
- `board_context` has zero consumers

No decision request needed — single clear approach, no trade-offs.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Switch move/pick to JSON output, remove board_context — tests" --priority needed --status ideation --tags "scope:mcp,type:test,phase-2" --body "## Acceptance Criteria\n\n- [ ] Add --json assertion to move_task success test\n- [ ] Add --json assertion to pick_task success test\n- [ ] Remove board_context import and success test\n- [ ] Remove board_context from parametrized error test\n- [ ] All mcp-kanban tests pass\n\n## Context\nTDD RED phase for #477. Pattern: show_task test already asserts --json in args."
kanban\kanban-md.exe create "Switch move/pick to JSON output, remove board_context — implementation" --priority needed --status ideation --tags "scope:mcp,type:build,phase-2" --body "## Acceptance Criteria\n\n- [ ] move_task passes --json to _run_kanban (1-line change)\n- [ ] pick_task passes --json to _run_kanban (1-line change)\n- [ ] board_context function and @mcp.tool() decorator removed from server.py\n- [ ] board_context removed from __all__\n- [ ] All mcp-kanban tests pass (unit + integration)\n- [ ] ruff clean\n\n## Context\nGREEN phase for #477. Pattern: copy show_task's --json usage.\n\n## Design Notes\n- show_task already uses: _run_kanban(app_ctx, 'show', task_id, '--json')\n- move_task change: add '--json' after status arg\n- pick_task change: add '--json' after pick args\n- Remove board_context function (7 lines) + __all__ entry" --depends-on 482
kanban\kanban-md.exe create "Update mcp-kanban SKILL.md after board_context removal" --priority needed --status ideation --tags "scope:mcp,type:docs,phase-2" --body "## Acceptance Criteria\n\n- [ ] Remove board_context row from tools table\n- [ ] Update tool count in description (7 to 6)\n- [ ] Update move_task description to note JSON return\n- [ ] Update pick_task description to note JSON return\n\n## Context\nDocs update for #477. The SKILL.md currently lists 7 tools including board_context." --depends-on 483
```
