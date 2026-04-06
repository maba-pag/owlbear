# Historical Docs: ideation → research Prose Cleanup

> **Owning task:** #656 — Update historical docs after ideation→research rename
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

After #641 renamed the kanban status "ideation" to "research" in all functional files (config, Python source, tests, agents, skills, instructions), ~150+ historical prose references were flagged for cleanup in research docs and decision files. **Question:** What is the actual blast radius, and is bulk updating these references worthwhile?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|---------------|
| 1 | `.owlbear/research/*.md` grep scan | 1.0 | 412 refs across 215 of 588 files |
| 2 | `.owlbear/decisions/resolved/*.md` grep scan | 1.0 | 11 refs across 5 of 25 files |
| 3 | `.owlbear/research/rename-ideation-to-research.md` | 0.9 | Original blast-radius analysis from #641 |
| 4 | `w-research`, `w-arch-review`, `w-task-verification` skills | 0.8 | How agents consume research docs |
| 5 | #641 task body (archived) | 0.9 | Confirmed functional rename is complete |
| 6 | Active system file scan (`share/`, `serve/`, config) | 1.0 | 0 stale refs in functional files |

## 3. Analysis

### Reference Classification

| Category | Count | % | Historical? | Risk if unchanged |
|----------|-------|---|-------------|-------------------|
| CLI command snippets (`kanban-md ... --status ideation`) | 236 | 56% | Yes — commands executed at time of writing | None — no agent re-executes these |
| Table snapshots (`\| ideation \|`) | 51 | 12% | Yes — task status at time of writing | None — informational context only |
| Prose context (pipeline mentions, status descriptions) | 105 | 25% | Mixed | Low — agents may see stale terminology |
| Pipeline flow diagrams (`→ ideation →`) | ~20 | 5% | Mixed | Low — could mislead on current pipeline |
| **Total** | **412** | | | |

### Agent Consumption Pattern

Agents read research docs in three workflows: architect (background context), researcher (pre-flight dedup), verifier (existence check). None execute embedded commands or treat status values in tables as current truth. Confusion is possible but self-correcting — MCP server rejects `ideation` as a status.

### Approach Comparison

| Approach | Files Touched | Effort | Accuracy Risk | Value | Score |
|----------|---------------|--------|---------------|-------|-------|
| A: Full find-replace (all 412 refs) | 215 + 5 | Very High | **High** — falsifies historical CLI commands/snapshots | Low | 0.30 |
| B: Selective (flow diagrams only, ~20 refs) | ~15 | Low | Low | Low-Med | 0.55 |
| **C: Accept as historical + deprecation note** | 1 | Minimal | **None** | Medium | **0.82** |
| D: Do nothing | 0 | None | None | Low | 0.60 |

## 4. Recommendation

**(rec:) Option C — Accept historical docs as-is.** Add a completion note to `rename-ideation-to-research.md` confirming the functional rename is done. No mass prose updates.

**Confidence: 0.85** — The 412 references are overwhelmingly historical records (68% CLI commands + table snapshots). Updating them falsifies history with negligible benefit. The task context itself says "historical documents can retain original terminology as-is if needed."

**AC revision needed:** The current AC asks for mass updates across 220 files. Research shows this is counterproductive. Recommend closing with narrowed scope: confirm functional rename complete, accept historical prose as-is.

Challenge: FALLBACK — challenger agent not in agent roster. Self-assessed: no design alternatives to challenge for a prose-only documentation decision. Risk is purely cosmetic.

## 5. Follow-up Tasks

- Close #656 with revised scope (no mass prose update needed)
- If future confusion arises, create a targeted task at that point (YAGNI)
