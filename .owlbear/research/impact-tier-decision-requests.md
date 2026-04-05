# Impact-Tier Field for Decision Requests — Research Validation

> **Owning task:** #459 — Update decision-requests skill with impact_tier field and T3 indefinite blocking
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #459 implements one of four follow-up tasks from #385 (mandatory user-decision gate research). The approved decision (#385) selected a 3-tier classification system with deterministic triggers. This task's scope: add `impact_tier` to the decision-requests skill frontmatter, differentiate auto-timeout behavior by tier, and update the file format documentation.

**Validation questions:** (1) Is the `impact_tier` field design sound? (2) Are there backwards-compatibility concerns? (3) Does the AC cover all needed changes? (4) Is any follow-up missing?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Parent research #385 | docs/research/mandatory-user-decision-gate.md | 1.0 |
| 2 | Approved decision #385 | docs/decisions/resolved/385-research-outcome-classification.md | 1.0 |
| 3 | Current decision-requests skill | skills/decision-requests/SKILL.md | 1.0 |
| 4 | Planner Recipe 0 research #226 | docs/research/planner-recipe0-action-request-extension.md | .90 |
| 5 | AutoGen Human-in-the-Loop | microsoft.github.io/autogen/stable/.../human-in-the-loop.html | .85 |
| 6 | GitHub Actions environments | docs.github.com/en/actions/.../managing-environments-for-deployment | .75 |

## 3. Analysis

### Field design validation

| Aspect | Assessment | Source |
|--------|-----------|--------|
| Tiered timeout is standard | GitHub Actions has per-environment wait-timers (S6); AutoGen blocks indefinitely on `UserProxyAgent` (S5) | S5, S6 |
| `impact_tier` is orthogonal to `urgency` | `urgency` = agent state (blocking/advisory); `impact_tier` = decision importance (1/2/3) — no overlap | S3 |
| Deterministic triggers over confidence | Agents self-gate unreliably; factual triggers (adds capability? changes arch?) are verifiable | S1 (§4) |

### Backwards compatibility gap

Existing decision requests lack `impact_tier`. The skill must specify a default.

| Option | Behavior | Risk |
|--------|---------|------|
| **Default T2 (rec:)** | Existing requests keep 5-day auto-resolve — no behavior change | None |
| Default T3 | Existing requests block indefinitely — breaks current expectations | High |
| Require field | Existing requests become invalid | High |

**Recommendation (.90): Default T2.** This preserves current behavior. Only new requests explicitly set `impact_tier: 3` to opt into indefinite blocking.

### AC completeness check

| AC item | Covered? | Notes |
|---------|---------|-------|
| impact_tier field (1, 2, 3) | Yes | |
| T3 no auto-resolve | Yes | |
| T2 keeps 5-day | Yes | |
| Updated file format example | Yes | |
| Updated blocking behavior section | Yes | |
| Default for missing field | **No** | Add: "Files without impact_tier default to tier 2" |

### Missing follow-up: dispatch-planning skill

The decision-requests skill documents the behavior, but the dispatch-planning skill's Recipe 0 must also be updated to skip auto-resolution when `impact_tier: 3`. No task exists for this. Recipe 0 currently auto-resolves all decisions after 5 days (S4, §3). The planner needs a conditional: if `impact_tier` is 3, skip auto-resolve and report as "permanently pending."

## 4. Recommendation (.90 confidence)

Task #459's AC is well-specified and ready for implementation with one addendum: the AC should include a default-value rule for backwards compatibility (`impact_tier` defaults to 2 when absent). The dispatch-planning skill update is a separate follow-up task.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Update dispatch-planning Recipe 0 to skip auto-resolve for impact_tier=3" --priority needed --status ideation --tags "process,scope:agents,quality" --body "Recipe 0 in dispatch-planning skill auto-resolves pending decisions after 5 days. With impact_tier (from #459), T3 decisions must NOT auto-resolve. Update Recipe 0 logic: check impact_tier field, skip 5-day timer when impact_tier=3, report T3 pending count separately in JSON output. See docs/research/impact-tier-decision-requests.md. AC: - [ ] Recipe 0 checks impact_tier field in decision request frontmatter - [ ] impact_tier=3 decisions skip 5-day auto-resolve timer - [ ] Missing impact_tier defaults to 2 (current behavior preserved) - [ ] JSON output pending field distinguishes T2 vs T3 pending counts - [ ] Updated Recipe 0 prose documents tier-aware auto-resolution"
```
