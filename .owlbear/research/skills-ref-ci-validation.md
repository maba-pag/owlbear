# Skills-Ref CI Validation

> **Owning task:** #44 — Add skills-ref validation to CI
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #44 asks to integrate the agentskills.io `skills-ref` validator into
OwlBear's CI pipeline. OwlBear has 21 skills in `.github/skills/`. The question:
can we use `skills-ref` as-is, and what integration approach fits best?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | agentskills.io specification | https://agentskills.io/specification | .95 — authoritative format rules |
| 2 | skills-ref PyPI package (v0.1.1) | https://pypi.org/project/skills-ref/ | .90 — published package, CLI, deps |
| 3 | skills-ref source (validator.py) | https://github.com/agentskills/agentskills/blob/main/skills-ref/src/skills_ref/validator.py | .90 — actual validation logic |
| 4 | VS Code Agent Skills docs | https://code.visualstudio.com/docs/copilot/customization/agent-skills | .85 — VS Code vendor extensions |
| 5 | Local validation run | `agentskills validate` on 21 OwlBear skills | .95 — direct evidence |

## 3. Analysis

### 3a. What skills-ref validates

| Check | Rule | Source |
|-------|------|--------|
| SKILL.md exists | Directory must contain SKILL.md | Spec §SKILL.md format |
| `name` present | Required, max 64 chars | Spec §name field |
| `name` format | Lowercase `[a-z0-9-]`, no `--`, no start/end `-` | Spec §name field |
| `name` = dirname | Must match parent directory | Spec §name field |
| `description` present | Required, non-empty, max 1024 chars | Spec §description field |
| `compatibility` | Optional, max 500 chars | Spec §compatibility field |
| Allowed fields | Only: name, description, license, allowed-tools, metadata, compatibility | validator.py `ALLOWED_FIELDS` |

### 3b. Compatibility issue — VS Code vendor extensions

**Critical finding:** 11 of 21 OwlBear skills use `user-invocable: false` in
frontmatter. This is a VS Code extension field not in the agentskills.io spec.

| Field | Spec status | VS Code docs | skills-ref result |
|-------|-------------|--------------|-------------------|
| `user-invocable` | Not in spec | Supported at top level | **FAIL** — "Unexpected fields" |
| `argument-hint` | Not in spec | Supported at top level | **Would FAIL** |
| `disable-model-invocation` | Not in spec | Supported at top level | **Would FAIL** |

**Verified locally:** `agentskills validate .github/skills/arch-review` exits 1
with "Unexpected fields in frontmatter: user-invocable." Skills without vendor
fields (e.g. `architecture-standards`) exit 0 — "Valid skill."

The spec's intended mechanism for vendor extensions is the `metadata` map, but
VS Code reads these fields at the top level. Moving them to `metadata` would
break VS Code behavior.

**Skills affected (11 FAIL / 10 PASS):**

| Status | Skills |
|--------|--------|
| FAIL | arch-review, code-review, curation-workflow, dispatch-planning, docs-gate, orchestration, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow |
| PASS | architecture-standards, decision-requests, excalidraw-diagram, frontend-design, kanban-md, knowledge-ops, project-definition, pytest-and-linting, retro, visual-output |

### 3c. Integration approach comparison

| Approach | KISS | Maintenance | Spec coverage | VS Code compat |
|----------|------|-------------|---------------|----------------|
| **A: Pre-commit hook + error filter** (.85) | Medium | Low | Full spec checks, skip vendor fields | Preserved |
| B: Move vendor fields to metadata | High | None | Full | **Broken** — VS Code ignores metadata |
| C: Custom validation script (no skills-ref) | Medium | High — must track spec changes | Partial (manual) | Preserved |
| D: Raw `agentskills validate` (no filter) | High | None | Full | **11 skills fail** — unusable |

### 3d. Package details

| Property | Value |
|----------|-------|
| PyPI package | `skills-ref` v0.1.1 |
| CLI entry point | `agentskills` (renamed from `skills-ref` in v0.1.1) |
| Dependencies | click, strictyaml (2 direct deps) |
| Python | ≥3.11 |
| License | Apache-2.0 |
| Install | `uv add --dev skills-ref` |

### 3e. Pre-commit integration

OwlBear already has `.pre-commit-config.yaml` with 5 repos (pre-commit-hooks,
ruff, actionlint, bandit, markdownlint-cli2). A `repo: local` hook using the
Python API can filter vendor-field errors while preserving all spec validation.
No GitHub Actions workflows exist yet — pre-commit is the right entry point.

## 4. Recommendation (.85 confidence)

**Use Option A: pre-commit local hook with vendor-field error filter.**

- Install `skills-ref` as a dev dependency
- Write a ~30-line Python script that calls `skills_ref.validate()` on each
  skill directory, filters errors mentioning known VS Code extension fields
  (`user-invocable`, `argument-hint`, `disable-model-invocation`), and reports
  remaining errors
- Add as a `repo: local` hook in `.pre-commit-config.yaml`

**Risk:** skills-ref is labeled "for demonstration purposes only" (README caveat).
If the project changes API/behavior, the wrapper may need updating. Mitigation:
pin to `==0.1.1` and track upstream releases.

**Deferred:** When the agentskills spec adds vendor extension support (active
discussion in repo issues), simplify to raw `agentskills validate` without the
filter wrapper.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add skills-ref dev dependency and pre-commit validation hook" --priority nice-to-have --status ideation --tags "phase-1,scope:skills,scope:build,type:build" --body "## Objective\nIntegrate agentskills.io skills-ref validator as a pre-commit hook.\n\n## Acceptance Criteria\n- [ ] Add skills-ref==0.1.1 as a dev dependency via uv add --dev\n- [ ] Create scripts/validate-skills.py that calls skills_ref.validate() on all .github/skills/*/SKILL.md, filtering errors for known VS Code extension fields (user-invocable, argument-hint, disable-model-invocation)\n- [ ] Add repo: local pre-commit hook in .pre-commit-config.yaml that runs scripts/validate-skills.py\n- [ ] All 21 skills pass the filtered validation\n- [ ] pre-commit run --all-files exits 0\n\n## Architecture Notes\nSee docs/research/skills-ref-ci-validation.md for analysis.\nThe wrapper filters VS Code vendor fields because the spec validator rejects them. When the agentskills spec adds vendor extension support, simplify to direct agentskills validate calls."
```
