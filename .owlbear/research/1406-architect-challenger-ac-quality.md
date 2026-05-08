# Architect/Challenger Skill Update — AC Validation & Consolidation-Test Backstop

> **Owning task:** #1406 — A3: Architect/challenger skill update
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Brief #1403 introduces the "checker subagent pattern": the architect delegates AC quality validation to the challenger rather than doing it itself. Task #1406 requires wiring `h-ac-quality` into the architect/challenger workflow and adding consolidation-test backstop detection. Prerequisite A1 (#1404, `h-ac-quality` skill) is complete. A2 (#1405, planner update) is done — planner now drafts AC using `h-ac-quality` and creates consolidation-test tasks.

**Core question:** What changes are needed to `w-arch-review`, `challenger.agent.md`, and `architect.agent.md`, and what constraints apply (especially challenger tool access)?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | Brief #1403 — D1 (AC quality), D4 (consolidation-test), checker pattern | Brief | 1.0 |
| S2 | `w-arch-review/SKILL.md` — current Steps 2, 2.1, 2.5 | Codebase | 1.0 |
| S3 | `challenger.agent.md` — tools, I/O contract, boundaries | Codebase | 1.0 |
| S4 | `architect.agent.md` — tools, agents, required_reading | Codebase | 0.95 |
| S5 | `h-ac-quality/SKILL.md` — two-tier schema, validation checklist | Codebase | 1.0 |
| S6 | `w-task-decomposition/SKILL.md` — consolidation-test rule | Codebase | 0.9 |
| S7 | Prior research: challenger-arch-review-integration (#468) | Research | 0.8 |

## 3. Analysis

### 3.1 Challenger Tool Constraint

The challenger's tool list is strictly read-only codebase tools — no `ob-kanban/*`:
```
tools: [read/readFile, ..., search/textSearch, search/searchSubagent, search/usages]
```

Consolidation-test detection requires inspecting sibling tasks under the same parent (`list_tasks`, `show_task`). Two approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **A: Architect passes sibling data in prompt** | No tool change; clean separation; challenger stays read-only | Architect must gather and format sibling data before dispatch |
| **B: Add kanban read tools to challenger** | Challenger independently verifies | Adds coupling; violates read-only-codebase principle; increases surface area |

**Recommendation: Approach A.** The architect already has kanban tools and gathers context in Step 1. Passing sibling task data as a new input field (`sibling_tasks`) keeps the challenger focused and pure.

### 3.2 Changes Per File (3 files, 4 logical changes)

| File | Change | Scope |
|------|--------|-------|
| `w-arch-review/SKILL.md` | 1. Expand Step 2.5 prompt to include AC quality validation via `h-ac-quality` rules. 2. Add `sibling_tasks` data gathering in Step 1 (or new Step 2.4). 3. Add post-challenger action table: AC quality finding → REFINE; missing consolidation-test → delegate to planner. | Primary |
| `challenger.agent.md` | 4. Add `h-ac-quality` to `<required_reading>`. 5. Add AC quality validation + consolidation-test detection responsibilities to `<critical_rules>`. 6. Add `sibling_tasks` to input contract. | Secondary |
| `architect.agent.md` | 7. Add `h-ac-quality` to `<required_reading>`. | Minimal |

### 3.3 Checker Subagent Pattern — No Overlap

The Brief states: "Architect acts on AC quality only when challenger flags issues." This means:
- Architect Step 2 keeps its architecture evaluation criteria (module layering, dependency correctness, KISS/YAGNI, etc.)
- Architect does NOT proactively validate AC wording quality itself
- The existing Step 2 "Interface clarity" criterion is about architectural interface design, not AC wording — no overlap
- Challenger validates AC wording quality using `h-ac-quality` rules (B1-B3, P1-P3)
- Architect acts on challenger findings: AC quality issue → REFINE; missing consolidation-test → planner dispatch

### 3.4 Consolidation-Test Backstop Logic

Challenger receives `sibling_tasks` (from architect) and applies:
1. Count implementation siblings (exclude tasks titled "consolidation test: *")
2. If ≥2 implementation siblings AND no sibling with "consolidation test" in title → flag
3. Single tasks (no parent, no siblings) → skip check

This is a backstop for the planner's primary responsibility (A2/#1405). It catches decompositions where the planner missed creating the consolidation-test task.

### 3.5 Step 2.5 Prompt Expansion

Current challenger input contract fields: `task_id`, `proposed_verdict`, `reasoning`, `ac_lines`, `codebase_evidence`, `research-doc`.

New field: `sibling_tasks` (optional, string) — formatted list of sibling task IDs and titles under the same parent. Architect gathers this via `list_tasks` filtered by parent in Step 1.

The challenger's 6-section output already accommodates AC quality findings in "Challenges" (category: `ac-quality` or `consolidation-test-gap`).

## 4. Recommendation

**Confidence: 0.88.** Straightforward skill-file modifications with no code changes. All three files are `.md` skill/agent definitions. The only design decision (Approach A vs B for consolidation-test detection) is clearly resolved by the challenger's read-only principle.

Challenge: skipped (T1 autonomous — no new capability, no architecture change; process AC modifications within existing checker subagent pattern).

## 5. Follow-up Tasks

One implementation task at `backlog` (the current task #1406 itself advances to `backlog` — no additional follow-ups needed since this task IS the implementation deliverable).
