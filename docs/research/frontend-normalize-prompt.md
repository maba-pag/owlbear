# Frontend-Normalize Prompt Research

> **Owning task:** #945 — Add frontend-normalize prompt built on frontend-design skill
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #945 asks for a `.prompt.md` that aligns a scoped frontend area against the
local `docs/design-context.md` and the `frontend-design` skill. This is the
second remediation command in OwlBear's `audit → normalize → polish` pipeline
adapted from Impeccable [S6]. The question is: what prompt structure, workflow
steps, and verification checks should the normalize prompt include?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Impeccable `/normalize` skill (`source/skills/normalize/SKILL.md`) | .90 | Plan → Execute → Clean Up structure, 8 dimension checklist, mandatory `.impeccable.md` prep, never-list |
| S2 | Impeccable website (`impeccable.style`) | .85 | Public `audit → normalize → polish` pipeline, usage examples (`/normalize blog`, `/normalize buttons`) |
| S3 | VS Code prompt file docs (`code.visualstudio.com/.../prompt-files`) | .95 | `.prompt.md` frontmatter (`description`, `${input:}` syntax, `tools`, `agent`), Markdown links for file references |
| S4 | OwlBear `design-context.prompt.md` | 1.0 | Establishes `docs/design-context.md` as the shared context file; 7 stable section names; skill reference pattern |
| S5 | OwlBear `frontend-design` skill (SKILL.md + references + anti-patterns) | 1.0 | 5-step workflow, 8 reference files, universal blockers, taste heuristics |
| S6 | OwlBear `impeccable-command-patterns.md` | 1.0 | Research recommending the 4-prompt pilot; normalize is task #945 |

## 3. Analysis

### 3.1 Structural comparison

| Aspect | Impeccable `/normalize` [S1] | Proposed OwlBear `/frontend-normalize` |
|--------|------------------------------|---------------------------------------|
| Context source | `.impeccable.md` | `docs/design-context.md` [S4] |
| Preparation | Reads `frontend-design` skill via mandatory prep [S1] | Reads `frontend-design` skill by relative path [S5] |
| Plan step | Discover design system, analyze feature, create normalization plan [S1] | Same three-part plan; plan shown to user before edits (AC3) |
| Dimensions | Typography, Color, Spacing, Components, Motion, Responsive, Accessibility, Progressive Disclosure [S1] | Same minus Progressive Disclosure + add Token Usage per AC3 |
| Verification | "Lint, type-check, and test" [S1] | Accessibility, responsive, remove one-off styling per AC4 |
| Never-list | 4 items (new one-offs, hardcoded values, new divergent patterns, accessibility compromise) [S1] | Adapt the same 4 as guardrails |
| Input | `feature` arg (optional) [S1] | `${input:scope}` (optional) [S3] |
| Frontmatter | `user-invocable: true`, `args` [S1] | `description` only per AC1 [S3] |

### 3.2 Design decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| File location | `.github/prompts/frontend-normalize.prompt.md` | Same | AC1, matches existing prompts [S4] |
| Frontmatter | Description + agent + tools vs description-only | Description-only | AC1, matches `design-context.prompt.md` [S4], KISS |
| Scope input | `${input:scope}` vs none | `${input:scope}` with placeholder | AC1, mirrors Impeccable's optional `feature` arg [S1, S3] |
| Design-context handling | Require file vs graceful fallback | Read if present, warn and proceed if absent | YAGNI; user may not have run `/design-context` yet |
| Skill reference | Inline knowledge vs link | Link to `../../skills/frontend-design/SKILL.md` | AC2, DRY, matches `design-context.prompt.md` pattern [S4, S5] |
| Plan-before-edit gate | Implicit vs explicit | Explicit step: show plan, then execute | AC3 [S1, S2] |
| Verification | Single check vs structured list | Structured: accessibility, responsive, one-off removal | AC4 [S1, S5] |

### 3.3 Risk assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `docs/design-context.md` doesn't exist yet | Medium | Prompt checks and warns; still proceeds with skill references only |
| Scope too broad (user passes "everything") | Low | Prompt says "focus on one page, route, or component at a time" |
| Overlap with `/frontend-audit` | Low | Audit is read-only; normalize makes edits. Pipeline is sequential [S2, S6] |

## 4. Recommendation (.90 confidence)

Create `.github/prompts/frontend-normalize.prompt.md` with:

1. Description-only frontmatter and a `${input:scope}` variable [S3, AC1].
2. Step 1: read `docs/design-context.md` and load the `frontend-design` skill via relative path [S4, S5, AC2].
3. Step 2: plan (discover design system, analyze scope, list changes) shown to user before edits [S1, AC3].
4. Step 3: execute across 6 dimensions (typography, layout, spacing, color, component usage, token usage) [S1, AC3].
5. Step 4: verify — accessibility, responsive behavior, removal of one-off styling [S1, S5, AC4].
6. Never-list adapted from Impeccable's 4 guardrails [S1].

No architectural risk. The prompt is a single Markdown file under `.github/prompts/` that references existing artifacts.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement frontend-normalize.prompt.md" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --body "Implement the prompt file per docs/research/frontend-normalize-prompt.md. Dependencies: #934 (done), #943 (done). AC from task #945."
```
