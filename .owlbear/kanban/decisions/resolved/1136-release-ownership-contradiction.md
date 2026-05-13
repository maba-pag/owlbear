---
response: approved
decision: "A: Close #1136 as superseded by #1133"
notes: "User confirmed: OCC timestamp comparison (#1133) is the correct mechanism. Admin force-release stays unconditional per D12. Ownership enforcement is not wanted."
task_id: 1136
agent: "architect"
created: 2026-04-26
urgency: blocking
decision_type: scope-decision
impact_tier: 2
---

# Decision: Task #1136 AC Contradicts Design Decision D12

## Context

Task #1136 acceptance criteria requires: "Release route rejects attempts to clear a claim owned by a different actor" (ownership enforcement).

Design decision **D12** (draft-cockpit/decisions.md) explicitly defines cockpit release as **unconditional admin force-release** — no ownership check.

Brief B §3.6 confirms: `release_task (Cockpit-only) — admin force-release`.

The original safety concern motivating #1136 (preventing stale-snapshot releases) is **already covered** by task #1133, which implements optimistic concurrency control (OCC) with compare-and-swap validation on all release attempts. This safety gate does not require ownership enforcement.

## Options

### A: Close #1136 as superseded by #1133 — (rec:) recommended
- **Effort:** Trivial (archive task)
- **Trade-off:** Removes perceived "safety check," but OCC/CAS on release (#1133) provides stronger safety (atomic validation, not just ownership)
- **Risk:** Low. Design intent (unconditional admin release) remains intact; safety is preserved by #1133. No D12 override needed.
- **Confidence:** 0.95

### B: Keep #1136 with modified AC (ownership enforcement) — (bp:) design override
- **Effort:** Re-implement release route, modify tests
- **Trade-off:** Strengthens release safety with ownership verification; contradicts D12 (unconditional admin release), making cockpit-only releases non-forceful
- **Risk:** High. This reverses an explicit design decision. Requires T3 approval; cascades to Brief B and any deployed systems expecting unconditional release.
- **Confidence:** 0.15 (pending user preference)

### C: Defer / request clarification
- **Effort:** None
- **Trade-off:** Leaves task blocked; design ambiguity persists
- **Risk:** Stalls release feature delivery pending user decision

## Recommendation

**0.95 confidence — Option A.** Close #1136 as superseded by #1133.

The real safety requirement (atomic CAS validation) is now covered by #1133, which is stronger than ownership enforcement alone. D12's unconditional release design remains valid. No contradictions need resolution; #1136's original concern is now satisfied by a different mechanism.

If the user prefers ownership enforcement despite D12, that is a legitimate T3 design override — but it must be explicitly requested and documented as a D12 amendment, not treated as a suppressed AC.

## Impact of Deferral

- Task #1136 remains blocked pending approval to close or re-scope
- Brief B release feature (#1100s) may be gated awaiting this decision
- 5-day auto-resolve window (T2 advisory): recommend approval of Option A unless user objects
