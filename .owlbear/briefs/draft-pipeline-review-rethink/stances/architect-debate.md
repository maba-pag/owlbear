# Architect Debate Log — Pipeline Review Rethink

## Critic Cycle 1

### Draft Position

The proposal is structurally sound but has three underspecified joints: (1) consolidation-test trigger has no first-class signal, (2) architect checker expansion conflates design validation and linguistic AC quality, (3) reviewer reading builder's quality-runner output is trust without verification.

### Critic Challenges (8 total, 4 critical)

1. **Critical — Consolidation trigger renamed, not resolved.** Draft replaced "feature chain" with "feature group" — equally undefined. The trigger was still not mechanically specified.
   - **Accepted.** Revised to: planner creates consolidation-test task during upfront decomposition with explicit dependencies. Acknowledged this is lightweight metadata maintenance, not zero-infrastructure.

2. **Moderate — AC quality is not just linguistic.** "Observable contract" requires codebase context (boundaries, functions). Characterizing it as purely linguistic was overstated.
   - **Accepted.** Revised to: challenger validates both design soundness AND AC quality as a unified design-level check. Dropped the "linguistic operation" framing.

3. **Critical — Reviewer source reading inconsistency.** Draft said reviewer must read source artifacts, then downgraded to "spot-checking" in warnings.
   - **Accepted.** Revised to: reviewer ALWAYS reads test files and implementation code directly. Quality-runner output used only for pass/fail status. No spot-checking hedge.

4. **Critical — Architectural fit moved to auditor is a known misalignment.** The context explicitly labels auditor owning architectural fit as "MISALIGNMENT."
   - **Accepted.** Revised to: architectural fit stays with architect (pre-implementation). Auditor handles only architectural *regression* (did this change break an existing boundary?).

5. **Moderate — One test per AC line is too strict.** A single AC can legitimately require multiple test scenarios.
   - **Accepted.** Revised to: test-writer derives exact *set* of scenarios (not one-to-one). The quality test is deterministic scenario derivation, not cardinality.

6. **Moderate — Loop-breaker 3-5x number is unsupported.** The diagnostic improvement from batching was asserted, not demonstrated.
   - **Accepted.** Softened to "substantially more diagnostic work" and recommended starting at 2 with empirical validation.

7. **Critical — 219 stale tests are structural, not cleanup.** The brief treats the lifecycle gap as a design problem, not incidental debt.
   - **Accepted.** Revised to: migration is part of the design, includes moving surviving tests and deleting the rest. Added prerequisite: TestFromAC immutability rule must be revised first.

8. **Minor — Architect "lightweight" cost claim is unsupported.** Architect uses the most expensive model.
   - **Accepted.** Revised to: architect cost is real; justified by leverage, not cheapness.

### Critic Blind Spots Addressed

- **Error-circumvention overhead**: Softened from "orthogonal" to "adjacent, lower-priority."
- **Duplicated rule authority**: Added shared skill requirement (`h-ac-quality`).
- **Temporary implementation lifecycle**: Acknowledged as open gap requiring more design.

## Critic Cycle 2

### Revised Position

Four load-bearing joints: consolidation trigger (upfront decomposition), AC ownership (architect owns, planner drafts), reviewer reads source directly, shared AC quality skill.

### Critic Challenges (7 total, 3 critical)

1. **Critical — No reviewer→auditor handoff artifact specified.** Brief leaves this open; locked outcome 8 requires clear handoff contracts.
   - **Accepted.** Added Joint 4: Review Evidence section with AC completion matrix, proof quality notes, flagged concerns.

2. **Critical — AC ownership chain still split.** Planner drafts with architect rules, architect validates, challenger stress-tests — three actors touching AC quality creates ambiguity.
   - **Partially accepted.** Clarified: planner is drafter only, architect is single accountable owner. Challenger is architect's internal checker, not a third owner. The ownership is architect's; the chain is delegation, not co-ownership.

3. **Moderate — Proof sufficiency bleed risk still under-evidenced.** Archive shows reviewer scope creep came from proof-quality escalation.
   - **Partially accepted.** Added explicit scope-creep guard: reviewer's 3-item checklist is exhaustive, anything outside is out-of-scope. Added boundary clarification (structural vs. semantic proof quality). Acknowledged this is the highest bleed risk and the skill file must include boundary examples.

4. **Moderate — Consolidation task dependencies are metadata.** Calling it "zero infrastructure" while requiring planner to maintain dependency updates is contradictory.
   - **Accepted.** Revised to honestly acknowledge lightweight metadata maintenance cost. Justified: planner already owns decomposition, this adds one task, not a new mechanism.

5. **Critical — TestFromAC immutability blocks migration.** Current auto-FAIL on TestFromAC removal conflicts with structural test lifecycle.
   - **Accepted.** Added Joint 5: TestFromAC immutability rule must be revised as a prerequisite. Location-based guard (task-scoped in `tests/` are deletable, durable in `serve/*/tests/` retain guard).

6. **Moderate — Security scanning placement asserted without evidence.** Brief leaves this unresolved between CI-only and opt-in reviewer check.
   - **Accepted.** Revised to hedge: SAST to CI, lightweight check for security-tagged tasks. Marked as needing empirical validation.

7. **Minor — Error circumvention is "adjacent" not "orthogonal."** Brief names it as core problem component.
   - **Accepted.** Softened language.

### Positions Defended

- **Two agents (reviewer + auditor) over one agent with two phases.** Critic did not challenge this in cycle 2. Position stands: attention contamination from sequential phases within one context is a real risk, supported by first-principles analysis.
- **Mandatory architect gate.** Critic challenged cost framing but not the gate itself. Position stands: leverage from preventing downstream spirals justifies per-task architect cost.

### Final Confidence Movement

- Cycle 1 draft: 0.79
- Post cycle 1: 0.76 (more gaps identified than expected)
- Post cycle 2: 0.78 (gaps addressed, but new joints added increase implementation surface)
