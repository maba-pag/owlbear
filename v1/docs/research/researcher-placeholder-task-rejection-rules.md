# Researcher Placeholder-Task Rejection Rules

> **Owning task:** #901 - Add placeholder-task rejection rules to researcher guidance
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #901 is the researcher-focused half of the placeholder-task guardrail split
from #900. The open question is how the researcher guidance should reject
`TEMP-*` titles and empty or unscoped task bodies without widening scope into
planner or architect rules, and where that rule should live so the researcher
refuses invalid inputs before it starts inventing scope.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `.github/agents/researcher.agent.md`, `.github/skills/research-workflow/SKILL.md` | Local | 1.0 | Current researcher guidance requires evidence-backed findings, but it does not explicitly reject `TEMP-*` titles or empty scoped bodies; Step 1 still says to ask questions when work is ambiguous |
| `docs/research/placeholder-task-rejection-guidance.md`, `docs/research/planner-temp-task-hygiene.md` | Local | .99 | The repo already treats `TEMP-planner-test` as board-noise evidence and recommends downstream rejection instead of inferred scope |
| `.github/agents/test-writer.agent.md`, `.github/agents/builder.agent.md` | Local | .96 | Later pipeline stages already block vague or empty inputs and explicitly say not to guess or invent AC |
| GitHub Docs - Syntax for issue forms | External | .87 | Structured intake uses required fields and validation, which is prior art for refusing underspecified work instead of inferring missing scope |
| GitHub Docs - Configuring issue templates for your repository | External | .86 | `blank_issues_enabled: false` is prior art for disabling blank intake paths rather than letting placeholders through |
| GitLab Docs - Description templates | External | .81 | Mature work trackers standardize scoped descriptions with templates and defaults instead of accepting empty work-item bodies |
| Atlassian Support - Configure advanced work item workflows | External | .80 | Workflow validators block invalid transition input before work items advance, which matches fail-fast researcher rejection |

## 3. Analysis

### 3.1 Scope fit

| Option | Scope fidelity | Drift risk | Board impact | Confidence |
|--------|----------------|------------|--------------|------------|
| Update `.github/agents/researcher.agent.md` only | Medium | Medium | Leaves the workflow skill's Step 1 ambiguity in place | .63 |
| Update `.github/skills/research-workflow/SKILL.md` only | Medium | Medium | Adds procedure, but the agent prompt still lacks a hard rule and concrete example | .68 |
| Update both the researcher agent file and the workflow skill | High | Low | Small docs-only diff that closes both policy and procedure gaps | .95 |

### 3.2 Best placement in `.github/agents/researcher.agent.md`

| Section | Current role | Placeholder-rule fit | Recommendation |
|--------|--------------|----------------------|----------------|
| `critical_rules` | Hard non-negotiable behavior | Highest | Add a hard rejection of `TEMP-*` titles and empty or unscoped bodies |
| `boundaries` | Defines what the researcher must not do | High | State that missing scoped body content alone is enough to refuse dispatch and that the researcher must not invent scope |
| `red flags` | Catches known failure modes during execution | High | Add `TEMP-planner-test` as the explicit stop-and-reassess example that points back to the owning task or research note |

### 3.3 Best placement in `.github/skills/research-workflow/SKILL.md`

| Location | Current behavior | Gap | Recommendation |
|---------|------------------|-----|----------------|
| `Step 1 - Clarify scope` | Says to ask questions if work is ambiguous | Bodyless placeholder tasks are invalid, not ambiguous | Add a fail-fast validation note before the `askQuestions` bullet |
| Workflow summary | Starts with `clarify scope` after claim | Does not distinguish invalid inputs from clarifiable inputs | Clarify that `TEMP-*` or empty scoped bodies must be refused before research starts |
| Self-critique / checklist | Focuses on sources and follow-up tasks | Does not remind the researcher to reject invalid task bodies | Add a quick check that invalid placeholder inputs were blocked rather than researched |

### 3.4 Minimum researcher rejection contract

| Trigger | Required behavior | Why |
|--------|-------------------|-----|
| Title matches `TEMP-*` | Reject as placeholder input | Prevents planner artifacts from becoming fake research scope |
| Body is empty or lacks scoped task content or AC | Refuse dispatch even if the title looks normal | Missing body content alone makes research speculative |
| Task has valid scope but still needs detail | Ask targeted questions only after a scoped body exists | Preserves clarification without inventing missing work |
| Example note | Use `TEMP-planner-test` and point back to the owning task or `docs/research/planner-temp-task-hygiene.md` | Keeps the audit trail concrete and reproducible |

## 4. Recommendation (.95 confidence)

Keep #901 limited to researcher guidance, but update both
`.github/agents/researcher.agent.md` and
`.github/skills/research-workflow/SKILL.md` in the same task.

This is the smallest change that closes the real gap:

- `critical_rules` should explicitly reject `TEMP-*` titles and empty or
  unscoped bodies
- `boundaries` should say missing scoped body content alone is enough to refuse
  dispatch and that the researcher must not invent scope
- `research-workflow` Step 1 should fail fast on placeholder or bodyless tasks
  before it reaches the `askQuestions` path
- at least one example should use `TEMP-planner-test` and point back to the
  owning task or `docs/research/planner-temp-task-hygiene.md`

That preserves `askQuestions` for legitimately scoped but ambiguous work while
making placeholder tasks invalid inputs instead of quasi-research prompts.

## 5. Follow-up Tasks

1. **Existing task #901 - Add placeholder-task rejection rules to researcher guidance**
   Priority rationale: `important` because the researcher is the first
   downstream gate that can stop placeholder tasks before they become invented
   research scope.
   Dependencies: none.
   One-line AC: update `.github/agents/researcher.agent.md` and
   `.github/skills/research-workflow/SKILL.md` so they reject `TEMP-*` and
   empty or unscoped task bodies, state that missing scoped body content alone
   is enough to refuse dispatch, and include a `TEMP-planner-test` example that
   points back to the owning task or
   `docs/research/planner-temp-task-hygiene.md`.

No new kanban tasks were created in this research pass because the recommended
action is already captured by #901. Creating another task would duplicate the
same researcher-guidance scope.
