# Architect Placeholder Rejection Rules

> **Owning task:** #902 - Add placeholder-task rejection rules to architect guidance
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #902 is the architect-stage half of the placeholder-task rejection split from
task #900. Prior research already established that `TEMP-*` titles and bodyless
tasks should not be expanded into invented work. The remaining question is
whether #902 should stay a single architect-gate task touching both
`.github/agents/architect.agent.md` and `.github/skills/arch-review/SKILL.md`,
and where each rule belongs inside the architect guidance.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `.github/agents/architect.agent.md`, `.github/skills/arch-review/SKILL.md` | Local | 1.0 | The architect gate already blocks vague work in general, but it does not explicitly reject `TEMP-*` titles or empty scoped bodies |
| `docs/research/placeholder-task-rejection-guidance.md`, `kanban/tasks/900-add-placeholder-task-rejection-rules-to-researcher.md` | Local | .99 | Upstream research already narrowed the architect follow-up to #902 and recommended updating both the architect agent file and the architect workflow skill |
| `kanban/tasks/695-add-single-domain-validation-to-architect-gate.md` | Local | .94 | Repo precedent shows architect tasks may touch either the agent file alone or both agent and skill, depending on where the missing contract text actually lives |
| GitHub Docs - Syntax for issue forms | External | .86 | Structured intake uses required fields and validations instead of inferring missing work-item scope |
| GitHub Docs - Configuring issue templates for your repository | External | .84 | `blank_issues_enabled: false` is explicit prior art for refusing blank intake paths |
| Atlassian Support - Configure advanced work item workflows | External | .83 | Validators check transition input before the transition is performed, and failed validators stop the work item from progressing |
| GitLab Docs - Description templates | External | .80 | Standardized description templates and defaults are normal prior art for requiring scoped task bodies |

## 3. Analysis

### 3.1 Scope fit

| Option | Scope fidelity | Drift risk | Board overhead | Confidence |
|--------|----------------|------------|----------------|------------|
| Split #902 into architect.agent-only and arch-review-only tasks | Medium | Medium | Higher | .46 |
| Update only `.github/agents/architect.agent.md` | Low | High | Low | .19 |
| Keep #902 as one architect-gate task covering both files | High | Low | Low | .95 |

The planner split from #899 does not transfer directly here. For planner work,
the agent file is the canonical rule source and the skill is a separate mirror.
For architect work, task #900 already created a single stage-specific child task,
and the current gap is split across two complementary parts of the same backlog
gate: the role file needs the named invalid-input rule, while the skill needs the
procedural refusal path.

### 3.2 Rule placement inside the architect gate

| Location | Best use in current file | Placeholder-rule fit | Recommendation |
|----------|--------------------------|----------------------|----------------|
| `architect.agent.md` `critical_rules` / `boundaries` / red flags | Named hard constraint plus visible failure mode | High | Add the explicit `TEMP-*` invalid-input rule, state that missing scoped body content is enough to block back to ideation, and include the `TEMP-planner-test` example |
| `arch-review` Step 1 | Early task-read contract | High | Say that empty or unscoped task bodies are sufficient reason to refuse dispatch before refinement begins |
| `arch-review` Step 4 | Decision and routing contract | High | Explicitly block back to `ideation` instead of refining invented AC when scoped body content is missing |

### 3.3 Minimum rejection contract

| Trigger | Required architect behavior | Source basis |
|---------|-----------------------------|--------------|
| Title begins `TEMP-` | Treat as invalid backlog input, not a refinement candidate | Prior placeholder evidence plus structured-intake prior art |
| Body is empty or lacks scoped context / AC | Refuse dispatch and block back to `ideation` | Current architect gate semantics plus workflow-validator prior art |
| Placeholder still needs context | Point back to the owning task or `docs/research/planner-temp-task-hygiene.md` instead of inventing scope | Existing OwlBear handoff discipline |
| Example needed | Use `TEMP-planner-test` explicitly | Matches the historical artifact behind #855 and #856 |

Recommended note pattern:

> Placeholder task rejected: `TEMP-planner-test` / missing scoped body content is
> not valid architect input. See the owning task or
> `docs/research/planner-temp-task-hygiene.md`. Add concrete context and
> acceptance criteria before re-dispatch.

## 4. Recommendation (.95 confidence)

Keep #902 as a single docs-only architect-gate task.

Update `.github/agents/architect.agent.md` with the named invalid-input rule and
the `TEMP-planner-test` example. Update `.github/skills/arch-review/SKILL.md`
with the procedural refusal path so empty or unscoped task bodies are rejected
before refinement and blocked back to `ideation` instead of being turned into
invented acceptance criteria.

This is the smallest change that closes prompt drift while preserving the split
already created by #900. A further split would add board overhead without
clarifying the architect-stage contract.

## 5. Follow-up Tasks

1. **Existing task #902 - Add placeholder-task rejection rules to architect guidance**
   Priority rationale: `important` because backlog review is the last place to
   stop placeholder work before implementation planning.
   Dependencies: none.
   One-line AC: architect guidance rejects `TEMP-*` and unscoped bodies, blocks
   missing scoped body content back to `ideation`, and uses `TEMP-planner-test`
   as the rejection example pointing to the owning task or
   `docs/research/planner-temp-task-hygiene.md`.

No new kanban tasks were created in this research pass because #902 already is
the concrete architect-stage follow-up created by #900. Splitting agent and
skill again would duplicate the same backlog-gate change.
