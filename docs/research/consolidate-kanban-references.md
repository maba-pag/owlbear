# Phase C: Consolidate Kanban References — Research

> **Owning task:** #486 — Phase C: Consolidate kanban references to central skill + minimal agent config
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #486 proposes consolidating kanban references from ~20 files to a central
skill + minimal per-agent config. The AC references `agent-common.instructions.md`
(items 4–5) and assumes skills contain "15-line cheatsheets" that need replacing.

**Key question:** Does the AC match the current architecture, and what
consolidation is actually needed?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | h-mcp-kanban/SKILL.md (160 lines) | Codebase | .95 — canonical MCP tool reference |
| 2 | r-pipeline-protocol/SKILL.md (200 lines) | Codebase | .95 — Channel A/B protocol, claiming, section-header mapping |
| 3 | 11 w-* workflow skills | Codebase | .90 — contain 32 inline `> **MCP equivalent:**` callouts |
| 4 | 16 agent .agent.md files | Codebase | .85 — Channel A/B sections, no kanban cheatsheets |
| 5 | test_mcp_tool_references_483.py (220 lines) | Codebase | .90 — constrains tool name presence in skills |
| 6 | docs/research/phase-b-mcp-only-kanban-migration.md | Research | .85 — Phase B scope analysis, h-kanban-md retention decision |
| 7 | h-kanban-md/SKILL.md (200 lines, deprecated) | Codebase | .80 — retained per #484 AC for CLI troubleshooting |

## 3. Analysis

### 3a. AC vs Current Architecture

| AC Item | Expected State | Actual State | Gap |
|---------|---------------|--------------|-----|
| 1. mcp-kanban SKILL.md is single source of truth | Needs consolidation | **Already true** — h-mcp-kanban is canonical | None |
| 2. Skill cheatsheets → 1-2 line references | 15-line cheatsheets exist | Skills have inline `> MCP equivalent:` callouts (1-2 lines each), not cheatsheets | AC outdated |
| 3. Agent files get compact kanban config block | Agents have long kanban sections | Agents have 5-8 line Channel A/B sections (agent-specific, not duplicated) | AC outdated |
| 4. agent-common.instructions.md updated | File exists with Channel B duplication | **File does not exist** | AC invalid |
| 5. Section-header mapping in agent-common | Table in agent-common | Table is in r-pipeline-protocol (Per-Agent Signal Mapping) | AC invalid |
| 6. No duplicated kanban param docs | Param docs scattered | **Already true** — h-mcp-kanban disclaims param docs, defers to schema | None |
| 7. Agents function correctly | Post-consolidation | Baseline — unchanged | N/A |

**Verdict:** 2/7 AC items reference non-existent files. 2/7 describe a state that
already holds. The AC was written before the skills-based architecture solidified.

### 3b. Actual Duplication Inventory

| Pattern | Instances | Lines | Classification |
|---------|-----------|-------|----------------|
| Step 0 claiming boilerplate (identical) | 7 skills | 21 | Generic — safe to consolidate |
| Step 0 claiming (variant: w-mem-curation) | 1 skill | 4 | Variant — keep separate |
| Generic MCP callouts (start_work/end_work) | ~14 | 28 | Generic — could simplify |
| Context-specific MCP callouts | ~18 | 36 | **Scenario-specific** — worked examples |
| h-kanban-md references in r-pipeline-protocol | 2 | 2 | Phase B (#484) scope |

### 3c. Context-Specific Callouts (NOT duplicated)

These callouts show composed tool calls unique to each workflow:

- `edit_task(…unblock=True)` — only in w-decision-routing
- `create_task(…depends_on=[…], body=…)` — only in w-task-decomposition
- `end_work(…note="retry handled"…)` — branch-specific in w-tdd-red
- `list_tasks(status=[…], unblocked=true, unclaimed=true)` — filter combo in w-dispatch-planning
- `edit_task(…append_body="## Builder Notes\n…")` — section header varies per skill

These are parametric worked examples, not DRY violations. h-mcp-kanban itself
says: "do not rely on this document for parameter details" (line 30).

### 3d. Test Constraint

`test_mcp_tool_references_483.py` checks 7 "cheatsheet" skills and 3 "inline-ref"
skills for `start_work`, `end_work`, `edit_task` strings. Prose references like
"claim via `start_work`" preserve these strings. Any consolidation must maintain
tool name presence in skill bodies.

### 3e. Agent Referral Chain

No agent file references `h-mcp-kanban` by name (0/16). Agents receive kanban
context from workflow skills → r-pipeline-protocol → h-mcp-kanban (2-hop chain).
Removing inline callouts forces agents through this chain to reach examples.

### 3f. Consolidation Options

| Option | Description | Lines saved | Risk | Confidence |
|--------|-------------|-------------|------|------------|
| A. Full AC | Create agent-common.instructions.md, rewrite all kanban sections | ~80 | Creates new file; AC targets non-existent architecture | .35 |
| B. Moderate | Remove all callouts, consolidate Step 0 | ~60 | Loses context-specific examples; 2-hop gap | .55 |
| C. Selective | Consolidate Step 0 boilerplate; keep context-specific callouts | ~25 | Preserves worked examples; modest DRY win | .78 |
| D. Recipes | Move context-specific callouts INTO h-mcp-kanban as "Recipes by Role" | ~40 | Consolidates without losing; h-mcp-kanban grows | .72 |

## 4. Recommendation

**Option C — Selective consolidation** (confidence: .78)

1. Simplify 7 identical Step 0 blocks to a 1-line reference + status gate.
2. Remove ~14 generic start_work/end_work callouts (prose verbs + tool names survive).
3. Keep ~18 context-specific callouts (unique parameter compositions).
4. Do NOT delete h-kanban-md — #484 explicitly retains it.
5. **Rewrite the AC** from scratch against current architecture: 2/7 items reference
   non-existent files, 2/7 are already satisfied.

Challenge: reconsider — confidence in original .55. Accepted C1 (h-kanban-md
retention), C2 (callout differentiation), B1 (test constraint), B2 (referral chain).
Revised from aggressive removal to selective consolidation.

## 5. Follow-up Tasks

1. **Rewrite #486 AC** — replace stale AC with scope matching current architecture
   (remove agent-common references, classify callout types, add test compat requirement)
2. **Consolidate Step 0 claiming boilerplate** — 7 identical blocks across w-* skills
3. **Remove generic MCP callouts** — ~14 redundant start_work/end_work syntax lines
4. **Update test_mcp_tool_references_483.py** — adjust if consolidation changes
   string locations (verify prose references maintain tool name presence)
