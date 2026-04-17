# Test Quality — Synthesis

## Convergences

### 1. Lifecycle is the core problem — not test-writer behavior

All four panelists agree the problem is what happens *after* task completion: no consolidation, no pruning, no promotion, no expiration. Task-scoped tests are correct output from the test-writer. The fix belongs downstream. *(Architect, End User, Security, Data)*

### 2. TestFromAC immutability must be scoped for lifecycle to operate

Every panelist identifies the current "removal = automatic FAIL" rule as a blocker. No lifecycle mechanism can function while this rule applies unconditionally. All agree immutability should be preserved during active pipeline passage but relaxed post-archive for a lifecycle agent. *(Architect, End User, Security, Data)*

### 3. Two-tier test model: transient task-scoped, durable module-level

All panelists converge on a two-tier structure: task-numbered files are transient scaffolding; module-level files (`test_{module}.py`) are the durable suite. The lifecycle mechanism bridges the gap. *(Architect, End User, Security, Data)*

### 4. Dedicated lifecycle agent, separate from existing roles

All agree the lifecycle responsibility should not be grafted onto reviewer, auditor, or builder. A new agent role with defined scope and authority. *(Architect, End User, Security, Data)*

### 5. Two hard gates: full-suite green + coverage ≥ 90%

All panelists agree on these minimum operational gates. No lifecycle operation may leave the suite red or drop coverage below floor. Both are blocking. *(Architect, End User, Security, Data)*

### 6. AC provenance must survive consolidation

All agree the link from test assertions to acceptance criteria must persist in the durable layer — via comments, docstrings, or metadata — even as task-numbered filenames disappear. *(Architect, End User, Security, Data)*

### 7. Legacy bootstrap is a prerequisite

All agree the ~190 existing task-numbered files require one-time triage before ongoing lifecycle can begin, starting from a green suite baseline. *(Architect, End User, Security, Data)*

### 8. Honest framing: gates do not guarantee behavioral preservation

Security and Data explicitly state that green suite + coverage floor ≠ "all behavioral assertions preserved." Architect acknowledges promotion ≠ quality transformation. End User insists consolidation without quality improvement perpetuates the trust problem. All agree the design must not overclaim. *(All — varying emphasis)*

---

## Disagreements

### D1: Consolidation scope — file reduction vs. semantic quality improvement

- **Architect**: The curator is a *file lifecycle manager*, not a quality transformer. Quality improvement (replacing implementation-coupled assertions with contract-level ones) is a separate, second-order concern handled by auditor pruning. Solve accumulation first, improve quality second.
- **End User**: Consolidation *must* produce contract-level behavioral tests, not transplanted implementation assertions. Shrinking the suite without improving test quality perpetuates the trust problem at the module level. Lifecycle without semantic upgrade is insufficient.
- **Data**: Agrees with End User — promotion must require `contract` classification. The "no promotion without quality improvement" invariant is non-negotiable in the schema.

*Tension*: Architect prioritizes stopping accumulation with a simpler agent (lower risk, faster to ship). End User and Data argue this defers the actual trust outcome indefinitely.

### D2: Data model complexity

- **Architect**: Consolidation log + pending-curation markers + escalation thresholds. Relatively lightweight.
- **Data**: Full callable-level data model with AC scenario tracking, stable identities, contract-level classification, and progressive enrichment tiers. Substantially heavier infrastructure.
- **Security**: Append-only JSONL diagnostic log (per-operation). Lightweight, focused on auditability.

*Tension*: Data's model enables richer lifecycle decisions (AC-lineage-based pruning) but requires significant bootstrapping. Architect's approach is operational sooner but uses coarser heuristics ("provable duplication only").

### D3: Builder visibility gap

- **End User**: Builders need at minimum a fast signal about module-level test breakage during development. The feedback loop is broken at the point of creation without this. Considers it part of the same problem.
- **Architect**: Mentions it as an "adjacent concern" that should be in the same brief but treats it as separate from the curator design.
- **Security, Data**: Do not focus on this dimension.

*Tension*: End User argues lifecycle + scoped-execution fix are both required for trust. Architect scopes the curator narrowly and defers execution model changes.

### D4: Independent verification of lifecycle operations

- **Security**: Lifecycle operations happen post-archive, outside the auditor's scope. The lifecycle agent's own gate run is self-verification, not independent verification. This is a structural gap.
- **Architect**: Assigns auditor a verification role over curator consolidations (diff module-level files, verify consolidation logs). This partially addresses the gap but within the existing audit cycle, not as real-time independent verification.

*Tension*: Security wants an explicit independent verifier. Architect relies on auditor spot-checks.

### D5: Module-level test lifecycle governance

- **End User**: Module-level tests also go stale and need periodic relevance review. Without durable-layer lifecycle, the accumulation problem returns in 12 months with different filenames.
- **Data**: Model structurally covers module-level lifecycle via the same schema, but doesn't emphasize urgency.
- **Architect, Security**: Do not address module-level lifecycle.

*Tension*: End User warns this is a predictable recurrence. Others scope the design to the immediate task-scoped problem.

---

## Recommendation

**Implement a lifecycle curator agent as a new pipeline stage (`curate`, after `review`) operating a two-tier test model, with scoped TestFromAC immutability and progressive data enrichment.**

### Concrete approach

1. **Scope TestFromAC immutability to active pipeline** — immutable from task creation through archive; lifecycle agent gains removal/promotion authority post-archive. This is the first action — everything else is blocked without it. Requires explicit user acceptance as a new authorized capability (per Security).

2. **Ship the curator agent with a conservative algorithm** — "when in doubt, promote" policy. Start with Architect's file-lifecycle scope (provable duplication detection, mechanical promotion with provenance comments). This stops the accumulation problem immediately.

3. **Progressive quality gate on promotion** — As a near-term follow-on (not deferred indefinitely), add Data's contract-level classification as a promotion requirement. Start with heuristic classification (assertion targets: public API = contract, internal state = implementation) and manual annotation for ambiguous cases. This addresses End User's and Data's insistence that promotion without quality improvement is insufficient.

4. **Two hard gates, atomic batch operations** — Full-suite green + coverage ≥ 90% after every module-batch. Git revert on failure. Append-only lifecycle log for diagnostics.

5. **Expand builder scoped-runs to include module-level tests** — Not full suite, just the affected module's durable test file. Low cost, high signal. Addresses the feedback-loop gap End User identified.

6. **Legacy bootstrap** — One-time triage of ~190 files starting from green suite. Classify by naming pattern → flag modules with existing module-level files → consolidate module-by-module with gate verification.

### What this defers

- Data's full callable-level data model (AC scenario tracking, stable identities) → Tier 2/3 progressive enrichment, not prerequisite
- Independent verification of lifecycle ops → auditor spot-checks initially, dedicated verification later if needed
- Module-level test lifecycle → flag for future brief once task-scoped accumulation is solved

### Confidence: **0.75**

Strong convergence on the structural design (two-tier model, dedicated agent, scoped immutability, two gates). The 0.25 discount reflects:

- **D1 is unresolved**: the curator's consolidation scope (file-reduction-only vs. semantic-quality-required) directly affects whether the trust outcome is achieved. The recommendation sequences them but the user must decide whether quality gates on promotion are shipped in v1 or deferred.
- **Semantic judgment risk**: all panelists acknowledge the curator must make equivalence judgments that no design eliminates. The conservative policy bounds but does not remove this risk.
- **Irreducible behavioral coverage gap**: Security's primary threat (silent assertion loss within maintained coverage) is real and unfixable by current infrastructure. The design is honest about this.

---

## Open Questions

### Q1: Should contract-level classification be a v1 promotion gate or a follow-on?

**Architect** says no — curator is a file-lifecycle manager; quality improvement is second-order. **End User** and **Data** say yes — promotion without quality improvement perpetuates noise at the module level. This directly determines whether the curator ships simpler/sooner (Architect) or with a heavier quality gate (End User + Data). The user must decide.

### Q2: Is the new authorized capability (agent-initiated assertion removal) accepted?

**Security** flags this as a genuinely new capability that changes the system's security properties: sanctioned permanent test removal by an agent. It is not a relaxation — it is an expansion of what is permitted. The user must explicitly accept this before implementation proceeds. All other design work is contingent on this acceptance.

### Q3: Should builder scoped-runs expand to module-level tests in the same brief?

**End User** considers this essential for the trust outcome — lifecycle cleans the suite but builders still can't see cross-task impacts without an execution model change. **Architect** treats it as adjacent. The user must decide whether this is in-scope or a separate brief.

### Q4: How much of the legacy corpus can be automatically triaged?

**Data** warns that if automated AC scenario extraction achieves <50% coverage of the existing corpus, the lifecycle model is not operational and manual triage dominates. The bootstrap complexity is unknown until attempted. The user should expect the bootstrap to be the most labor-intensive phase.
