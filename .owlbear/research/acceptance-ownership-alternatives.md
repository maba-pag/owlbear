# Acceptance Ownership Alternatives

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Which acceptance meaning belongs in Specification, which may be added during Planning, and how should builders and acceptors see the combined contract?
> **Status:** Open decision analysis. The alternatives are not a closed list and no selection is implied.

## 1. Context and Question

OwlBear needs acceptance at two moments with different information available:

- During Specification, agents and the user understand desired value, workflows, important failure
  behavior, architecture, interfaces, risks, and proof boundaries.
- During Planning, an agent has inspected the exact repository and leads implementation strategy,
  packet boundaries, concrete outputs, and detailed proof tactics under reviewed priorities.

Too little acceptance in Specification permits post-approval value erosion. Too much detailed
acceptance in Specification forces speculative implementation design before repository-grounded
planning. Repeating the complete contract in both places improves local readability but creates
drift and review work.

Acceptance follows `graduated-semantic-collaboration.md`: the user reviews representative behavioral
meaning, failures, and exclusions; agents translate that meaning into detailed scenarios and prove
their completeness and testability.

This decision has five separate dimensions:

1. What behavior must be approved before Delivery begins?
2. What detail may a planner add without returning to Specification?
3. What discovery requires Specification re-entry and renewed user review?
4. What canonical content is stored versus generated as a resolved view?
5. What combined contract must builders, reviewers, acceptors, and users see?

## 2. Sources Studied

| Source | Relevant fact |
|---|---|
| `intent.md` | The Product Promise requires admitted outcomes and proof ownership before Delivery, followed by bounded agent planning. |
| `design.md` sections 5 and 6 | Nodes are independently plannable/acceptable; plans refine admitted nodes without changing admitted obligations. |
| `decisions.yaml` DEC-006 and DEC-028 | Prior selections favored node-complete Specification and post-admission packets, but those choices require informed revalidation. |
| `delivery/nodes.yaml` DN-003 | A node already binds outcome, obligations, interfaces, dependencies, risks, and one proof contract. |
| `delivery/contracts.yaml` PROOF-003 | Specification already contains a substantial public proof boundary and scenario families. |
| `plans/DN-003.yaml` | Planning repeats eleven broad obligation scenarios and adds two implementation-specific regressions. |
| `plans/DN-016.yaml` | Planning adds execution-order, live-state, and role-specific observations that were unknowable at generic requirement level. |
| `graduated-semantic-collaboration.md` | User review operates on acceptance storyboards while agents own detailed contract completeness and testability. |

## 3. Alternatives

### A. Specification-complete acceptance

Specification owns both outcome-level and detailed executable acceptance. Planning chooses only the
implementation approach, packet assignment, and commands needed to satisfy it. New normative
scenarios always require Specification re-entry.

**Strongest when:** behavior is externally contracted, regulated, safety-critical, or sufficiently
known before implementation.

**Benefits:** The user approves the complete behavior contract; acceptance cannot drift after
admission; acceptors consume one canonical set.

**Costs:** Detailed scenarios may be speculative; Specification becomes implementation-aware;
repository discoveries cause re-admission even when product meaning did not change.

**Failure mode:** Agents write exhaustive but shallow scenarios early to avoid later re-entry.

### B. Layered acceptance with a resolved projection

Specification owns outcome-level scenarios. Planning keeps those unchanged and adds mapped,
implementation-specific scenarios. The engine presents a resolved contract containing both layers
without copying inherited text into the authored plan.

**Strongest when:** product behavior is stable but implementation-specific failure and proof details
emerge only after focused source inspection.

**Benefits:** Knowledge is authored when available; no text duplication; builders and acceptors still
receive one complete view; plan review can assess both inherited and local criteria.

**Costs:** Requires a precise promotion/re-entry rule, a coverage compiler, and UI that clearly shows
origin and authority. Two canonical layers can confuse users if the projection hides provenance.

**Failure mode:** A planner labels a product-significant behavior as implementation detail and avoids
renewed approval.

### C. Full plan restatement

Specification owns outcome-level acceptance. Every plan copies and refines the complete relevant
node acceptance alongside its local scenarios, producing one self-contained authored plan.

**Strongest when:** plans must remain understandable in isolation without runtime projection tools.

**Benefits:** One-file review and interruption recovery; inherited and local scenarios are visible
together; builders need no resolver.

**Costs:** Repetition, drift, weakening by paraphrase, larger review diffs, and reconciliation churn.
Validators must compare restated meaning with authority, which is partly semantic and hard to prove.

**Failure mode:** A polished restatement subtly changes the admitted outcome while appearing complete.

### D. Planning-owned executable acceptance

Specification owns Product Promise, workflows, outcomes, and key constraints, but no complete scenario
set. Planning writes the executable node and packet acceptance after repository inspection.

**Strongest when:** implementation uncertainty is high and pre-delivery behavior can remain broad.

**Benefits:** Acceptance is concrete and source-grounded; Specification is easier to understand;
little duplication.

**Costs:** Admission cannot prove complete acceptance/proof ownership; users approve less of the
eventual behavior; planners gain authority to redefine value during Delivery.

**Failure mode:** Product compromises become technical details and bypass user review.

### E. Separate acceptance catalog

Acceptance scenarios are stable entities in a dedicated authority catalog. Specification nodes and
plans reference or extend them; shared scenarios can be reused across nodes and packets.

**Strongest when:** many scenarios are genuinely shared, independently versioned, or reused across
several product changes.

**Benefits:** One canonical scenario source; explicit reuse and provenance; resolved views are easy to
assemble.

**Costs:** Adds another authored artifact, identity system, ownership rules, and promotion lifecycle.
For mostly local scenarios, indirection creates more ceremony than it removes.

**Failure mode:** The acceptance catalog becomes a second specification system maintained for its own
sake.

### F. Materiality-gated layered acceptance

Specification owns scenarios for product value, normal workflows, public interfaces, destructive or
security behavior, irreversible choices, material failures, and proof boundaries. Planning adds
implementation-specific discriminators. A planner may refine wording without re-entry only when the
observable promise, failure semantics, authority boundary, and proof meaning are unchanged. The engine
generates a resolved projection with provenance.

**Strongest when:** OwlBear wants layered timing but needs a stricter barrier against value erosion
than a simple high-level/detail distinction provides.

**Benefits:** Protects material behavior before Delivery while allowing source-grounded detail later;
gives Specification re-entry a test based on consequence rather than document location.

**Costs:** Materiality requires semantic judgment and independent review; borderline cases may still
need a Decision Request. The rule must include examples and stable escalation behavior.

**Failure mode:** Repeated borderline classifications recreate review debate unless the policy is
clear and bounded.

## 4. Comparative Analysis

| Model | User approves behavior before Delivery | Detail timed to source knowledge | Canonical duplication | Post-admission value-erosion risk | New mechanism cost |
|---|---|---|---|---|---|
| A. Specification-complete | Highest | Low | Low | Lowest | Low |
| B. Layered + projection | High | High | Low | Medium without promotion rule | Medium |
| C. Full restatement | High | High | High | Medium through paraphrase | Low/medium |
| D. Planning-owned | Medium | Highest | Low | Highest | Low |
| E. Separate catalog | High | High | Low | Low/medium | Highest |
| F. Materiality-gated layered | High | High | Low | Low/medium | Medium |

### DN-003 discriminator

The broad runtime behaviors already in DN-003 and PROOF-003 belong before Delivery under A, B, C,
E, and F. The later causal-ordering and public reconciliation regressions are planning-local under B
and F unless they change IF-003 failure semantics; under A they force re-entry, under C they are
restated with the full node contract, and under D Planning owns the complete executable set.

### DN-016 discriminator

The user-visible atomic handoff, fail-closed startup, protected-file preservation, and exact-commit
proof belong before Delivery under A, B, C, E, and F. The exact sequencing between builder actions,
live completion, and read-only acceptor observations is naturally planning-local under B and F unless
it changes an irreversible or public failure guarantee.

## 5. Candidate Synthesis To Test

F can be combined with B's resolved projection:

1. User and agent shape material acceptance through representative workflow and failure stories.
2. A Planning agent translates reviewed meaning into mapped implementation-specific acceptance.
3. Material additions return to collaborative Specification; local additions receive independent
  semantic review, while the user reviews changed meaning and consequences rather than the matrix.
4. The engine compiles inherited and local scenarios into one provenance-preserving resolved view.
5. Builders and acceptors consume that resolved view; authored files retain their separate owners.

This remains an acceptance-storage candidate, not a decision or approval request. Its collaboration
method is governed by the graduated model rather than a generic review gate.

## 6. Recommendation, Confidence, And Limits

**Recommendation:** Do not select an option yet. First agree on the materiality/re-entry test using
two or three concrete examples from DN-003 and one ordinary feature change. Then compare A, C, and the
B/F synthesis against those examples.

**Confidence:** High in the tradeoff distinctions; medium in the B/F synthesis until ordinary feature
work is tested, because the current change is unusually infrastructure-heavy.

**Limits:** This note does not decide ownership, alter admitted authority, or claim the alternatives
are exhaustive. New models and hybrids should be added before selection when they expose a materially
different tradeoff.