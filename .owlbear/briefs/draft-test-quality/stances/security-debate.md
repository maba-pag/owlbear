# Security Stance — Critic Debate Log

## Cycle 1: Initial Position

**Position:** Automated test lifecycle introduces a critical trust boundary problem — agents participating in code creation being granted authority to remove safety checks. Proposed seven controls: fox-guarding-henhouse separation, coverage floor as hard gate, behavioral equivalence before deletion, immutable audit trail, human escalation gate, alert fatigue as security issue, blast radius control.

**Critic challenges (5 critical):**
1. Human escalation contradicts the "automated without human intervention" constraint. — ACCEPTED
2. Coverage % ≠ behavioral coverage. Stale tests inflate coverage without testing behavior. — ACCEPTED
3. Behavioral equivalence proof non-operational at ~190 task-numbered files. Risks freezing cleanup. — ACCEPTED
4. Separation-of-duties asserted not established in actual pipeline architecture. — ACCEPTED
5. Position missed whole-suite validation after pruning and the TestFromAC immutability blocker. — ACCEPTED

**Critic confidence: 0.31 — Reject**

## Cycle 2: Restructured Around Behavioral Coverage

**Position:** Protected asset is exercised behavioral coverage, not test count or coverage %. Two-tier verification (line coverage floor + assertion inventory). Assertion classification replaces equivalence proof. Whole-suite green gate added. TestFromAC immutability scoped to active pipeline. New lifecycle agent role (not auditor extension). Git-based rollback. Signal integrity metric.

**Critic challenges (3 critical, 3 moderate):**
1. Classification + audit trail is post-escape forensics, not prevention. Coverage floor satisfied while assertions deleted. — ACCEPTED
2. Behavioral/implementation classification boundary is unstable. Historical evidence of assertions looking expendable from later vantage while being accepted contract. — ACCEPTED
3. Per-module rollback doesn't match actual artifact layout (module files mix multiple TestFromAC classes). — ACCEPTED
4. Late-detection claim caught between insufficiency and infeasibility. Full-suite runs timeout outside auditor. — ACCEPTED
5. Auditor extension collapses the verification boundary being cited as a control. — ACCEPTED
6. No durable post-archive source of truth for behavioral contract. — ACCEPTED

**Critic confidence: 0.34 — Reject**

## Cycle 3: Empirical Coverage Delta as Primary Gate

**Position:** Empirical coverage delta is the primary safety gate. Three-gate protocol (coverage delta, full-suite green, audit record). Durable behavioral contract reference. Per-file atomic operations. Batch identification + sequential removal for cost management. Explicit residual risks acknowledged.

**Critic challenges (3 critical, 3 moderate):**
1. Coverage delta not operational — current infra only supports aggregate reporting, not per-test provenance. — ACCEPTED
2. Cross-module tests break the one-module assumption. Delta check can miss adjacent-module assertions. — ACCEPTED
3. Same-path-different-assertion blindness is common, not exceptional. Primary gate blind to ordinary case. — ACCEPTED
4. Lifecycle agent tool boundaries bypassable (terminal access bypasses hooks). — ACCEPTED
5. Source of truth stored in mutable test files is not durable (writable by same actor). — ACCEPTED
6. Success metric (failure causality ratio) not computable with current pipeline. — ACCEPTED

**Blind spots identified:** Control cost (3 suite runs per candidate). Audit record is self-reporting, not independently attestable.

**Critic confidence: 0.27 — Reject**

## Cycle 4: Stripped to Honest Fundamentals

**Position:** Irreducible behavioral-assertion-loss risk acknowledged. Two operational gates only (full-suite green + suite-level coverage floor). Honest about what controls can and cannot catch. Prerequisites: scoped immutability, new agent role, atomic operations, legacy bootstrap plan. Explicit "must NOT promise" section. Independent verification gap flagged.

**Critic challenges (3 critical, 2 moderate):**
1. "Eliminates the secondary threat entirely" is overclaimed — small unique paths can disappear within the 90% floor. — ACCEPTED
2. Scoping TestFromAC immutability to post-archive is a genuinely new security-relevant capability, not just the same risk under a new label. — ACCEPTED
3. "Every remaining failure is a genuine signal" is aspirational, not backed by the proposed controls. — ACCEPTED
4. Full-suite per-commit is too expensive at per-file frequency — will be pressured into bypass. — ACCEPTED
5. Lifecycle log as mitigation is weak given nominal boundaries and self-reporting. — ACCEPTED

**Blind spots identified:** Starting-state must be green before lifecycle begins. Post-archive operations inherit audited trust without justification.

**Critic confidence: 0.34 — Reject**

## Cycle 5: Final Position (max cycles reached)

Accepted remaining challenges. Hardened into final stance: security-stance.md.

Key final refinements:
- Downgraded Gate B from "eliminates secondary threat" to "catches most gross coverage loss"
- Acknowledged scoped immutability as a genuinely new authorized capability requiring explicit risk acceptance
- Replaced aspirational signal-integrity promise with measurable but limited control claims
- Adjusted operation batching to reduce gate cost
- Downgraded lifecycle log from "mitigation" to "diagnostic aid"
- Added green-suite starting state as prerequisite
- Acknowledged post-archive trust inheritance gap as unresolved
