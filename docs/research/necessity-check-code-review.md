# Necessity Check for Code-Review Skill

> **Owning task:** #196 — Add necessity check to code-review skill critical checks
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #192 (pipeline-quality-audit) found that six pipeline agents approved a
redundant GitHub MCP server addition (#121) because no agent is instructed to
question whether a feature should exist. Recommendation R3 proposes adding a
"Necessity Check" to the reviewer's Pass 1 critical checks. This research
validates that recommendation and identifies an AC discrepancy.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `docs/research/pipeline-quality-audit.md` §3.3–3.4 | Internal | 1.0 — identifies the gap: 0/88 reviewer rejections cited "unnecessary feature" |
| S2 | Google Eng-Practices: "What to Look For in a Code Review" | External | 0.9 — Design section: "Does this change belong in your codebase?" Complexity: warns against "functionality that isn't presently needed" |
| S3 | Fowler, "Yagni" (2015, martinfowler.com) | External | 0.8 — Kohavi et al.: ⅔ of features don't improve intended metrics. Cost of carry analysis. |
| S4 | SmartBear "Best Practices for Peer Code Review" | External | 0.7 — Checklists are the most effective way to eliminate omission-type errors |

## 3. Analysis

### 3.1 AC Numbering Discrepancy

The AC specifies "New section 6.5." However, the current code-review skill
already has section 6.5 ("Implementation-aware test gap analysis"). The new
section should be **6.6** to avoid collision.

### 3.2 Coverage Gap Confirmation

| Error type | Current pipeline coverage | Evidence |
|------------|--------------------------|----------|
| Wrong implementation | Strong — reviewer catches lint, tests, assertions | S1 §3.4 |
| Missing implementation | Moderate — auditor runs full suite | S1 §3.4 |
| Unnecessary addition | **None** — no agent questions premise | S1 §3.3 |

Google's review framework (S2) explicitly asks "Does this change belong?" under
Design. OwlBear's reviewer checks none of these dimensions. Fowler (S3) provides
the theoretical basis: ⅔ of presumptive features don't deliver intended value,
and all carry cost-of-carry overhead.

### 3.3 Scoping the Check

The check must be conditional — bug fixes and refactors don't add new
capabilities. Existing skill precedent: sections 6.0 and 6.2 use `> **Conditional:**`
gates. The same pattern applies here.

**Trigger conditions** (any of):
- Task adds a new dependency or integration
- Task adds a new tool, server, or external capability
- AC describes "add", "integrate", or "connect" a capability

**Not triggered by**: bug fixes, refactors, renames, config tweaks, test improvements.

### 3.4 What the Reviewer Should Check

Per S2 and S3, the reviewer asks three questions:
1. Does the IDE, runtime, or an installed extension already provide this?
2. Does existing project tooling already solve this need?
3. Is this a presumptive feature (building for speculated future need)?

If yes to any: FAIL with evidence citing the existing provider.

### 3.5 Red-Flag Addition

The reviewer agent's red-flags list (`reviewer.agent.md` → boundaries) already
has 16 items. Adding one more for necessity is low burden and consistent.

## 4. Recommendation (.90 confidence)

Proceed with implementation. The concept is well-supported by both internal
evidence (S1 — 0/88 rejections for "unnecessary") and external practice (S2, S3).

**AC corrections for the architect:**
- Section number: 6.6, not 6.5 (6.5 is taken)
- Use the existing `> **Conditional:**` pattern for scoping

## 5. Follow-up Tasks

No new follow-up tasks needed — #196 itself is the implementation task. The
architect should correct the section numbering during review.
