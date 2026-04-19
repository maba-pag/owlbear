# Ad-hoc Critic Invocation in Ideation Flow

> **Owning task:** #1004 — Ad-hoc Critic invocation in ideation flow (user-request + Mediator self-trigger)
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

The ideation Critic (`ideation-critic`) is invoked only at four fixed moment boundaries (after M1, M2, M4, M5) and embedded inside panelist Critic loops during M3→M4 deliberation. No mechanism exists for:

- **User-initiated:** User asks "what does the Critic think?" mid-moment.
- **Mediator-initiated:** Mediator recognises a structural proposal that wasn't covered by prior panel deliberation and proactively invokes the Critic.

During the ideation session for #984, the user explicitly asked the Mediator to consult the Critic about a proposed audit dimension mid-walkthrough. The ad-hoc invocation surfaced critical false-positive risks (confidence 0.28) that would have been baked into the Brief. This depends on the user knowing to ask.

**Question:** Where and how should ad-hoc Critic invocation be documented?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `share/skills/w-ideation/SKILL.md` | Codebase | 1.0 — 6-moment flow, all current Critic invocation points |
| 2 | `share/skills/h-ideation-panel/SKILL.md` | Codebase | 1.0 — Critic loop protocol, standalone invocation patterns |
| 3 | `share/agents/ideation-critic.agent.md` | Codebase | 0.9 — Dual-Scope Invocation contract (already supports arbitrary positions) |
| 4 | `share/agents/ideator.agent.md` | Codebase | 0.8 — Mediator critical_rules and subagent table |
| 5 | Task #984 session evidence (in #1004 body) | Observation | 0.9 — real-world gap evidence |

## 3. Analysis

### 3.1 Current Invocation Landscape

| Invocation Type | Where Documented | Trigger | Moments |
|-----------------|------------------|---------|---------|
| Fixed standalone | w-ideation Steps 1–5; h-ideation-panel "Standalone Critic Invocations" | Moment boundary reached | After M1, M2, M4, M5 |
| Embedded loop | h-ideation-panel "Critic Loop Protocol" | Panelist forms position | M3→M4 deliberation |
| Ad-hoc (user) | **Not documented** | User request | Any |
| Ad-hoc (Mediator) | **Not documented** | Structural change detected | Any |

### 3.2 Feasibility: Agent Changes Required?

**None.** `ideation-critic` already supports arbitrary standalone invocations via its Dual-Scope Invocation contract. The Mediator already lists `ideation-critic` in its `agents:` frontmatter. This is purely a rules change.

### 3.3 Placement Options

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| A | h-ideation-panel only | All patterns together | Mediator may miss it (w-ideation is process authority) |
| B | w-ideation only | Mediator reads this for process | h-ideation-panel pattern catalogue incomplete |
| C | Both (duplicated) | Complete | DRY violation — two authoritative copies of trigger logic |
| **D** | **w-ideation (full rule) + h-ideation-panel (cross-reference)** | DRY-compliant, w-ideation authoritative, h-ideation-panel acknowledges pattern | h-ideation-panel readers must follow the cross-ref |

### 3.4 Trigger Definition

**User request (explicit):** User asks "what does the Critic think?" or similar. Low-impact to document — the Mediator already complies when asked (proven by #984). Formalising it makes the skill complete and signals sanctioned behavior.

**Mediator self-trigger (structural change detected):** Single structural principle rather than an enumerated list of conditions:

> When a proposal changes the problem boundary, outcome set, or approach AFTER the corresponding fixed-boundary Critic has already run, the Mediator MAY invoke the Critic on the changed element.

This collapses all trigger signals into one testable condition: "has the fixed-boundary Critic already covered this?" If yes and the thing has changed, re-invoke. If no boundary Critic has run yet, the upcoming boundary will catch it.

**MAY not MUST:** Consistent with the Mediator's existing judgment-based behavior on tier calibration, panelist selection, and depth. The Mediator exercises judgment; it is not a rules engine. At Scratch/Tool tier, the Mediator should lean toward skipping ad-hoc invocations (consistent with Adaptive Depth compression). At Shared/Production tier, the Mediator should lean toward invoking.

**Rate limiting:** At most one ad-hoc Critic invocation per user turn. If multiple changes surface in a single statement, the Mediator batches them into one focused Critic prompt.

### 3.5 Recording and Attribution

Ad-hoc Critic findings follow the **same treatment as fixed-boundary findings**:
- Critic returns response to Mediator (no direct file write — consistent with existing contract).
- Mediator presents findings to user with attribution: "[Critic] challenged this proposal — confidence {X}."
- If the finding influences a user decision, the *decision* is recorded in `decisions.md` with rationale citing the Critic finding (same as M4 decisions that cite the M4 Critic).
- No special tag needed — the existing recording pattern is sufficient.

### 3.6 Tier Gating via Adaptive Depth

w-ideation's Adaptive Depth section already compresses or skips Critic invocations at lower tiers. Ad-hoc triggers respect the same calibration:

| Tier | Self-trigger disposition |
|------|------------------------|
| Scratch | Skip — compressed flow, minimal Critic |
| Tool | Mediator judgment — invoke if the change is material |
| Shared / Production | Lean toward invoking |

### 3.7 Silent resolution

When a self-triggered Critic finds nothing material: the Mediator does NOT burden the user. It continues without mentioning the check. Only present findings to the user when they have moderate or critical severity.

## 4. Recommendation

**Option D** — full rule in w-ideation, cross-reference in h-ideation-panel.

**Confidence: 0.85**

Rationale: w-ideation is the Mediator's process authority. The full ad-hoc rule (trigger principle, MAY/rate-limit, tier gating, recording) belongs there. h-ideation-panel gets a one-line addition to the "Standalone Critic Invocations" section acknowledging that ad-hoc invocations exist and pointing to w-ideation.

**Implementation approach:**
1. **w-ideation** → New "Ad-hoc Critic Invocations" subsection (after Adaptive Depth). Contains: trigger principle, user-request path, MAY self-trigger with single-principle condition, rate limit (1 per turn), tier gating table, recording treatment, worked example.
2. **h-ideation-panel** → Add one row to "Standalone Critic Invocations" table: `| Ad-hoc | "See w-ideation — Ad-hoc Critic Invocations" |` and a brief note that ad-hoc invocations are additive to fixed-boundary checks.
3. **w-ideation Verification Checklist** → Add: "Ad-hoc Critic invocations (if any) presented to user when material."
4. No changes to ideation-critic.agent.md or ideator.agent.md.

**Worked example** (to include in w-ideation):
> During M5 walkthrough, user proposes adding a new artifact type (`.owlbear/audit-log.md`) not discussed in M3–M4 panel deliberation. The M5 fixed-boundary Critic has already run on the Brief. The Mediator recognises this changes the outcome set after the relevant boundary. Mediator invokes `ideation-critic`: "User proposes adding an audit-log artifact to the Brief. This wasn't part of panel deliberation. What risks does this introduce?" Critic returns findings (confidence 0.45 against — artifact duplicates existing kanban activity log). Mediator presents: "[Critic] flagged overlap with the existing activity log — confidence 0.45 against adding this. Your call." User decides to drop it.

Challenge: `reconsider` — confidence in original: 0.60. Revised to address: collapsed triggers to single principle, MUST→MAY, added tier gating, fixed recording inconsistency, DRY-compliant placement (Option D), added rate limit.

## 5. Follow-up Tasks

- **Follow-up #1:** Implement Option D — add ad-hoc Critic invocation rules to w-ideation + cross-reference in h-ideation-panel (at `research` status).
