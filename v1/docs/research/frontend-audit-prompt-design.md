# Frontend Audit Prompt Design

> **Owning task:** #944 — Add frontend-audit prompt built on frontend-design skill
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

Task #944 asks for a `.github/prompts/frontend-audit.prompt.md` — the first
audit stage in the `audit → normalize → polish` pipeline adapted from
Impeccable. The prompt must produce a severity-ranked report across four
categories (accessibility, responsive behavior, design-system consistency,
anti-patterns) without editing code. This research validates the audit
structure, severity scheme, and output format before implementation.

Dependencies #934 (frontend-design skill), #938 (anti-pattern taxonomy), and
# 943 (design-context onboarding) are all archived.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Impeccable `/audit` SKILL.md | .95 | 5-dimension scored audit (a11y, perf, theming, responsive, anti-patterns), P0–P3 severity, 0–20 health score, recommended-commands section |
| S2 | Impeccable README + website | .85 | `audit → normalize → polish` pipeline, scoped audit via area argument, command-chaining UX |
| S3 | OwlBear `frontend-design` SKILL.md + 7 references | 1.0 | Universal blockers, taste heuristics, reference-pack structure, design-context protocol |
| S4 | OwlBear sibling prompts (`frontend-normalize`, `frontend-polish`, `design-context`) | 1.0 | Established prompt pattern: load context → plan → execute → verify → guardrails |
| S5 | axe-core rule taxonomy (WCAG tooling standard) | .70 | Impact tiers (critical/serious/moderate/minor), category grouping precedent |
| S6 | `docs/research/impeccable-command-patterns.md` (task #930) | .90 | Verdict to adapt Impeccable as `.prompt.md`, not `SKILL.md`; pilot audit first |

## 3. Analysis

### 3.1 Category Selection

| AC category | Impeccable equivalent | OwlBear reference file | Verdict |
|-------------|----------------------|----------------------|---------|
| Accessibility | Accessibility (1 of 5) | `interaction-design.md`, `color-and-contrast.md` | **Keep** — core gate, WCAG-backed [S1, S3, S5] |
| Responsive behavior | Responsive Design (4 of 5) | `responsive-design.md`, `spatial-design.md` | **Keep** — measureable from markup [S1, S3] |
| Design-system consistency | Theming (3 of 5) | `color-and-contrast.md`, `typography.md`, `spatial-design.md` | **Keep** — renamed from "theming" to match broader token/pattern consistency [S1, S3] |
| Anti-patterns | Anti-Patterns (5 of 5) | `anti-patterns.md` | **Keep** — AI-slop detection + universal blockers [S1, S3] |
| *(dropped)* Performance | Performance (2 of 5) | *(none)* | **Drop** — requires runtime measurement, not static code reading [S1] |

The AC's 4 categories are sound. Dropping performance is KISS-aligned — it would
require the LLM to speculate about runtime behavior without profiling data [S1, S5].

### 3.2 Severity Scheme

| Scheme | Source | Tiers | Fit |
|--------|--------|:-----:|-----|
| P0–P3 | Impeccable [S1] | 4 | Good resolution; maps naturally to fix urgency |
| Critical/Serious/Moderate/Minor | axe-core [S5] | 4 | Industry standard for a11y; same granularity |
| Blocker/Major/Minor | Simplified | 3 | KISS but loses the "polish-only" tier |

**Recommendation (.85):** Use P0–P3 to match Impeccable vocabulary [S1, S2].
The sibling prompts already reference this audit, so consistent severity labels
help the user triage which command to run next. Map: P0=Blocker (universal
blockers from S3), P1=Major (WCAG AA violation), P2=Minor (workaround exists),
P3=Polish (taste heuristic, no user impact).

### 3.3 Scoring vs. Ranking

| Approach | Pros | Cons |
|----------|------|------|
| Numeric health score (0–20) [S1] | Trackable over time; quick summary | Subjective calibration; adds complexity |
| Severity-ranked list only | KISS; the AC says "severity-ranked" not "scored" | No single number for progress tracking |

**Recommendation (.80):** Severity-ranked list without numeric scoring. The AC
says "severity-ranked audit" — not "scored audit." Numeric scoring requires
calibration heuristics that add prompt complexity for marginal value [S1, S3].

### 3.4 Output Format

The prompt should produce a structured markdown report with these sections
(adapted from Impeccable [S1] and filtered for KISS):

1. **Summary** — finding count by severity (P0/P1/P2/P3), scope audited
2. **Findings by severity** — P0 first, each with: category, location,
   impact, WCAG/standard citation, recommendation, suggested next command
3. **Systemic patterns** — recurring issues across multiple locations
4. **Positive findings** — what works well (prevents audit-fatigue)
5. **Recommended next steps** — map to `/frontend-normalize` or
   `/frontend-polish` commands

### 3.5 Prompt Structure

Following the sibling prompt pattern [S4]:

1. **Load context** — read `docs/design-context.md` + frontend-design SKILL +
   relevant references (a11y, responsive, anti-patterns, color)
2. **Determine scope** — use `${input:scope}` or identify one surface
3. **Execute audit** — scan each of the 4 categories systematically
4. **Generate report** — structured output per §3.4
5. **Guardrails** — no code edits, no structural redesign, cite standards

## 4. Recommendation (.85 confidence)

Build `frontend-audit.prompt.md` with:

- Description-only frontmatter (no `agent:` field), optional `${input:scope}`
- Four audit categories from AC (accessibility, responsive, design-system
  consistency, anti-patterns)
- P0–P3 severity ranking without numeric scoring
- Structured report: summary → findings → patterns → positives → next steps
- Reference frontend-design skill by relative path, load `design-context.md`
- Guardrails: read-only, cite standards, no false positives without evidence

Risk: prompt may be long (~80–100 lines). Mitigate by keeping per-category
check lists brief and referencing skill references for detail rather than
inlining them [S3, S4].

## 5. Follow-up Tasks

No new tasks needed — #944 itself covers the implementation. The research
validates the approach for the architect to gate.
