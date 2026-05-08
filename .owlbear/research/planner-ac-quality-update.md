# Planner Skill Update — AC Quality Integration

> **Owning task:** #1405 — A2: Planner skill update — AC drafting via h-ac-quality, consolidation-test creation, routing
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Task #1405 requires three changes to the planner agent toolchain:
1. Wire `h-ac-quality` into the AC drafting workflow
2. Add consolidation-test creation logic
3. Enforce routing: planner never creates at `todo` — only architect moves `backlog→todo`

Prerequisite A1 (h-ac-quality skill creation) is confirmed complete — skill exists at `share/skills/h-ac-quality/SKILL.md`.

## 2. Current State Audit

| File | Current state | Gap |
|------|--------------|-----|
| `share/skills/w-task-decomposition/SKILL.md` | `required_reading` = `r-pipeline-protocol` only. Durability Principles (line ~73) provide 4 inline AC rules. No `h-ac-quality` reference. No consolidation-test logic. | Missing: h-ac-quality ref, consolidation-test step, explicit `todo` prohibition |
| `share/agents/planner.agent.md` | `required_reading` = `r-pipeline-protocol`, `w-task-decomposition`. No `h-ac-quality` reference in `<critical_rules>`. | Missing: h-ac-quality in required_reading or critical_rules |

### Status Routing (current)

- Decomposition mode default: `research`
- Shortcut mode default: `backlog` (or caller-provided)
- No explicit prohibition on caller requesting `todo`

## 3. Implementation Approach

### Change 1: h-ac-quality reference in w-task-decomposition

**Location:** `## Durability Principles` section (after Step 3).
**Action:** Add `h-ac-quality` to the section as the authoritative expanded schema for AC drafting. Keep existing 4 inline bullets as a quick summary but reference h-ac-quality for the full validation checklist.

Also add to Step 0 required_reading list: `h-ac-quality` alongside `r-pipeline-protocol`.

### Change 2: Consolidation-test creation logic

**Location:** New subsection within Step 3 or as a new Step 3a.
**Rule (from Brief D4):** When ≥2 implementation tasks exist under a common parent during decomposition, create one consolidation-test task with:
- Title pattern: `"consolidation test: {feature name}"`
- `depends_on:` all sibling implementation task IDs
- Created at `backlog` status alongside implementation tasks
- No consolidation-test needed for single-task shortcut mode

**Trigger conditions:**
- Only in decomposition mode (not shortcut)
- ≥2 implementation tasks (not test tasks) share the same parent
- No existing consolidation-test task for that parent

### Change 3: Status routing enforcement

**Location:** Step 6 (Create Tasks) — add explicit prohibition.
**Rule:** Planner must never create tasks at `todo` status. The `todo` status is reserved for architect promotion via `backlog→todo`. Decomposition creates at `research`; shortcut creates at `backlog` or `research` per caller.

Also add to `planner.agent.md` `<critical_rules>`: "Never create tasks at `todo` — only architect moves `backlog→todo`."

### Change 4: planner.agent.md h-ac-quality reference

**Location:** `<required_reading>` or `<critical_rules>` section.
**Action:** Add `h-ac-quality` to `<required_reading>` list.

## 4. Recommendation

Confidence: **0.92** — straightforward .md edits with clear specifications from the brief. All target files exist, all insertion points are identified, no ambiguity in the changes.

Challenge: SKIP — trivial T1 modification with no trade-offs or alternative approaches. Changes are prescribed by an approved brief.

## 5. Follow-up Tasks

Single implementation task needed: modify the two files per the approach above. Task should proceed at `backlog` for architect gate under new AC rules.
