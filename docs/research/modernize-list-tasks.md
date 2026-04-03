# Modernize list_tasks: lean JSON, archived, limit, blocked tri-state

> **Owning task:** #472 — Modernize list_tasks: lean JSON, archived, limit, blocked tri-state
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

The `list_tasks` MCP tool currently returns `--compact` text output and uses a string-based `block_filter` parameter. This limits downstream JSON processing and adds friction for agents that need structured data. The task asks: what changes are needed to add `archived`, `limit`, `reverse`, and `blocked` tri-state parameters, and switch to lean JSON output?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| kanban-md v0.33.0 `list --help` | Local binary | 1.0 — authoritative CLI flag reference |
| kanban-md `list --json` output | Local binary | 1.0 — actual JSON schema with all fields |
| mcp-kanban server.py (current) | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L100-133 | 1.0 — current implementation |
| mcp-kanban test_server.py | `packages/mcp-kanban/tests/test_server.py` L170-416 | 1.0 — existing test patterns |
| FastMCP tool registration docs | https://gofastmcp.com/servers/fastmcp#tools | 0.8 — tool parameter typing conventions |
| Python `Optional[bool]` typing | https://docs.python.org/3/library/typing.html#typing.Optional | 0.7 — tri-state pattern reference |

## 3. Analysis

### 3.1 CLI flag availability (kanban-md v0.33.0)

All required flags already exist in the CLI:

| Flag | kanban-md support | Currently exposed in MCP |
|------|-------------------|-------------------------|
| `--archived` | Yes | No |
| `--limit N` / `-n N` | Yes | No |
| `--reverse` / `-r` | Yes | No |
| `--blocked` | Yes | Yes (via `block_filter="blocked"`) |
| `--not-blocked` | Yes | Yes (via `block_filter="not-blocked"`) |
| `--json` | Yes (global flag) | No (uses `--compact`) |

No kanban-md changes needed — all flags ship with v0.33.0.

### 3.2 Output format: compact vs lean JSON

**Current:** `--compact` returns one-line-per-task text. Agents must parse free text.

**Proposed:** `--json` returns a JSON array with all fields per task. The `body`, `file`, `created`, `updated` fields are noisy for listing purposes.

**Lean JSON approach:** Parse `--json` output with `json.loads()`, strip `body`, `file`, `created`, `updated` from each task dict, return `json.dumps()`. This is ~5 LOC in `list_tasks`.

| Criterion | `--compact` (.30) | `--json` raw (.50) | `--json` lean (.90) |
|-----------|-------------------|--------------------|---------------------|
| Parsability | Text, fragile regex | Native JSON | Native JSON |
| Token cost | Low (one line/task) | High (all fields) | Medium (stripped) |
| Body noise | None | Full body included | Stripped |
| Agent usability | Must parse text | Direct dict access | Direct dict, cleaner |

**Recommendation (.90 confidence):** Lean JSON — strip `body`, `file`, `created`, `updated` server-side. Agents get structured data without body bloat.

### 3.3 `blocked` tri-state design

| Approach | Signature | Mapping |
|----------|-----------|---------|
| Current string enum | `block_filter: str = ""` | `"blocked"` → `--blocked`, `"not-blocked"` → `--not-blocked` |
| Proposed Optional[bool] | `blocked: bool \| None = None` | `True` → `--blocked`, `False` → `--not-blocked`, `None` → no flag |

**Risk:** FastMCP/MCP protocol represents `Optional[bool]` in JSON Schema as `{"anyOf": [{"type": "boolean"}, {"type": "null"}]}`. LLM callers handle this correctly (.85 confidence) — null/true/false are native JSON values. Verified: `show_task` already uses typed params successfully.

**Breaking change:** Renaming `block_filter` to `blocked` is a breaking change for any callers using the string parameter by name. Since all callers are internal OwlBear agents, this is acceptable per project principles ("no backwards compatibility").

### 3.4 Test coverage plan

Existing test pattern uses `_patch_run()` context manager to mock `_run_kanban` and inspect args. New tests should follow this pattern:

| Test case | What to verify |
|-----------|---------------|
| `archived=True` | `--archived` in args |
| `archived=False` (default) | `--archived` not in args |
| `limit=5` | `--limit` and `"5"` in args |
| `limit=0` (default) | `--limit` not in args |
| `reverse=True` | `--reverse` in args |
| `reverse=False` (default) | `--reverse` not in args |
| `blocked=True` | `--blocked` in args, `--not-blocked` not in args |
| `blocked=False` | `--not-blocked` in args, `--blocked` not in args |
| `blocked=None` (default) | neither `--blocked` nor `--not-blocked` |
| Lean JSON output | `body`, `file`, `created`, `updated` stripped from result |

## 4. Recommendation (.90 confidence)

Proceed with all AC items as specified. The implementation is straightforward:

1. **Parameter changes** — Add `archived: bool`, `limit: int`, `reverse: bool`; replace `block_filter: str` with `blocked: bool | None`
2. **Output change** — Switch `--compact` to `--json`, parse with `json.loads()`, strip noisy fields, re-serialize
3. **Tests** — Follow existing `_patch_run()` mock pattern; add lean JSON output test with mock JSON return
4. **SKILL.md update** — Update parameter table for `list_tasks`

Risk: Lean JSON adds ~5 LOC of `json.loads/dumps` in the hot path. For board sizes ≤500 tasks, this is negligible.

## 5. Follow-up Tasks

Tasks created at `ideation` for architect review — see kanban commands below.
