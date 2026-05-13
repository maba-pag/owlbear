# Decisions — Dep-Status Guidance in start_work

## D1 — 2026-05-13 — Project Type

**Status quo:** Input brief proposes a small additive change to existing `agent_view.start_work()`.
**Decision to make:** Is this net-new or existing-feature/refactor?

**Options considered:**

- A: existing-feature/refactor — all infrastructure exists, change is additive
- B: net-new — requires new subsystems

**Chosen:** A (existing-feature/refactor) — `_compute_dep_status`, `SingleTaskResponse.guidance`, and `start_work` all exist and ship today.

**Rejected:**

- B because no new infrastructure is needed; this wires existing primitives together.

## D2 — 2026-05-13 — Investment Tier

**Status quo:** Change is bounded to one method in agent_view.py, wiring existing primitives.
**Decision to make:** What depth/rigor calibration is appropriate?

**Options considered:**

- A: Scratch — too shallow; this touches a real workflow path
- B: Tool — internal utility, single consumer (agents), bounded scope
- C: Shared — overkill; no multi-consumer concern
- D: Production — overkill; internal-only

**Chosen:** B (Tool) — standard M2, selective early challengers, full Brief.

**Rejected:**

- A because even though small, it affects live agent behavior on real tasks.
- C/D because this is internal-only with a single consumption point.

## D3 — 2026-05-13 — Simplifier Cuts

**Status quo:** Original brief proposed ~15-20 LoC covering both blocked/redirect, with per-dep status detail.
**Decision to make:** Accept simplifier's scope reduction?

**Options considered:**

- A: Accept all three cuts — drop redirect, skip per-dep detail, reuse show_task (~5 LoC)
- B: Keep redirect in scope
- C: Keep per-dep detail
- D: Reject cuts, keep original scope

**Chosen:** A — minimal is better. Blocked is the dangerous case; redirect means deps are archived. Flat "unresolved deps: [IDs]" is enough; agent can show_task each dep if curious.

**Rejected:**

- B because redirect means deps are done (just archived with a non-standard reason). Low risk.
- C because per-dep status detail requires N+1 lookups — gold-plating for a soft gate.
- D because simpler is better when the change is a soft guardrail.

## D4 — 2026-05-13 — First-Principles Challenge: Soft vs Hard Gate

**Status quo:** First-principles argued that if risk warrants action, a hard block is honest; if not, the change isn't worth it. Also argued dep_status is one symptom of broader "unvalidated manual assignment."
**Decision to make:** Is soft directive guidance the right intervention?

**Chosen:** Soft directive guidance — the "disease" is the user doing what they want. Hard blocks create perverse incentives (user manually edits tasks to remove deps). Soft guardrails preserve human autonomy while surfacing risk.

**Rejected:**

- Hard block because it forces escape-hatch complexity and incentivizes workarounds.
- Upstream orchestrator check because the user IS the orchestrator in manual assignment — can't validate against yourself.
- Kill the idea because the gap is real and the cost is ~5 LoC.
