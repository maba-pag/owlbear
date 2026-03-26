# Placeholder Task Rejection Guidance

> **Owning task:** #900 - Add placeholder-task rejection rules to researcher and architect guidance
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #900 asks whether OwlBear should explicitly reject placeholder kanban items,
especially titles matching `TEMP-*` or tasks with no scoped body content, in the
researcher and architect stages. The question is not whether intake should improve
(#899 already covers that), but whether downstream safety-net guidance should make
these items invalid inputs instead of turning them into invented scope.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `docs/research/planner-temp-task-hygiene.md` | Local | 1.0 | #855/#856 prove placeholder tasks can survive long enough to hit downstream gates; the prior research already recommends researcher/architect guardrails |
| `.github/agents/researcher.agent.md`, `.github/skills/research-workflow/SKILL.md` | Local | .99 | Researcher guidance requires sourced recommendations but does not explicitly reject `TEMP-*` or bodyless tasks as invalid inputs |
| `.github/agents/architect.agent.md`, `.github/skills/arch-review/SKILL.md` | Local | .99 | Architect guidance blocks vague AC, but the current workflow also omits explicit placeholder-task rejection language |
| `.github/agents/test-writer.agent.md`, `.github/instructions/agent-common.instructions.md` | Local | .97 | Later pipeline stages already block vague or empty inputs and use handoff notes instead of guessing scope |
| GitHub Docs - Syntax for issue forms | External | .87 | Standard prior art uses required fields and validation to prevent underspecified work items |
| GitHub Docs - Configuring issue templates for your repository | External | .86 | Repositories can disable blank issues entirely and steer contributors into structured intake |
| GitLab Docs - Description templates | External | .80 | Mature trackers standardize issue descriptions with reusable templates rather than accepting free-form placeholders |

## 3. Analysis

### 3.1 Current gap

| Location | Existing safeguard | Missing rule | Effect |
|----------|--------------------|--------------|--------|
| researcher.agent.md | Requires evidence-backed research and follow-up tasks | No explicit `TEMP-*` or empty-body invalid-input rule | Researcher can still spend cycles trying to infer scope |
| research-workflow skill | Tells researcher to clarify scope and gather sources | No early exit for bodyless placeholder tasks | Workflow nudges clarification, not refusal |
| architect.agent.md | Rejects vague AC and allows block/refine | No named placeholder-task pattern or example | Architect may treat a planning artifact as a real backlog item |
| arch-review skill | Has block verdict and AC review steps | No rule that missing scoped body content alone is enough to refuse dispatch | `Read task + refine AC` can be misread as license to invent AC |

### 3.2 Options

| Option | Coverage | Drift resistance | Diff size | Confidence |
|--------|----------|------------------|-----------|------------|
| Update agent files only | Medium | Medium | Smallest | .73 |
| Update workflow skills only | Medium | Medium | Small | .69 |
| Update both agent files and skills, with one shared rejection-note example | High | High | Small docs-only change | .94 |

### 3.3 Recommended rejection contract

| Trigger | Required behavior | Why |
|---------|-------------------|-----|
| Title matches `TEMP-*` | Reject as placeholder input | Explicit pattern keeps planners' temporary artifacts from becoming fake scope |
| Body has no scoped context or AC | Refuse dispatch even if title looks normal | Missing body content is enough to make research or approval speculative |
| Placeholder task needs context | Point back to owning task or research note, do not invent AC | Matches OwlBear's handoff discipline and preserves audit trail |

Recommended note pattern:

> Placeholder task rejected: `TEMP-planner-test` / empty scoped body is not valid
> research or architecture input. See the owning task or
> `docs/research/planner-temp-task-hygiene.md`. Refine the task with concrete
> context and acceptance criteria before redispatch.

## 4. Recommendation (.94 confidence)

Add the rule in both places that actually steer behavior:

1. Role files:
   - `.github/agents/researcher.agent.md`
   - `.github/agents/architect.agent.md`
2. Workflow skills:
   - `.github/skills/research-workflow/SKILL.md`
   - `.github/skills/arch-review/SKILL.md`

This is the smallest change that closes the gap without touching `src/` or `tests/`.
It aligns with existing OwlBear practice:

- planner-side intake should prevent placeholders (#899)
- researcher/architect should reject any placeholders that still leak through
- later stages already block vague or empty contracts instead of guessing

## 5. Follow-up Tasks

1. **#901 - Add placeholder-task rejection rules to researcher guidance**
   Priority rationale: `important` because the researcher is the first downstream
   safety net after ideation.
   Dependencies: none.
   One-line AC: researcher guidance explicitly rejects `TEMP-*` or unscoped-body
   tasks, states missing scoped body content is enough to refuse dispatch, and
   shows a `TEMP-planner-test` note pointing back to the owning artifact.

   Created command:
   `kanban\kanban-md.exe create "Add placeholder-task rejection rules to researcher guidance" --priority important --status ideation --tags "agent,docs,scope:copilot,type:docs" ...`

2. **#902 - Add placeholder-task rejection rules to architect guidance**
   Priority rationale: `important` because backlog review is the last place to stop
   placeholders before implementation planning.
   Dependencies: none.
   One-line AC: architect guidance explicitly rejects `TEMP-*` or unscoped-body
   tasks, states missing scoped body content is enough to block back to ideation,
   and shows a `TEMP-planner-test` note pointing back to the owning artifact.

   Created command:
   `kanban\kanban-md.exe create "Add placeholder-task rejection rules to architect guidance" --priority important --status ideation --tags "agent,docs,scope:copilot,type:docs" ...`
