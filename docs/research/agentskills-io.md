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

| Field | Purpose | v1 usage | Recommendation |
|-------|---------|----------|----------------|
| `argument-hint` | Slash-command hint text | Not used | Add to user-invocable skills (project-definition, retro) |
| `user-invocable` | Show in `/` menu (default: true) | Not used | Set `false` on pipeline-only skills (11 skills) that agents auto-load |
| `disable-model-invocation` | Block auto-loading (default: false) | Not used | No need — all skills should remain auto-loadable |

### 3c. Directory Structure

| Spec convention | v1 status | Notes |
|-----------------|-----------|-------|
| `SKILL.md` present | All 21 ✅ | — |
| `scripts/` | None | OK — OwlBear skills are procedural knowledge, not executable |
| `references/` | 3 skills use it (excalidraw-diagram, frontend-design, kanban-md) ✅ | Already compliant |
| `assets/` | None | visual-output uses `templates/` — spec allows arbitrary dirs |

### 3d. Progressive Disclosure

| Tier | Spec guidance | v1 status |
|------|--------------|-----------|
| 1. Metadata (~100 tokens) | `name` + `description` | ✅ All skills |
| 2. Instructions (<5000 tokens, <500 lines) | SKILL.md body on activation | ✅ All ≤365 lines, well under 500 |
| 3. Resources (on demand) | scripts/, references/, assets/ | ✅ 3 skills use references/ |

### 3e. Skill Discovery Paths

| Path | Scope | v1 location | Compatible? |
|------|-------|-------------|-------------|
| `.github/skills/` | Project, VS Code | ✅ Current location | Yes |
| `.agents/skills/` | Project, cross-client | Not used | Optional for portability |
| `~/.copilot/skills/` | User-level | Not used | N/A (project skills) |

### 3f. Validation Tooling

The `skills-ref` Python library (agentskills/agentskills repo) provides `skills-ref validate ./my-skill` to check frontmatter validity and naming conventions. Not yet integrated into our workflow.

## 4. Recommendation (.90 confidence)

**Port with minimal changes.** All 21 v1 skills are already compliant with the agentskills.io spec on required fields. The porting work is additive, not breaking:

1. **Add `user-invocable: false`** to 11 pipeline-only skills so they don't clutter the `/` slash-command menu but remain auto-loadable by agents
2. **Add `argument-hint`** to the 2 user-invocable skills (project-definition, retro) for better UX
3. **Optionally add `compatibility`** to 2 skills that reference OwlBear runtime tools
4. **Run `skills-ref validate`** on all skills as a CI/lint step after porting

Risk: VS Code extensions (`user-invocable`, `argument-hint`, `disable-model-invocation`) are not part of the open spec — they're VS Code-specific. Other clients will ignore them harmlessly.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add user-invocable: false to pipeline-only skills" --priority important --status ideation --tags "phase-1,scope:skills,type:build" --body "## Objective\nAdd user-invocable: false to pipeline-only skills that should not appear in the / slash-command menu.\n\n## Acceptance Criteria\n- [ ] Add user-invocable: false to: arch-review, code-review, curation-workflow, dispatch-planning, docs-gate, orchestration, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow\n- [ ] Verify remaining 10 skills keep default (true): architecture-standards, decision-requests, excalidraw-diagram, frontend-design, kanban-md, knowledge-ops, project-definition, pytest-and-linting, retro, visual-output\n- [ ] Test slash-command menu shows only user-invocable skills"
kanban\kanban-md.exe create "Add argument-hint to user-invocable skills" --priority nice-to-have --status ideation --tags "phase-1,scope:skills,type:build" --body "## Objective\nAdd argument-hint frontmatter to user-invocable skills for better slash-command UX.\n\n## Acceptance Criteria\n- [ ] Add argument-hint to project-definition (e.g. '[project name or idea]')\n- [ ] Add argument-hint to retro (e.g. '[date range or sprint name]')\n- [ ] Verify hints appear in VS Code slash-command menu"
kanban\kanban-md.exe create "Add skills-ref validation to CI" --priority nice-to-have --status ideation --tags "phase-1,scope:skills,scope:build,type:build" --body "## Objective\nIntegrate agentskills.io skills-ref validator into CI pipeline.\n\n## Acceptance Criteria\n- [ ] Install skills-ref from agentskills/agentskills repo\n- [ ] Run skills-ref validate on all .github/skills/*/SKILL.md\n- [ ] Add as pre-commit or CI check\n- [ ] All 21 skills pass validation"
```
