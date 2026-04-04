# Agent-Common Memory-MCP Integration

> **Owning task:** #526 — Update agent-common for memory-mcp integration
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

How should agent-common.instructions.md, copilot-instructions.md, and the new mcp-memory skill be updated to integrate the memory-mcp server (approved in DR #387)? The design doc §3G-3H prescribes Step 0 (auto-loading via `get_knowledge`) and write mechanism (via `record_learning`), but the concrete instruction text, category mapping, error handling, and tool access prerequisites need research.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | memory-mcp design doc §3G-3H | `docs/research/memory-mcp-server-design.md` | 1.0 |
| S2 | DR #387 (approved) | `docs/decisions/resolved/387-memory-mcp-architecture.md` | 1.0 |
| S3 | agent-common L187-199 | `instructions/agent-common.instructions.md` | .95 |
| S4 | copilot-instructions L83-105 | `.github/copilot-instructions.md` | .90 |
| S5 | tools.py implementation | `packages/mcp-memory/src/owlbear_mcp_memory/tools.py` | .95 |
| S6 | setup.py MCP registration | `scripts/setup.py` L78-82 (server name: `owlbearMemory`) | .90 |
| S7 | mcp-kanban skill template | `skills/mcp-kanban/SKILL.md` | .85 |
| S8 | Agent .agent.md frontmatter | `agents/*.agent.md` (14 files, tools: arrays) | .95 |
| S9 | curator-workflow-memory doc | `docs/research/curator-workflow-memory-mcp.md` | .80 |

## 3. Analysis

### 3A. Prerequisite: Agent Tool Allowlists

**Critical gap:** No agent currently has `'owlbear-memory/*'` in its `tools:` frontmatter (S8). All pipeline agents include `'owlbear-kanban/*'` but not the memory server. Without this, `get_knowledge` and `record_learning` calls fail silently.

| Fix approach | KISS | Risk | Effort |
|-------------|------|------|--------|
| Add to all 14 agents (blanket) | High | Low — tool exclusion env var exists | ~14 one-line edits |
| Add to pipeline agents only (8) | Medium | Low — but Step 0 applies to all | ~8 edits |
| Prerequisite task before #526 | High | None | New task |

**Recommendation (.90):** Create a prerequisite task to add `'owlbear-memory/*'` to all pipeline agent tools arrays. Non-pipeline agents (challenger, code-reader, scribe) need only `get_knowledge` (read-only) — use `MEMORY_TOOLS_EXCLUDE` per-server if needed. This must complete before #526 implementation.

### 3B. Step 0: Institutional Knowledge Pre-Flight

**Location:** New `## Institutional knowledge pre-flight` section above `## Resolved decision pre-flight` (L119 of agent-common, S3).

**Instruction content:**
- Call `get_knowledge` with agent name, limit=20, min_confidence=0.7
- Graceful degradation: if call fails or returns empty, proceed normally
- Contextualizes agent behavior with accumulated learnings

**Design decisions backed by S1 §3G:**
- `limit=20` (not tool default 50) — prevents context bloat while providing useful entries
- `min_confidence=0.7` — matches write-time floor, filters noise
- Single call, not per-category — KISS, agent gets union of all relevant knowledge

### 3C. Post-Task Reflection Update

**Current (S3 L187-199):** Write markdown to `/memories/repo/inbox/{task-id}-{agent}.md`.

**Proposed dual-write (per S1 §3H):**
1. Keep existing `memory create` call (backward compat during migration)
2. Add `record_learning` calls with formal categories

**Category mapping (from S1 §3L):**

| Informal label | MCP category | Rationale |
|----------------|-------------|-----------|
| `problems_faced` | `knowledge` | Factual obstacle encountered |
| `workarounds_applied` | `knowledge` | Factual resolution technique |
| `patterns_discovered` | `behavior` | Reusable approach/idiom |
| `time_sinks` | `context` | Situational awareness |
| `quality_gaps` | `context` | Upstream quality signals |

**Call structure:** One `record_learning` call per notable finding (not one per bullet list). Each entry gets its own category and confidence=0.8 default (above 0.7 floor, below 1.0 certainty). If nothing notable happened, skip both writes.

**Error handling:** If `record_learning` fails, the `memory create` fallback still captures the data. Log failure, don't block task completion.

### 3D. mcp-memory Skill Structure

Template from S7 (mcp-kanban skill). Server registered as `owlbearMemory` (S6).

| Section | Content |
|---------|---------|
| Frontmatter | name, description, user-invocable: false |
| Tools table | 4 tools with params, returns, annotations |
| Tool details | get_knowledge sort/scope, record_learning validation, list_entries filters, mark_for-deletion idempotency |
| Error handling | `error:` prefix for record_learning/list_entries; ToolError for mark_for-deletion not-found |
| Configuration | `MEMORY_TOOLS_EXCLUDE`, `OWLBEAR_MEMORY_DB_PATH` |
| Usage examples | Step 0 pattern, post-task reflection pattern, curator pattern |

### 3E. Memory Governance Update

Current copilot-instructions.md (S4) describes three tiers: `/memories/` (user), `/memories/repo/` (agent inbox), `/memories/session/` (session). Update adds mcp-memory as the canonical agent knowledge store.

| Tier | Current | After update |
|------|---------|-------------|
| `/memories/` | User preferences and tool patterns | Unchanged |
| `/memories/session/` | Session-scoped notes | Unchanged |
| `/memories/repo/inbox/` | Agent lessons-learned | Legacy (dual-write during migration) |
| mcp-memory (`owlbearMemory`) | Not documented | Agent institutional knowledge (canonical) |

## 4. Recommendation (.75 confidence)

Implement per approved design doc §3G-3H with the following refinements:
1. **Prerequisite task:** Add `'owlbear-memory/*'` to all pipeline agent tool allowlists
2. **Step 0:** limit=20, min_confidence=0.7, graceful degradation on failure
3. **Post-task reflection:** One `record_learning` per finding with mapped category, confidence=0.8 default
4. **Skill:** Follow mcp-kanban template with usage examples
5. **Governance:** Four-tier model (user / session / legacy inbox / mcp-memory)

Challenge: block — confidence in original: .40. Challenger surfaced critical agent tool allowlist gap (accepted: added prerequisite task), category mapping gap (accepted: table added), confidence floor (accepted: default 0.8 specified), call structure ambiguity (accepted: one call per finding). Revised confidence .75 after adding prerequisite and refinements.

## 5. Follow-up Tasks

T1 — implements pre-approved design (DR #387). No new DR needed.

```
kanban\kanban-md.exe create "Add owlbear-memory tool access to all pipeline agents" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Add 'owlbear-memory/*' to the tools: array in every pipeline agent .agent.md frontmatter. Prerequisite for #526. AC: - [ ] All 14 agents in agents/*.agent.md include 'owlbear-memory/*' in tools: - [ ] validate_agents.py passes"
```
