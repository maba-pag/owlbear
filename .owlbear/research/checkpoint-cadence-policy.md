# Checkpoint Cadence Policy

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** When should user input block work, and what work should continue?
> **Status:** S2 resolution derived from current user input.

## 1. Governing Principle

User Requests are scoped dependencies. A Decision Request or Action Request blocks the task that
requires its resolution. Work that mechanically depends on that task also waits because it is not
actually ready. Work unrelated to the unresolved request continues.

The system must not halt an entire change merely because one task needs user input, and it must not
pretend dependent work is unrelated merely to keep agents busy.

## 2. User-Facing Language

Internal commitment classes may support routing, but user-facing discussion names their meaning:

- **dealbreaker:** explicitly non-negotiable or change-defining;
- **protected request:** something the user specifically asked for;
- **important reviewed commitment:** important but potentially revisable with renewed discussion;
- **agreed path:** a current agent recommendation the user accepted; and
- **implementation detail:** agent-owned work inside reviewed meaning.

Do not ask the user about “C1-C3 issues” or other internal identifiers without explaining them.

## 3. Cadence By Activity

### Shaping

- Discuss one material consequence when it becomes understandable and controls downstream meaning.
- Let the agent continue research and synthesis that does not depend on the answer.
- Close a coherent topic with an integrated recap; do not request approval after every artifact or
  field.
- Present a readiness review when outcomes, important consequences, representative acceptance, and
  strategy effects form an understandable whole.

### Delivery

- Implementation details and equivalent strategy improvements proceed with agent review.
- A necessary change to a dealbreaker, protected request, or important reviewed commitment creates a
  focused Decision Request.
- An operation only the user can perform creates an Action Request.
- The request blocks its referenced task and engine-known dependents.
- Other ready tasks continue, subject to real dependencies, writer coordination, and safety.

### Acceptance and correction

- Technical defects create corrective work without user interruption.
- A failed proof creates a user request only when credible correction requires changing protected
  meaning or user action.
- Completion reports satisfied commitments, accepted deviations, and known limits without requiring
  another approval of technical evidence.

## 4. Request Grouping

One request may cover several effects when:

- they arise from one underlying consequence or priority;
- one answer resolves their routing together; and
- presenting them together improves understanding without hiding a distinct tradeoff.

Use separate requests when answers can differ independently, urgency differs materially, or grouping
would force one choice across unrelated consequences. Do not create one request per affected artifact,
node, test, or diagnostic.

Grouping should not delay a blocking request merely to accumulate more issues. Agents may append
newly discovered effects only while the request remains the same decision and the user has not begun
resolving stale framing.

## 5. Dependency Semantics

Request scope follows semantic and execution dependencies:

1. Block the task whose completion requires the response.
2. Block tasks that consume that task's unresolved output or assume one of its possible outcomes.
3. Continue tasks whose reviewed meaning, inputs, proof, and safe execution do not depend on it.
4. Recompute readiness after resolution; do not manually release guessed dependents.

When independence is ambiguous and proceeding could create material rework or violate protected
meaning, block and expose the ambiguity. When the risk is only a reversible implementation detail,
continue and record the assumption.

## 6. User Experience

A request shows:

- the task and reviewed commitment that need input;
- why agents cannot proceed safely without it;
- what remains blocked and what continues;
- the evidence and consequence comparison;
- the exact response needed to resume; and
- whether related effects were grouped and why.

Cockpit should show localized waiting rather than presenting the entire change as blocked.

## 7. Completion Checks

- [ ] A request blocks its task and true dependents, not the entire change.
- [ ] Unrelated ready work continues.
- [ ] User-facing requests avoid unexplained internal classification codes.
- [ ] Related effects are grouped only when one answer resolves one consequence.
- [ ] Technical defects and equivalent implementation changes do not create user requests.
- [ ] Readiness is recomputed mechanically after resolution.

## 8. Confidence and Limits

**Confidence:** High in task-scoped blocking and continuation of unrelated work because the user
explicitly connected this behavior to the purpose of User Requests. Medium in request amendment and
grouping timing until S4 exercises real correction scenarios.

**Limits:** Exact graph propagation, request mutation/versioning, notification delivery, and Cockpit
layout remain engineering work. “Task” will need mapping to native plan/build/accept/audit jobs and
semantic targets without changing this behavior.