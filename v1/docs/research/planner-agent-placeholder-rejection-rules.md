# Planner Agent Placeholder Rejection Rules

> **Owning task:** #903 - Add placeholder-task rejection rules to kanban-planner.agent.md
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #903 is the agent-file half of the planner placeholder-guardrail split from
task #899. Prior research already established that OwlBear should reject placeholder
board artifacts. The remaining question is how to keep #903 scoped to
`.github/agents/kanban-planner.agent.md`, which sections in that file should
carry the rule, and what rejection contract the architect should preserve.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `.github/agents/kanban-planner.agent.md` | Local | 1.0 | The planner prompt already separates hard constraints, scope boundaries, and self-check red flags, so the placeholder rule should land in the same control points |
| `.github/skills/task-decomposition/SKILL.md` | Local | .98 | The skill is the procedural mirror, which confirms the planner agent file can stay canonical while the skill mirror remains separate work |
| `docs/research/planner-placeholder-guardrails.md`, task #904 | Local | .97 | Prior research already split the work into agent canonical rule (#903) and skill mirror (#904); widening #903 would duplicate a sibling task |
| `docs/research/planner-temp-task-hygiene.md`, `docs/research/placeholder-task-rejection-guidance.md` | Local | .95 | `TEMP-planner-test` and bodyless tasks are real board artifacts, and the correct response is reject or refine rather than infer scope |
| GitHub Docs - Syntax for issue forms | External | .86 | Structured intake uses required fields and validation, so hard rejection rules belong at input time instead of as soft prose |
| GitHub Docs - Configuring issue templates for your repository | External | .84 | `blank_issues_enabled: false` is prior art for disabling blank intake paths instead of letting placeholders through |
| GitLab Docs - Description templates | External | .80 | Mature work trackers standardize scoped descriptions with templates or defaults rather than accepting empty work-item bodies |

## 3. Analysis

### 3.1 Scope fit

| Option | Scope fidelity | Drift risk | Board impact | Confidence |
|--------|----------------|------------|--------------|------------|
| Expand #903 to agent + skill | Low | High | Duplicates #904 and blurs canonical vs. mirror ownership | .18 |
| Move the rule into shared instructions | Medium | Medium | Over-broad; placeholder creation is planner-specific behavior | .41 |
| Keep #903 agent-only, leave #904 as the skill mirror | High | Low | Matches the existing split and preserves a single canonical source | .94 |

### 3.2 Rule placement inside the agent file

| Section | Best use in current file | Placeholder-rule fit | Recommendation |
|---------|--------------------------|----------------------|----------------|
| `critical_rules` | Hard non-negotiable planner constraints | Highest | Put the actual ban on `TEMP-*` titles and empty or scopeless bodies here |
| `boundaries` | Scope limits and do-not-cross rules | Medium | Useful reinforcement, but not strong enough as the only location |
| `red flags` | Self-check triggers before output | High | Add `TEMP-planner-test` as a stop-and-reassess example so the planner catches the failure mode before emitting commands |

### 3.3 Minimum rejection contract

| Trigger | Required planner behavior | Source basis |
|---------|---------------------------|--------------|
| Title begins `TEMP-` | Reject as a placeholder title | Prior placeholder evidence plus GitHub issue-form validation |
| Body is empty after frontmatter | Reject as blank intake | GitHub blank-issue disablement plus GitLab description templates |
| Body lacks scoped task content or AC | Refine the task or stop; do not emit `kanban-md create` output | Existing OwlBear guardrail docs plus structured-workflow prior art |
| Example needed | Use `TEMP-planner-test` explicitly | Matches the historical artifact and existing sibling-task ACs |

## 4. Recommendation (.94 confidence)

Keep #903 limited to `.github/agents/kanban-planner.agent.md`. The planner agent
file should remain the canonical source for this rule, while task #904 mirrors it
in the decomposition skill.

Within the agent file, put the hard prohibition in `critical_rules` and repeat the
failure mode in `red flags`. That is the smallest diff that makes the behavior
unambiguous:

- `critical_rules` forbids titles starting with `TEMP-`
- `critical_rules` forbids bodies that are empty after frontmatter or lack scoped task content
- the same rule text tells the planner to refine the task or stop instead of emitting a placeholder board artifact
- `red flags` uses `TEMP-planner-test` as the explicit rejected pattern

This matches OwlBear's current agent-file structure, keeps the skill mirror
separate, and follows external prior art that invalid intake should be blocked at
the point of creation rather than cleaned up downstream.

## 5. Follow-up Tasks

1. **Existing task #903 - Add placeholder-task rejection rules to kanban-planner.agent.md**
   Priority rationale: `important` because the canonical rule belongs at planner output time.
   Dependencies: none.
   One-line AC: add a hard ban on `TEMP-*` titles and empty or scopeless bodies, require refine-or-stop behavior, and include `TEMP-planner-test` as the rejected example.

2. **Existing task #904 - Add placeholder-task validation step to task-decomposition skill**
   Priority rationale: `important` because the skill should mirror the canonical rule after #903 lands.
   Dependencies: #903.
   One-line AC: add a validation or self-check step in the skill that rejects the same placeholder patterns and points back to the planner agent file.

No new kanban tasks were created in this research pass because the recommended
action items already exist as #903 and #904. Duplicating them would violate the
single-responsibility split established in `docs/research/planner-placeholder-guardrails.md`.
