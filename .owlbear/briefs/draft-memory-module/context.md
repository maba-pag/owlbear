# Context — Memory Module (Keep / Restructure / Cut)

## Problem Statement

**Agent performance suffers because lessons-learned are drowned in a high-volume, low-signal memory stream.** Agents produce ~150+ memory entries per few weeks via VS Code's built-in memory tool. These are uncurated, ungated, and unranked — useful knowledge gets lost among one-offs and banalities. Agents repeat known mistakes because they can't efficiently surface the high-value subset.

**The gap is a quality-gated promotion layer** that surfaces only high-confidence, recurring, verified knowledge to agents at startup — without adding infrastructure complexity that makes the system harder to maintain than the problem it solves.

## VS Code Memory — What It Does and Doesn't Do

| Tier | Committable | Shareable | Quality-gated | Queryable |
|------|-------------|-----------|---------------|-----------|
| User memory (`/memories/`) | ✗ (local AppSupport) | ✗ | ✗ | ✗ (file list) |
| Session memory (`/memories/session/`) | ✗ | ✗ | ✗ | ✗ |
| Repo memory (`/memories/repo/`) | ✗ (despite name — lives in workspace storage) | ✗ | ✗ | ✗ |

VS Code also uses memory for **context compaction** — so it cannot be fully replaced even if a custom system exists.

## What Exists Today

- **`mcp-memory` module** — fully coded (5 tools, SQLite, approval workflow) but non-functional (0 tools exposed due to registration bug)
- **`/memories/repo/*.md` files** — manual curated files, committable, in git, partially read by agents
- **Knowledge MCP server** (`mcp-knowledge`) — exists separately, could potentially serve as the promoted-knowledge store

## Coexistence Model (user direction)

- VS Code memory = **raw capture** (cannot eliminate — used for compaction)
- Custom system = **curated promotion space** (high-signal only, quality-gated)
- Curator agent = auto-filters low-confidence/one-offs, promotes recurring patterns
- Manual curation = periodic human review prompt
- Open question: does promotion target need its OWN MCP server, or could `mcp-knowledge` serve that role?

## Active Tensions

1. Incremental value of structured metadata vs. maintenance cost of custom module
2. Current scale (11 topic files, ~25KB) → metadata filtering is low-impact; future scale (50+) → matters more
3. Dedicated `mcp-memory` server vs. merging promotion function into `mcp-knowledge`
4. SQLite (not diffable/mergeable) vs. markdown+frontmatter (git-native, like kanban)

## Early Challenger Corrections

Challengers assumed: instructions untested, curation not running, agents not reading. All three wrong.
- Instructions are good and tested
- Curation runs every ~2hr, current files are result of a 150→11 reduction audit
- Agents do read `/memories/repo/` files at startup (confirmed by observation)

Challengers' useful contributions:
- The MCP module has never transmitted — no production data on its value
- The file-based system is genuinely working at current scale
- The "coexistence adds complexity" concern remains valid
- The "fix bug + measure" suggestion is sound methodology

Challenger overreach: dismissing structured quality gating as "just an instruction problem" when the instruction+curation baseline is already operational and the question is incremental value of METADATA.

## Refined Problem

The file-based curation pipeline works but is unstructured. The confirmed direction is: restructure the memory module to use markdown+frontmatter (kanban pattern) with MCP tools providing queryable/filtered retrieval. This gives committable, git-native, quality-gated agent memory that VS Code cannot provide.

## Strategic Direction

**Option B — Restructure to markdown+frontmatter, keep MCP tools, git-native storage.**

Phase 2 handles: storage layout, tool API design, migration from SQLite, data model, Brief.

**Best:** Clear keep/restructure/merge/cut decision → winning option operational → agents surface fewer, higher-quality memories → less repetition of known mistakes.
**Minimum:** Firm strategic direction with enough rationale for Phase 2 Brief. Path to fix/migrate/cut is scoped.
**Scope boundary:** This decides direction, not implementation. Storage format, curator redesign, and bug fix are downstream.

## Current State

- **Package:** `serve/mcp-memory/` — fully coded, tested, documented
- **Storage:** SQLite at `store/memory/memory.db`
- **Tools:** 5 (get_knowledge, record_learning, list_entries, set_approval_state, mark_for_deletion)
- **Consumers:** All pipeline agents (pre-flight knowledge load + post-task reflection dual-write)
- **Supporting artifacts:** h-mcp-memory skill, h-memory-structure skill, w-mem-curation workflow, memory-curator agent
- **Design decisions:** DR #387, DR #428

## Project Type

`existing-feature/refactor` — evaluating whether to restructure, repurpose, or cut an existing module.

## Active Tensions

- VS Code memory improvements vs. custom module value proposition
- Committable/shared memory vs. local-only ephemeral memory
- Agent-scoped institutional knowledge vs. general user memory
- Maintenance cost of a custom module vs. leveraging built-in tooling
