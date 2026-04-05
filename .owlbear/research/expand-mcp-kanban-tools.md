# Expand mcp-kanban to Full kanban-md Tool Set

> **Owning task:** #56 — Expand mcp-kanban to full kanban-md tool set
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #56 asks to port the remaining 6 tools from v1 `KanbanToolset` (show,
create, move, edit, pick, context) to the mcp-kanban MCP server, for a total of
7 tools (list already exists from scaffold #39). This research validates the
approach, identifies v1 signature gaps, and recommends the tool surface.

**Blocker:** `packages/mcp-kanban/` does not exist yet. #39 (scaffold) is at
`backlog`; #7 (monorepo skeleton) is at `ideation`. This task depends on both.

## 2. Sources

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OwlBear v1 KanbanToolset | `v1/src/owlbear/tools/kanban.py` | .95 |
| 2 | MCP Python SDK README (v1) | <https://github.com/modelcontextprotocol/python-sdk> | .90 |
| 3 | kanban-md CLI v0.33.0 help | `kanban\kanban-md.exe --help` (local) | .95 |
| 4 | Scaffold mcp-kanban research | `docs/research/scaffold-mcp-kanban.md` | .90 |
| 5 | Scaffold mcp-knowledge research | `docs/research/scaffold-mcp-knowledge.md` | .80 |
| 6 | agent-common instructions | `.github/instructions/agent-common.instructions.md` | .85 |

## 3. Analysis

### 3a. v1 Signature Gaps vs Current CLI

The v1 KanbanToolset was written against an earlier kanban-md version. The CLI
has since gained significant surface area. Key gaps per tool:

| Tool | v1 params | Missing CLI params (notable) |
|------|-----------|------------------------------|
| `list` | status, tag, priority, block_filter | search, sort, limit, reverse, group-by, claimed-by, unclaimed, class |
| `show` | task_id | (none — complete) |
| `create` | title, priority, tags, body, depends_on | claim, class, due, estimate, parent, assignee |
| `move` | task_id, status | (none — complete) |
| `edit` | task_id, body, block, unblock, tags, priority, append_body | claim, release, status, title, timestamp, parent, class, assignee, add-dep, remove-dep, add-tag, remove-tag, due, estimate |
| `pick` | status, claim, move | tags filter, no-body |
| `context` | (none) | (none — complete) |

### 3b. Tool Surface Options

| Option | Tools | New params | Effort | KISS |
|--------|-------|------------|--------|------|
| A. Mirror v1 exactly | 7, same params | 0 | Low | .90 |
| B. Mirror v1 + update params | 7, expanded params | ~20 | Medium | .80 |
| C. Add handoff tool | 8, expanded params | ~25 | Medium | .75 |
| D. Full CLI wrap | 15+ tools | 50+ | High | .40 |

`handoff` is heavily used in agent-common (every pipeline agent calls it via
shell). However, agents currently call it via `run_in_terminal`, not via MCP
tool. Adding `handoff` as an MCP tool adds value only when agents use MCP
toolsets directly — which is a v2 daemon concern, not a VS Code Copilot concern.

### 3c. Parameter Update Strategy

| Strategy | Pros | Cons | Score |
|----------|------|------|-------|
| Full parity (all CLI flags) | Complete, future-proof | Over-engineered, many rarely used | .55 |
| Agent-essential subset | Covers real usage, KISS | May miss edge cases | .85 |
| v1 exact (no changes) | Simplest, proven | Stale, misses claim/release | .70 |

Agent-essential additions beyond v1: `edit --claim`, `edit --release`,
`edit --status`, `edit --timestamp`, `create --claim`, `list --search`,
`list --sort`, `list --unclaimed`, `pick --tags`. These are used in
agent-common workflows daily.

### 3d. Subprocess Helper Design

v1 uses `self._run_kanban(*args) -> (stdout, stderr, returncode)` as an
instance method. For MCP (module-level `@mcp.tool()` functions), the helper
needs binary path from lifespan context.

| Pattern | Description | Score |
|---------|-------------|-------|
| Module function + ctx | `async def _run(ctx, *args)` extracts path from lifespan | .85 |
| Module function + explicit path | `async def _run(bin, dir, *args)` — tools unpack ctx | .80 |
| Helper class on AppContext | `ctx.lifespan_context.run_kanban(*args)` | .70 |

Source 2 (MCP SDK) shows `ctx.request_context.lifespan_context` for accessing
lifespan state. A thin module function that accepts the lifespan context is
cleanest.

### 3e. Error Handling

v1 returns `f"error: {stderr.strip()}"` on non-zero exit. MCP tools have two
options: return error text (model sees it) or raise an exception (SDK formats
as `isError=True`). Agent workflows benefit from seeing error text to
self-correct. Return error text, consistent with v1.

### 3f. Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit (required per AC) | Each tool function | Mock `asyncio.create_subprocess_exec`, verify args |
| Unit | Subprocess helper | Mock process, verify flag construction |
| Unit | Error paths | Mock non-zero returncode, verify error string |

Source 5 (mcp-knowledge research) confirms mock-subprocess unit testing as the
standard pattern for CLI-wrapping MCP servers.

## 4. Recommendation (.85 confidence)

**Option B: Mirror v1's 7 tools with agent-essential parameter updates.**

1. Port all 7 tools: `list`, `show`, `create`, `move`, `edit`, `pick`, `context`
2. Add these agent-essential params beyond v1:
   - `edit`: `claim`, `release`, `status`, `timestamp` (4 new)
   - `create`: `claim` (1 new)
   - `list`: `search`, `sort`, `unclaimed` (3 new)
   - `pick`: `tags` (1 new)
3. Keep `_run_kanban(ctx, *args)` module function pattern
4. Return error text (not exceptions) for non-zero exit codes
5. Unit test each tool with mock subprocess

**Risk:** #39 (scaffold) and #7 (monorepo) must land first. No code can be
written until the package exists. The dependency chain is:
`#7 (monorepo) → #39 (scaffold) → #56 (expand tools)`.

## 5. Follow-up Tasks

Task #56 itself is the implementation task. No new follow-up tasks needed —
the AC is well-scoped. Add a dependency on #39 so the pipeline enforces
ordering.
