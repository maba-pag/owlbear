---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Approve SSE approach"
notes: ""
# >> Agent metadata
task_id: 1233
agent: researcher
created: 2026-04-30
urgency: blocking
decision_type: approach-selection
impact_tier: 3
---

# Decision: Cockpit polling vs. server-sent events (SSE) in v1

## Context

Research task #1233 recommends replacing cockpit's current polling strategy with server-sent events (SSE), claiming improved latency and lower server load.

However, existing cockpit architecture brief has explicit locked decisions:
- `.owlbear/briefs/draft-cockpit/decisions.md:19` — "no SSE/WebSocket in v1"
- `.owlbear/briefs/draft-cockpit/decisions.md:65` — "Poll @ 3s"

This is a **T3 architecture decision** that overturn existing brief authority. Accepting the research recommendation would unlock follow-up implementation tasks #1234/#1235/#1236 (SSE client, SSE server, polling removal).

## Options

### A: Approve SSE approach — overturn v1 polling lock
- **Effort:** Medium (rewrite polling → SSE; backend streaming endpoint; browser compatibility testing)
- **Trade-off:** Defers polling-based v1 ship; extends v1 scope; requires brief authority rollback
- **Risk:** Scope creep; latency testing needed to validate research claim; potential browser compatibility gaps
- **Confidence: 0.7 (rec:)**

### B: Reject SSE — retain polling in v1
- **Effort:** None (existing architecture stands; follow-up tasks archived)
- **Trade-off:** Keeps v1 simple and on schedule; polling remains permanent or deferred to v2
- **Risk:** Potential user-facing latency complaints if polling cadence is inadequate
- **Confidence: 0.8 (bp:)**

### C: Defer to v2 — keep polling for now, retain SSE for future
- **Effort:** Minimal now; revisit in v2 planning
- **Trade-off:** Decouples v1 ship from architecture experimentation; moves SSE to v2 backlog at someday priority
- **Risk:** Research findings may become stale; v1 users may demand latency improvements post-launch
- **Confidence: 0.65**

## Recommendation

**Confidence: 0.6** — Option B (retain polling). Current brief authority locked polling explicitly; research recommendation lacks quantitative latency/load measurements to justify scope expansion. Ship v1 on polling, gather user feedback on latency, then revisit in v2 planning with empirical data.

If research has concrete benchmarks comparing v1 polling latency vs. SSE target latency, provide those to upgrade recommendation confidence.

## Impact of Deferral

**No auto-resolution for T3 decisions.** Awaiting explicit user response.

- **If approved (A):** Unlock follow-up tasks #1234/#1235/#1236; brief authority must be explicitly amended in `.owlbear/briefs/draft-cockpit/decisions.md`.
- **If rejected (B):** Archive #1234/#1235/#1236; retain polling for v1.
- **If deferred (C):** Retain polling for v1; move #1234/#1235/#1236 to someday priority for v2 review.
