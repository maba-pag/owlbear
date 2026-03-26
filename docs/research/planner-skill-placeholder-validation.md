# Planner Skill Placeholder Validation

> **Owning task:** #904 - Add placeholder-task validation step to task-decomposition skill
> **Date:** 2026-03-22  **Status:** Complete

## 1. Context and Question

Task #904 is the skill-file half of the planner placeholder-guardrail split from
task #899. Task #903 already made `.github/agents/kanban-planner.agent.md` the
canonical rule for rejecting placeholder tasks. The remaining question is how to
mirror that rule in `.github/skills/task-decomposition/SKILL.md` without
creating a second source of truth or widening scope beyond the skill file.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `.github/skills/task-decomposition/SKILL.md` | Local | 1.0 | The skill owns the procedural decomposition flow, but it still lacks an explicit placeholder-task validation step or self-check |
| `.github/agents/kanban-planner.agent.md`, task #903 | Local | .99 | The canonical planner rule already exists, so the skill should mirror it and point back to the agent file instead of redefining policy |
| `docs/research/planner-placeholder-guardrails.md`, `docs/research/planner-agent-placeholder-rejection-rules.md` | Local | .97 | Prior research already split the work into agent canonical rule (#903) and skill mirror (#904); creating new tasks would duplicate that split |
| `docs/research/planner-temp-task-hygiene.md`, tasks #855/#856 | Local | .94 | `TEMP-planner-test` and empty bodies were real board artifacts, so the skill needs a visible fail-fast check before command emission |
| GitHub Docs - Syntax for issue forms | External | .86 | Required fields and validation are intake-time controls, which supports a pre-output validation step rather than downstream cleanup |
| GitHub Docs - Configuring issue templates for your repository | External | .84 | `blank_issues_enabled: false` is prior art for refusing blank intake paths instead of letting placeholders reach the board |
| Atlassian Support - Configure advanced work item workflows | External | .82 | Validators block invalid input before a transition completes, which matches refine-or-stop behavior before `kanban-md create` output |

## 3. Analysis

### 3.1 Scope fit

| Option | Scope fidelity | Drift risk | Builder clarity | Confidence |
|--------|----------------|------------|-----------------|------------|
| Expand #904 to update both the agent file and the skill | Low | High | Duplicates archived task #903 and blurs canonical ownership | .14 |
| Move the rule into shared instructions only | Medium | Medium | Too broad for planner-specific behavior; weak procedural guidance | .38 |
| Keep #904 skill-only and mirror the canonical agent rule | High | Low | Matches the existing split and keeps the implementation atomic | .95 |

### 3.2 Minimum skill contract

| Skill location | Why it fits | Recommendation |
|----------------|-------------|----------------|
| Workflow step before task generation | Earliest procedural checkpoint before output | Add a fail-fast validation step for `TEMP-*` titles and empty or unscoped bodies |
| Self-critique checklist | Final guard against prompt drift | Add a checklist item that re-checks placeholder-task rejection |
| Example or red-flag text | Makes the failure mode obvious to the planner | Use `TEMP-planner-test` and tell the planner to refine the task or stop |

### 3.3 Required mirror behavior

| Trigger | Required skill behavior | Source basis |
|---------|-------------------------|--------------|
| Title begins `TEMP-` | Stop decomposition and refine the task or stop entirely before emitting commands | Planner agent rule plus GitHub issue-form validation |
| Body is empty after frontmatter | Treat as invalid intake; do not emit a placeholder task | Planner research plus blank-issue disablement prior art |
| Body lacks scoped task content or AC | Refine the task or stop instead of inventing scope in the skill | Existing OwlBear placeholder research plus workflow-validator prior art |
| Canonical rule lookup | Point back to `.github/agents/kanban-planner.agent.md` | The split already established by #899 and #903 |
| Example needed | Use `TEMP-planner-test` explicitly | Matches the historical artifact in #855 and #856 |

## 4. Recommendation (.95 confidence)

Keep #904 limited to `.github/skills/task-decomposition/SKILL.md`. The skill
should mirror the canonical planner rule with a fail-fast validation step and a
final self-check, while pointing back to `.github/agents/kanban-planner.agent.md`
as the rule owner.

That is the smallest diff that satisfies the task and avoids prompt drift:

- add placeholder-task validation before `kanban-md create` commands are generated
- reject `TEMP-*` titles and empty or unscoped bodies explicitly
- tell the planner to refine the task or stop instead of emitting the placeholder task
- include `TEMP-planner-test` as the visible rejected example
- state that `kanban-planner.agent.md` remains the canonical rule

This matches the existing canonical-plus-mirror structure already used in the
planner guardrail work, keeps the task docs-only, and follows external intake
validation prior art that invalid work items should be blocked before they are
created.

## 5. Follow-up Tasks

1. **Existing task #903 - Add placeholder-task rejection rules to kanban-planner.agent.md**
   Priority rationale: `important` because the canonical rule belongs at planner output time and is already complete.
   Dependencies: none.
   One-line AC: keep the hard prohibition on `TEMP-*` titles and empty or scopeless bodies in the planner agent file.

2. **Existing task #904 - Add placeholder-task validation step to task-decomposition skill**
   Priority rationale: `important` because the skill should mirror the canonical rule procedurally.
   Dependencies: #903.
   One-line AC: add a fail-fast validation step or self-check in the skill that rejects the same placeholder patterns and points back to the planner agent file.

No new kanban tasks were created in this research pass because the recommended
split already exists as #903 and #904, and #903 is archived. Creating duplicate
tasks would add board noise rather than new action.
