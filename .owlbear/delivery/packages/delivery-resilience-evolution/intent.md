# Delivery Resilience Evolution

> Status: approved direction; exact implementation authority pending admission
> Evidence: `.owlbear/research/delivery-interface-usage-audit-2026-09-11.md` and independent GPT-6 Astra / Claude Opus 5 plan challenges

## Problem

Delivery is a mature, failure-hardened system with strong authority, custody, replay, review, publication, and recovery guarantees. Its principal weakness is operational progress: deterministic recoverable conditions are often surfaced as attention that requires agents or users to collect internal identities and sequence low-level repair operations. Repair ownership is fragmented, background retries are duplicated and opaque, expired claims may be recycled without proving the previous writer stopped, and ordinary callers must know more engine mechanics than their intent requires.

## Product Promise

Delivery preserves its proven safety guarantees while becoming materially more self-healing and simpler to operate. Deterministic, evidence-preserving convergence happens inside the engine. Repository reasoning uses the existing Builder and build-reviewer boundary. Materially different outcomes produce one bounded repair proposal and one coherent interaction. After repair, orchestration resumes the same Change without requiring the user to select low-level tools.

## Normal Workflow

1. The user authors and approves one versioned Design.
2. Orchestrator asks Delivery for current actions.
3. Delivery reconciles safe deterministic conditions before selecting work.
4. Orchestrator dispatches Planner, Builder, Finalizer, or a bounded repair interaction selected by Delivery.
5. The worker submits one claim-bound replay-safe result.
6. Delivery advances, repairs, asks one material question, or quarantines only the affected Change.
7. Publication, checkpoint replay, readiness, and acceptance observations converge through bounded background behavior.
8. The user normally decides Design meaning, material repair alternatives, and the provider merge.

## Commitments

- Preserve one writer per Change, dirty-byte quarantine before reset, exact reviewed commits, independent review, atomic writes, descriptor locks, transaction recovery, provider-observed completion, and per-Change quarantine.
- Never use elapsed timeout alone to reset a worktree while the prior worker may still write.
- Never treat `retry_safe` as proof that an operation had no side effect; automatic convergence uses an explicit operation policy and durable replay identity.
- Keep current proven primitives and failure tests while the new intention facade is additive. Remove external low-level operations only after parity proof.
- Use JSON and the current process topology unless a residual measured problem justifies another storage engine or daemon process.
- Require no runtime-state migration. Existing Changes finish or are intentionally abandoned before interface cutover; source branches and preserved refs remain evidence.
- Retain remote semantic snapshots until a smaller recovery contract proves fresh-clone restoration of admitted authority and review permission.

## Accepted Exclusions

- No clean replacement of `DeliveryRuntime`, `ChangeWorkspaceManager`, transaction storage, publication providers, or reviewed-commit evidence.
- No SQLite migration, new daemon process, generic untyped MCP dispatcher, or all-powerful Git repair agent.
- No backward-compatible aliases for retired public tools after cutover.
- No automatic semantic decisions, destructive discard, non-fast-forward external mutation, or unreviewed advancement of product authority.

## Technically Done But Wrong

A smaller MCP registry that still requires manual choreography; a repair coordinator that directly resets or commits Git; expired-claim automation that cannot fence a live writer; retry loops driven only by `retry_safe`; a facade that drops semantic version or identical-replay checks; deleting remote snapshots before replacement recovery proof; or rewriting the core while retaining the same operational failure paths.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: current custody, review, transaction, and completion contracts
statement: Delivery retains one-writer custody, dirty-byte preservation, reviewed-commit authority, independent review, atomic transaction recovery, provider-observed completion, and per-Change failure isolation while resilience behavior changes.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: user request and plan challenges
statement: Deterministic evidence-preserving recovery is engine-owned; repository reasoning remains reviewed Builder work; materially different outcomes produce one bounded user proposal.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
provenance: diagnostics and cancellation contracts
statement: Automatic convergence uses explicit idempotent-intent policy and durable operation fingerprints rather than transport retry_safe metadata.
```

```yaml target-contract
kind: commitment
id: COM-004
class: agreed-path
provenance: independent challenge recommendation
statement: The change evolves the current proven core through additive hardening and an intention facade before removing public low-level operations.
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: user clean-cut authorization
statement: Interface cutover migrates no active claims, attempts, frontier positions, repair state, or compatibility schemas; active Changes finish or are explicitly abandoned first.
```

```yaml target-contract
kind: commitment
id: COM-006
class: implementation-discretion
provenance: user request and current architecture evidence
statement: Storage technology and host topology remain unchanged unless focused proof identifies a residual correctness or operability problem that the current mechanisms cannot solve.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Fenced execution recovery
promise: Delivery restores progress after worker failure without resetting a worktree beneath a potentially live writer and without losing dirty bytes.
dependencies: []
commitments: [COM-001, COM-002, COM-003, COM-004]
acceptance:
  - "Given a claim past its timeout whose worker termination is not established, acquisition retains custody and emits one bounded recovery action without resetting or relaunching the Change worktree."
  - "Given an established-dead Builder claim with changed files, recovery creates isolated preservation evidence, restores the reviewed worktree boundary, releases custody, and permits successor acquisition."
  - "Given repeated matching worker or provider failures, persisted retry policy reaches bounded attention instead of starting an unbounded fresh-worker or provider loop."
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Coherent repair ownership
promise: One repair coordinator diagnoses current Delivery attention, applies engine-owned safe convergence, obtains one material user answer when needed, delegates reviewed repository repair, and returns control to orchestration.
dependencies: []
commitments: [COM-001, COM-002, COM-004]
acceptance:
  - "Given the shared repair prompt, VS Code selects a named repair coordinator whose declared tools cover the current repair workflow and whose mutations remain Delivery-owned."
  - "Given repair evidence with one safe route, the coordinator applies that route and reports the observed successor state without asking the user to select low-level operations."
  - "Given materially different preservation, adoption, or discard outcomes, the coordinator presents one bounded question and applies only the selected engine-owned proposal."
  - "Given repair requiring source edits or merge reasoning, Delivery issues a scoped Builder repair launch with normal exact-commit review before ordinary orchestration resumes."
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Bounded background convergence
promise: Checkpoint, publication, and acceptance reconciliation retry with bounded backoff, visible health, and no duplicate mutation ownership across concurrent hosts.
dependencies: [OUT-001]
commitments: [COM-001, COM-002, COM-003, COM-006]
acceptance:
  - "Given a persistently failing checkpoint provider, reconciliation records attempt count, last failure, and next retry while bounded backoff prevents a fixed five-second retry storm."
  - "Given Cockpit and MCP hosts against one workspace, shared reconciliation ownership prevents overlapping mutation while host restart permits pending work to continue."
  - "Given a healthy pending checkpoint or acceptance observation, convergence proceeds without requiring the browser page to remain visible."
```

```yaml target-contract
kind: outcome
id: OUT-004
title: Intention-oriented Delivery interface
promise: Routine callers express Design, action, result, answer, and repair intentions without sequencing internal heads, receipts, operation identifiers, or cleanup variants.
dependencies: [OUT-001, OUT-002, OUT-003]
commitments: [COM-001, COM-002, COM-003, COM-004, COM-006]
acceptance:
  - "Given one current Change, the public read projection supplies its semantic state, next action, repair proposal, and evidence links without requiring callers to join separate operator, health, Integration, and finalization views."
  - "Given a Planner, Builder, Finalizer, or repair launch, one claim-bound submission contract records an identical replay once and rejects a different replay without exposing internal publication tokens."
  - "Given current repair attention, one high-level repair request either converges safely, returns a reviewed repair launch, returns one version-bound proposal, or quarantines the affected Change."
  - "Given the additive facade, maintained parity tests demonstrate the retained normal and repair behaviors before low-level MCP operations are removed from caller grants."
```

```yaml target-contract
kind: outcome
id: OUT-005
title: Clean interface cutover
promise: MCP, Cockpit, and shared agents use the intention interface while proven internal primitives remain private or are deleted only when their behavior is subsumed.
dependencies: [OUT-004]
commitments: [COM-001, COM-004, COM-005, COM-006]
acceptance:
  - "Given a quiescent cutover inventory, active Changes are completed or explicitly abandoned and no claim, attempt, frontier position, repair record, or compatibility schema is migrated."
  - "Given the new caller surfaces, retired low-level MCP operations and repair choreography are absent from active agents, skills, prompts, HTTP routes, and generated operation registries."
  - "Given a fresh canary Change, Design through provider-observed completion succeeds using the intention interface and injected worker, publication, restart, and repair failures converge through the retained guarantees."
  - "Given fresh-clone recovery proof for admitted authority and review permission, remote snapshot machinery is retained, simplified, or removed according to that demonstrated contract rather than interface-count preference."
```