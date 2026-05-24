# End-User Stance — Critic Debate Log

## Cycle 1

### Draft Position Summary

Core: the resolver must feel like making a choice, not filling a form. Decision requests are micro-interruptions. Minimize time-to-comprehension and time-to-action. Options as cards, one-tap select + confirm, confidence as relative bars (no numbers), inline expansion, disappearance as primary feedback.

### Critic Challenges (Severity: Critical)

1. **Overfits to easy case.** The "Worth Using" metric was defined only for instant-resolution with high confidence spread. Ambiguous cases, free-text-only cases, and error paths were afterthoughts.
2. **"Ratifying the agent" masquerading as choosing.** Recommended option as fast path + hidden rationale + visual dominance = rubber-stamping, not deciding.
3. **Action resolver hardcodes unresolved states.** Context still lists action resolution states as open. Stance prematurely locked "Done (success), Done (with problems), Rejected."
4. **Feedback is happy-path only.** "It's gone from my queue" ignores stale resolution, network failure, partial writes, and multi-step mechanical flow.
5. **Queue-clearing vs work-unblocking.** The user's actual job is continuing blocked work, not clearing notifications.

### Critic Challenges (Severity: Moderate)

6. **Tap count inconsistency.** "One tap select + one tap confirm" contradicts "one glance, one click."
7. **Confidence rejection contradicts user statement.** User said "the higher the difference the faster I decide" — they need the numeric spread visible, not just a vague relative bar.
8. **Inline expansion + item removal = layout churn.** The anti-modal argument creates the same problem it avoids.

### Blind Spots Surfaced

- Multiple pending requests per task: resolution of one doesn't imply task unblock
- Authority boundary (human vs agent resolution) unaddressed
- Option ID stability for machine-readable resolution
- Accessibility entirely absent (keyboard, focus, non-visual interpretation)
- Partial-success lifecycle states between "clicked confirm" and "task unblocked"

### Resolution

Accepted all critical challenges. Revised stance to:
- Show numeric confidence (user explicitly values the spread)
- Make rationale visible by default (choosing, not rubber-stamping)
- Frame action resolver as outcome-reporting principles, not hardcoded states
- Task-unblock-centric feedback, not queue-centric
- Explicit error/stale state handling
- Detail panel approach instead of inline expansion or modal

---

## Cycle 2

### Revised Position Summary

Core: resolver's job is to unblock work by recording a real decision. Two speeds: instant for clear winners, deliberate for ambiguous. Numeric confidence shown. Rationale visible by default. Select + Confirm (two actions). Detail panel (not modal, not inline). Feedback: resolved state shown briefly, then "Task unblocked" toast. Actions framed as outcome reporting.

### Critic Challenges (Severity: Critical)

1. **Two-speed resolver is still one dense surface.** Rationale visible + free text always visible + confidence primary = the "clear winner" path still loads comparison-grade UI.
2. **Card visual hierarchy unresolved.** Recommended badge, confidence, and rationale cannot all be the dominant first-read signal simultaneously.
3. **Action model still underspecified.** Does not state whether actions use option cards, confidence, or the same select+confirm contract.
4. **Interaction pattern is a menu of three options** (right panel, expansion, routed detail) — not a committed decision a designer can implement.
5. **Unblock message overclaims.** One request resolved ≠ task unblocked when sibling requests exist.
6. **Confidence calibration not addressed.** Numbers are shown but their meaning/trustworthiness is unspecified.

### Critic Challenges (Severity: Moderate)

7. **Action bias dressed as neutrality.** "Positive completion is primary" steers habitual responses.
8. **Delayed collapse still churns.** Moving the churn by 2-3s doesn't eliminate it.
9. **Empty confidence vs tie conflated.** Missing numbers and meaningful ties need different treatment.
10. **Truncation rules inconsistent** between "first line" and "first sentence."
11. **Quality bar false for free-text-only path.**

### Blind Spots Surfaced

- In-flight state (between confirm click and response)
- Confirm enablement rules (what must be present to enable the button)
- Draft persistence when navigating away
- Recommendation cardinality (can multiple options be recommended?)
- Age indicator ambiguity (request age vs task-blocked-since vs last-updated)

### Resolution

Addressed all critical challenges in final stance:
- Committed to routed detail view (one pattern, implementable)
- Separated two modes: quick-confirm (pre-selected recommendation, just confirm) and full-compare (all options equal)
- Actions explicitly do NOT use option cards — they use direct outcome buttons
- Unblock message is conditional on being the last pending request
- Confidence shown as-is from the model; UI does not interpret calibration
- Visual hierarchy: recommended badge → confidence spread → rationale (clear priority order)

---

## Final Confidence

0.74 — Strong UX position with clear interaction contract. Remaining uncertainty: exact action states (open design parameter), and whether the two-mode approach adds complexity that outweighs its benefit in a low-volume single-user system.
