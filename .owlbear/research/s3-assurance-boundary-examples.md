# S3 Assurance Boundary Examples

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Which failures justify independent agent assurance, and where should assurance adapt to risk rather than run uniformly?
> **Status:** Evidence base for the S3 resolution in `assurance-cadence-policy.md`.

## 1. Current Assurance Stack

| Boundary | Claim reviewed | Failure uniquely visible here | Cost |
|---|---|---|---|
| Semantic challenge | Intent, outcomes, constraints, acceptance, architecture, graph | Missing value, technically-done-but-wrong outcome, unowned interface/migration/proof | Fresh context over broad authority; repair can reopen discussion |
| Plan challenge | One source-grounded implementation plan | Incoherent packets, escaped scope, unsupported verification-only claim, proof bypass | Fresh source read per plan and fresh review after every repair |
| Committed build review | Exact packet commit, diff, outputs, focused proof | Concrete code defect, omitted output, escaped change, weak packet proof | One fresh read per commit/repair while builder remains warm |
| Node acceptance | Assembled node at exact commit | Packets pass locally but node contract, interface, or assembled proof fails | Exact checkout, full node proof, corrective routing |
| Whole-change audit | Product Promise and cross-node workflows at exact commit | Nodes pass independently but end-to-end workflow, migration, removal, or integration fails | Broadest proof after all nodes; failure can invalidate substantial work |

Deterministic validation, tests, types, graph checks, and receipt currentness support these boundaries.
They do not replace semantic or adversarial judgment, but reviewers should not narrate checks code can
decide.

## 2. Observed Cost and Overlap

- Fifteen current plan files each contain independent plan-review evidence.
- Persisted review identities commonly reach `r2` to `r6`; the final unpublished DN-003 attempt
  reached `r13` without publication.
- Plan review currently repeats six mandatory dimensions even for one-packet plans and successful
  deterministic checks.
- Every repaired candidate requires another complete fresh review, with no convergence budget.
- Node acceptance and whole-change audit are distinct only when node proof stays local and audit proves
  genuinely cross-node Product Promise workflows. Re-running the same test inventory at both adds
  ceremony without new assurance.

This evidence shows that independence has value, but independence plus fixed review shape plus
unbounded repair can become repeated prose negotiation.

## 3. The Actual Change: Delivery Pipeline Replacement

### Semantic challenge is high-value

Authority, user collaboration, correction, currentness, assurance, cutover, and deletion interact.
An omitted edge can invalidate the whole operating model. Independent challenge should examine the
complete consequence model, not merely schema coverage.

### Plan challenge is selectively high-value

It earns a fresh adversarial pass when a plan introduces or changes:

- cross-module ownership or predecessor strategy;
- destructive, irreversible, concurrent, security, or bootstrap work;
- verification-only claims;
- proof boundaries or lower replacements; or
- large/cohesion-risk packet decomposition.

It adds less value when reconciliation preserves the reviewed strategy and only updates generated
identity, exact paths, or commands.

### Build review is high-value

Shared runtime, transaction, migration, and destructive changes have defects expensive to discover at
node acceptance. Warm repair plus an independent exact-diff review is useful, provided review findings
remain concrete and bounded.

### Node acceptance is high-value

Each deep runtime or cutover outcome needs independent exact-commit proof before dependents rely on it.
Acceptance should prove the node's assembled public boundary, not repeat packet review.

### Whole-change audit is high-value

The pipeline promise exists only across Specification, Planning, Build, Acceptance, Audit, Cockpit,
MCP, setup, and cutover. Node receipts cannot prove the user journey or atomic removal alone.

## 4. Assurance Shapes and Consequences

### Uniform assurance

Run every independent boundary for every change, plan, packet, node, and final change.

**Improves:** Predictability, simple policy, maximum fresh-context scrutiny.

**Costs:** Startup and context load can dominate the work; reviewers restate deterministic passes;
overlapping gates can reward document completeness instead of defect discovery.

### Boundary-minimum assurance

Keep one semantic challenge, committed build review, and one independent final acceptance/audit;
remove separate plan challenge and node acceptance by default.

**Improves:** Lower cost and fewer repeated gates.

**Costs:** Planning omissions reach implementation; deep nodes can become dependencies before assembled
proof; final failures are later and more expensive.

### Risk-adaptive assurance

Always protect meaning and committed implementation, then add plan challenge, node acceptance, and
whole-change audit according to distinct risk and integration triggers. No gate may duplicate another
boundary's claim.

**Improves:** Preserves independent scrutiny where failure is consequential while ordinary work stays
proportionate.

**Costs:** Requires transparent risk classification and anti-gaming rules. Misclassification can miss
failures or quietly restore uniform ceremony.

## 5. Concrete Checkpoints

The evidence supports evaluating five concrete checkpoints:

1. **Before coding, review the feature meaning.** A second agent reads the user-reviewed outcome,
  failure behavior, exclusions, and strategy summary. For this change it could catch authority or
  user-collaboration gaps before they become architecture and code.
2. **Before coding, optionally review the implementation plan.** A second agent checks the proposed
  source boundaries and proof. This change can benefit when a plan concerns cutover, concurrency,
  verification-only claims, or several modules. Mechanical plan revisions do not receive another
  full review.
3. **After coding, review the exact commit.** A separate read-only agent inspects the complete diff,
  required outputs, and focused test result. The original builder remains in the same session, with
  the code and reasoning still loaded, and fixes concrete defects. This is what “warm repair context”
  means; it does not reduce reviewer independence.
4. **Before other work relies on the result, independently run the assembled feature.** For
  a completed pipeline part, run its public interface at the exact commit. This catches code that
  passes local review but fails when assembled.
5. **At change completion, run an independent end-to-end audit only when the promise spans several
  accepted results.** This change needs that check because its user workflow crosses agents,
  runtime, Cockpit, setup, and cutover.

Deterministic schema, reference, type, and test checks run before the relevant agent checkpoint. A
reviewer explains only semantic or technical judgment, not successful mechanical checks. Repeated
disagreement escalates with the unresolved finding instead of starting an unlimited fresh-review loop.

This is not a selected policy. S3 must first establish which checkpoints are valuable for this change
and what should happen when reviewers disagree. Rules for classifying future work should be derived
afterward rather than assumed through an invented example.

## 6. Limits

Review-round identities indicate churn but do not fully measure model cost, elapsed time, or defects
caught. Exact risk triggers, repair budgets, and whether a single-node change needs a separate final
audit remain to be derived after S3 guidance.