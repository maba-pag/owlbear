# Delivery Capacity Consolidation

## Problem And Product Promise

Delivery currently has two global limits for acquired work: `execution_capacity` for Planner and Builder outcome claims, and `writer_capacity` for Builder writer reservations in `capacity.json`. The global writer ledger duplicates the authoritative per-Change writer record and can retain stale residue that blocks otherwise-free work. It is not the source of per-Change ownership.

The product promise is a single clear global budget: `execution_capacity` is the only global limit for acquired Planner and Builder outcome claims and defaults to `3`. Each Change still admits at most one active outcome claim, and each Build still retains exact per-Change writer custody and recovery. Cockpit and delivery-MCP may share one workspace runtime, so shared-root acquisition must reconcile persisted membership under the existing cross-process acquisition lock.

## Normal Workflow

1. Delivery loads optional host configuration and uses `execution_capacity=3` when `host.json` is absent.
2. A stale host file containing `writer_capacity` is rejected by strict Pydantic validation; startup does not rewrite it.
3. Normal `PortfolioCoordinator` construction no longer creates, reads, or writes current-runtime `capacity.json`; existing files are inert residue. The strict `CapacityLedger` model remains historical migration input only.
4. Acquisition enters the shared lock before coordinator-owned recovery, persisted discovery, runtime reconciliation, occupancy calculation, candidate selection, and claim creation.
5. Occupancy combines parsed persisted frontier claims with readable retained-runtime claims by Change, while candidate selection separately excludes active or reconciliation-error Changes.
6. An eligible Builder uses an execution slot and exact per-Change writer custody; unrelated Builders are not filtered by a global writer-only budget.
7. Existing startup validation and post-construction reconciliation retain their malformed-frontier behavior; this Change adds no quarantine, reservation, or new acquisition-result model.

## In Scope

- Move acquisition-specific recovery, discovery, reconciliation, occupancy, candidate selection, and claim preparation under the cross-process acquisition lock.
- Add a coordinator-owned transaction-recovery operation for raw discovery while preserving constructor startup recovery.
- Count parsed frontier claims even when runtime composition fails, and combine them with readable retained-runtime claims by maximum per Change without double-counting.
- Default `DeliveryHostConfig.execution_capacity` to `3` and remove `writer_capacity` from active host configuration and coordinator composition.
- Remove global writer-ledger initialization, admission, availability checks, and Build acquire/release ledger mutation while preserving per-Change writer custody.
- Remove the global Builder-only admission filter.
- Derive Integration attention from the acquisition snapshot before claim preparation while retaining the public reconciling operation.
- Remove current-runtime ledger reads from Integration retirement while retaining authoritative coordination, frontier, recovery, and transaction checks.
- Keep the strict `CapacityLedger` model as historical migration input with existing schema, defaults, and holder validation; remove only obsolete global capacity-conflict exceptions.
- Update all direct coordinator callers, focused tests, the E2E seed, current Delivery and MCP documentation, the setup operating guide's three current capacity statements, and generated Python navigation.

## Out Of Scope And Preserved Remainder

Do not add a renamed Builder capacity, host resource detection, an execution ledger, malformed-frontier quarantine, host-file rewrite/schema migration, Integration-repair accounting, or legacy target-root migration redesign. Preserve the legacy ignore paths, retired-line matcher, cleanup fixtures, `setup/init.py`, and its setup-initializer tests. Do not alter Cockpit controls, the MCP tool inventory, provider behavior, target branch behavior, or completed history.

Preserve one active outcome claim per Change, exact writer identity validation, per-Change locks, managed worktree recovery, runtime transaction recovery, strict unknown-field diagnostics, legacy migration checks, and non-capacity Delivery contracts. Existing current-runtime `capacity.json` files may remain inert residue and are not authority.

## Confirmed Decisions

- `execution_capacity` is the sole global concurrency limit for acquired Planner and Builder outcome claims and defaults to `3`.
- Shared-root acquisition enters `acquisition_lock` before coordinator recovery, discovery, reconciliation, occupancy, selection, and claim creation.
- Occupancy combines parsed frontier claims and readable retained-runtime claims by per-Change maximum; candidate filtering remains separate.
- `writer_capacity` and normal current-runtime `capacity.json` behavior are removed; per-Change writer custody remains.
- Current retirement no longer requires current-runtime `capacity.json`; legacy migration retains strict historical checks.
- Strict schema-1 host loading remains read-only; stale `writer_capacity` is rejected by field-aware Pydantic validation.
- The setup initializer's retired-line matcher, legacy ignore data, and setup-initializer tests remain unchanged because that surface is cleanup history rather than emitted current-runtime documentation.
- One implementation outcome contains runtime/source, retirement, historical compatibility, all callers/tests, E2E, current docs, MCP startup/error proof, and generated navigation.

## Success

With no host file, Delivery uses `execution_capacity=3`. Across claim-establishing state, acquisition admits no more than three active Planner/Builder outcome claims, admits eligible Builders regardless of unrelated Build custody, and never admits two claims for one Change. Two applications sharing one runtime serialize recovery, discovery, reconciliation, occupancy, and claim creation, including a Change persisted after one application was constructed. Parsed frontier claims remain counted when runtime composition fails, retained readable claims remain counted once when reconciliation records an error, and candidates still exclude errored Changes. Current runtime creates no `capacity.json`; retirement uses authoritative state; legacy migration remains strict; current docs/indexes describe the execution-only contract.

## Technically Done But Wrong

Normal current-runtime Delivery paths creating or consulting `capacity.json`; retaining a global Builder gate; deleting per-Change writer custody; permitting two claims per Change; counting from a pre-lock map; dropping parsed claims when composition fails; double-counting sources; silently accepting stale `writer_capacity`; rewriting `host.json`; weakening legacy migration; changing setup cleanup paths, retired-line matching, or cleanup fixtures; or claiming malformed-frontier quarantine or Integration-repair accounting was implemented.

## Evidence And Assumptions

Current source shows acquisition reconciliation before `acquisition_lock`, occupancy from `self._runtimes`, a Builder-only writer filter, and one production outcome-claim creation path. `PortfolioCoordinator` persists `CapacityLedger` with per-Change coordination, and retirement reads the ledger in two places. Cockpit and delivery-MCP resolve the same workspace-root convention. Legacy migration reads and stages the strict ledger from the retired target-runtime root.

The user confirms the policy reversal and default `3`. Focused review confirms the lock topology, coordinator recovery seam, per-Change custody, parsed-frontier occupancy, MCP test boundary, and setup legacy boundaries. Durable research remains supporting evidence for the authored Design; executable authority is limited to the verified intent/design package and derived contract. The implementation does not claim malformed-frontier repair, host migration, legacy cleanup, Integration-repair accounting, or host resource policy.
