# Restore Pipeline Protocol MCP Callouts

> **Owning task:** #625 — Restore #574 pipeline protocol MCP callouts — 8 failing tests
> **Date:** 2026-04-05  **Status:** Complete

## 1. Context and Question

Task #574 added 6 `> **MCP equivalent:**` callout blocks to
`.github/skills/r-pipeline-protocol/SKILL.md` (commit 724062e). During v2
reorganization, the file moved to `share/skills/r-pipeline-protocol/SKILL.md`
but the callout blocks were NOT carried over. 8 acceptance tests now fail.

**Question:** What exact content must be restored, and does it still apply to the
current file structure?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `git show 724062e` (diff with 6 callout blocks) | Git history | .95 |
| 2 | `share/skills/r-pipeline-protocol/SKILL.md` (current HEAD) | Codebase | .95 |
| 3 | `tests/test_mcp_tool_references_574.py` (8 assertions) | Codebase | .95 |
| 4 | `.owlbear/research/575-agent-mcp-lifecycle-audit.md` §3d | Research | .85 |

## 3. Analysis

### 3a. Current vs Required State

| Section | Required Callout | Present? |
|---------|-----------------|----------|
| Resolved Decision Pre-flight | `show_task(task_id="{id}")` | No |
| Follow-up Task Quality | `create_task` | No |
| Channel B — Task Body | `edit_task(..., append_body="...", timestamp=True)` | No |
| Reading Rules | `show_task(task_id="{id}")` | No |
| Blocking Convention | `edit_task(block="reason")` / `edit_task(unblock=True)` | No |
| Handoff | `edit_task(append_body="...")` | No |

All 6 sections exist in the current file. The callout format matches existing
patterns (blockquote with bold `MCP equivalent:` prefix + backtick-wrapped tool call).

### 3b. Path References

The original callouts referenced `docs/decisions/` — the current file already uses
`.owlbear/decisions/`. No path fixup needed in the callout text itself; the callouts
reference tool parameters, not file paths.

### 3c. Test Coverage

8 tests check 8 assertions across 6 sections. Two Channel B tests check `append_body`
and `timestamp` separately; the remaining 6 are parametrized section→tool checks.
All pass with the callout blocks from 724062e restored verbatim.

## 4. Recommendation

**Restore the 6 callout blocks verbatim from commit 724062e.** Confidence: .95.

The callout content references MCP tool names and parameters that are current
(`show_task`, `create_task`, `edit_task` with `append_body`, `timestamp`, `block`,
`unblock`). No adaptation needed — direct copy-paste restoration.

Challenge: FALLBACK — trivial restoration, no recommendation trade-off to challenge.

## 5. Follow-up Tasks

No new follow-up tasks needed — task #625 itself is the implementation task.
The builder should apply the 6 callout blocks from commit 724062e to the
current `share/skills/r-pipeline-protocol/SKILL.md`.
