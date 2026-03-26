# Planner Temp Task Hygiene

> **Owning task:** #855 - TEMP-planner-test
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #855 is an ideation item titled `TEMP-planner-test` with no body content or
acceptance criteria. Archived task #856 has the same placeholder title. This
research checks whether #855 should be expanded into real work and, if not, what
guardrails should prevent similar placeholder tasks from surviving to later
pipeline stages.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `kanban/tasks/855-temp-planner-test.md`, `kanban/tasks/856-temp-planner-test.md`, `kanban/config.yml` | Local | 1.0 | #855 is a bodyless placeholder, #856 is an archived duplicate, and stale claims expire after 1 hour |
| `.github/instructions/research-docs.instructions.md`, `.github/copilot-instructions.md` | Local | .99 | Research tasks are expected to say what the research must produce, and task files normally carry body content plus acceptance criteria |
| `.github/skills/wave-planning/SKILL.md`, `.github/agents/test-writer.agent.md` | Local | .97 | Downstream pipeline stages rely on concrete task content and explicitly block vague or empty inputs |
| GitHub Docs - Syntax for issue forms | External | .86 | Structured forms support required fields and validation, which is standard prior art for stopping underspecified work at intake |
| GitHub Docs - Configuring issue templates for your repository | External | .84 | Repositories can disable blank issues and steer contributors into structured templates/forms instead of free-form placeholders |

## 3. Analysis

### 3.1 Current board evidence

| Item | Current state | Implication |
|------|---------------|-------------|
| #855 | `ideation`, title `TEMP-planner-test`, no body content | No researchable scope exists |
| #856 | Archived duplicate with the same placeholder title | Confirms this is board noise, not a unique feature request |
| Claim timeout | `claim_timeout: 1h` | The stale `test-agent` claim was not evidence of active ownership |

### 3.2 Process fit

| Rule | Evidence | Effect on #855 |
|------|----------|----------------|
| Research tasks should already say what the research must produce | `research-docs.instructions.md` | #855 does not meet the entry condition for normal research |
| Tasks are expected to have scoped body content and acceptance criteria | `copilot-instructions.md` | #855 lacks the minimum structure for downstream execution |
| Downstream agents block vague or empty task inputs rather than inventing scope | `test-writer.agent.md` | Advancing #855 as real work only creates churn and speculative AC |
| Structured intake with required fields is normal prior art | GitHub issue forms/templates docs | Preventing placeholders at creation time is lower-cost than cleaning them up later |

### 3.3 Options

| Option | Outcome | Trade-off | Confidence |
|--------|---------|-----------|------------|
| Advance #855 as if it were a real feature | Fastest short-term path | Forces later agents to invent scope and violates evidence-over-claims rules | .04 |
| Archive #855 immediately and stop there | Removes one artifact | Leaves the creation and downstream-review gaps unchanged | .61 |
| Treat #855 as evidence, keep it as a historical research handoff, and add guardrail follow-ups | Preserves the audit trail and fixes the root cause | Slightly more board overhead | .93 |

## 4. Recommendation (.93 confidence)

Do not derive feature or implementation scope from #855. The task is a temporary
board artifact, not a partially specified feature. The correct response is to use
task #855 as evidence of a board-hygiene gap, then close the gap in two places:

1. At creation time, planners should not emit `TEMP-*` titles or empty task bodies.
2. At downstream review time, researcher/architect guidance should refuse to turn
   placeholder tasks into executable scope.

The owning task #855 should move through the architect gate as a historical or
cleanup item, not as a builder handoff.

## 5. Follow-up Tasks

1. **#899 - Add planner guardrails for placeholder task titles and empty bodies**
   Priority rationale: `important` because creation-time rejection is the cheapest
   place to stop board noise.
   Dependencies: none.
   One-line AC: planner guidance explicitly forbids `TEMP-*` titles and empty task
   bodies and tells the planner to refine or stop instead of leaving placeholders.

2. **#900 - Add placeholder-task rejection rules to researcher and architect guidance**
   Priority rationale: `important` because downstream gates still need a safety net
   when placeholder items bypass creation-time checks.
   Dependencies: none.
   One-line AC: researcher/architect guidance explicitly blocks, refines, or archives
   `TEMP-*` or bodyless tasks instead of expanding them into implementation scope.

No separate cleanup task was created for #855 itself. This owning task is already
the evidence trail for the artifact and should not be turned into feature work.
