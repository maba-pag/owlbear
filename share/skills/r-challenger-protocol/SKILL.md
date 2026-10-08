---
name: r-challenger-protocol
description: "Rules: Advisory challenger decisions, evidence boundaries, and caller routing"
user-invocable: false
---

# Challenger Protocol

Shared contract for native design challenge, plan challenge, and committed-packet review.
Reviewers advise the owning workflow; they never own lifecycle state.

## Role Boundary

- Inspect only the immutable revision, plan, commit, evidence, and adjacent source needed to judge
  the supplied claim.
- Never pick, start, finish, reject, release, or recover a job; create a request; edit authority or
  implementation; or commit repository state.
- Do not perform open-ended orientation or invent product direction. Report missing authority or
  planning premises to the caller.
- Run commands or deterministic auto-fixes only when the challenger agent's own tools and rules
  explicitly allow them. The caller remains responsible for all resulting files and evidence.

## Decision Contract

Each reviewer returns the complete typed mapping defined by its agent contract. Every required
dimension receives a disposition and discriminating evidence; aggregate approval prose is invalid.
The owning workflow interprets those rows and returns its own structured disposition. Review output
never authorizes a lifecycle call by itself.

## Evidence Rules

- Judge the claim against admitted authority, direct evidence, the supplied immutable identity, and
  the caller's stated revision, packet, or review boundary.
- A prior decision is binding until the user re-decides it, not beyond question. When evidence shows
  one no longer serves the outcome, report it as a proposed reversal for the user, naming the
  decision, its record, and the options; never treat it as an unquestionable constraint or change it
  silently.
- Before accepting a grouping, ownership, or boundary claim, read the reviewed artifact's own scope,
  out-of-scope, and non-overlap statements. A shared file, envelope, or handbook is sequencing
  evidence, not a shared outcome.
- Read authoritative state from its own store rather than a summary, projection, or prior report, and
  confirm any cited path, line, or command result before treating it as evidence. An unverified
  assertion is not a finding, in either direction.
- Evidence proves only the boundary it exercises. Do not accept aggregate counts, mocks, injected
  dependencies, or local checks as proof of an unexercised command, endpoint, assembled context,
  workflow, or user journey.
- For cross-boundary claims, confirm each production boundary exists in current source, each cited
  artifact owns its claimed responsibility, and proof would fail if the claimed dataflow or
  operation were bypassed. Co-occurring inputs and outputs do not prove control.
- When a route requires an executor, tool, agent profile, mutation owner, or downstream capability,
  confirm it is currently available or that the accepted contract defines an observable fail-closed
  state. A mocked or replaced executor may prove behavior below an allowed boundary; it cannot hide
  the absence of the production boundary being approved.
- One focused proof may cover several acceptance criteria. Do not require one test per criterion,
  broad coverage, or speculative hardening.
- Fail only for a concrete defect in the proposed route. Style preference, alternate implementation
  taste, and unsupported doubt are not findings.

### Test Evidence Boundary

A passing test or test suite is baseline evidence for only the assertions, inputs, execution path,
and environment it actually exercises. It does not by itself prove user intent, complete
functionality, integration, security, usability, or operational correctness. A test may be adequate
for a deliberately narrow claim about that exact contract; otherwise require source/control-point
evidence and the cheapest public, assembled, runtime, or manual evidence that matches the claim.
Do not demand broad or E2E proof merely because a test is insufficient.

### Minimum Change Review

For committed-packet review, compare the complete diff with the admitted packet envelope, required
outputs, impact closure, and cheapest falsifying proof.

- Every added file, helper, abstraction, fallback, compatibility branch, edge case, and durable test
  must be required by accepted scope or an observed defect.
- The default durable-test delta is zero. A durable test earns its cost only when existing maintained
  coverage does not protect the risk and the behavior is easy to regress and hard to notice, shared,
  security-sensitive, data-loss-prone, or cheaper to test than to verify repeatedly.
- Do not accept file replacement when a targeted edit works, adjacent cleanup, speculative
  hardening, one-test-per-criterion mapping, or scope expansion justified by adding more tests.

## Operating Context

Judge every finding against the operating context of the work under review: who and what can act on
it or feed it, how far each is trusted, what reaches it from outside that trusted set, and what a
failure costs. The Design package states it in `intent.md`; otherwise use the context the caller
supplies, or state the narrowest context the evidence supports.

A **plausible trigger** is an action by an actor or input that this context includes, at a likelihood
that matters for the stakes. A concern that needs an actor or input the context excludes, such as a
deliberately misbehaving agent, a same-user attacker, or a coincidence of independent timing events,
is outside the context and is not a material finding. If the context itself looks wrong for the
evidence, say so once as a context concern; do not convert it into defects.

## Finding Quality

A reviewer is asked to find problems, so it will almost always report something, and each repeated
review reaches further for less likely scenarios. A finding's existence is therefore no evidence that
anything must change.

- **Reviewer:** report only findings with a plausible trigger, a concrete consequence, and evidence.
  For each, name the actor or input, the action, the consequence, and the cheapest adequate response,
  which may be a documented limit, a check that fails safely, or no change. `No material findings` is
  a complete and valuable result. Marginal findings are not harmless: each one costs repair work,
  permanent complexity, and another review.
- **Caller:** treat every finding as a claim to evaluate, never as a work order. Verify it, test it
  against the operating context, and weigh consequence and likelihood against the full cost of the
  fix, including permanent complexity, new failure modes, and new review surface. Rejecting a finding
  is normal; record a one-line reason so a later review does not reopen it. Pass your dispositions,
  not the reviewer's findings, to whoever repairs.
- **Prefer the smallest response.** A fix that adds a mechanism invites findings about that
  mechanism. When the same area keeps producing findings, question the design and simplify it
  instead of adding another layer.
- **Review again when it is worth it.** Request another review when accepted findings of substance
  changed something material. When a review produces only rejected, marginal, or cosmetic findings,
  the work has reached its useful quality; stop. Decide by the substance of the findings, not by a
  count of rounds.
- **Dispute instead of complying.** When a typed gate needs `pass` and the caller rejects a finding on
  an unchanged candidate, request a fresh review of the same identity with the caller's dispositions
  and evidence. The reviewer either upholds the finding with a plausible trigger inside the operating
  context or withdraws it. The caller never writes its own `pass`; a finding that is upheld and still
  disputed goes to its owning authority through the normal return or block route. Judge a proposed
  fix separately from its finding: an oversized fix never makes a real defect disappear.

## Caller Routing

| Reviewer | Caller route |
| --- | --- |
| designer-challenger | Designer repairs candidate authority, reruns deterministic validation and challenge, and seeks fresh user approval before admission |
| planner-challenger | Planner interprets advisory `pass` or `finding`; only pass permits plan publication and Planner alone selects `advance`, `retry`, `return`, or `block` |
| build-reviewer | Builder interprets advisory `pass` or `finding`; implementation findings may be repaired, while Planning or Design findings return through Builder-selected transitions without result publication |

Every repaired candidate requires a fresh review against its new immutable identity or commit.

## Memory Candidate Routing

Reviewers may recall memory but remain mutation-free. When a review establishes one specific,
non-obvious, reusable lesson that meets `h-memory-structure`, return exactly one optional candidate
inside the advisory mapping:

```yaml
memory_candidate:
  source_agent: <reviewer's canonical agent name>
  title: <concise title>
  content: <single actionable lesson with exact evidence locator>
  categories: [<memory categories>]
  confidence: <0.7-0.9>
```

Use `memory_candidate: null` when no lesson qualifies. Never include `scope_agents`; the memory
curator owns relevance scope. The task-owning caller validates the candidate against
`h-memory-structure` and, when it qualifies, calls `save_memory` with the reviewer-provided
`source_agent`. The caller must not rewrite provenance, invent a candidate, or let memory handling
change the primary advisory or lifecycle disposition.
