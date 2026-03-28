# Add user-invocable: false to Pipeline-Only Skills

> **Owning task:** #42 — Add user-invocable: false to pipeline-only skills
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #42 adds `user-invocable: false` to 11 pipeline-only SKILL.md files so they don't appear in the VS Code `/` slash-command menu while remaining auto-loadable by agents. This research validates the property, the 11/10 categorization, and implementation approach.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Agent Skills docs | https://code.visualstudio.com/docs/copilot/customization/agent-skills | .95 — official spec for `user-invocable` in SKILL.md frontmatter |
| 2 | agentskills-io research | docs/research/agentskills-io.md (task #3) | .90 — prior research that created this task |
| 3 | Impeccable command patterns | docs/research/impeccable-command-patterns.md | .80 — real-world usage of `user-invocable: false` in skills |
| 4 | OwlBear .agent.md files | .github/agents/*.agent.md | .85 — existing `user-invocable` usage in project |

## 3. Analysis

### 3a. Property Validation

`user-invocable` is a supported SKILL.md YAML frontmatter field per VS Code docs [S1]:
- **Default:** `true` — skill appears in `/` menu and is auto-loadable
- **`false`:** hidden from `/` menu, still auto-loaded by agents when relevant
- Non-standard (VS Code extension to agentskills.io spec) — other clients ignore it harmlessly [S2]

### 3b. Categorization Validation

| Skill | Agent owner | User-invocable? | Rationale |
|-------|-------------|:----------------:|-----------|
| arch-review | architect | false | Pipeline gate — architect dispatched by orchestrator |
| code-review | reviewer | false | Pipeline gate — reviewer dispatched by orchestrator |
| curation-workflow | curator | false | Agent is user-invocable; skill is auto-loaded |
| dispatch-planning | planner | false | Internal planner workflow |
| docs-gate | writer | false | Pipeline gate — writer dispatched by orchestrator |
| orchestration | orchestrator | false | Internal dispatch loop |
| research-workflow | researcher | false | Pipeline gate — researcher dispatched or user-invoked via agent |
| task-decomposition | kanban-planner | false | Internal decomposition workflow |
| task-verification | auditor | false | Pipeline gate — auditor dispatched by orchestrator |
| tdd-red | test-writer | false | Pipeline gate — test-writer dispatched by orchestrator |
| tdd-workflow | builder | false | Pipeline gate — builder dispatched by orchestrator |
| architecture-standards | any | **true** | General reference knowledge for any context |
| decision-requests | any | **true** | Any agent or user may need the async decision process |
| excalidraw-diagram | user | **true** | User invokes for diagram generation |
| frontend-design | user | **true** | User invokes for design guidance |
| kanban-md | any | **true** | Reference knowledge for board operations |
| knowledge-ops | any | **true** | Users query/ingest knowledge directly |
| project-definition | user | **true** | User invokes for project scoping |
| pytest-and-linting | any | **true** | Users run tests/lint directly |
| retro | user | **true** | User invokes for sprint reports |
| visual-output | user | **true** | User invokes for visual artifacts |

**Key insight:** `user-invocable: false` on a skill ≠ inaccessible. Users still benefit when agents auto-load these skills. The flag only controls the `/` menu. The user invokes the *agent* (e.g., `@researcher`), which auto-loads the *skill* on demand [S1, S4].

### 3c. Implementation Approach

Add one YAML frontmatter line to each of 11 SKILL.md files:

```yaml
---
name: arch-review
description: "..."
user-invocable: false
---
```

No body changes needed. Existing `name` and `description` fields stay as-is [S1, S2].

### 3d. Risks

| Risk | Likelihood | Mitigation |
|------|:----------:|------------|
| VS Code ignores `user-invocable` on older versions | Low | Graceful degradation — skill still works, just shows in menu |
| Other clients don't support attribute | Low | Spec says unknown fields are ignored [S2] |
| Miscategorized skill hides useful slash command | Low | All 10 user-invocable skills validated against agent ownership above |

## 4. Recommendation (.95 confidence)

Proceed as specified in the AC. The 11/10 split is correct. Implementation is a trivial frontmatter addition — no source code changes, no behavioral risk.

**Testing:** After adding the property, open VS Code chat, type `/`, and confirm only the 10 user-invocable skills appear in the menu. Pipeline-only skills should be absent from the menu but still auto-load when agents reference them.

## 5. Follow-up Tasks

Task #42 already exists with correct AC — no additional tasks needed. Related tasks #43 (argument-hint) and #44 (skills-ref validation) were created by the prior research and remain at ideation.
