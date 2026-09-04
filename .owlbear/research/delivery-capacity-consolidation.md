# Delivery Capacity Consolidation

> **Owning task:** none - delivery architecture research
> **Date:** 2026-08-23
> **Question:** Should Delivery use one defaulted `execution_capacity` of `3`, remove
> `writer_capacity`, and enforce concurrency only through execution slots while retaining
> one-agent-per-Change safety?
> **Status:** Research updated after an independent architecture challenge and focused source review;
> implementation has not started.

## 1. Context And Question

Delivery currently models two global limits and one per-Change ownership record:

- `execution_capacity` limits the total number of active Planner and Builder claims.
- `writer_capacity` limits the number of active Builder writer reservations through a global ledger.
- `ChangeCoordination.writer` binds a Builder to one exact Change claim and workspace.

The current runtime already has one active-claim-per-Change selection, one managed branch and
worktree per Change, and exact Build custody in `ChangeCoordination.writer`. The global ledger is
therefore a second, independently persisted "already has a writer" predicate as well as a
Builder-only admission throttle. Removing it would remove a redundant divergence point, but only
the global predicate and ledger should be removed; per-Change custody remains required.

The shaping decision is therefore whether to simplify the global contract without weakening the
per-Change invariant. The evidence needs to answer five points:

1. Where does each capacity currently affect admission, startup, retirement, and recovery?
2. Which writer state is redundant global occupancy and which is required for ownership and recovery?
3. Can two Delivery processes share one runtime root, and is the current occupancy read safe there?
4. How should old `host.json` and `capacity.json` artifacts be handled without silently losing custody?
5. What focused tests would prove the bounded behavior that the implementation actually claims?

## 2. Sources Studied

| Source | Load-bearing fact | Evidence limit |
| --- | --- | --- |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | Acquisition calls `_reconcile_runtimes()` before `acquisition_lock()`, counts `active_claims()` from the process-local runtime map against `execution_capacity`, and currently applies an additional Builder-only writer-capacity filter. `_candidates()` skips Changes with active claims. | Establishes the current admission boundary; it also identifies a cross-process discovery race that must be proved or fixed before claiming a global bound across shared processes. |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | `CapacityLedger` is read and written in the same transaction as coordination and acts as a second active-writer predicate. `ChangeCoordination.writer` and `ChangeWriter` retain exact per-Change Build custody, validation, release, restart, and recovery state. | The module contains redundant global and required per-Change concerns; the former can be removed without weakening the latter. |
| [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py) | `DeliveryHostConfig` is strict, schema `1`, and currently defaults both fields to `1`. Missing `host.json` returns defaults; loading is read-only. Two coordinator construction sites pass `writer_capacity`. | Shows that startup rewrite would be a new behavior, not an existing migration mechanism. |
| [`target_context.py`](../../serve/cockpit/src/owlbear_cockpit/target_context.py), [`main.py`](../../serve/cockpit/src/owlbear_cockpit/main.py), and [`server.py`](../../serve/delivery-mcp/src/owlbear_delivery_mcp/server.py) | Cockpit and delivery-MCP resolve the workspace from `Path.cwd()` and delegate to the same core application loader. The MCP server is an independent process; Cockpit is an independent Uvicorn process. | Confirms technical shared-root possibility, not a documented or tested co-running support promise. |
| [`.vscode/mcp.json`](../../.vscode/mcp.json) | The workspace starts delivery-MCP as a stdio process from the project context while Cockpit can run separately. | Shows a plausible co-running topology; it does not prove users are expected to run both admission surfaces concurrently. |
| [`delivery_integration_retirement.py`](../../serve/tools/src/owlbear_tools/delivery_integration_retirement.py) | Normal retirement and journal recovery both load `capacity.json` from the current `.owlbear/delivery/runtime`, not only from a retired legacy root. | Absence handling is mandatory in the first capacity change; this is not merely a legacy-parser concern. |
| [`delivery_migration.py`](../../serve/tools/src/owlbear_tools/delivery_migration.py) | Legacy migration already fails closed when global holders or active claims exist, and currently copies and validates the old ledger in staged state. | It is a historical-state boundary; new cross-check logic would duplicate an existing quiescence gate. |
| [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py) | Tests cover execution admission, writer-capacity skipping, ledger persistence, exact claim recovery, dirty Build custody, and startup conflict behavior. | Existing expectations encode the old contract and will need deliberate replacement, not blanket deletion. |
| [`test_change_workspace.py`](../../serve/delivery/tests/test_change_workspace.py) | Tests directly specify `CapacityLedger` creation, concurrent ledger updates, configured-capacity conflicts, and per-Change writer operations. | The global-ledger tests should be retired or moved to legacy migration coverage; per-Change custody tests remain relevant. |
| [`test_target_server.py`](../../serve/delivery-mcp/tests/test_target_server.py) | MCP startup currently expects the runtime `capacity.json` artifact to exist after application construction. | Confirms a transport-level observable that must change with the runtime contract. |
| [`target-delivery-information-flow-step-10.md`](target-delivery-information-flow-step-10.md) | The older information-flow decision recommended separate execution and writer capacities for its then-current reservation flow. | It is not sufficient rationale for the present reversal: focused history reports that the current capacity split was intentionally added later, after isolated workspaces and one-claim acquisition already existed. |
| Git history (`f67722ba9`, `fd8faf31c`, `2044f1bdc`, `ca2f3aea2`, `118b14cdc`) | The recent redesign introduced/configured both capacities, separately classified ledger races, and refined isolated workspaces and claim acquisition. A writer-capacity bypass test deliberately preserved Planning admission when the writer ledger was full. | The exact resource rationale for retaining a Builder-only cap remains unresolved and must be acknowledged before implementation. |
| [`operating-owlbear.md`](../../setup/operating-owlbear.md) and [`serve/delivery/README.md`](../../serve/delivery/README.md) | Current operator documentation describes both capacities and the generated writer ledger. | These current contract statements are in scope for the first capacity change. |
| [`init.py`](../../setup/init.py), [`seed/.owlbear/.gitignore`](../../seed/.owlbear/.gitignore), and [`test_setup_init_settings.py`](../../tests/test_setup_init_settings.py) | The capacity-specific entries there refer to the legacy `.owlbear/target/target-runtime/capacity.json` path; current `.owlbear/delivery/runtime/` is already ignored as a whole. | These are not first-change surfaces unless legacy target-root retirement is separately authorized. |
| [`.owlbear/py-index.md`](../../.owlbear/py-index.md) | The generated symbol index still lists `writer_capacity_available`. | It must be refreshed if the public/runtime symbol is removed; it is not a concurrency authority. |

## 3. Analysis

### 3.1 Current concurrency model

There are three distinct controls in the current implementation:

| Control | Scope | Current role | Required after consolidation |
| --- | --- | --- | --- |
| `execution_capacity` | Portfolio-wide | Bounds active Planner and Builder outcome claims as observed by the process-local runtime map. | Keep as the only global Planner/Builder concurrency limit; default to `3`. |
| `writer_capacity` plus `capacity.json` | Portfolio-wide, Builders only | Skips eligible Builders once the global writer ledger is full and independently rejects a Change already listed in the ledger. | Remove from production admission and canonical runtime state. |
| `ChangeCoordination.writer` and per-Change custody | One Change | Binds a Builder writer to an exact claim, worktree, branch, and recovery path. | Keep unchanged in meaning; it prevents two workers from owning one Change. |

The important distinction is that the second and third rows are not interchangeable. The ledger is
not only a throttle: `_acquire()` commits its Change ID with the coordination record and treats
either record as evidence of an active writer. That duplicate predicate can diverge and currently
creates a soft deadlock when the ledger retains a Change ID after coordination loses its writer.
Removing the ledger removes that divergence class, but must not remove `ChangeWriter`, writer claim
identity checks, dirty-worktree custody, or exact recovery. Those records answer "who owns this
Change?" The retired ledger answered "how many Build writers may exist on this host?" and repeated
part of the first question.

The current one-agent-per-Change rule also means a global writer cap no longer protects a Build from
another worker changing its source baseline. A second claim on that Change is already rejected.
Unrelated Changes have separate managed worktrees and can safely consume any remaining execution
slots, regardless of whether their workers are Planners or Builders.

#### Shared-root occupancy boundary

Cockpit and delivery-MCP are separate processes that both resolve `Path.cwd()` and delegate to the
same core loader. The repository does not document or test co-running them against one runtime root,
but it also has no single-owner guard, and its filesystem locks are descriptor-backed and usable
across processes. Shared-root operation is therefore technically possible and cannot be treated as
impossible merely because it lacks a support statement.

The current acquisition sequence reconciles the process-local runtime map before entering
`acquisition_lock()`, then counts `active_claims()` from that map under the lock. Existing runtime
objects re-read their frontier, but a Change admitted after reconciliation can be absent from the
map. Two processes can consequently over-admit execution slots if shared-root operation is allowed.
This is a pre-existing occupancy-discovery issue, not a benefit of the writer ledger, and it must be
resolved or explicitly excluded before claiming a cross-process global bound.

Integration repair claims are also not included in this occupancy count. Current producers no longer
auto-claim that work, so counting it is a separate lifecycle decision rather than an unannounced
part of this consolidation.

### 3.2 Alternatives

| Alternative | Benefits | Costs and risks | Decision |
| --- | --- | --- | --- |
| Remove `writer_capacity` and the canonical writer ledger; retain per-Change custody. | One understandable global budget; no Builder starvation behind a second budget; removes a real ledger/coordination divergence deadlock; fewer startup conflicts; directly matches the requested execution-only policy. | Removes an optional host-wide throttle; current retirement must tolerate ledger absence; existing ledger-focused tests and docs need replacement. | **Recommended, subject to the shared-root occupancy gate.** |
| Remove the setting but retain a redundant `capacity.json` ledger. | Smaller first source edit and some legacy tooling can remain unchanged. | Leaves an unexplained global artifact, keeps two sources of writer state, preserves stale-ledger failures, and makes it unclear whether the file is authoritative. | Reject. |
| Rename or retain a Builder-only capacity such as `build_capacity`. | Preserves a way to limit resource-heavy Builders independently. | Still violates the requested single-limit contract, retains Builder starvation, and requires another policy/configuration surface with no correctness need. | Reject unless a later resource-bound decision supplies evidence. |
| Replace the writer ledger with an execution ledger. | Could make global occupancy explicit and durable. | Duplicates active claims already persisted in runtime state, adds another cross-store transaction, and risks divergence during claim recovery. | Not part of this consolidation; revisit only if execution admission cannot remain atomic with existing claim state. |

The recent decision history raises the evidence bar for this reversal. Focused history identifies the
current capacity configuration as an intentional change after isolated workspaces and claim-based
acquisition already existed, plus a later classification of capacity-ledger races. Existing tests
also deliberately prove that read-only Planning can proceed while the writer ledger is full. The
older Step 10 rationale therefore cannot by itself explain why the current Builder-only cap should
be removed. No reviewed source currently supplies a CPU, memory, disk, or external-service rationale
that requires retaining it. The plan records `3` and writer-cap removal as user policy inputs, not
as deductions from host measurements.

### 3.3 Prior decision check

The reported history sequence is:

| History item | Relevance to this plan |
| --- | --- |
| `2044f1bdc` isolated Change workspaces | Establishes separate managed worktrees and branches before the current capacity configuration. |
| `ca2f3aea2` and `118b14cdc` claim/acquisition refinements | Establish claim-based occupancy and reduce automatic Integration repair production. |
| `f67722ba9` on 2026-08-14 | Intentionally configures host-local `execution_capacity` while retaining/configuring `writer_capacity` in the current model. |
| `fd8faf31c` on 2026-08-14 | Classifies capacity-ledger races, making ledger behavior a recent deliberate concern rather than an untouched relic. |
| `3e7df8368` / `497b35605` | Preserve proof that a full writer ledger does not block read-only Planning. |

The reversal is defensible because the ledger duplicates per-Change custody and can deadlock when
the two records diverge, but the plan must say explicitly why the Aug-14 resource decision no
longer applies. That rationale is still a user decision, not a resolved repository fact.

### 3.4 Recommended runtime contract

The implementation should establish this contract:

- `DeliveryHostConfig` exposes `execution_capacity` only and defaults it to `3`. The first capacity
  change keeps schema `1`, strict extra-key rejection, and the current read-only loading behavior.
- Every active Planner or Builder outcome claim consumes exactly one execution slot. Admission never
  applies a separate Builder-only capacity check. Integration repair remains outside this change.
- A Change can have at most one active claim. This remains the primary same-Change concurrency
  invariant and must be checked under the existing acquisition coordination.
- A Build still acquires `ChangeCoordination.writer` for its exact active claim. That custody is
  ownership and recovery state, not a second global capacity budget.
- There is no canonical writer-only `capacity.json` in a newly initialized runtime. Execution
  occupancy remains derived from active runtime claims and the existing acquisition/recovery
  protocol. A temporary migration-only reader may understand old ledgers without making them
  authoritative.
- A failed, interrupted, dirty, or mismatched Build continues to retain or release per-Change
  custody according to the existing exact-claim recovery rules. Removing the global ledger must not
  turn an ambiguous worktree into an available Change.
- The public and MCP startup contract reports one capacity setting. It must not silently continue
  to enforce a legacy `writer_capacity` value.
- If shared-root co-running is supported, runtime discovery and occupancy enumeration must occur
  under the acquisition lock before the execution bound is claimed. If it is intentionally
  unsupported, that boundary must be made explicit and the plan must not claim cross-process
  enforcement.

The default is a behavioral contract, not just a model default: a missing host configuration,
newly written host configuration, E2E seed, and documentation must all converge on `3`.

### 3.5 Migration and retirement boundary

#### Old `host.json`

Do not add a startup rewrite in the first capacity change. `_load_host_config()` currently treats
`host.json` as optional, read-only, strict schema-1 input. After removing the field:

1. A missing file uses the new execution default of `3`.
2. A stale schema-1 file containing `writer_capacity` fails strict validation with a typed startup
   diagnostic naming the unknown field. It is never silently discarded or passed to the coordinator.
3. A separate host-config migration may later preserve an existing execution value and remove the
   obsolete writer field, but it must be separately justified because it adds a startup write to an
   ignored, host-local file. Schema `2` is optional rather than a prerequisite for the policy change.

This keeps the first change read-only at startup and avoids introducing partial-write or concurrent
startup failure modes. Existing users with an old host file need an explicit migration or edit before
the new loader accepts it.

#### Old `capacity.json`

Treat the old ledger as transitional input, never as current runtime authority:

- Current Integration retirement must accept an absent ledger in both its normal and journal
  recovery paths. If an old file is present, it may be parsed and non-empty holders must still block
  retirement; absence must not be treated as active custody.
- The existing state migration already fails closed when the legacy ledger has holders or when a
  coordination record has an active writer. Do not add a second holder cross-check without a fixture
  that reaches a genuinely different state.
- Leave legacy migration copy/validation behavior unchanged in the first capacity change unless a
  supported migration test proves it creates an unsafe new state. A migrated old tree may retain an
  inert `capacity.json` temporarily; the normal newly initialized runtime must not create or read it.
- A later legacy-cleanup change can move the parser into the tools boundary, stop copying the file,
  and remove it from retired roots after supported legacy installations are enumerated.
- Existing ignored legacy target paths may remain for that migration generation. They must not be
  documented as current runtime artifacts.

This preserves fail-closed handling for old state while preventing a stale global writer count from
authorizing new work or becoming a new runtime dependency.

### 3.6 File-by-file implementation plan

#### Change 0 - shared-root occupancy gate

The repository confirms technical co-running but not a documented support promise. Before claiming
that `execution_capacity` bounds work across processes, choose one of these explicit boundaries:

- **Support shared roots:** move discovery/reconciliation or an equivalent complete occupancy read
  inside `acquisition_lock()`, then add a two-process regression using a Change admitted after one
  application instance was constructed. The test must prove no more than the configured number of
  Planner/Builder claims are active.
- **Do not support shared roots:** add a real single-owner guard or an explicit contract that prevents
  concurrent admission surfaces from sharing a runtime. Documentation alone does not repair the
  current over-admission window.

This gate is separate from writer-capacity semantics, but it must precede any cross-process capacity
claim. A single-process implementation may proceed without it only if the support boundary is
explicitly narrowed.

#### Change 1 - capacity consolidation

- [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py)
  - Change the host model to the single execution setting with default `3`, retaining strict schema-1
    validation and no startup rewrite.
  - Construct the coordinator without a writer-capacity argument at both construction sites and
    remove writer-ledger startup error handling.
- [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py)
  - Remove only the global Builder writer-capacity filter.
  - Keep execution-slot counting, stable candidate ordering, one active claim per Change, and
    exact Build writer acquisition/release sequencing.
- [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py)
  - Remove canonical runtime `CapacityLedger` initialization, mutation, and availability checks from
    `PortfolioCoordinator`; remove its global conflict APIs from the production surface.
  - Keep a narrow legacy parser only where migration or retirement still needs to read old files,
    or relocate that parser into the tools boundary in the same change if required by imports.
  - Preserve `ChangeCoordination.writer`, `ChangeWriter`, per-Change writer validation, recovery,
    restart, and the coordination lock that protects one writer per Change.
- [`__init__.py`](../../serve/delivery/src/owlbear_delivery/__init__.py)
  - Remove public exports for retired global-ledger behavior and exceptions; do not remove a
    migration-only parser until its legacy callers have moved or been deliberately retired.
- [`delivery_integration_retirement.py`](../../serve/tools/src/owlbear_tools/delivery_integration_retirement.py)
  - Make `capacity.json` optional in both current-runtime quiescence and journal recovery. Preserve
    fail-closed rejection when an existing legacy ledger reports active holders.

#### Change 1 tests and current docs

- [`test_change_workspace.py`](../../serve/delivery/tests/test_change_workspace.py) and
  [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py)
  - Retire global ledger initialization/race/conflict assertions; preserve exact per-Change writer
    custody, dirty recovery, and mismatched-owner attention tests.
  - Replace writer-capacity skipping with execution-only admission and one-claim-per-Change tests.
- [`test_target_server.py`](../../serve/delivery-mcp/tests/test_target_server.py)
  - Replace the generated `capacity.json` startup expectation with the single host setting and
    no-new-ledger contract.
- [`test_delivery_integration_retirement.py`](../../serve/tools/tests/test_delivery_integration_retirement.py)
  - Cover current runtime retirement with no ledger, journal recovery with no ledger, and legacy
    non-empty-ledger fail-closed behavior.
- [`seed-work-portfolio-delivery.py`](../../serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py)
  - Seed only the single execution setting and construct the coordinator under the new API.
- [`serve/delivery/README.md`](../../serve/delivery/README.md),
  [`serve/delivery-mcp/README.md`](../../serve/delivery-mcp/README.md), and
  [`operating-owlbear.md`](../../setup/operating-owlbear.md)
  - Document `execution_capacity=3`, no `writer_capacity`, no newly generated writer ledger, the
    one-agent-per-Change invariant, and per-Change writer custody as a separate ownership concept.
- [`.owlbear/py-index.md`](../../.owlbear/py-index.md)
  - Refresh generated symbol references after removing `writer_capacity_available`.

#### Change 2 - explicit host-file migration, if required

Only add a one-way schema migration if rejecting stale host files is unacceptable for supported
installations. It must preserve a valid old `execution_capacity`, discard `writer_capacity` by an
explicit documented rule, use atomic replacement, and have a concurrency/read-only-filesystem test.
It should not be bundled into the runtime capacity change merely to make the schema number look new.

#### Change 3 - legacy target-root cleanup, if still supported

After enumerating supported installations, decide whether the old `.owlbear/target/` migration and
retirement strand still matters. If it does, move the ledger parser into a migration-only boundary,
stop copying inert `capacity.json` into new canonical trees, and retain fail-closed recovery tests.
If it does not, retire that strand separately. `setup/init.py`, `seed/.owlbear/.gitignore`, and
`test_setup_init_settings.py` are not first-change surfaces because their capacity references are
legacy target paths.

#### Deferred concerns

Counting Integration repair claims against execution capacity and introducing a renamed Builder-only
resource throttle both require separate evidence. Neither should be smuggled back into this change.

## 4. Acceptance Scenarios And Validation

The implementation is complete only when these scenarios pass for the support boundary it claims:

1. A missing host configuration starts with `execution_capacity == 3` and creates no canonical
  writer ledger.
2. A stale schema-1 host file containing `writer_capacity` fails with a typed unknown-field
  diagnostic; any separate host migration proves preservation of execution capacity and atomic
  rewrite independently.
3. With execution capacity `3`, three claims across distinct Changes can be active in any Planner /
   Builder combination, and a fourth claim is not admitted.
4. A Builder is admitted when an execution slot is available even if two or more other Changes are
   already in Build custody. No global writer count blocks it.
5. A second claim for the same Change is never admitted, including when execution capacity has free
  slots and no global ledger exists. Exact recovery releases only the matching claim and per-Change
  writer; dirty or mismatched recovery retains custody and attention.
6. Current Integration retirement and journal recovery complete without `capacity.json`; an existing
  legacy ledger with active holders still fails closed.
7. Existing legacy migration tests continue to reject active holders. Any later change that removes
  the legacy copy must separately prove staged-state and interrupted-migration recovery.
8. If shared-root operation is supported, a two-process test proves the execution bound and the
  newly discovered-Change case. If it is unsupported, a real single-owner boundary prevents that
  topology and the documentation does not claim cross-process enforcement.
9. MCP startup, E2E seed data, current documentation, and generated indexes no longer rely on
  `writer_capacity` or a newly generated `capacity.json`; legacy setup ignore rules remain unchanged.

Targeted implementation validation should cover these scopes:

```text
uv run pytest serve/delivery/tests/test_change_workspace.py \
  serve/delivery/tests/test_portfolio_application.py \
  serve/delivery-mcp/tests/test_target_server.py \
  serve/tools/tests/test_delivery_integration_retirement.py \
  serve/tools/tests/test_delivery_migration.py
uv run ruff check serve/delivery serve/delivery-mcp serve/tools
```

## 5. Recommendation, Confidence, And Limits

**Recommendation:** consolidate the global policy to `execution_capacity`, default it to `3`,
remove `writer_capacity` and the canonical writer-only `capacity.json`, and retain exact
per-Change writer custody plus the one-active-claim-per-Change rule. Land the shared-root occupancy
gate first if the product intends Cockpit and delivery-MCP to admit work against one runtime.

**Confidence:** high that the global ledger is redundant for per-Change correctness and that its
divergence can deadlock recovery. Medium for the global execution guarantee because occupancy is
counted from a process-local runtime set reconciled outside the acquisition lock. Medium for the
reversal of the recent two-capacity decision because the repository history confirms intent but not
the original resource rationale. Medium for legacy migration details until supported installations
and old-state fixtures are enumerated.

**Risks and limits:** removing the writer setting removes a host-wide resource throttle. If the
host has a separate CPU, memory, or external-service limit, that constraint needs independent
evidence and a separately named policy; it should not be smuggled back into writer ownership. The
plan also assumes active runtime claims and the existing acquisition lock remain the authoritative
execution occupancy mechanism. A later implementation must verify that crash recovery cannot leave
an active claim uncounted when the global ledger is removed. The current plan does not claim that
Integration repair claims consume execution capacity.

**Questions that block implementation:**

1. Is shared-root co-running of Cockpit and delivery-MCP a supported topology? If yes, Change 0 is
  mandatory; if no, what real single-owner guard should enforce that boundary?
2. What concrete resource concern motivated the Aug-14 retention of `writer_capacity`, and does the
  user explicitly accept losing that host-wide throttle in favor of `execution_capacity == 3`?
3. Must existing schema-1 `host.json` files migrate automatically, or is typed rejection plus an
  explicit operator edit acceptable?
4. Are legacy `.owlbear/target/` installations still supported, or can the parser/copy strand be
  retired later?

The historical Step 10 recommendation for separate capacities remains evidence for the older
reservation model, while the current ledger/coordination divergence is evidence for consolidation.
Neither source alone resolves the shared-root support boundary or the recent resource-policy choice.
