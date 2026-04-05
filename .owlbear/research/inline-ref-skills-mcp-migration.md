# Inline-Ref Skills MCP Migration Scope Analysis

> **Owning task:** #582 — P2-B3: Update inline-ref skills to MCP-only
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #582 targets 5 skill files with inline CLI references for MCP-only migration:
w-dispatch-planning, w-decision-routing, h-kanban-md, w-orchestration, w-research.
Phase A (#483, archived) added MCP alternatives alongside CLI. Phase B removes CLI.

**Question:** What is the actual CLI reference inventory per file, and what does
each transformation look like?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | w-dispatch-planning SKILL.md | Codebase | .95 |
| 2 | w-decision-routing SKILL.md | Codebase | .90 |
| 3 | h-kanban-md SKILL.md | Codebase | .95 |
| 4 | w-orchestration SKILL.md | Codebase | .85 |
| 5 | w-research SKILL.md | Codebase | .90 |
| 6 | h-mcp-kanban SKILL.md | Codebase | .95 |
| 7 | r-pipeline-protocol SKILL.md | Codebase | .85 |
| 8 | phase-b-mcp-only-kanban-migration.md | Research | .90 |

## 3. Analysis

### 3a. Actual CLI Reference Inventory

| File | `kanban\kanban-md.exe` | CLI flag/syntax artifacts | Vestigial blockquotes | Total changes |
|------|------------------------|--------------------------|----------------------|---------------|
| w-dispatch-planning | 2 (Recipes 1, 2) | 4 (checklist, pitfalls, scope table) | 0 | Moderate |
| w-decision-routing | 0 | 0 | 2 (`> MCP equivalent:` L33, L35) | Minor |
| h-kanban-md | 18+ (throughout) | 20+ (flags, recipes, escaping) | 0 | Major rewrite |
| w-orchestration | 0 | 0 | 0 | None |
| w-research | 0 | 0 | 2 (`> MCP equivalent:` L17, L138) | Minor |

**Finding:** Only 2 files have direct CLI refs. 2 files have vestigial MCP-equivalent
blockquotes (where main text already uses MCP names but blockquotes frame MCP as
secondary). 1 file needs zero changes.

### 3b. Transformation Strategy per File

**w-dispatch-planning (moderate):**

| Section | Current | Target |
|---------|---------|--------|
| Recipe 1 code block | PowerShell with `kanban\kanban-md.exe list` | MCP `list_tasks()` call + structured algorithm for gate logic |
| Recipe 2 code block | PowerShell with `kanban\kanban-md.exe show` | MCP `show_task()` call |
| Scope translation table | `--tag phase-3` CLI flags | `tag="phase-3"` MCP parameter |
| Verification Checklist L1 | "`--unblocked --not-blocked --unclaimed` triple" | MCP filter parameter names |
| Known Pitfalls | CLI flag semantics, PowerShell parsing | MCP filter semantics, body content rules |

**Risk:** Recipe 1 encodes dual-key sorting and 4 gate-flag conditions as executable
PowerShell. The MCP conversion must preserve this as a structured numbered algorithm
(not prose), since the dispatcher agent consumes it as specification.

**w-decision-routing (minor):**
Fold MCP parameter signatures from blockquotes into main text. Delete `> **MCP
equivalent:**` wrapper lines. Before: "via `edit_task` (with `append_body`)." +
blockquote. After: "via `edit_task(task_id="{id}", append_body="...", timestamp=True)`."

**h-kanban-md (major):**

| Option | Description | Confidence |
|--------|-------------|------------|
| A: Thin redirect | Strip all CLI content, retain only: title, deprecation notice, cross-ref to h-mcp-kanban, board config (statuses/priorities) | .80 |
| B: MCP claiming + redirect | Rewrite claiming section in MCP syntax, strip CLI sections | .65 |
| C: Delete file entirely | Remove and update all references | .50 |

**Recommendation: Option A (.80).** h-mcp-kanban already covers the claiming lifecycle
identically (Agent Lifecycle Pattern section). Duplicating it in h-kanban-md creates
maintenance burden. Board config is the only non-CLI-specific content worth retaining.
The file becomes a ~20-line redirect with board config reference.

**w-research (minor):**
Fold `start_work(task_id="{id}")` and `end_work(...)` parameter signatures into
main text. Delete the 2 `> **MCP equivalent:**` blockquote lines.

**w-orchestration (none):** Already fully MCP-native. Verify-only.

### 3c. h-kanban-md Content Overlap with h-mcp-kanban

| Content | h-kanban-md | h-mcp-kanban | Action |
|---------|-------------|-------------|--------|
| Claiming lifecycle | CLI 3-phase | MCP 3-call | Covered by h-mcp-kanban |
| Body content gotchas | 3 rules (pipes, arrows, tokens) | Same 3 rules | Covered by h-mcp-kanban |
| Board config | statuses, priorities | env vars only | Retain in h-kanban-md or move |
| PS escaping | 5 subsections | N/A | Obsolete with MCP |
| Flag reference | 30+ flags | Deferred to schema | Obsolete with MCP |
| Known gotchas | 7 CLI-specific | 1 (binary discovery) | Obsolete with MCP |

**References to h-kanban-md:** 21 across workspace (2 in pipeline protocol, 1 in
h-mcp-kanban, rest in research docs and tasks). The pipeline-protocol refs already
pair h-kanban-md with h-mcp-kanban as fallback/primary.

## 4. Recommendation (.80 confidence)

**T1 classification** — documentation migration of existing MCP tools, pre-approved
by user. No new capabilities, no architecture changes.

The AC is verification-oriented (predicates + grep test). 3 of 5 files satisfy AC
predicates already or need only minor blockquote cleanup. Primary work concentrates
on 2 files: w-dispatch-planning (moderate — algorithm preservation) and h-kanban-md
(major — content reduction to thin redirect).

**Challenge:** reconsider — confidence in original: .65. Challenger identified:
(C1) w-decision-routing blockquotes missed (accepted, added to analysis); (C2)
dispatch-planning needs structured algorithm not vague pseudocode (accepted,
specified in §3b); (C3) h-kanban-md end-state unspecified (accepted, Option A
specified); (C4) blockquote fix should fold params into main text, not bare-delete
(accepted, specified for both files); (C5) AC is verification-oriented, no
correction needed (accepted). Revised confidence from .80 to .80 (findings refined
but direction unchanged).

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #582 itself is the implementation task. Findings
refine scope for the architect/builder — no decomposition changes required.
