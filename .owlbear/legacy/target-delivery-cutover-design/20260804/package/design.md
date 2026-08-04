# Target Delivery Cutover Design

## Current System

The current implementation already supplies reusable transaction, Git, and projection foundations:

- `TargetAuthorityRegistry` validates and atomically admits current schema authority.
- `TargetRuntime` owns jobs, attempts, requests, receipts, and frontier derivation.
- `PortfolioCoordinator` provides per-change writer ownership, capacity, Integration serialization,
  and durable transaction recovery.
- `ChangeWorkspaceManager` owns warm branches, worktrees, reviewed boundaries, restart, and target CAS.
- `ProofCheckoutManager` owns contained commit materialization and validation.
- `WorkItemProjector`, MCP Kanban, and Cockpit expose current runtime state.

The principal contradictions are structural. `TargetAuthority` contains runtime evidence;
`TargetRuntime` persists reviewer dispositions, arbitration, `RETURNED`, and `ReturnLevel`; current
orchestration chooses identities and joins context; and Integration neither snapshots the complete
package nor owns terminal runtime state.

## Proposed Ownership

### Package Store

Add a transport-free change-package owner in `serve/kanban`. It owns safe identity paths, package
manifest and inventory, initialized authored files, generated-contract destination, atomic directory
publication, package locking, semantic checkpoint refs, immutable snapshot capture, and cleanup
verification. Active package paths remain outside tracked product-tree content. No MCP adapter edits
package internals directly.

The target package begins with `intent.md`, `design.md`, generated contract destination, and manifest.
The current bootstrap `decisions.yaml` is transitional workflow metadata only; accepted meaning is
already incorporated into its owning authored document, and the cutover neither derives from nor
archives a separate decision authority. Runtime/admission/request/result records join the package as
their owning features land. Change-owned research and source-context references remain package
members through completed history; shared project knowledge and product source remain outside it.

### Contract Compiler

Add one transport-free compiler in `serve/kanban`. It parses fenced `yaml target-contract` blocks from
`intent.md` and `design.md`, rejects unknown keys and duplicate or unresolved identities, canonicalizes
semantic definition, binds source hashes, and emits schema-v2 Delivery Contract bytes. It performs no
model inference or prose summarization.

Representative block syntax in `intent.md` is provisional implementation design until parser and
readability proof pass. If strict YAML fences cannot preserve readable complete authority, Design
reopens around the separately reviewed contract fallback rather than adding inference.

Schema v2 contains change identity, the exact first level-one heading from `intent.md` as its display
title, commitments, outcomes, deterministic outcome-owned plan scopes, and source bindings. It has no
change-assembly scope; every composition contract belongs to an outcome. A limitation constrains
Delivery only when authored as commitment or outcome behavior. The current normative-block and
Integration proof gates are already OUT-002 and OUT-006 acceptance and are not duplicated as limit
records or admission-receipt fields. Other weaknesses remain Design prose.

Design re-entry remains runtime successor context. Generic `SemanticUpdate` and `CompletionSummary`
records are retired: neither has a production writer, resumed work consumes typed transition/request
context instead, and completed lookup consumes the package and Integration identities. OUT-007 removes
their MCP operations, OUT-008 removes their Cockpit projections, and OUT-009 removes agent dependencies.
Review output, requests, results, and progress remain runtime/package records owned by their respective
Delivery outcomes.

### Admission And Revision

Refactor admission around current `RuntimeTransaction` staging:

1. lock the package and authority registry;
2. reread source bytes and derive schema-v2 contract;
3. validate references, coverage, dependencies, source bindings, and frontier;
4. idempotently checkpoint the exact package tree on its semantic-history ref;
5. prepare contract and runtime participants under one filesystem transaction;
6. publish the minimal receipt participant last.

The Git checkpoint and filesystem transaction are deliberately not one atomic store. A checkpoint
without a visible receipt is inert; retry recognizes the same package tree and resumes the
filesystem transaction. Source mutation, a changed checkpoint ref, or conflicting participant bytes
fails before executable authority becomes visible.

Revision requires no active claims. It archives the prior admitted revision and computes outcome
carry-forward from canonical projections that close over linked commitment bodies. Changed outcomes
and their dependent closure return to Planning; unaffected task chains and result bindings rebind to
the new digest. Removed accepted behavior requires an ordinary removal or replacement outcome.

This change is bootstrapped through the current schema-v1 package. Cutover migration requires a
quiescent target portfolio, derives schema-v2 authority from authored source, and replaces old runtime
records once. There is no dual runtime or compatibility reader after migration.

### Runtime State And Transitions

Replace technical job state as user progress authority with canonical outcome stages:
`design`, `planning`, `implementation`, `assembly`, and `completed`. Derive change lifecycle as
`design`, `active-delivery`, `integration`, or `completed`.

Planning publishes an idempotent claim-scoped task-chain candidate. Build produces an owned commit and
result binding. Assembly carries its read-only verified binding with advance. One transition operation
accepts:

- `advance`, referencing required current-column output;
- `retry`, ending the claim in the same stage;
- `return`, naming an allowed earlier stage and its consumed successor context;
- `block`, ending the claim in place with reason, condition, evidence needs, and optional request.

Runtime validates claim identity, output identity, stage routing, dependency state, and workspace
coordination, then updates runtime and writer custody through replayable transactions. Reviewer output
never enters this operation. Delete `TargetReview`, owner response, arbitration, `ReviewDisposition`,
`TargetJobState.RETURNED`, `ReturnLevel`, and process-liveness leases.

Invariant-checked administration may move an outcome backward only with an operator reason. It
invalidates later task and result authority plus the completed dependent closure of each invalidated
result, retaining only evidence deterministically proven unaffected. Forward administration remains
subject to normal destination invariants and cannot synthesize completion.

### Task And Request Authority

A promoted task owns result-oriented title, outcome and scope IDs, task dependencies, required outputs,
maintained surfaces, constraints, acceptance observations, and proof boundaries. Reviewed completed
tasks retain result identity; replanning rules only over unreviewed candidates.

Decision and Action Requests remain distinct. Resolution requires selected option or response text and
is joined directly into the next role context. Requestless block clearing records an operator note and
locators. These records persist because resumed work consumes them.

### Acquisition And Context

Create a portfolio application service in `serve/kanban` composing runtimes, package store,
`PortfolioCoordinator`, and `ChangeWorkspaceManager`:

- stable selection by topology and creation identity;
- one active claim per change;
- separate execution and writer capacities;
- runtime attempt before Build writer custody;
- role/model policy and bounded locator-rich launch packages;
- Integration-ready IDs returned separately without claims.

Role-specific `show_plan_context` and `show_build_context` projections resolve admitted semantic
references, task or scope authority, predecessor results, request resolution, return context, and
source coordination. They exclude portfolio state and review history.

Exact-claim recovery is explicit after the operator stops or confirms loss of an invocation. Planning
needs no writer recovery. Build recovery preserves a clean attempt head, resets to the reviewed
boundary, and releases custody; dirty or ambiguous state retains custody and creates attention.

### Build Proof

Keep `ProofCheckoutManager` as the exact-commit containment boundary. The Builder owns candidate proof
and reviewer invocation inside its work cycle. Materialize and validate the candidate checkout before
review; clean it replayably afterward. Reviewer observations remain transient. The Builder critically
resolves observations and issues the transition.

Assembly is a read-only verifier without another reviewer. Composition requiring code becomes a
normal dependent implementation task before Assembly.

### Integration And Completion

Add `integrate_ready_change(change_id)` as a Kanban application operation. Under the existing
portfolio Integration lock plus package/runtime lock it:

1. revalidates completed outcomes, Assembly, revision state, admitted target identity, and branch-head
   equality with the reviewed boundary;
2. inventories and hashes the stable package source;
3. derives the product merge tree without rewriting reviewed commits;
4. inserts or replaces only this change's stable completed-package path while preserving sibling paths;
5. runs changed-path proof in the clean warm worktree when target divergence requires it;
6. creates the target commit and compare-and-swaps the configured target;
7. publishes terminal runtime identity and replayably removes matching active package and warm worktree.

For package-only completion, retain the target product tree and replace only the package path. A replay
recognizes the committed package identity and completes residue cleanup without another commit.

Conflict, proof failure, mutation, or stale authority produces one change-scoped Integration attention
record containing failure kind, unchanged heads, diagnostics, target, and retry condition. Merge repair
is a user-invoked bounded prompt using the existing worktree and Build Reviewer; it may create one
additive reviewed repair commit but may not redesign or rewrite completed work. A passing review
advances the recorded reviewed/completed boundary to that commit and clears the matching attention;
only then is deterministic Integration retry eligible.

Completed history uses one stable package path per change. Git history preserves earlier revisions.
A bounded rebuildable index supports exact and semantic-summary lookup. Active tools exclude completed
package bodies. Reopen remains documented manual recovery from package, branch, and history ref.

### Adapters And UI

MCP Kanban validates and delegates the new package, Design, admission, acquisition, role-context,
transition, request-creation, recovery, Integration, and completed-lookup contracts. Answer-bearing
request resolution and requestless unblock remain user/Cockpit-owned backend operations and are not
registered as agent-callable MCP tools. The adapter removes retired tools in the same cutover; it
does not preserve aliases.

Cockpit backend projects typed runtime attention and exposes user-owned controls. Cockpit frontend adds
only controls and views required for requests, dead-claim recovery, backward administration,
Integration retry/attention, and completed lookup. It does not expose reviewer prose or machine
contract internals as user decisions.

Agent configuration lands last. Designer authors Specification and invokes Forward and Reverse
Specification Reviewers. Orchestrator becomes a thin launch adapter. Planner and Builder consume one
role context, run advisory review internally, publish output, and issue one transition. Agent files
are verified structurally and by review; durable text assertions are not added.

## Interface Summary

Public Kanban interfaces to add or replace:

- Design package: create, list/search summaries, show orientation/intent/architecture/contract,
  checkpoint, derive, validate, admit, revise.
- Delivery: acquire frontier work, show Plan context, show Build context, publish task chain,
  transition work, resolve/unblock request, remove exact claim.
- Completion: list Integration-ready IDs, integrate ready change, show Integration attention,
  lookup completed package.

Keep transport-free `TargetAuthorityRegistry`, `TargetRuntime`, `PortfolioCoordinator`,
`ChangeWorkspaceManager`, and `ProofCheckoutManager`, but reshape their models and composition around
the target contracts. Avoid new adapter interfaces where a direct in-process call is sufficient.

## Normative Architecture Boundaries

```yaml target-contract
kind: commitment
id: COM-009
class: agreed-path
provenance: target delivery cutover architecture
statement: Change-package ownership, contract compilation, admission, revision, and semantic snapshot transactions live in serve/kanban behind transport-free public interfaces; adapters do not edit package internals or reimplement validation.
```

```yaml target-contract
kind: commitment
id: COM-010
class: agreed-path
provenance: target delivery cutover architecture
statement: Runtime transitions, acquisition, role-context projection, workspace coordination, exact-claim recovery, and Integration live in serve/kanban; MCP and Cockpit remain validation, transport, projection, and user-control adapters.
```

```yaml target-contract
kind: commitment
id: COM-011
class: dealbreaker
provenance: target delivery cutover failure semantics
statement: Stale identity, invalid transition, source mutation, target race, or interrupted publication fails before visible authority or replays from durable identity; dirty ambiguous Build recovery retains custody and Integration failure preserves completed outcomes.
```

```yaml target-contract
kind: commitment
id: COM-012
class: important-reviewed
provenance: target delivery cutover proof strategy
statement: Proof crosses the public compiler, runtime transition, acquisition, request-context, representative Git transaction, assembled MCP registry, interactive Cockpit, and one representative lifecycle boundaries, with no durable prose-wording tests.
```

## Failure Semantics

- Parse/reference/source mismatch: typed validation failure, no admission publication.
- Transaction interruption before receipt: replay or repair prepared participants; no visible authority.
- Stale claim/output/digest: typed conflict, no state mutation.
- Invalid transition target: typed reference failure, no state mutation.
- Lost launch: operator-controlled exact-claim removal.
- Dirty Build recovery: retain custody and expose repair attention.
- Integration conflict/proof/mutation: preserve completed outcomes and publish Integration attention.
- Target CAS race: discard candidate identity and retry from fresh heads.
- Cleanup interruption after CAS: replay by committed package identity.

## Delivery Packets

| Order | Outcome | Primary domain | Depends on |
|---|---|---|---|
| 1 | OUT-001 package foundation | kanban | none |
| 2 | OUT-002 compiler/admission/revision | kanban | OUT-001 |
| 3 | OUT-003 mechanical runtime state | kanban | OUT-002 |
| 4 | OUT-004 task/result authority | kanban | OUT-003 |
| 5 | OUT-005 acquisition/context/recovery | kanban | OUT-003, OUT-004 |
| 6 | OUT-006 Integration/completed history | kanban | OUT-001, OUT-003, OUT-004, OUT-005 |
| 7 | OUT-007 MCP surface | mcp-kanban | OUT-002 through OUT-006 |
| 8 | OUT-008 Cockpit backend and frontend | split by Planner into Python and web tasks | OUT-007 |
| 9 | OUT-009 agent ecosystem cutover | agent-config | OUT-007, OUT-008 |
| 10 | OUT-010 canonical guidance | docs | OUT-006 through OUT-009 |

Planner must keep each implementation task inside one architecture domain. Tests belong to the task
whose behavior they protect; there is no test-count or one-test-per-acceptance target.

## Proof Strategy

Use the cheapest maintained boundary that can falsify each risky behavior:

- parser and source-binding examples through the public compiler;
- transaction interruption/replay at admission and Integration boundaries;
- table-driven transition routing and dependency behavior through `TargetRuntime`;
- one acquisition concurrency scenario covering execution/writer separation and claim ordering;
- request resolution and role-context projection through Kanban public interfaces;
- representative Git repositories for reviewed-head rejection, target divergence, package-only commit,
  sibling-path protection, CAS, and cleanup replay;
- assembled MCP registry tests for operation names, request validation, and retired-tool absence;
- focused Cockpit API/component tests for new interactive behavior only;
- one end-to-end representative lifecycle across assembled runtime boundaries.

Do not add tests for reviewer prose, prompt phrasing, documentation sentences, private helper layout,
or exhaustive permutations already enforced by one schema/state boundary. Existing tests that encode
retired behavior are replaced or deleted rather than preserved as compatibility obligations.

## Weaknesses And Limits

- Fenced normative blocks may prove too cumbersome; representative compiler work must falsify this
  before schema-v2 admission is frozen.
- Whole-package Integration is the highest-risk Git transaction and needs representative repository
  proof before adapter or agent cutover.
- The implementation changes persisted state broadly; migration must require quiescence and preserve a
  recovery snapshot/ref before destructive replacement.
- VS Code still requires an agent Orchestrator for custom-agent invocation. It remains intentionally
  thin until a deterministic launch API exists.
- Manual reopen is adequate initially; repeated operational use may justify a dedicated tool later.
