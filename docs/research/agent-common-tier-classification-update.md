# Update agent-common Defer-to-User Boundary with Tier Classification

> **Owning task:** #462 — Update agent-common defer-to-user boundary with tier classification
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #385 established a 3-tier research outcome classification system (T1: autonomous, T2: advisory, T3: mandatory) with deterministic triggers, documented in `docs/research/mandatory-user-decision-gate.md`. The defer-to-user boundary in `instructions/agent-common.instructions.md` still uses vague language ("an important product/spec decision," "a research finding recommends a feature") that relies on agent judgment — exactly the gap the tier system was designed to close.

**Question:** What specific changes to agent-common's defer-to-user section align it with the tier classification system?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `docs/research/mandatory-user-decision-gate.md` (§4, §6-C5) | 1.0 — defines tier system and lists this file as change target |
| 2 | `instructions/agent-common.instructions.md` (lines 40–75) | 1.0 — current text to be updated |
| 3 | Anthropic "Building Effective Agents" (via parent research S1) | .90 — "programmatic checks" over agent self-assessment |
| 4 | AutoGen Human-in-the-Loop docs (via parent research S2) | .85 — typed termination conditions, not confidence thresholds |

## 3. Analysis

### Current state (lines 40–75 of agent-common)

| Element | Current text | Problem |
|---------|-------------|---------|
| Bullet 1 | "An important product/spec decision has multiple valid options" | Subjective — "important" is agent-judged |
| Bullet 2 | "A research finding recommends a feature or architectural direction" | Too broad — covers T1/T2/T3 indiscriminately |
| Researcher row | "Finding recommends a feature or direction the user hasn't approved" | No tier reference — doesn't distinguish T2 (advisory) from T3 (mandatory) |
| Other rows | Trigger descriptions are role-specific | Mostly still valid — can add tier context parenthetically |

### Proposed changes

**Bullet list** — Replace bullets 1–2 with tier-aware language:

- Replace bullet 1 with: "A T2 (advisory) or T3 (mandatory) outcome requires a decision request — see tier classification in the decision-requests skill"
- Replace bullet 2 with: "A T3 outcome (new capability, arch change, security/process change, breaking change) always requires a blocking decision request that does not auto-resolve"
- Keep bullets 3–4 unchanged (credentials/access and test failures are independent of tiers)

**Per-role triggers table** — Update rows with tier references:

| Agent | Updated trigger |
|-------|----------------|
| Researcher | T3 outcome per research classification (mandatory blocking DR); T2 outcome with no clear winner (advisory DR) |
| Architect | T3-origin task without approved DR; scope decision affecting downstream tasks |
| Builder | T3 design fork with product implications (not just technical choice) |
| Other rows | Add "(T2/T3)" qualifier where applicable; keep role-specific detail |

**Inline tier summary** — Add a brief tier definition before the table so agent-common is self-contained without requiring agents to load the decision-requests skill just to understand the concept:

> **Tier classification:** T1 (autonomous) = bug fix, refactor, config — proceed directly. T2 (advisory) = approach with trade-offs — advisory DR, 5-day auto-resolve. T3 (mandatory) = new feature, arch change, security/process change, breaking change — blocking DR, no auto-resolve. See the decision-requests skill for full trigger list.

### Dependency check

| Sibling task | Status | Blocks #462? |
|-------------|--------|-------------|
| #459 — Update decision-requests skill with impact_tier | ideation | Soft — #462 can reference tiers conceptually even before #459 adds the frontmatter field. Recommend ordering #459 first so the reference target exists. |
| #460 — Update researcher/research-workflow with tiers | ideation | No — independent file changes |

## 4. Recommendation (.90 confidence)

Apply the three changes above (bullet list, table, inline summary). The changes are mechanical text replacements guided by the tier definitions in the parent research doc. No new concepts introduced — just making existing guidance precise.

**Dependency note:** Ideally #459 lands first so the decision-requests skill defines `impact_tier` before agent-common references it. However, the agent-common changes are self-contained enough to land independently (the inline summary provides sufficient context). The architect should set `depends_on: [459]` if strict ordering is preferred.

## 5. Follow-up Tasks

No additional follow-up tasks needed — #462 itself is the implementation task. The AC is clear and the changes are well-scoped. The architect should review and advance to `todo`.
