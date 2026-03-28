# Add argument-hint to User-Invocable Skills

> **Owning task:** #43 — Add argument-hint to user-invocable skills
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #43 adds `argument-hint` YAML frontmatter to user-invocable skills so the VS Code chat input shows placeholder text when a skill is invoked via `/skill-name`. The AC specifies project-definition and retro. This research validates the property, proposes hint text, and identifies additional skills that would benefit.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Agent Skills docs | https://code.visualstudio.com/docs/copilot/customization/agent-skills | .95 — official spec for `argument-hint` field |
| 2 | agentskills.io specification | https://agentskills.io/specification | .90 — open spec confirms `argument-hint` is VS Code-specific, not in base spec |
| 3 | OwlBear `.agent.md` files | `.github/agents/*.agent.md` | .85 — all 11 agents already use `argument-hint` as established pattern |
| 4 | Prior research: agentskills-io.md | `docs/research/agentskills-io.md` (task #3) | .80 — recommended this task |

## 3. Analysis

### 3a. Property Validation

Per VS Code docs [S1]: `argument-hint` is an optional YAML frontmatter field — "Hint text shown in the chat input field when the skill is invoked as a slash command." Example: `[test file] [options]`.

Per agentskills.io [S2]: `argument-hint` is **not** in the open spec. It's a VS Code extension. Other clients ignore unknown frontmatter fields harmlessly.

### 3b. Scope Assessment — AC vs Full Opportunity

The AC targets 2 skills. Of the 10 user-invocable skills, 5 are actively user-invoked (benefit from hints) and 5 are reference/auto-loaded knowledge (hints add marginal value):

| Skill | Invocation pattern | Proposed hint | In AC? |
|-------|--------------------|---------------|:------:|
| project-definition | `/project-definition my app` | `[project name or idea]` | Yes |
| retro | `/retro last 2 weeks` | `[date range or sprint name]` | Yes |
| excalidraw-diagram | `/excalidraw-diagram arch overview` | `[diagram description]` | No |
| visual-output | `/visual-output deployment flow` | `[diagram or visual description]` | No |
| frontend-design | `/frontend-design button component` | `[component or design question]` | No |
| architecture-standards | Auto-loaded by agents | — | No |
| decision-requests | Agent protocol, rarely user-invoked | — | No |
| kanban-md | Reference auto-loaded | — | No |
| knowledge-ops | Auto-loaded + agent-driven | — | No |
| pytest-and-linting | Reference auto-loaded | — | No |

### 3c. Implementation Approach

Add one YAML line to each skill's frontmatter [S1, S3]:

```yaml
---
name: project-definition
description: "..."
argument-hint: "[project name or idea]"
---
```

No body changes. Pattern matches existing `.agent.md` usage [S3].

### 3d. Verification

After adding, open VS Code chat, type `/project-definition` — the hint text should appear in the input field as placeholder. Per VS Code docs [S1], this is a client-side rendering feature with no runtime impact.

## 4. Recommendation (.95 confidence)

Proceed as specified in the AC for project-definition and retro. Implementation is trivial — one YAML line per file. Create a follow-up task for the 3 additional skills (excalidraw-diagram, visual-output, frontend-design) since they follow the same pattern but are out of the current AC scope.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add argument-hint to remaining user-invoked skills" --priority nice-to-have --status ideation --tags "phase-1,scope:skills,type:build" --body "## Objective\nAdd argument-hint frontmatter to the 3 remaining actively user-invoked skills that were out of scope for #43.\n\n## Acceptance Criteria\n- [ ] Add argument-hint: '[diagram description]' to excalidraw-diagram\n- [ ] Add argument-hint: '[diagram or visual description]' to visual-output\n- [ ] Add argument-hint: '[component or design question]' to frontend-design\n- [ ] Verify hints appear in VS Code slash-command menu\n\n## Context\nSee docs/research/argument-hint-user-invocable-skills.md for rationale and analysis."
```
