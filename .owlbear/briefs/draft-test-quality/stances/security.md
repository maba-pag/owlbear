# Security Stance — Test Quality Lifecycle

## Security Position

Automated test lifecycle is a net security improvement over the current degraded state, but it introduces a genuinely new authorized capability (agent-initiated assertion removal) and carries an irreducible risk of silent behavioral coverage loss that no feasible automated control eliminates.

The current state — agents dismissing test failures as pre-existing noise — means behavioral assertions exist but are functionally inert. The suite creates false confidence. Lifecycle automation trades an irreducible small-probability risk of individual assertion loss for restored signal integrity across the suite. This trade is acceptable **if and only if** the prerequisites and gates below are met, and the design is honest about what it cannot promise.

## Risk Assessment

### Primary Threat (Irreducible)

A test asserting a behavioral contract property is removed. The code path it exercises is also covered by other tests. Coverage doesn't drop. Suite stays green. A contract assertion is silently lost. **This is ordinary in this codebase** — multiple TestFromAC classes assert different contract properties on overlapping code paths. No automated control prevents this.

### Secondary Threat (Partially Mitigable)

A test that is the sole exerciser of a code path is removed. Coverage drops and/or suite breaks. Gates A and B catch most instances, but a small unique path can disappear within the 90% suite-level floor without triggering the gate.

### New Capability Threat

Scoping TestFromAC immutability to post-archive grants the lifecycle agent a genuinely new security-relevant capability: sanctioned permanent assertion removal. Today, removing TestFromAC assertions is treated as an integrity failure throughout the pipeline. The proposed change authorizes this action under controlled conditions. This is not "the same risk under a new label" — it is a new authorized capability that must be explicitly risk-accepted by the user.

## Gates

Two operational gates. These use only capabilities the current infrastructure supports.

### Gate A: Full-Suite Green

After a lifecycle batch operation, the full pytest suite must pass. Catches: regressions from removing sole-exerciser tests, cross-module interaction breakage, consolidation errors. **Does not catch:** silent assertion loss where coverage is maintained by other tests.

### Gate B: Suite-Level Coverage Floor

After a lifecycle batch, total line coverage (pytest-cov, as currently configured) must remain ≥ 90%. This is a coarse backstop against gross coverage loss. **Does not catch:** fine-grained assertion loss within maintained coverage, or small unique-path loss within the 90% margin.

Both gates are blocking. If either fails, the lifecycle batch commit is reverted.

**What these gates guarantee:** The suite stays green and exercised-line coverage doesn't collapse. **What they do not guarantee:** Behavioral contract preservation. The design must not conflate "green at 90%+ coverage" with "all behavioral assertions preserved."

## Prerequisites

### P1: TestFromAC Immutability Scoped to Active Pipeline

Current rule (always immutable) blocks any lifecycle mechanism. Required change: immutable during active pipeline passage (task creation through archive). After archive, lifecycle agent gains removal authority subject to Gates A and B. This preserves the protection that matters: no weakening of tests during active development and review of the task that created them.

**This is a new authorized capability** — not a relaxation of an enforcement boundary, but a deliberate expansion of what the system permits. The user must explicitly accept this.

### P2: New Distinct Lifecycle Agent Role

Not builder, test-writer, reviewer, or auditor. Defined by its own `.agent.md`. The boundary is nominal (definition-scoped, consistent with how all pipeline agent boundaries work). This is separation of concern for auditability, not a security boundary — I am explicit about that.

### P3: Atomic Batch Operations with Git Rollback

Lifecycle operations are batched per-module (all test file changes for one module in one commit). If Gate A fails after the batch, the commit is reverted. Per-file commits are too expensive (full-suite run per file is infeasible given suite runtime). The batch-per-module approach bounds blast radius to one module while keeping gate costs manageable.

### P4: Green-Suite Starting State

The suite must be fully green before lifecycle operations begin. If pre-existing failures exist, the lifecycle agent has no valid baseline. The legacy bootstrap (triaging ~190 existing task-numbered files) must achieve a green starting state first.

### P5: Legacy Bootstrap Plan

The ~190 existing task-numbered files need a one-time triage before ongoing lifecycle can begin. This triage is itself subject to Gates A and B. The security stance requires this plan to exist and to start from a green suite.

## What the Design Must NOT Promise

- **Must NOT promise** "all behavioral assertions are preserved." The primary threat is irreducible. Any such claim is false confidence.
- **Must NOT promise** "the lifecycle agent makes correct decisions." The agent will sometimes misclassify. The audit log enables diagnosis, not prevention.
- **Must NOT promise** "every remaining test failure is a genuine signal." This is the aspirational outcome. The gates ensure green-suite and coverage, not signal quality.
- **Must promise instead:** "The suite stays green, coverage stays above 90%, lifecycle operations are reversible, and a diagnostic log exists for post-escape investigation."

## Least-Privilege Recommendations

1. **Lifecycle agent tool scope:** Test directories (read/write), lifecycle log (append), pytest (execute), git (commit/revert). No production code directories. Nominal enforcement via agent definition.
2. **Lifecycle log:** Append-only JSONL (`.owlbear/lifecycle/test-removals.jsonl`). Records: timestamp, files affected, assertions removed, coverage before/after, disposition. This is a **diagnostic aid**, not a security control — the lifecycle agent with terminal access could modify it. Its value is enabling human review and post-escape root-cause analysis, not tamper resistance.
3. **No pipeline authority creep.** The lifecycle agent does not participate in active task pipelines. It operates only on archived-task test artifacts. It does not influence builder, reviewer, or auditor decisions.

## Warnings

### W1: Irreducible Behavioral Gap
The test suite after lifecycle operations is NOT provably equivalent to the pre-lifecycle suite in behavioral coverage. The design must communicate this honestly. "Maintaining coverage" is a misleading frame; the honest frame is "maintaining exercised-line coverage while reducing noise."

### W2: Independent Verification Gap
Today, the auditor independently verifies pipeline outputs. Lifecycle operations happen post-archive, outside the auditor's scope. No independent verifier exists for lifecycle operations. The lifecycle agent's Gate A run is self-verification, not independent verification. This is a structural gap. The minimum future mitigation: have the quality-runner independently validate post-lifecycle suite state.

### W3: New Authorized Capability
Scoping TestFromAC immutability creates a capability that doesn't exist today: sanctioned test assertion removal by an agent. This changes the system's security properties. Even though all other agent boundaries are nominal, this one explicitly authorizes destructive action on safety artifacts. It requires deliberate user acceptance, not quiet implementation.

### W4: Per-Test Coverage Attribution Would Reduce Risk
If the team later adds per-test coverage attribution (which test files uniquely cover which lines), Gate B becomes significantly stronger — it could detect small unique-path loss. This is a recommended investment but not a prerequisite. Current infrastructure only supports aggregate coverage.

### W5: Cost Pressure on Gates
Full-suite runs are expensive (minutes, not seconds). Per-file gating is infeasible. Batch-per-module gating is feasible but still costly. Over time, there will be pressure to skip or relax gates. The design must make gate bypass structurally difficult (e.g., lifecycle agent cannot mark operations complete without gate results), not just procedurally discouraged.

## Confidence

**0.72.** The position is honest about irreducible risks and infrastructure limitations. The two gates are operational with current tooling. Prerequisites are minimal and clearly scoped. Residual risks are named, not hidden. Confidence is not higher because the Critic correctly identified that the primary threat is common (not edge-case) and that the gates don't address it — the position accepts this rather than solving it.
