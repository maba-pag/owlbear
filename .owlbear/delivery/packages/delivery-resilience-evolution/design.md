# Delivery Resilience Evolution Design

> Status: exact architecture and implementation sequence for admission
> Evidence: `.owlbear/research/delivery-interface-usage-audit-2026-09-11.md`, current source at `8ff70e38ac280da9ffd97d216fd57aed9e36f36a`, and independent GPT-6 Astra / Claude Opus 5 plan challenges

## Architecture Decision

Evolve the existing Delivery core rather than replace it. The current stores, runtime, workspace manager, transaction layer, publication providers, reviewed-commit evidence, and failure-derived tests remain authoritative. Add resilience policy and an intention facade over these primitives, then demote or delete low-level caller surfaces only after assembled parity proof.

The architecture has four layers:

1. **Existing state owners:** Design package, admission registry, Delivery runtime, workspace manager, publication providers, completed history, and remote semantic snapshots.
2. **Reconciliation policy:** classifies current conditions as automatic convergence, reviewed repair work, version-bound user proposal, waiting, or fatal per-Change quarantine.
3. **Action projection:** returns Planner, Builder, Finalizer, repair interaction, waiting, and quarantine actions from current authority.
4. **Thin clients:** MCP, Cockpit, Orchestrator, and repair coordinator express intentions and render results; they do not calculate internal heads or sequence primitive repair methods.

## Repair Policy

### Automatic convergence

Permitted only when the action:

- preserves changed bytes before cleanup;
- cannot choose different semantic intent;
- cannot advance reviewed product authority;
- cannot perform non-fast-forward external mutation;
- has one durable replay identity and one observable successor state.

Examples include transaction replay, checkpoint replay, finalization invalidation after observed head drift, reproducible worktree restoration, completed-worktree garbage collection, and dead-worker recovery after termination is established.

An isolated quarantine commit is permitted because it preserves bytes without advancing the Change branch, reviewed head, publication, or completion authority.

### Reviewed repair work

Repository edits, target merge resolution, clean target merge creation, and foreign-commit adoption review enter the existing Builder and build-reviewer boundary through a repair launch. A repair launch includes immutable scope, allowed starting state, exact evidence, managed custody, completion condition, and continuation target. It does not create a second repair state machine.

### User proposal

Divergent valuable histories, intentional discard, semantic Design change, abandonment, and invalidation of accepted downstream work return one proposal with consequences and a version-bound proposal identity. The repair coordinator asks one question and applies only that proposal after revalidation.

### Fatal per-Change quarantine

When no trustworthy authority remains, the affected Change becomes non-actionable with bounded evidence. Independent Changes remain serviceable. Shared-root corruption remains a host-level startup failure.

## Public Intention Direction

The final public surface is outcome-oriented rather than fixed to a numerical target. Candidate intentions are:

- `put_design`
- `admit_change`
- `list_changes`
- `get_change`
- `next_actions`
- `submit_result`
- `answer`
- `repair`
- `set_change_intent`

Design replacement and admission remain version-bound. Worker submissions remain finite discriminated payloads with claim-bound identical replay. Repair proposals carry one opaque proposal identity. Internal heads, receipt identifiers, operation identifiers, and primitive cleanup variants remain engine implementation details unless a worker or reviewer must observe an exact commit.

## Repair Coordinator

Create one named `delivery-repairer` agent and route the existing repair prompt to it. The coordinator owns diagnosis, one-question interaction, and invoking existing Delivery-owned repair operations. It receives no unrestricted shell or edit authority for managed worktrees. When source reasoning is required, it returns or delegates an engine-produced Builder repair launch under normal review.

The first implementation slice establishes this owner using the current repair skill and operations. It changes no persisted Delivery schema or repair semantics. Later slices replace low-level tool choreography with engine-authored proposals.

## Execution Safety

Timeout is suspicion, not proof of worker death. Automatic recovery may reset and reuse a worktree only after the dispatch owner establishes termination or an enforced writer fence prevents the old worker from writing. Unknown liveness retains custody and emits one repair action. The implementation must not introduce a daemon or lease subsystem unless the existing dispatch boundary cannot provide this fence.

Retry policy stores a failure fingerprint, attempt count, last failure, and next eligible retry for repeated worker and provider failures. `retry_safe` remains transport metadata; a separate explicit idempotent-intent policy controls automatic replay.

## Background Convergence

Retain acquisition-time replay as the fast path. Replace duplicate fixed-interval silent supervisor behavior with bounded backoff and observable health. Concurrent hosts use existing descriptor locks and authoritative rereads; add ownership state only if a two-host proof shows locks cannot prevent overlapping mutation or duplicate provider effects.

Acceptance observation must not depend on Cockpit page visibility. Host startup and current action queries resume pending convergence.

## Portability

Do not delete `owlbear/delivery-state` during initial hardening or facade work. First define and prove the smaller recovery contract against a fresh clone containing only promised surviving artifacts. The replacement may discard active claims and unfinished task progress, but it must recover or require fresh approval for admitted authority and review permission. It must never infer reviewed authority from a branch tip.

## Clean Cutover

The intention facade is additive until normal and repair parity passes. Before interface cutover:

1. stop new admission briefly;
2. finish or explicitly abandon current Changes;
3. preserve source branches and quarantine refs;
4. migrate no runtime state, claims, attempts, frontier positions, or compatibility schemas;
5. switch MCP, Cockpit, and shared agents together;
6. remove old public operations and compatibility readers in the same cutover sequence;
7. run a fresh canary Change with injected failures.

## Dependency-Ordered Implementation Plan

### Slice 1 - Repair ownership (`agent-config`)

- Add `share/agents/delivery-repairer.agent.md` with the current repair workflow as required reading, explicit Delivery repair/query tools, `askQuestions`, and no source edit or terminal mutation authority.
- Route `share/prompts/resolve-delivery-attention.prompt.md` to `delivery-repairer`.
- Register the agent in `share/WIRING.md` and ecosystem validation inventories.
- Keep the current skill as procedure authority; do not duplicate its steps in the agent.
- Prove the prompt selects the agent, the agent/skill tool set is callable, and ordinary repair tools remain unavailable to unrelated agents.

### Slice 2 - Writer fencing and retry convergence (`delivery`)

- Separate timeout suspicion from recovery authorization.
- Add dispatch-termination or writer-fence evidence before worktree restart/reuse.
- Persist bounded failure fingerprints and retry eligibility for repeated worker failures.
- Preserve dirty-byte quarantine and exact claim replay.
- Prove a live writer cannot overlap successor custody and a dead writer still recovers.

### Slice 3 - Background convergence (`delivery`)

- Add bounded exponential backoff and visible supervisor state.
- Prevent duplicate mutation ownership across concurrent Cockpit/MCP hosts using current locks and authoritative rereads; add ownership state only if the focused proof requires it.
- Move acceptance observation scheduling out of browser visibility.
- Prove provider outage attempts remain bounded and recovery resumes after restart.

### Slice 4 - Repair proposals and actions (`delivery`)

- Add one reconciliation classification vocabulary and version-bound repair proposal model.
- Extend current portfolio guidance/acquisition into action projection.
- Apply automatic convergence only under the declared policy.
- Add Builder repair launch authority and continuation results.
- Prove current attention cases map to convergence, reviewed repair, one proposal, waiting, or per-Change quarantine.

### Slice 5 - Intention facade (`delivery`, then adapters by separate task)

- Add additive core intention methods over existing primitives.
- Add claim-bound discriminated `submit_result` and version-bound `answer`/`repair` contracts.
- Preserve low-level core methods and tests until parity passes.
- Add Delivery MCP, Cockpit, and agent-config adapter tasks separately so each task remains in one architecture domain.

### Slice 6 - Interface cutover and cleanup (`delivery-mcp`, `cockpit`, `agent-config`, `delivery` as separate tasks)

- Switch callers to intention operations.
- Remove retired MCP/HTTP operations and manual repair choreography after parity proof.
- Remove legacy readers and compatibility paths only at quiescent cutover.
- Retain, simplify, or remove remote snapshots only after fresh-clone recovery proof.

## Stop/Go Gates

- **Gate A:** Slice 1 proves coherent repair ownership without changing runtime semantics.
- **Gate B:** Slices 2-3 reduce unsafe or unbounded recovery behavior under fault injection. If they do not materially simplify operational attention, stop before facade work.
- **Gate C:** Slice 4 maps the maintained repair catalogue without a second state machine. If any current repair requires caller choreography not representable by one action/proposal, revise the abstraction before adapter work.
- **Gate D:** Slice 5 assembled parity covers normal and repair workflows before low-level public tools are removed.
- **Gate E:** Slice 6 canary and fresh-clone proof pass before cleanup is final.

## Risks And Controls

- **Facade displacement:** require measurable deletion or demotion of caller choreography after parity; do not merely wrap 53 tools.
- **Unsafe automation:** policy tests forbid semantic choice, unpreserved deletion, reviewed-authority advancement, and non-fast-forward mutation in automatic convergence.
- **Repair agent authority:** coordinator has interaction and Delivery tools only; Builder owns source changes.
- **Concurrent hosts:** use existing locks first; avoid speculative leader infrastructure.
- **Failure-knowledge loss:** port maintained failure tests by retained guarantee and delete a test only when its guarantee is deliberately removed.
- **Cutover complexity:** no runtime migration or dual writes.

## Proof Plan

- Agent ecosystem validation for Slice 1.
- Focused live-writer, dirty-quarantine, retry-budget, and independent-change tests for Slice 2.
- Supervisor outage, two-host contention, restart, and browser-independent acceptance tests for Slice 3.
- Table-driven repair-classification and assembled repair-to-resumption tests for Slice 4.
- Real MCPServer, HTTP route, Cockpit hook, and agent workflow parity for Slice 5.
- Fresh canary and fresh-clone recovery proof for Slice 6.

## Decision Consequences

This plan does not promise a small internal state machine. It removes caller coordination and restores progress while retaining the failure-hardened core. A clean replacement becomes justified only if Gates B-C show that current primitives cannot express the required convergence without preserving equivalent external complexity.