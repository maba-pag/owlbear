---
name: r-challenger-protocol
description: "Rules: Advisory challenger decisions, evidence boundaries, and caller routing"
user-invocable: false
---

# Challenger Protocol

Shared contract for shaper-challenger, builder-challenger, verifier-challenger, and their callers.
Challengers advise the task-owning caller; they never own pipeline state.

## Role Boundary

- Inspect only the proposal, changed slice, evidence, and adjacent context needed to judge the claim.
- Never claim, mutate, advance, release, or block a task; create a request; assess memory; call
  `end_work`; or commit pipeline state.
- Do not perform open-ended orientation or invent product direction. Report missing authority or
  planning premises to the caller.
- Run commands or deterministic auto-fixes only when the challenger agent's own tools and rules
  explicitly allow them. The caller remains responsible for all resulting files and evidence.

## Decision Contract

Return exactly one advisory decision:

| Decision | Use when | Caller obligation |
|----------|----------|-------------------|
| `pass` | The proposed route is supported by the supplied claim and evidence | Continue only if the caller's own checks also pass |
| `fail` | A concrete defect exists within the accepted contract and the caller can correct or route it without changing that contract | Do not continue; correct or route the defect, then re-run the required challenge before success |
| `reconsider` | The proposed route depends on a missing, contradictory, or newly invented planning premise, authority, interface, owner, dependency, or acceptance meaning | Do not continue or patch around it; the task-owning caller must return to the planning owner or user decision boundary |

`fail` and `reconsider` are advisory decisions, not pipeline Channel A signals. The task-owning
caller performs any required board mutation and records the challenger result in its own notes.

Use this output shape unless the challenger agent defines an additional required field:

```text
decision: pass|fail|reconsider
problem: {one-line reason, required for fail or reconsider}
root_cause: {why this invalidates the proposed route, optional}
recommendation: {specific caller action, optional}
notes: {checks run, auto-fixes applied, or non-blocking observations; optional}
```

## Evidence Rules

- Judge the claim against task intent, named authorities, direct evidence, current follow-up keys,
  and the caller's stated change or review boundary.
- Evidence proves only the boundary it exercises. Do not accept aggregate counts, mocks, injected
  dependencies, or local checks as proof of an unexercised command, endpoint, assembled context,
  workflow, or user journey.
- For repeated-failure or cross-boundary routes, inspect the caller's Repair Closure Map. Confirm
  that each claimed production boundary exists in current source, each cited artifact contains its
  claimed responsibility, and the proposed proof would fail if the repaired dataflow or operation
  were bypassed. Co-occurring inputs and outputs do not prove that one controls the other.
- When a route requires an executor, tool, agent profile, mutation owner, or downstream capability,
  confirm it is currently available or that the accepted contract defines an observable fail-closed
  state. A mocked or replaced executor may prove behavior below an allowed boundary; it cannot hide
  the absence of the production boundary being approved.
- One focused proof may cover several acceptance criteria. Do not require one test per criterion,
  broad coverage, or speculative hardening.
- Fail only for a concrete defect in the proposed route. Style preference, alternate implementation
  taste, and unsupported doubt are not findings.

### Minimum Change Review

For build and verify challenges, compare the proposed route with the caller's change envelope: the
expected files or symbols, required behavior, and cheapest falsifying proof.

- Every added file, helper, abstraction, fallback, compatibility branch, edge case, and durable test
  must be required by accepted scope or an observed defect.
- The default durable-test delta is zero. A durable test earns its cost only when existing maintained
  coverage does not protect the risk and the behavior is easy to regress and hard to notice, shared,
  security-sensitive, data-loss-prone, or cheaper to test than to verify repeatedly.
- Do not accept file replacement when a targeted edit works, adjacent cleanup, speculative
  hardening, one-test-per-criterion mapping, or scope expansion justified by adding more tests.
- A verifier patch must remain within its declared local repair budget. New helpers, abstractions,
  generalized behavior, or durable tests return to the owning stage.

## Caller Routing

| Challenger | `reconsider` owner and route |
|------------|------------------------------|
| shaper-challenger | Shaper resolves the missing planning premise or user-owned decision, rebuilds the complete provisional graph, and re-runs the challenge before approval |
| builder-challenger | Builder records the planning defect and rejects the task to `shape` |
| verifier-challenger | Verifier records the planning defect and reshapes the task to `shape` |

Callers may repair a `fail` only within their existing authority and local repair budget. If the
reported defect instead changes the accepted contract, treat it as `reconsider` regardless of the
challenger's label and route it to the planning owner.
