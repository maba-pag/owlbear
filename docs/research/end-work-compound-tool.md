# end_work Compound Tool for mcp-kanban

> **Owning task:** #471 — Add end_work compound tool to mcp-kanban server
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Pipeline agents currently need 2–3 separate MCP tool calls to finish work on a task (append note, move status, release claim). Can we consolidate these into a single `end_work` tool? What implementation approach fits the existing server patterns?

## 2. Sources Studied

| # | Source | URL | What | Relevance |
|---|--------|-----|------|-----------|
| 1 | kanban-md `handoff` command | CLI `handoff --help` | Existing compound CLI: move + note + block + release in one call | .95 |
| 2 | FastMCP tools documentation | gofastmcp.com/servers/tools | `Literal` types, error handling, `ToolError`, async patterns | .90 |
| 3 | kanban-md `edit` command | CLI `edit --help` | Supports `--json` return, `-a` + `--timestamp` + `--status` + `--release` + `--block` in one call | .95 |
| 4 | kanban-md `config --json` | CLI output | Returns `statuses` array for next-status derivation | .90 |
| 5 | MCP spec — Tools | modelcontextprotocol.io/specification/2025-03-26/server/tools | Tool design, error reporting patterns | .80 |
| 6 | Existing `server.py` | packages/mcp-kanban/src/owlbear_mcp_kanban/server.py | 7 tools, all delegate to `_run_kanban`, `AppContext` at lifespan | .95 |

## 3. Analysis

### 3.1 Implementation Approach — CLI call composition

The `edit` command already supports combining `-a` + `--timestamp` + `--status` + `--release` + `--block` in a single invocation, and `--json` returns the mutated task. This means most outcomes need only **one** `_run_kanban` call:

| Outcome | CLI calls needed | Commands |
|---------|-----------------|----------|
| `fail` | 1 | `edit ID -a NOTE -t --release --json` |
| `block` | 1 | `edit ID -a NOTE -t --block REASON --release --json` |
| `reject` | 1 | `edit ID -a NOTE -t --status TARGET --release --json` |
| `success` (not done) | 1 | `edit ID -a NOTE -t --status NEXT --release --json` |
| `success` (done) | 2 | `edit ID -a NOTE -t --release` then `archive ID --json` |

The done-to-archive case needs two calls because `archive` is a separate command. All other outcomes are single-call.

### 3.2 Next-status derivation

Two options for reading the statuses list:

| Criterion | Option A: Cache at lifespan | Option B: Read per-call |
|-----------|---------------------------|------------------------|
| Latency | Zero (cached) | ~50ms subprocess per call |
| Consistency | Stale if config changes mid-session | Always fresh |
| Complexity | Extend `AppContext`, one `config --json` at startup | No AppContext change |
| KISS score | High — config is static during MCP session | Medium — unnecessary work |

**Recommendation (.85):** Option A — cache statuses in `AppContext` at lifespan. Config changes require server restart anyway. Add `statuses: list[str]` to `AppContext`, populate via `config --json` subprocess during `app_lifespan`.

### 3.3 Parameter design

FastMCP supports `Literal` types for constrained string parameters, generating proper JSON Schema enums. The `outcome` parameter should use `Literal["success", "fail", "block", "reject"]`.

For `block_reason` and `move_to`: use `str = ""` defaults. Validate `block_reason` required when `outcome="block"` before any CLI calls — fail fast with error return.

### 3.4 Claim handling

`edit` requires `--claim AGENT` when the task is claimed. The `end_work` tool doesn't need an explicit claim parameter — the agent's claim name is already on the task. Use `show --json` first to read `claimed_by`, then pass it to `edit --claim`. This adds one subprocess call for the success-not-done path (show + edit = 2 calls), but avoids exposing a claim parameter that the agent shouldn't need to know.

**Alternative:** Accept an optional `claim` parameter so the caller can pass it, avoiding the extra `show` call. This is what #470 (`start_work`) does — it returns `claim_name` so the agent already has it.

**Recommendation (.80):** Accept optional `claim` parameter. If provided, use it directly. If not, read from `show --json`. This supports both the optimized path (agent passes claim from start_work) and the fallback path.

### 3.5 Error handling

Follow existing pattern: return `"error: {message}"` string on failures. Validate inputs before CLI calls. The `edit` command's own error responses (claimed by other agent, invalid status) propagate naturally through `_run_kanban`.

## 4. Recommendation (.85 confidence)

Implement `end_work` as a thin orchestrator over existing kanban-md CLI commands:

1. Extend `AppContext` with `statuses: list[str]` cached from `config --json` at lifespan
2. Use `Literal["success", "fail", "block", "reject"]` for outcome parameter
3. Validate inputs (block_reason required for block outcome) before any CLI calls
4. Single `edit --json` call for most outcomes; `edit` + `archive --json` for done-to-archive
5. Accept optional `claim` parameter for the optimized path
6. Return the `--json` output from the final CLI call

Risk: The done-to-archive path is non-atomic (two sequential CLI calls). If `archive` fails after `edit` succeeds, the note is appended but the task isn't archived. Mitigation: return the error clearly so the agent can retry the archive manually — same as any CLI failure today.

## 5. Follow-up Tasks

Task #471 itself is the implementation task — no additional follow-up tasks needed. The AC is comprehensive and covers all outcomes, edge cases, validation, and testing. The SKILL.md update is included in the AC.

One note for the architect: the `claim` parameter addition (optional, for the optimized path where start_work provides the claim name) is a refinement to the current AC worth considering.
