# Fix ideator/w-ideation askQuestions instruction conflict

> **Owning task:** #996 — Fix ideator/w-ideation askQuestions instruction conflict
> **Date:** 2026-04-18 (updated 2026-04-19) **Status:** Complete

## 1. Context and Question

**Original issue:** The ideator agent's `critical_rules` originally scoped `askQuestions` to "decision points." The `w-ideation` skill described M1 as natural investigative dialogue with no `askQuestions` annotation on probe steps. This caused silent stalls. Fix was applied; original 4 AC are met.

**Extension issue (from #984 ideation session):** The "use confidence (0.0–1.0) and one `recommended` choice when trade-offs exist" rule lives in `ideator.agent.md` critical_rules but is not operationalized in `w-ideation`. Per `r-pipeline-protocol`, skills are the authority — agents trained to follow the skill (not the agent file) will miss the confidence pattern.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `share/agents/ideator.agent.md` (line 40) | 1.0 — contains confidence/recommended rule |
| 2 | `share/skills/w-ideation/SKILL.md` (Steps 4, 5) | 1.0 — lacks worked examples for confidence pattern |
| 3 | Prior research: `.owlbear/research/996-ideator-askquestions-conflict.md` (v1) | 0.9 — validated original 4 AC |
| 4 | Prior research: `.owlbear/research/998-planner-askquestions-approval.md` | 0.7 — shows confidence pattern in planner context |
| 5 | User memory "askQuestions Best Practice" | 0.8 — documents the incident |
| 6 | `r-pipeline-protocol` § Skill Authority | 0.9 — skills override agent files |

## 3. Analysis

### Original AC — ✅ All Met (unchanged from v1)

| AC | Status | Evidence |
|----|--------|----------|
| Agent file has unambiguous "askQuestions is the only way to end a user-facing turn" | ✅ | ideator.agent.md line ~40 |
| w-ideation Step 1 has "every probe ends with askQuestions" | ✅ | Turn-ending rule + per-step annotations |
| Worked `allowFreeformInput: true` example | ✅ | Code block in Step 1 |
| No conflict between the two documents | ✅ | Aligned |

### Extension AC — ❌ 3 Gaps Remain

| Extension AC | Status | Current State |
|---|---|---|
| Step 4: worked askQuestions with 3-4 options, per-option confidence, one `recommended: true` | ❌ | Line 111 says "confidence and recommendation per option" — prose only, no worked example |
| Step 5: explicit instruction that trade-off askQuestions carry per-option confidence | ❌ | Walkthrough section shows procedural options only ("Good, next" / "Needs adjustment") — no confidence rule |
| Confidence/recommended rule stated in w-ideation itself | ❌ | Rule exists only in ideator.agent.md; w-ideation has a prose mention, not a standalone rule |

### Root Cause

The confidence pattern was added to `ideator.agent.md` critical_rules but never propagated to `w-ideation/SKILL.md`. Since skills are authoritative (`r-pipeline-protocol`), the Mediator reads the skill and misses the pattern.

### Implementation Approach

Three changes to `share/skills/w-ideation/SKILL.md` (all within existing file, no new files):

1. **Step 4, after line 111:** Add a worked `vscode_askQuestions` example showing 3 approaches with per-option confidence and one marked `recommended: true`. ~15 lines.
2. **Step 5, Walkthrough Loop sub-section:** Add an explicit instruction: "When presenting options that involve genuine trade-offs (not procedural next/back choices), include per-option confidence (0.0–1.0) and mark one as `recommended`." ~3 lines.
3. **Before Step 1 or as a new preamble rule:** State the general rule: "When any askQuestions call presents >2 options with genuine trade-offs, include per-option confidence (0.0–1.0) and one `recommended` option." ~2 lines.

Estimated diff: ~25 lines added, 0 removed. Scope: `w-ideation/SKILL.md` only.

## 4. Recommendation

Create one follow-up implementation task to add the three items above. T1 — docs-only, no architecture, no security, no new capability.

Confidence: **0.90** — straightforward text additions to an existing file with clear placement points.

Challenge: FALLBACK — mechanical fix, no design trade-off to challenge.

## 5. Follow-up Tasks

See follow-up task created via `create_task`.
