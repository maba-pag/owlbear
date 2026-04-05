# Frontend-Polish Prompt Research

> **Owning task:** #946 — Add frontend-polish prompt built on frontend-design skill
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #946 adds a `.prompt.md` file that performs a final frontend detail pass
before shipping. It is the last stage of the `audit → normalize → polish`
pipeline adapted from Impeccable (#930). The question: what should the prompt
check, how should it reference existing design guidance, and what scope
guardrails prevent it from becoming a redesign?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Impeccable `/polish` skill (`source/skills/polish/SKILL.md`) | .95 | 11-category deep checklist (alignment, typography, color, interaction states, micro-interactions, copy, icons, forms, edge cases, responsiveness, code quality) plus pre-polish assessment and final verification [S1] |
| S2 | VS Code Prompt Files docs | .95 | Frontmatter format (`description`, `${input:}` syntax), Markdown body, relative file references [S2] |
| S3 | OwlBear `frontend-design` skill (`SKILL.md`, `references/*.md`) | 1.0 | 8-file reference pack, Universal Blockers list, design-context gathering protocol, and anti-pattern taxonomy [S3] |
| S4 | OwlBear `design-context.prompt.md` and `orchestrate.prompt.md` | 1.0 | Format precedent: description-only frontmatter, `${input:}` syntax for optional user input, markdown body [S4] |
| S5 | Parent research `docs/research/impeccable-command-patterns.md` | .95 | Pattern verdicts: adapt polish as a thin `.prompt.md` wrapper on the `frontend-design` skill [S5] |

## 3. Research Checklist

### 3.1 Theoretical Validity — PASS

A finishing pass focused on visual detail is a well-established UI workflow
step. Impeccable's `/polish` separates this from structural normalization and
audit work, reducing cognitive load by giving the user a single-concern
command [S1, S5]. OwlBear's adaptation keeps the lightweight intent.

### 3.2 Prior Art — PASS (2+ sources)

| Pattern | Source | Evidence |
|---------|--------|----------|
| Final detail pass with explicit checklist | Impeccable `/polish` [S1] | 11-category checklist, pre-polish assessment, final verification steps |
| Prompt file with optional scope input | VS Code docs [S2], OwlBear prompts [S4] | `${input:variableName:placeholder}` syntax |
| Skill reference from prompt body | OwlBear `design-context.prompt.md` [S4] | Markdown link to `frontend-design/SKILL.md` |

### 3.3 Technical Feasibility — PASS

| Requirement | Feasible? | Evidence |
|-------------|-----------|----------|
| Description-only frontmatter | Yes | VS Code docs: all frontmatter fields optional [S2] |
| Optional scope input | Yes | `${input:}` syntax used in `orchestrate.prompt.md` [S4] |
| Read `docs/design-context.md` | Yes | Prompt body can reference files via Markdown links [S2] |
| Reference `frontend-design` skill | Yes | Same pattern as `design-context.prompt.md` [S4] |
| No code changes | Yes | Pure `.prompt.md` file creation |

### 3.4 Architecture Fit — PASS

- **Location:** `.github/prompts/frontend-polish.prompt.md` alongside siblings
- **Input:** `docs/design-context.md` (when present) + skill references
- **Dependencies:** #934 (archived), #943 (prompt exists) — both satisfied
- **Pipeline position:** last step after audit (#944) and normalize (#945)

### 3.5 Implementation Approach

The AC names 6 focus areas: spacing, interaction states, copy consistency,
focus treatment, loading/empty states, and mobile readiness. Impeccable's
`/polish` covers 11 categories [S1]. The OwlBear adaptation should:

1. **Scope to the 6 AC-named categories.** Do not import Impeccable's full
   11-category checklist — KISS/YAGNI. The skill reference pack already
   covers typography, color, and motion detail for users who want depth [S3].
2. **Reference the skill for deep guidance.** The prompt body should link to
   `frontend-design/SKILL.md` and specific references (interaction-design,
   spatial-design, responsive-design, ux-writing) so the AI can load them
   on demand without bloating the prompt itself [S3].
3. **Include guardrails against redesign.** Impeccable explicitly states
   "polish is the last step, not the first" and "don't introduce bugs while
   polishing" [S1]. The prompt should echo these constraints.
4. **Include final verification steps.** Impeccable's 5-point verification
   (use it yourself, test on real devices, ask for review, compare to design,
   check all states) is highly valuable — adapt the applicable subset [S1].

**Frontmatter:** description-only, matching sibling prompts. No `agent:` field
needed — the user invokes it in agent mode naturally since it makes edits.

**Optional input:** `${input:scope:Files or feature area to polish (optional)}`
matching the AC and sibling prompt precedent [S4].

### 3.6 Testing Strategy — Inspection-only

This is a `type:docs` task producing a `.prompt.md` file. No automated tests.
Verification is by file inspection: correct frontmatter, all 6 focus areas
covered, skill reference present, design-context reference present,
verification steps included, no redesign language.

### 3.7 Findings Documented — This document

## 4. Recommendation (.92 confidence)

The AC is well-scoped and implementation-ready. Both dependencies are satisfied.
The polish prompt should be a thin wrapper (~60–80 lines) that:

- Loads `docs/design-context.md` when present
- References the `frontend-design` skill and 4 specific reference files
- Checks the 6 named areas systematically
- Explicitly forbids structural redesign
- Ends with a verification checklist

No trade-off decision is needed — the approach is clear and aligned with
KISS/YAGNI. No decision request required.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #946 and its siblings (#944, #945) were
already created by the parent research (#930). Implementation is a single
`.prompt.md` file requiring no code changes.
