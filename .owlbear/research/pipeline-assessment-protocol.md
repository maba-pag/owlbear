# Pipeline Instruction — Assessment Protocol

> **Owning task:** #1847 — P2-08: Pipeline instruction — assessment protocol
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Task #1847 adds memory assessment instructions to the pipeline protocol so agents know to call `assess_memories` at end-of-task. The `assess_memories` MCP tool was implemented in #1846 (archived). This task writes the instructions that make agents aware of the tool and when to call it.

Key constraint: use the exact framing text from the task body (verbatim, deliberate design). No scoring mechanics exposed to agents (opaque bucketing).

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `share/skills/r-pipeline-protocol/SKILL.md` §4 Post-task Reflection (L275-293) | 1.0 — current end-of-task protocol |
| 2 | `share/instructions/pipeline-agents.instructions.md` (full file) | 1.0 — target instruction file |
| 3 | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` L462-510 | 0.9 — tool signature |
| 4 | Task #1846 body — assess_memories AC and implementation | 0.9 — confirms tool contract |
| 5 | r-pipeline-protocol §1 Knowledge Pre-flight (L42-48) | 0.8 — symmetric start-of-task pattern |

## 3. Analysis

### 3.1 Insertion Points

| File | Location | Rationale |
|------|----------|-----------|
| `pipeline-agents.instructions.md` | New section after "Per-Agent Section Mapping" | End_work protocol is a distinct concern; needs own heading |
| `r-pipeline-protocol SKILL.md` | Insert before `save_memory` paragraph in Post-task Reflection (L277) | Assessment of recalled memories logically precedes creating new memories; maintains data-flow order (recall → use → assess → reflect) |

### 3.2 Design Decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Where in pipeline-agents.instructions.md | New `## Memory Assessment Protocol` section | Keeps Channel B section clean; assessment is a distinct lifecycle step |
| Where in r-pipeline-protocol | Subsection under Post-task Reflection | Natural home — both happen at end-of-task before `end_work` |
| Conditionality phrasing | "When `recall_memory` was called during this session" | Clear trigger; matches Knowledge Pre-flight symmetry |
| Tool call instruction | `assess_memories(assessments=[...], task_id="{task_id}")` | Matches actual tool signature from #1846 implementation |
| Framing approach | Verbatim text from task body, blockquoted | Task body explicitly states "do not rephrase or summarize" |
| Scoring explanation | None | AC1 requires "no scoring mechanics are explained" |

### 3.3 Scope of Changes

- `pipeline-agents.instructions.md`: ~20 lines added (section header + instruction text + verbatim framing)
- `r-pipeline-protocol SKILL.md`: ~5 lines added (mandatory reference + conditionality)
- No code changes. No other files affected.

## 4. Recommendation

Proceed with implementation — both insertion points are clear, the text is prescribed, and no architectural decisions are needed.

**Confidence: 0.92** — trivial scope, verbatim text provided, clear insertion points, no ambiguity.

Challenge: skipped (trivial docs task, no trade-off between options).

## 5. Follow-up Tasks

None needed. The AC is fully self-contained and implementation is trivial markdown editing.
