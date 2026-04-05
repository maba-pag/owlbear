# Recipe 0 Tier-Aware Auto-Resolution — Research Validation

> **Owning task:** #464 — Update dispatch-planning Recipe 0 to skip auto-resolve for impact_tier=3
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #464 is a follow-up from #459 (impact_tier field for decision requests). Recipe 0 in the dispatch-planning skill currently auto-resolves all pending decisions after 5 days. With the T1/T2/T3 classification system (approved in #385), T3 decisions must block indefinitely — they represent new features, architecture changes, security policy, and process changes that require explicit user approval.

**Validation questions:** (1) Is the AC complete for the skill file change? (2) What specific Recipe 0 lines change? (3) How should the JSON `pending` field report tier-distinguished counts? (4) Are there edge cases?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Impact-tier research #459 | docs/research/impact-tier-decision-requests.md | 1.0 |
| 2 | Approved decision #385 | docs/decisions/resolved/385-research-outcome-classification.md | 1.0 |
| 3 | Recipe 0 action-request extension #226 | docs/research/planner-recipe0-action-request-extension.md | .95 |
| 4 | Current dispatch-planning skill | skills/dispatch-planning/SKILL.md (lines 58–71) | 1.0 |
| 5 | GitHub Actions environment protection | docs.github.com/en/actions/.../managing-environments-for-deployment | .75 |
| 6 | AutoGen Human-in-the-Loop | microsoft.github.io/autogen/stable/.../human-in-the-loop.html | .70 |

## 3. Analysis

### Current Recipe 0 behavior (lines 58–71 of dispatch-planning SKILL.md)

Recipe 0 lists `docs/decisions/pending/*.md`, reads frontmatter, and applies two rules:
- `approved: true` (or `completed: true` for action requests) → unblock task + move to `resolved/`
- `approved: false` and older than 5 days → auto-resolve with agent recommendation

The change: add a conditional check for `impact_tier` before the 5-day auto-resolve.

### Implementation approach validation

| Aspect | Assessment | Source |
|--------|-----------|--------|
| Tier skip is standard | GitHub Actions: production environments have required-reviewers with no auto-bypass; staging has wait-timers. Per-environment differentiation is the norm. | S5 |
| Indefinite blocking is safe | AutoGen `UserProxyAgent` blocks indefinitely. OwlBear is single-user — indefinite T3 blocking is acceptable because the planner surfaces pending counts each cycle. | S6 |
| Default T2 preserves compat | Existing files without `impact_tier` keep 5-day auto-resolve. Confirmed in S1 at .90 confidence. | S1 |

### Recipe 0 change scope (confined to SKILL.md prose)

| Section | Current | Updated |
|---------|---------|---------|
| Recipe 0 prose (lines 58–71) | "If `approved: false` and older than 5 days, auto-resolve" | Add: "If `impact_tier: 3`, skip auto-resolve regardless of age. Missing `impact_tier` defaults to 2." |
| Step 1 paragraph (line 159) | "Run Recipe 0 (Decision requests)" | Add: "Recipe 0 now distinguishes T2 (auto-resolvable) from T3 (permanently pending)." |
| Step 3 JSON (line 290+) | No `pending` field exists yet (#226 research proposed it but was not implemented) | Add `pending` field: `{"decisions_t2": N, "decisions_t3": N, "actions": N}` |

### JSON `pending` field design

The #226 research proposed `{"decisions": N, "actions": N}`. With tier awareness, split decisions into T2 and T3:

| Option | Format | KISS | Info value |
|--------|--------|------|------------|
| **A: Split decisions by tier (rec:)** | `{"decisions_t2": 1, "decisions_t3": 2, "actions": 0}` | High — flat keys | High — orchestrator knows which need user action |
| B: Nested object | `{"decisions": {"t2": 1, "t3": 2}, "actions": 0}` | Lower — nesting adds parsing | Same |
| C: Single count + flag | `{"decisions": 3, "has_t3": true, "actions": 0}` | Medium | Lower — no T3 count |

**Recommendation (.90): Option A.** Flat keys are simplest to parse, provide full information, and align with KISS. T1 decisions are not pending (they proceed autonomously).

### Edge cases

| Edge case | Handling |
|-----------|---------|
| Missing `impact_tier` in old files | Default to T2 — current behavior preserved |
| `impact_tier: 1` in pending file | Should not exist (T1 proceeds autonomously, no DR created). If found, treat as T2. |
| Action requests (`request_type: action`) | `impact_tier` does not apply — actions have their own `completed` field and keep 5-day auto-resolve |
| `approved: auto` already set | File already auto-resolved in a prior cycle — skip (move to resolved/) |

### AC completeness check

| AC item | Valid? | Notes |
|---------|--------|-------|
| Recipe 0 checks impact_tier field | Yes | Read from YAML frontmatter |
| T3 skips 5-day auto-resolve | Yes | Core change |
| Missing impact_tier defaults to 2 | Yes | Backwards compat |
| JSON pending distinguishes T2 vs T3 | Yes | New `pending` field with split keys |
| Updated Recipe 0 prose | Yes | Prose + Step 1 + Step 3 sections |

AC is complete. No gaps found.

## 4. Recommendation (.90 confidence)

Task #464's AC is complete and ready for implementation. The change is confined to one file (`skills/dispatch-planning/SKILL.md`) with three sections updated:

1. **Recipe 0 prose** — add tier check before auto-resolve
2. **Step 1 paragraph** — note tier-aware behavior
3. **Step 3 JSON format** — add `pending` field with `decisions_t2`, `decisions_t3`, `actions` keys

No code changes needed (this is a skill/docs task). No new files. No decision request needed — the approach is clear with one valid option.

**Dependency:** #459 should land first so the decision-requests skill defines `impact_tier` before the dispatch-planning skill references it. However, both are skill-prose tasks that can land independently.

## 5. Follow-up Tasks

No additional follow-up tasks needed beyond #464 itself. The AC covers all required changes.
