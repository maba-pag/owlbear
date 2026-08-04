# Semantic Commitment Policy

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Which agreed semantics may adapt during Delivery, and which require renewed user guidance?
> **Status:** S1 resolution derived from current user input; terminology and mechanics remain agent-owned refinements.

## 1. Governing Principle

Plans should change as evidence improves. What must not change silently is the meaning the user
specifically requested or identified as especially important.

Commitment strength depends on provenance and explicit importance, not on which document or phase
contains a statement:

- A user-originated request is protected by default.
- An explicit non-negotiable or dealbreaker is stronger than an ordinary requested outcome.
- A user-accepted agent recommendation is an agreed path, not an immutable promise.
- Agent-selected implementation detail is adaptable inside protected meaning.

The system must preserve these distinctions instead of flattening every requirement into equal
authority.

## 2. Commitment Classes

### C1. Dealbreaker

The user explicitly states that an outcome, boundary, exclusion, or quality is non-negotiable or that
the change is not worth doing without it.

**Delivery rule:** Agents may not weaken, omit, trade away, or reinterpret it for convenience, cost,
or schedule. If evidence shows it is impossible or conflicts with another dealbreaker, work blocks and
returns to the user with the evidence and consequences. The system must not claim implementation of
an impossible commitment.

**Change route:** Explicit user revision or cancellation through one focused Decision Request.

### C2. Protected request

The user specifically asks for an outcome or constraint but does not label it a dealbreaker.

**Delivery rule:** It remains part of the Product Promise and may not change silently. If implementation
evidence makes deviation materially necessary, uneconomical, unsafe, or destructive to another
protected result, agents explain the necessity and consequences through a Decision Request.

**Change route:** User accepts a specific deviation, substitute, or removal. Lack of objection is not
approval.

### C3. Important reviewed commitment

The user and agent identify a behavior, constraint, acceptance meaning, or strategy consequence as
important but revisable under new evidence.

**Delivery rule:** Agents continue under it until evidence establishes a material reason to deviate.
One consolidated Decision Request is required before the semantic consequence changes. Related
deviations should be grouped when one decision can resolve them without obscuring distinct tradeoffs.

**Change route:** User resolves the consequence after being enabled to understand why the current path
no longer fits and what each credible response enables or prevents.

### C4. Agreed path

The user accepts an agent recommendation or plan direction without making the underlying choice a
specific requested outcome or important constraint.

**Delivery rule:** Agents may revise it when source evidence shows a more feasible, economical, safe,
or maintainable route, provided C1-C3 meaning and reviewed acceptance remain unchanged. The revision
is recorded with rationale and surfaced in the next semantic summary; it does not automatically block
Delivery.

**Change route:** Agent-owned plan revision plus independent review. Escalate only when consequences
cross into C1-C3.

### C5. Implementation discretion

Code structure, algorithms, schemas, commands, paths, fixtures, and other local choices selected by
agents inside the reviewed strategy.

**Delivery rule:** Freely adaptable with normal technical review and proof. No user request is needed
unless a newly discovered consequence changes C1-C4 meaning.

## 3. Default Classification

When no explicit label is given:

1. Direct user requests default to C2 protected requests.
2. Consequences the user explicitly calls important default to C3 unless described as non-negotiable.
3. Agent proposals the user agrees to default to C4 unless the user adopts a specific consequence as
   their own requirement.
4. Agent-derived technical choices default to C5.
5. Explicit “must,” “dealbreaker,” “non-negotiable,” or equivalent user language triggers a brief
   confirmation of C1 meaning when ambiguity would materially affect Delivery; it must not become a
   routine confirmation prompt.

The user may strengthen or relax a commitment at any time. Agents should infer obvious provenance and
ask only when ambiguity changes routing.

## 4. Decision Request Policy

Decision Requests exist for necessary semantic deviation, not routine implementation updates.

Create one when:

- C1 appears infeasible or contradictory;
- C2 cannot be preserved without a material consequence;
- evidence supports changing C3; or
- a proposed C4/C5 revision would cross a protected semantic boundary.

Do not create one for:

- local implementation changes that preserve reviewed meaning;
- a better technical route with equivalent consequences;
- generated lifecycle mechanics;
- repeated symptoms of one unresolved semantic cause; or
- information that can be grouped into an existing focused request.

Each request explains the current commitment and provenance, new evidence, why deviation appears
necessary, credible responses, and what each response enables, prevents, weakens, costs, and risks.
The agent may include its technical assessment after that comparison.

## 5. Planning and Review Effects

- Intent and outcome summaries preserve user-originated wording and commitment class.
- Constraints, acceptance, and strategy link back to the commitments they protect.
- Plans distinguish protected meaning from adaptable strategy and implementation discretion.
- Review checks for silent weakening, accidental promotion of recommendations into promises, and
  unnecessary escalation of technical detail.
- Cockpit presents C1-C3 prominently, C4 as current direction, and C5 through technical drill-down.
- Reconciliation compares semantic consequences, not merely text or plan digest changes.

## 6. S1 Resolution

Delivery may begin when protected meaning and its consequence-level acceptance are understandable,
internally coherent, and feasible enough to support a strategy. The entire plan need not be immutable.
Later evidence may revise C4-C5 autonomously; C1-C3 receive the routing above.

Risky, irreversible, destructive, security-sensitive, or cross-boundary work requires deeper early
analysis because more facts may belong in C1-C3. It does not require execution-level detail merely
because it is risky.

## 7. Completion Checks

- [ ] Direct user requests cannot be silently downgraded into recommendations.
- [ ] User agreement with an agent proposal does not make every implementation choice immutable.
- [ ] Dealbreakers block compromise but do not permit false claims of feasibility.
- [ ] Important deviations use focused, consequence-rich Decision Requests without request storms.
- [ ] Equivalent technical changes proceed without user interruption.
- [ ] Every semantic change can explain which commitment changed, why, and under whose authority.

## 8. Confidence and Limits

**Confidence:** High that C1, C2, C4, and C5 directly reflect the user's distinction. Medium on the C3
boundary and grouping behavior until exercised on real correction scenarios in S4.

**Limits:** Names, serialization, and UI treatments are provisional engineering choices. This policy
does not yet define exact request batching, urgency, timeout behavior, or conflict resolution between
multiple protected commitments.