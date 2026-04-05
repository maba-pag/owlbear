# Impeccable Design Skills Research

> **Owning task:** #929 - Research: Impeccable design skills - evaluate adoption for OwlBear frontend skill
> **Date:** 2026-03-22 **Status:** Complete

## 1. Context and Question

Task #929 asks whether OwlBear should adopt the design guidance in Paul
Bakaus's Impeccable project. OwlBear currently has one scoped instruction file,
`.github/instructions/frontend.instructions.md`, covering design-system choice,
WCAG baseline, component structure, basic responsiveness, and testing, but no
dedicated frontend-design skill or reference pack [S1, S2]. The question is not
"copy Impeccable?" but "what belongs in OwlBear's always-on instructions, what
belongs in a reusable skill, and which anti-patterns should be hard rules
versus taste heuristics?" [S3, S4, S5, S6].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `.github/instructions/frontend.instructions.md` | .95 | Current OwlBear frontend baseline: design system, a11y, component structure, responsive, testing |
| S2 | `docs/research/instruction-token-audit.md` + task #705 audit | .85 | Current instruction size (776 tokens) and rationale for keeping frontend guidance scoped rather than global |
| S3 | Impeccable `source/skills/frontend-design/SKILL.md`, seven `reference/*.md` files, `NOTICE.md` | .95 | Primary material: context-gathering protocol, reference-pack architecture, anti-pattern catalog, attribution model |
| S4 | Impeccable README + website | .90 | Public description of the 7 reference files, anti-pattern positioning, and VS Code/Copilot support |
| S5 | Anthropic `skills/frontend-design/SKILL.md` | .85 | Baseline skill Impeccable extends; useful to separate original broad direction from Impeccable's added depth |
| S6 | VS Code Agent Skills docs | .90 | Skills vs custom instructions, progressive loading, and resource-backed skill structure |

## 3. Coverage Comparison

| Topic | OwlBear instructions | Anthropic skill | Impeccable | Recommendation |
|-------|----------------------|-----------------|------------|----------------|
| Design-system policy | Strong | None | None | Keep in instructions |
| Accessibility/testing minimums | Strong baseline | Implicit | Expanded examples | Keep baseline in instructions; add richer examples in skill |
| Design context gathering | Missing | Broad design-thinking prompts | Explicit required context plus escalation path | Add to skill, not instructions |
| Typography/color/space/motion specifics | Minimal | Broad aesthetic bullets | Deep references plus examples | Add curated references |
| Interaction and UX writing | Missing | Broad | Deep references | High-value addition |
| Anti-pattern catalog | Missing | Generic warnings | Extensive DO/DON'T examples | Add split hard/soft taxonomy |
| Packaging model | Scoped instruction | Skill | Skill plus reference files | OwlBear should use both |

## 4. Reference Catalog

| Reference | Key content | Verdict | Rationale |
|-----------|-------------|---------|-----------|
| Typography | Vertical rhythm, modular scale, font pairing and loading, fluid vs fixed type, OpenType, accessibility | Adapt | High technical value; soften anti-default-font absolutism [S3, S4] |
| Color and contrast | OKLCH, tinted neutrals, palette roles, contrast traps, dark-mode semantics | Adapt | Good modern CSS guidance; soften absolute bans on HSL or pure black and white [S3, S4] |
| Spatial design | 4pt spacing, hierarchy, cards-not-default, container queries, touch targets, z-index scale | Adapt | Strongly reusable and mostly taste-neutral [S3, S4] |
| Motion design | Durations, easing tokens, transform and opacity only, reduced motion, perceived performance | Adapt | Strong performance and a11y guidance; keep easing preferences as defaults, not laws [S3, S4] |
| Interaction design | Interactive states, `:focus-visible`, labels, dialog/popover, undo vs confirm, keyboard patterns | Adapt | Valuable and concrete; keep browser-support caveats contextual [S3, S4] |
| Responsive design | Mobile-first, pointer and hover queries, safe areas, responsive images, real-device testing | Adapt | Fills a real gap beyond OwlBear's current breakpoint guidance [S1, S3] |
| UX writing | Button labels, error-message formula, empty states, tone, i18n, terminology | Adapt | High-value addition that is missing today [S1, S3] |

**Verbatim adoption:** reject for all seven files. The useful move is curated
adaptation into OwlBear-owned references, not copying Impeccable text wholesale
into always-on instructions [S3, S4, S6].

## 5. Anti-Pattern Split

**Universal blockers**: missing focus replacement, placeholder-as-label,
hover-only critical actions, low contrast or gray-on-color text, touch targets
under 44px, hidden critical mobile actions, missing reduced-motion fallback,
ambiguous primary actions like "OK" or "Submit", and generic error messages
[S1, S3, S5].

**Taste-specific heuristics**: defaulting to Inter or system fonts, purple or
cyan AI palettes, glassmorphism everywhere, large rounded icon tiles over
headings, centered-everything layouts, decorative sparklines, generic drop
shadows, hero-metric templates, and bounce easing [S3, S4, S5].

Hard rules belong in OwlBear's skill as blocking guidance. Taste heuristics
belong there only as examples of "AI slop" signatures to avoid, not as absolute
policy [S3, S4, S5].

## 6. Recommendation (.88 confidence)

- Create a dedicated `.github/skills/frontend-design/` skill with adapted
  reference files, rather than expanding `.github/instructions/frontend.instructions.md`
  into a large always-on prompt [S1, S2, S3, S6].
- Keep `frontend.instructions.md` as the lean policy layer: design-system
  choice, WCAG minimums, component hygiene, responsive and testing guardrails
  [S1, S2].
- Import the seven reference topics as adapted OwlBear resources. Do not copy
  any reference file verbatim; Impeccable's wording includes taste-heavy bans,
  command references, and a `teach-impeccable` dependency that do not map
  directly to OwlBear [S3, S4].
- Add one anti-pattern resource that separates universal blockers from taste
  heuristics, and preserve attribution similar to Impeccable's `NOTICE.md`
  because both Impeccable and OwlBear build on Anthropic prior art [S3, S5].
- Defer command-style adoption (`/teach-impeccable`, `/polish`, `/audit`) to
  task #930; this task's scope should stop at design-guidance architecture
  [S3, S4].

Why this fits OwlBear:

- VS Code skills are designed for resource-backed, on-demand expertise, while
  custom instructions are for project-wide standards [S6].
- OwlBear already treats frontend guidance as scoped instructions, not a global
  rule set, so moving depth into a skill continues that pattern instead of
  bloating background context [S1, S2].
- No reference file is worth skipping outright, but none is safe to import
  unchanged; the value is in curated adaptation, not wholesale adoption [S3,
  S4, S5].

## 7. Follow-up Tasks

1. #934 - Create OwlBear frontend-design skill from curated Impeccable references
   Priority rationale: unlock deep design guidance without turning always-on
   instructions into a large prompt blob.
   Dependencies: none.
   One-line AC: add a `frontend-design` skill with seven adapted references,
   design-context prompts, and attribution.
   Created: `kanban\kanban-md.exe create "Create OwlBear frontend-design skill from curated Impeccable references" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 929 ...`

2. #937 - Refactor frontend.instructions.md into lean guardrails plus skill handoff
   Priority rationale: preserve the current scoped baseline and avoid duplicating
   the new skill content.
   Dependencies: #934.
   One-line AC: keep repo-level rules in `frontend.instructions.md` and add a
   brief handoff to the new skill.
   Created: `kanban\kanban-md.exe create "Refactor frontend.instructions.md into lean guardrails plus skill handoff" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 929 --depends-on 934 ...`

3. #938 - Add OwlBear frontend anti-pattern taxonomy
   Priority rationale: preserve Impeccable's anti-slop benefits without turning
   taste into hard law.
   Dependencies: #934.
   One-line AC: add an anti-pattern resource that separates universal blockers
   from taste-specific heuristics and cites prior art.
   Created: `kanban\kanban-md.exe create "Add OwlBear frontend anti-pattern taxonomy" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 929 --depends-on 934 ...`
