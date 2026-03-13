# Two-Pass Review Checklist with Suppressions

> **Owning task:** #784 — Add two-pass review checklist with suppressions to reviewer skill
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

OwlBear's code-review SKILL.md uses a single-pass workflow: all findings (security, style, naming)
are treated equally. This creates noise — style nits compete with injection risks for reviewer
attention. How should we restructure the checklist into priority tiers with an explicit suppressions
list?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| gstack review/checklist.md | <https://github.com/garrytan/gstack/blob/main/review/checklist.md> | .90 | Two-pass (CRITICAL blocks ship, INFORMATIONAL included but non-blocking) + suppressions list |
| Google Eng Practices — Review Standard | <https://google.github.io/eng-practices/review/reviewer/standard.html> | .80 | "Nit:" prefix for non-critical; reviewer should not block progress on polish |
| Conventional Comments | <https://conventionalcomments.org/> | .75 | Formal label taxonomy: issue/suggestion/nitpick + blocking/non-blocking decorations |

## 3. Analysis

### Approach Comparison

| Dimension | gstack two-pass | Google "Nit:" prefix | Conventional Comments labels | OwlBear fit |
|-----------|----------------|----------------------|------------------------------|-------------|
| Complexity | Low — 2 tiers | Minimal — prefix only | Medium — 8+ labels | Low preferred (KISS) |
| Blocking semantics | CRITICAL blocks, INFO doesn't | Nit = non-blocking | Explicit `(blocking)` decorator | Need explicit |
| Suppressions | Yes — explicit list of DO-NOT-flag patterns | No — reviewer discretion | No — reviewer discretion | Yes (reduces noise) |
| Automation fit | High — can be parsed by auditor | Low — human convention | High — structured format | High preferred |
| Adoption effort | Low — restructure existing checklist | Trivial | Medium — new format standard | Low preferred |

### Mapping to OwlBear's Existing Structure

The code-review SKILL.md already has implicit tiers:

- **Step 5b (Security review)** = naturally CRITICAL (any vuln = FAIL)
- **Step 5a (Test quality)** = naturally CRITICAL (WEAK = FAIL)
- **Step 5 (Code reading)** = mix of critical (missing types) and informational (style)
- **Step 5c (Test writer comparison)** = naturally CRITICAL (WEAKENED/REMOVED = FAIL)

The restructuring doesn't require new checks — it reorganizes existing ones into explicit passes
and adds a suppressions list to reduce false positives from common harmless patterns.

### Suppressions Analysis

From reviewing recent OwlBear reviewer sessions and gstack's patterns, these suppressions apply:

| Suppression | Rationale | gstack analog |
|-------------|-----------|---------------|
| Threshold/constant values without justification comments | Tuned empirically, comments rot | "Eval threshold changes" |
| Redundant guards that aid readability | Harmless, defensive | "X is redundant with Y" |
| Test exercises multiple guards simultaneously | Valid integration style | Same pattern |
| Already-addressed items in the diff | Reader didn't read full diff | "ANYTHING already addressed" |
| Style-only consistency changes | Not a defect | "Suggesting consistency-only changes" |
| Regex edge cases for constrained inputs | Input never hits the edge | "Regex doesn't handle X" |

### OwlBear-Specific Suppressions (not in gstack)

| Suppression | Rationale |
|-------------|-----------|
| `from __future__ import annotations` presence in test files | Convention, not a defect to flag repeatedly |
| Agent/skill markdown formatting nits | Formatting is fluid during active development |
| Coverage gaps in code not touched by the task | Out of scope for task-scoped review |

## 4. Recommendation (.85 confidence)

**Adopt the gstack two-pass model**, adapted for OwlBear's existing reviewer structure:

**Pass 1 — CRITICAL (any finding = FAIL):**

- Security review (Step 5b checks): injection, secrets, path traversal, deserialization, input validation
- Test integrity (Step 5c): TestFromAC weakened/removed assertions
- Test quality (Step 5a): any WEAK dimension
- Data safety: unvalidated LLM output persisted, race conditions, missing atomicity

**Pass 2 — INFORMATIONAL (noted but does not block PASS):**

- Style: naming, dead code, unused imports
- Documentation: missing/stale docstrings, comments
- Minor test improvements: could-be-tighter assertions that already cover behavior
- Code structure: flat-vs-nested, function length suggestions

**Suppressions section** prevents the reviewer from flagging 9 specific harmless patterns.

**Risk:** Low. This is a documentation-only change to SKILL.md and agent.md. No Python code
changes. The reviewer agent's behavior shifts through updated instructions, not code.

**Why not Conventional Comments?** Over-engineering for an automated reviewer that produces
structured tables, not inline PR comments. The two-pass model maps directly to the existing
binary PASS/FAIL verdict. Conventional Comments would require a new output format (YAGNI).

## 5. Follow-up Tasks

Single implementation task (the AC is already well-defined in #784):

```
kanban\kanban-md.exe create "Implement two-pass review checklist in code-review SKILL.md" --priority needed --status ideation --tags "scope:agent-config,type:docs" --body "## Goal\nRestructure code-review SKILL.md to use two-pass review with suppressions.\n\n## AC\n- [ ] Steps 5/5a/5b/5c reorganized under Pass 1 (CRITICAL) and Pass 2 (INFORMATIONAL) headers\n- [ ] Pass 1 includes: security (5b), test integrity (5c WEAKENED/REMOVED), test quality (5a WEAK), data safety\n- [ ] Pass 2 includes: style, documentation, minor test improvements, code structure\n- [ ] New 'Suppressions' section with 9 DO-NOT-flag patterns\n- [ ] reviewer.agent.md workflow summary updated to mention two-pass structure\n- [ ] Review output format template updated with CRITICAL/INFORMATIONAL sections\n- [ ] No changes to .py files\n\nSee docs/research/two-pass-review-checklist.md for analysis."
```
