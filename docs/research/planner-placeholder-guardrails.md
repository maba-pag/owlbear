# Planner Placeholder Guardrails

> **Owning task:** #899 - Add planner guardrails for placeholder task titles and empty bodies
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #899 turns the #855/#856 placeholder evidence into a concrete planner rule. The research question is where the guardrail should live so the planner stops emitting placeholder work items instead of leaving `TEMP-*` titles or empty or scopeless task bodies on the board.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `.github/agents/kanban-planner.agent.md` | Local | 1.0 | Planner already has red-flag language for empty bodies, so the missing piece is a placeholder-specific rule plus a refine/stop action |
| `.github/skills/task-decomposition/SKILL.md` | Local | .97 | The skill owns the procedural decomposition checklist but currently has no placeholder-title/body validation step |
| `docs/research/planner-temp-task-hygiene.md`, `kanban/tasks/855-temp-planner-test.md`, `kanban/tasks/856-temp-planner-test.md` | Local | .96 | #855/#856 are repeated TEMP placeholders and the prior research already recommended planner-side prevention |
| `docs/research/task-decomposition-rules.md`, `kanban/tasks/694-update-kanban-planner-with-single-domain.md` | Local | .91 | Prior planner-quality work put the canonical rule in the planner agent file and mirrored enforcement in the supporting skill |
| GitHub Docs - Syntax for issue forms | External | .86 | Structured issue intake supports required fields, defaults, and validation instead of free-form placeholders |
| GitHub Docs - Configuring issue templates for your repository | External | .84 | Repositories can disable blank issues entirely, which is direct prior art for refusing blank or placeholder work items at intake |
| Atlassian Support - Configure advanced work item workflows | External | .80 | Validators block invalid transition input before a work item advances, which is prior art for stop/refine behavior instead of downstream cleanup |

## 3. Analysis

### 3.1 Current local gap

| Evidence | Current state | Implication |
|----------|---------------|-------------|
| Planner agent file | Warns about empty bodies, but does not forbid `TEMP-*` titles or say to refine/stop | Placeholder titles can still be emitted as board artifacts |
| Task-decomposition skill | No placeholder-title/body validation step | Even if the prompt hints at quality, the procedural checklist does not re-check it |
| #855/#856 research trail | The same placeholder title appeared twice, including one archived duplicate | This is not theoretical debt; it already happened on the board |

### 3.2 Options

| Option | Coverage | Drift risk | Fit with current patterns | Confidence |
|--------|----------|------------|---------------------------|------------|
| Agent file only | Canonical rule exists at prompt level | Medium | Partial; the skill would still lack an explicit self-check | .71 |
| Skill only | Procedural check exists before output | High | Weak; the planner prompt would still not define the rule clearly | .46 |
| Agent canonical + skill mirror | Prompt defines the rule and the skill re-checks it during decomposition | Low | Strong; matches prior planner rule placement from #694 | .92 |

## 4. Recommendation (.92 confidence)

Make `.github/agents/kanban-planner.agent.md` the canonical source for placeholder-task rejection and mirror the same stop/refine behavior in `.github/skills/task-decomposition/SKILL.md`.

This is the best fit for current OwlBear structure. Local precedent from the single-domain planner work shows that canonical planner constraints belong in the agent file while the skill carries the operational checklist. External issue-form and workflow-validator prior art also points to the same principle: reject incomplete intake early instead of letting it travel downstream and requiring later cleanup.

Do not move this rule into shared instructions. Placeholder-task rejection at creation time is planner-specific behavior, while downstream safety-net work is already separately tracked by #900.

## 5. Follow-up Tasks

1. **#903 - Add placeholder-task rejection rules to kanban-planner.agent.md**
   Priority rationale: `important` because creation-time rejection is the lowest-cost place to stop board noise.
   Dependencies: none.
   One-line AC: the planner agent file explicitly forbids `TEMP-*` titles and empty or scopeless bodies, tells the planner to refine or stop instead of emitting the task, and uses `TEMP-planner-test` as the rejected example.

2. **#904 - Add placeholder-task validation step to task-decomposition skill**
   Priority rationale: `important` because the planner skill should mirror the canonical rule before command emission.
   Dependencies: #903.
   One-line AC: the task-decomposition skill adds a placeholder-task validation step or self-check that rejects `TEMP-*` titles and empty or scopeless bodies while pointing back to the canonical planner rule.
