# agentskills.io Spec Validation

> **Owning task:** #3 — agentskills.io spec validation
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

OwlBear v1 has 21 skills in `.github/skills/`. The agentskills.io open standard (Anthropic, Apache-2.0) defines a portable skill format adopted by VS Code, Claude Code, Cursor, Gemini CLI, and others. Can v1 skills be ported with minimal changes?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | agentskills.io specification | https://agentskills.io/specification | .95 — authoritative format spec |
| 2 | VS Code Agent Skills docs | https://code.visualstudio.com/docs/copilot/customization/agent-skills | .90 — VS Code-specific extensions and discovery paths |
| 3 | agentskills/agentskills repo | https://github.com/agentskills/agentskills | .80 — reference SDK and validation tool (skills-ref) |
| 4 | anthropics/skills repo | https://github.com/anthropics/skills | .75 — 100k-star example skills collection |
| 5 | Client implementation guide | https://agentskills.io/client-implementation/adding-skills-support | .85 — progressive disclosure lifecycle |

## 3. Analysis

### 3a. Frontmatter Compliance

| Constraint | Spec requirement | v1 status | Action |
|------------|-----------------|-----------|--------|
| `name` present | Required, max 64 chars | All 21 ✅ (5–22 chars) | None |
| `name` format | `[a-z0-9-]`, no start/end hyphen, no `--` | All 21 ✅ | None |
| `name` = dir name | Must match parent directory | All 21 ✅ | None |
| `description` present | Required, max 1024 chars | All 21 ✅ (100–265 chars) | None |
| `license` | Optional | None use it | Optional — skip |
| `compatibility` | Optional, max 500 chars | None use it | Recommended for 2 skills (knowledge-ops, excalidraw-diagram) that reference OwlBear runtime tools |
| `metadata` | Optional key-value map | None use it | Optional — skip |
| `allowed-tools` | Optional, experimental | None use it | Skip (experimental) |

**Result: 100% compliant on required fields.** No breaking changes needed.

### 3b. VS Code Extensions (non-standard but supported)

| Field | Purpose | Current usage | Remaining action |
|-------|---------|---------------|------------------|
| `user-invocable: false` | Hide from `/` menu; agents still auto-load | 11 skills (arch-review, code-review, curation-workflow, dispatch-planning, docs-gate, orchestration, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow) ✅ | None — all pipeline-only skills already set |
| `argument-hint` | Slash-command hint text | 5 skills (excalidraw-diagram, frontend-design, project-definition, retro, visual-output) ✅ | Task #79: remaining user-invocable skills without a hint |
| `disable-model-invocation` | Block auto-loading (default: false) | Not used | Not needed — all skills should remain auto-loadable |

**10 skills remain user-invocable (default: true):** architecture-standards, decision-requests, excalidraw-diagram, frontend-design, kanban-md, knowledge-ops, project-definition, pytest-and-linting, retro, visual-output.

### 3c. Per-skill Directory Structure and Required Changes

| Skill | Lines | `user-invocable` | `argument-hint` | `references/` | Required changes |
|-------|-------|-----------------|----------------|---------------|-----------------|
| arch-review | 120 | `false` ✅ | — | ❌ | None |
| architecture-standards | 102 | — (default true) | — | ❌ | None |
| code-review | 366 | `false` ✅ | — | ❌ | None |
| curation-workflow | 98 | `false` ✅ | — | ❌ | None |
| decision-requests | 162 | — (default true) | — | ❌ | None |
| dispatch-planning | 309 | `false` ✅ | — | ❌ | None |
| docs-gate | 125 | `false` ✅ | — | ❌ | None |
| excalidraw-diagram | 141 | — (default true) | ✅ | ✅ | Optional: add `compatibility` note (OwlBear-specific tools) |
| frontend-design | 65 | — (default true) | ✅ | ✅ | None |
| kanban-md | 49 | — (default true) | — | ✅ | None |
| knowledge-ops | 140 | — (default true) | — | ❌ | Optional: add `compatibility` note (OwlBear-specific tools) |
| orchestration | 273 | `false` ✅ | — | ❌ | None |
| project-definition | 111 | — (default true) | ✅ | ❌ | None |
| pytest-and-linting | 161 | — (default true) | — | ❌ | None |
| research-workflow | 125 | `false` ✅ | — | ❌ | None |
| retro | 223 | — (default true) | ✅ | ❌ | None |
| task-decomposition | 126 | `false` ✅ | — | ❌ | None |
| task-verification | 145 | `false` ✅ | — | ❌ | None |
| tdd-red | 188 | `false` ✅ | — | ❌ | None |
| tdd-workflow | 175 | `false` ✅ | — | ❌ | None |
| visual-output | 93 | — (default true) | ✅ | ❌ | None |

**Summary:** 19 of 21 skills need zero structural changes. 2 skills (excalidraw-diagram, knowledge-ops) optionally benefit from a `compatibility` note for OwlBear-specific toolsets. No `scripts/` or `assets/` directories are needed — OwlBear skills are procedural knowledge, not executable.

### 3d. Progressive Disclosure — Tier Compliance for All 21 Skills

| Tier | Spec guidance | Compliance |
|------|--------------|-----------|
| 1. Metadata (~100 tokens) | `name` + `description` (required) | ✅ All 21 — both fields present |
| 2. Instructions (<5000 tokens, <500 lines) | SKILL.md body on activation | ✅ All 21 — range 49–366 lines, max 366 (code-review), well under 500 |
| 3. Resources (on demand) | `scripts/`, `references/`, `assets/` | ✅ 3 of 21 use `references/` (excalidraw-diagram, frontend-design, kanban-md); none need `scripts/` or `assets/` |

All 21 skills are tier-3 compatible today — any that add `references/` in future will be automatically compliant.

### 3e. Skill Discovery Paths

| Path | Scope | v1 location | Compatible? |
|------|-------|-------------|-------------|
| `.github/skills/` | Project, VS Code | ✅ Current location | Yes |
| `.agents/skills/` | Project, cross-client | Not used | Optional for portability |
| `~/.copilot/skills/` | User-level | Not used | N/A (project skills) |

### 3f. Validation Tooling

The `skills-ref` Python library (agentskills/agentskills repo) provides `skills-ref validate ./my-skill` to check frontmatter validity and naming conventions. Not yet integrated into our workflow.

## 4. Recommendation (.92 confidence)

**All 21 skills are already agentskills.io compliant.** The porting has been completed — required fields are present, directory structure is correct, and VS Code extensions (`user-invocable`, `argument-hint`) are applied to the appropriate skills. Remaining work is additive and low-risk:

1. **Task #79 open:** Add `argument-hint` to remaining user-invocable skills still missing it (architecture-standards, decision-requests, kanban-md, knowledge-ops, pytest-and-linting)
2. **Task #44 open:** Integrate `skills-ref validate` as a CI/lint step to catch regressions
3. **Optional:** Add `compatibility` notes to 2 skills (excalidraw-diagram, knowledge-ops) that reference OwlBear-specific runtime tools

Risk: VS Code extensions (`user-invocable`, `argument-hint`, `disable-model-invocation`) are not part of the open spec — they're VS Code-specific. Other clients will ignore them harmlessly.

## 5. Follow-up Tasks

Follow-up tasks created from this research:

| Task | Title | Status |
|------|-------|--------|
| #42 | Add user-invocable: false to pipeline-only skills | in-progress |
| #79 | Add argument-hint to remaining user-invocable skills | todo |
| #44 | Add skills-ref validation to CI | todo |

Original `kanban-md create` commands (reference only — tasks already created):

```
kanban\kanban-md.exe create "Add user-invocable: false to pipeline-only skills" --priority important --status ideation --tags "phase-1,scope:skills,type:build" --body "## Objective\nAdd user-invocable: false to pipeline-only skills that should not appear in the / slash-command menu.\n\n## Acceptance Criteria\n- [ ] Add user-invocable: false to: arch-review, code-review, curation-workflow, dispatch-planning, docs-gate, orchestration, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow\n- [ ] Verify remaining 10 skills keep default (true): architecture-standards, decision-requests, excalidraw-diagram, frontend-design, kanban-md, knowledge-ops, project-definition, pytest-and-linting, retro, visual-output\n- [ ] Test slash-command menu shows only user-invocable skills"
kanban\kanban-md.exe create "Add argument-hint to user-invocable skills" --priority nice-to-have --status ideation --tags "phase-1,scope:skills,type:build" --body "## Objective\nAdd argument-hint frontmatter to user-invocable skills for better slash-command UX.\n\n## Acceptance Criteria\n- [ ] Add argument-hint to project-definition (e.g. '[project name or idea]')\n- [ ] Add argument-hint to retro (e.g. '[date range or sprint name]')\n- [ ] Verify hints appear in VS Code slash-command menu"
kanban\kanban-md.exe create "Add skills-ref validation to CI" --priority nice-to-have --status ideation --tags "phase-1,scope:skills,scope:build,type:build" --body "## Objective\nIntegrate agentskills.io skills-ref validator into CI pipeline.\n\n## Acceptance Criteria\n- [ ] Install skills-ref from agentskills/agentskills repo\n- [ ] Run skills-ref validate on all .github/skills/*/SKILL.md\n- [ ] Add as pre-commit or CI check\n- [ ] All 21 skills pass validation"
```
