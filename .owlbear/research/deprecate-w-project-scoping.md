# Deprecate w-project-scoping Skill

> **Owning task:** #643 — P4-03: Deprecate w-project-scoping skill
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

The Phase-4 Thinking Companion Framework (`.owlbear/research/thinking-companion-framework.md`, Section 13, prerequisite #9) specifies that `w-project-scoping` should be deprecated in favor of the planned Ideator agent. The Ideator subsumes the skill's "vague idea → structured definition" function with a richer deliberation model (Mediator + Voice Panel).

**Question:** What deprecation approach fits existing conventions, and what references need updating?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `share/skills/h-kanban-md/SKILL.md` (deprecated skill) | 0.9 | Deprecation pattern: `(DEPRECATED)` in description + banner in body with redirect |
| 2 | `share/skills/w-dispatch-planning/SKILL.md` (archived skill) | 0.8 | Archive pattern: `(ARCHIVED)` in description + supersession note |
| 3 | `.owlbear/research/thinking-companion-framework.md` §13 | 1.0 | Spec authority: deprecate or refactor to delegate to ideator |
| 4 | Codebase grep for `w-project-scoping` (9 hits) | 0.9 | Full reference inventory |

## 3. Analysis

### Reference Inventory

| Location | Type | Action needed |
|----------|------|---------------|
| `share/skills/w-project-scoping/SKILL.md` | Skill file | Deprecate frontmatter + add banner |
| `share/skills/h-agent-structure/SKILL.md` L182 | Documentary example | Update example to use non-deprecated skill or annotate |
| `tests/test_argument_hint_skills.py` L8,L19 | Test for argument-hint | No change — tests still valid (file persists, just deprecated) |
| `.owlbear/research/thinking-companion-framework.md` | Spec (read-only) | No change |
| `.owlbear/kanban/tasks/643-*.md` | Task file | No change |

### Pattern Comparison

| Criterion | DEPRECATED (h-kanban-md) | ARCHIVED (w-dispatch-planning) |
|-----------|--------------------------|-------------------------------|
| Description prefix | `(DEPRECATED)` | `(ARCHIVED)` |
| Body banner | Redirect to replacement | Supersession note |
| Content preserved | Yes — reduced to redirect | Yes — retained as reference |
| Applies when | Replacement exists or is in progress | Skill fully superseded, retained for reference data |

### Recommendation

Use the **DEPRECATED** pattern (not ARCHIVED), matching `h-kanban-md`:
- The skill is not fully superseded yet — the Ideator doesn't exist
- Deprecation signals intent while keeping the skill usable as fallback
- When the Ideator ships, a second pass can archive or remove

**Confidence: .90** — two established patterns, clear spec mandate, zero active pipeline dependencies.

**Challenge: SKIPPED** — trivial deprecation following established patterns.

## 4. Follow-up Tasks

Two concrete implementation tasks created at `ideation`:

1. **Deprecate `w-project-scoping` frontmatter + body** — edit SKILL.md with DEPRECATED description and banner
2. **Update `h-agent-structure` documentary reference** — replace or annotate the `w-project-scoping` example at L182

## 5. Tier Classification

**T1 — Autonomous.** Config/chore change, established pattern, spec-approved direction. No architecture decisions or breaking changes.
