# Delivery Capacity Consolidation Design

## Ownership And Flow

`PortfolioApplication.acquire_frontier_work()` enters `PortfolioCoordinator.acquisition_lock()` before calling `PortfolioCoordinator.recover_transactions()`, `_reconcile_runtimes()`, occupancy calculation, candidate selection, and claim preparation. The lock serializes the only production `runtime.activate_claim(...)` path.

`PortfolioCoordinator.recover_transactions()` wraps `RuntimeTransaction.recover_all(self._state_root)` so `PortfolioApplication` does not import transaction internals. The constructor keeps state-root creation and startup transaction recovery. Acquisition and runtime-root locks are distinct; do not add another runtime-root lock around discovery because descriptor-backed `locked_roots()` is not reentrant. Preserve acquisition -> recovery -> publication locking and never the reverse.

Inside the lock, recovery runs first and reconciliation refreshes persisted membership. The acquisition keeps two related but distinct capture sets. Occupancy uses the discovered `DeliveryChangeObservation` set plus retained runtime objects: each observation with a parsed frontier contributes its active outcome-claim count, even when admission evidence, binding validation, or runtime composition reports an error; each retained runtime contributes its readable active claims, including runtimes retained with reconciliation errors; when both sources describe a Change, take the maximum rather than summing duplicate views. The Integration-attention helper uses only the pre-claim `DeliveryPortfolioSnapshot` runtime set and the existing live workspace-context read for superseded status. The runtime snapshot cache refresh happens before claim activation; parsed observations remain available only for occupancy and are not forced through the portfolio-snapshot shape.

Candidate selection uses the same local runtime and reconciliation-error snapshots but remains stricter: active-claim and reconciliation-error Changes are excluded. Occupancy is never calculated from the candidate-filtered set. If a retained active-claims read fails, existing propagation/reconciliation behavior remains unchanged. Fresh malformed or unreadable frontier state remains the existing startup-validation boundary. No fallback cache, quarantine, reservation, or new acquisition-result model is introduced.

The private attention helper preserves the public operation's filters for absent attention, retryable dispositions, existing Integration repair claims, and superseded attention; the superseded check remains a live workspace-context read. A focused test instruments a post-claim `_reconcile_runtimes()` call and requires that call to remain unused while verifying the pre-claim attention result. The public `list_integration_attention()` retains its existing reconciling behavior for other callers. The existing unconditional `available` decrement after every `_activate_candidate()` attempt remains because a runtime claim persists before coordinator custody can fail and stays occupied until exact recovery.

## Coordinator And Configuration

Remove the global writer-ledger path: `PortfolioCoordinator` no longer accepts `capacity`, and `_capacity`, `_ledger_path`, `_initialize_ledger()`, `writer_capacity_available()`, and ledger participants in `_acquire()`/`release()` are deleted. Keep state-root creation, startup `RuntimeTransaction.recover_all(state_root)`, `ChangeCoordination.writer`, `ChangeWriter` identity checks, publication locks, OCC, and exact recovery. A writerless release becomes idempotent even with inert residue; exact writer-identity conflicts remain.

Keep `CapacityLedger` as the strict historical payload model with `schema_version: Literal[1] = 1`, required positive `capacity`, default `change_ids: tuple[ChangeId, ...] = ()`, and sorted unique/holder-count validation. Update its docstring to identify historical migration input and retain its package export for legacy migration compatibility. Delete `CapacityLedgerConflictError` and `CapacityConfigurationConflictError`, their package-root exports, loader handlers, and global-capacity wording in coordinator/conflict/acquire/release docstrings.

Expose `recover_transactions()` on the coordinator and use it from acquisition. Both ordinary composition and remote bootstrap use `PortfolioCoordinator(paths.runtime_root)` with no capacity argument; remove the now-unused `host_config` parameter from `_bootstrap_remote_state()`.

`DeliveryHostConfig` keeps schema `1`, strict extra-key rejection, read-only loading, positive `execution_capacity`, and default `3`. A stale positive or zero `writer_capacity` field produces `extra_forbidden` at field `writer_capacity` and is not discarded or rewritten. Preserve the tracked `DeliveryStartupConfig` unknown-`execution_capacity` test because it covers another model.

## Retirement And Historical Compatibility

Remove current-runtime `capacity.json` reads from Integration retirement quiescence and cleanup postconditions. Coordination writers/publication leases, frontier active claims/recovery attention/Integration attention, pending transactions, and worktree state remain authoritative. Current residue is inert. Legacy migration retains the strict `CapacityLedger` parser, active-holder quiescence, copy, and staging validation unchanged; migrated current roots may contain inert residue. Current documentation explains that the retained `CapacityLedger` export exists for this legacy target-root migration path only.

Fresh startup continues to reject malformed or unreadable frontier state through `require_startup_contracts()`. Post-construction reconciliation retains existing behavior; this Change does not add malformed-frontier repair.

## Tests And Maintained Surfaces

The single outcome includes both loader construction sites; `portfolio_application.py`; `change_workspace.py`; `owlbear_delivery/__init__.py`; `serve/tools/src/owlbear_tools/delivery_integration_retirement.py`; retirement tests; all direct coordinator callers in `test_change_publication.py`, `test_change_workspace.py`, `test_delivery_runtime.py`, `test_delivery_state.py`, `test_portfolio_application.py`, and `serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py`; `serve/delivery-mcp/tests/test_target_server.py`; current Delivery and MCP READMEs; `setup/operating-owlbear.md`; and `.owlbear/py-index.md`. `setup/init.py`, its retired-line matcher, and `tests/test_setup_init_settings.py`/`tests/test_setup_init_uninstall.py` remain unchanged.

Keep loader-level default and positive/zero stale-host `extra_forbidden` proof in `serve/delivery/tests/test_portfolio_application.py`; add MCP-lifespan startup and stale-host diagnostic surfacing proof to `serve/delivery-mcp/tests/test_target_server.py`; preserve its existing `DeliveryStartupConfig` unknown-`execution_capacity` case. Replace global-ledger initialization, race, conflict, and writer-capacity skip assertions; retain exact per-Change custody/recovery tests. Add proof for lock-before-reconciliation with two subprocesses, parsed-frontier occupancy when composition fails, retained readable claims with reconciliation errors, maximum-per-Change counting, no current-ledger creation/read, inert residue, current retirement without the ledger, pending transaction recovery, multiple Builders, and pre-claim attention derivation.

The subprocess test constructs the reader before a new claim-establishing Change is persisted, coordinates the second process at `claims/acquisition-lock`, then verifies the second process observes the Change after lock entry. The test is bounded to that interleaving, not universal fuzz coverage.

## Documentation And Generated Navigation

Update current Delivery and Delivery MCP READMEs and `setup/operating-owlbear.md` to describe `execution_capacity=3` as the global budget for Planner and Builder outcome claims, no active `writer_capacity`, per-Change writer custody, current-runtime `capacity.json` as non-authoritative residue, stale-host edit/delete remediation, and the legacy-only purpose of the retained `CapacityLedger` export. Update the `.owlbear/delivery/config.json` row, the Delivery expected-outcome sentence, and the snapshot statement in `setup/operating-owlbear.md`.

Regenerate `.owlbear/py-index.md` after source removal. The deleted conflict symbols, `writer_capacity_available`, and obsolete `capacity` constructor parameter must disappear; `CapacityLedger` and its migration references remain expected generated entries because the definition and historical consumer remain.

## Risks And Limits

The acquisition lock spans recovery, discovery, reconciliation, candidate preparation, and per-Change publication locking, so head-of-line blocking may increase. The lock ordering remains acquisition -> recovery -> publication -> runtime transaction with no reverse path. A concurrent worker completion may conservatively overcount; no new claim can be created outside the lock. The global bound is claimed for claim-establishing parsed frontiers and readable retained runtime claims; malformed post-construction frontier recovery remains outside scope. Removing the global ledger removes its divergence deadlock and optional Builder throttle. Default `3` is user policy, not host-performance evidence. Integration repair claims remain outside this Change.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-confirmed concurrency policy and current acquisition behavior
statement: Delivery uses execution_capacity as the only global concurrency limit for acquired Planner and Builder outcome claims, with a default of 3, and never applies a separate writer_capacity admission limit.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: current per-Change coordination and recovery source
statement: Removing the global writer ledger preserves one-active-claim-per-Change selection, exact ChangeCoordination.writer custody, writer identity validation, publication locking, and clean, dirty, mismatched, and idempotent Build recovery; current-runtime ledger residue is not ownership authority.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: current shared application entry points and filesystem acquisition lock
statement: When multiple Delivery applications share one runtime root, acquisition recovers pending transactions through the coordinator, reconciles persisted membership before counting active claims, and serializes Planner and Builder outcome-claim creation under acquisition_lock for claim-establishing persisted state.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: current retirement and legacy migration source
statement: Current Integration retirement uses coordination, frontier, recovery-attention, and transaction state rather than current capacity.json, while legacy migration's active-holder and staged-ledger fail-closed behavior remains unchanged.
```

```yaml target-contract
kind: commitment
id: COM-005
class: important-reviewed
provenance: strict host loader and explicit migration boundary
statement: The active host configuration contains execution_capacity only with default 3; stale writer_capacity input produces a typed strict-validation diagnostic and is never silently rewritten or enforced.
```

```yaml target-contract
kind: commitment
id: COM-006
class: agreed-path
provenance: current package documentation, E2E fixture, tests, setup operating documentation, and generated index surfaces
statement: Delivery core, MCP startup and error proof, E2E seed data, current documentation describing the Planner and Builder outcome budget and legacy-only CapacityLedger export, all direct coordinator callers, focused regression tests, setup operating documentation, and generated Python indexes describe the execution-only capacity contract while legacy target-root ignore, cleanup data, retired-line matching, and setup-initializer tests remain unchanged.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Lock-consistent execution-only runtime
promise: Shared Delivery applications observe one bounded execution frontier for claim-establishing Planner and Builder outcome claims, one active claim per Change, no Builder-only global gate, exact per-Change Build custody, and current retirement independent of a writer ledger.
acceptance:
  - Given a PortfolioApplication initialized before a new claim-establishing Change is persisted, acquisition enters acquisition_lock before recovery, discovery, reconciliation, occupancy, selection, and claim creation, then observes the new Change and its active claims before selecting work.
  - Given two real concurrent applications sharing one runtime and execution_capacity 3, the deterministic subprocess-barrier scenario proves persisted active Planner/Builder outcome claims never exceed 3 for the constructed claim-establishing interleaving.
  - Given a parsed frontier whose runtime cannot compose, its active outcome claims consume occupancy; given a readable retained runtime with a reconciliation error, its active claims consume occupancy; candidate selection excludes those Changes and occupancy uses the maximum per Change.
  - Given eligible Planning and Implementation Changes with an available execution slot and unrelated active Build custody, acquisition admits the Builder instead of applying a writer-capacity filter, and multiple Builders on distinct Changes acquire and release independently.
  - Given one Change with an active claim and free execution slots, a second claim for that Change is not admitted.
  - Given a coordinator constructed without a current capacity.json, Build acquisition and release use only exact per-Change writer custody, and inert current-ledger residue cannot affect them.
  - Given current runtime state without current capacity.json, Integration retirement uses authoritative coordination/frontier/recovery/transaction checks and does not require the ledger.
  - Given a pending runtime transaction manifest, the coordinator-owned recovery operation completes it before raw acquisition discovery.
  - Given an instrumented acquisition in which a post-claim reconciliation would produce a different Integration-attention snapshot, acquire_frontier_work returns the pre-claim attention and the spy records no _reconcile_runtimes call after claim activation; the private helper consumes the pre-claim runtime snapshot set, preserves the runtime snapshot cache refresh, and performs the live superseded check.
  - Given fresh malformed or unreadable frontier state, existing loader validation rejects startup as before; post-construction read-side reconciliation retains its existing behavior.
  - Given an absent host.json, execution_capacity defaults to 3; given positive or zero stale writer_capacity input, strict Pydantic validation reports extra_forbidden at writer_capacity.
  - Given current documentation, MCP startup/error tests, the E2E seed, and generated navigation are rebuilt, focused source and test inspection shows both Delivery READMEs and the three named operating-guide statements describe the Planner and Builder outcome budget, no active writer_capacity, and the legacy-only CapacityLedger export; MCP lifespan startup leaves no current-runtime capacity.json and stale host.json surfaces the field-aware writer_capacity error; the seed omits writer_capacity; setup/init.py, its retired-line matcher, and its two named tests retain their existing retired-line behavior; and the Python index omits deleted conflict symbols while retaining CapacityLedger and its migration references.
  - Given the strict historical CapacityLedger model and legacy migration fixtures, schema/default/holder validation and fail-closed staging behavior remain unchanged.
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005, COM-006]
dependencies: []
```