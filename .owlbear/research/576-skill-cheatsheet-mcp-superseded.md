# #576 Skill Cheatsheet MCP Alternatives — Superseded

> **Owning task:** #576 — P2-05: Update skill cheatsheets with MCP tool alternatives alongside CLI
> **Date:** 2026-04-05 **Status:** Complete (validation pass)

## 1. Context and Question

Task #576 proposed adding `> **MCP equivalent:** tool_name(...)` blockquotes after inline CLI invocations in 14 skill SKILL.md files, plus normalizing 3 inconsistent MCP note patterns. The Cycle 3 architect rejected the task as superseded. This research validates that conclusion.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | share/skills/**/SKILL.md (14 targets) | Codebase grep | .95 — current state of deliverable targets |
| 2 | #486 task body + audit record | Kanban | .95 — DRY consolidation that removed inline MCP notes |
| 3 | #484 task body + arch review | Kanban | .90 — CLI removal phase, also confirmed superseded |
| 4 | #575 research doc (.owlbear/research/575-*.md) | Research | .85 — sibling task reached same conclusion independently |
| 5 | .owlbear/research/skill-cheatsheet-mcp-alternatives.md | Research | .70 — original research, now outdated |

## 3. Analysis

### Codebase Evidence (grep verified 2026-04-05)

| Check | Result |
|-------|--------|
| `kanban-md` CLI refs in 14 target skills | **0 matches** — no CLI invocations to annotate |
| `MCP equivalent` blockquotes in skills | **0 matches** — none exist, none needed |
| `MCP note:` / `MCP equivalents` patterns | **0 matches** — normalization targets absent |
| `kanban-md Commands` cheatsheet tables | **0 matches** — removed by #486 |
| `Kanban operations: See h-mcp-kanban` pointer | **10 workflow skills** — consolidated by #486 |
| MCP tool names in h-mcp-kanban | All 7 tools documented as single source of truth |

### Supersession Chain

| Task | Status | Action that eliminated #576 scope |
|------|--------|----------------------------------|
| #486 (Phase C) | Archived (audited 1.00) | Removed 39 inline MCP notes from 11 skills, consolidated to h-mcp-kanban. Deliberate DRY decision. |
| #484 (Phase B) | Ideation (also superseded) | CLI refs removed during workspace reorg. All AC met. |
| #575 (sibling) | Ideation (claimed) | Independent research reached same conclusion: close as resolved-by-architecture (.78 confidence). |

### Trade-off: Reintroduce vs. Close

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| A: Archive as superseded | Respects #486's audited DRY consolidation; zero deliverables | None — following established architecture | **.92** |
| B: Reintroduce inline blockquotes | Would duplicate what h-mcp-kanban already provides | Violates DRY; contradicts #486 (audited at 1.00); circular (annotating MCP names with MCP names) | .10 |

## 4. Recommendation (.92 confidence)

**Archive #576 as superseded by #486.**

The task's entire premise — annotating CLI invocations with MCP equivalents — is invalidated:
- Zero CLI invocations remain in any target skill
- All 14 skills are MCP-native (use tool names directly, point to h-mcp-kanban)
- #486 deliberately removed inline MCP blockquotes as a DRY consolidation (audited at 1.00)
- Adding "MCP equivalent" notes after MCP tool names would be circular

Challenge: SKIP — confirming completed architectural work, no new recommendation to challenge.

## 5. Follow-up Tasks

Parent #483 is archived with failed completion criteria (#576 not archived). Parent's AC should be updated to reflect #576 closure as superseded, per Cycle 3 architect recommendation.
