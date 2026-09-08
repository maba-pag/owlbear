# Frontier Serialization Contract

> Status: candidate Design authority; formal gates pending
> Issue: #215 — Restore the strict Delivery frontier JSON round-trip contract
> Evidence: `.owlbear/research/frontier-serialization-contract-baseline.md`

## Problem And Product Promise

Delivery has a canonical frontier JSON parser, but typed consumers in startup loading, portable-state projection, portfolio admission response, and remote snapshot reading still select permissive parsing directly. The audit reported one 35-failure family under Pydantic 2.13.5: runtime 8, portfolio 13, Delivery state 13, and checkpoint regression 1. The current runtime-file suite passes 62 tests only after several direct strict reads changed to `strict=False`, so that green result is not independent proof of a repaired contract.

The Product Promise is one explicit, tested frontier serialization contract. Standalone and frontier-bearing typed Delivery consumers use the canonical JSON boundary while preserving model validation, runtime-relative validation, raw-byte drift detection, snapshot identity, quarantine behavior, frozen state, extra-field rejection, and recovery evidence. This is a verification and boundary-consistency Change, not a runtime-outage claim.

## Normal Workflow

A typed frontier is serialized by the canonical writer. Standalone readers use `parse_delivery_frontier()`. Frontier-bearing remote snapshots use an owning snapshot parser that delegates the embedded frontier to that function before envelope construction. A `DeliveryRuntime` read additionally applies `_validate_frontier()` for contract-relative bindings and lifecycle consistency.

## Scope

- Reconcile the audit failure family and current test history in `.owlbear/research/frontier-serialization-contract-baseline.md`.
- Keep one canonical JSON-boundary parser for standalone `DeliveryFrontier` data.
- Route `delivery_application_loader.py`, `portfolio_application.py`, and `_portable_frontier()` through it.
- Add `parse_delivery_state_snapshot()` and route `read_snapshots()`, `read_snapshot_inventory()`, and `_read_snapshot()` through it.
- Validate missing and non-object embedded `frontier` values through errors that remain contained by snapshot inventory quarantine.
- Preserve original raw bytes from `_read_local_snapshot_frontier()` for byte-for-byte remote drift comparison after canonical validation succeeds.
- Restore affected runtime, portfolio, Delivery-state, and checkpoint-regression tests to the canonical boundary; retain direct rejection tests at their owning model or runtime layer.
- Preserve `DeliveryRuntime._validate_frontier()` as the owner of contract-relative validation.

## Accepted Exclusions

- No global relaxation of strict validation or changes to unrelated Delivery models.
- `serve/tools/src/owlbear_tools/delivery_config.py` remains a shallow target-branch blocker scan, not typed authority.
- No movement of runtime-relative validation into the parser.
- No Pydantic-regression or production-outage claim.
- No remote Git, retry-policy, schema, or persisted-representation change.

## Preserved Behavior

Frontier and snapshot schema versions, frozen models, in-model semantics, runtime-relative checks, timezone requirements, receipt checks, OCC, transaction recovery, raw-byte drift detection, snapshot identity, and inventory quarantine remain effective. Quarantine retains code family `snapshot-invalid | snapshot-identity-invalid` and bounded non-sensitive detail; nested errors may gain a `frontier.` location prefix, while bare parser errors use the existing generic fallback.

## Decisions

- User-confirmed: canonical frontier parsing uses JSON-boundary mode; `strict=False` is confined to the JSON-to-model boundary.
- User-confirmed: remote-state snapshots are included through an owning wrapper that replaces the raw embedded frontier with its canonical parsed model representation before envelope construction.
- Source-confirmed: `_validate_frontier()` remains the separate runtime-relative validation owner.
- Source-confirmed: loader must return original raw bytes after validation so noncanonical local bytes cannot compare equal to a canonical remote snapshot.
- Source-confirmed: `_read_local_snapshot_frontier()` must catch `TypeError` together with `OSError` and `ValueError`, preserving the existing `_bootstrap_failure` route for non-object local frontier JSON.
- Evidence-confirmed: audit and current locks pin Pydantic 2.13.5; post-baseline tests relaxed direct reads, explaining why current green output is not independent repair proof.
- Rejected: strict Python normalization, persisted representation migration, and excluding nested snapshots.

## Success

Typed frontier readers use the canonical parser or owning wrapper; raw-byte drift checks remain byte-exact; parser/model, runtime-relative, and snapshot failures remain at their owners; equivalent snapshot models preserve `snapshot_id`; malformed snapshots remain quarantined with the documented code family and bounded diagnostics; loader type failures retain the established bootstrap error boundary; affected suites prove parser ownership; and the reconciliation artifact records evidence and limits.

## Technically Done But Wrong

Broad permissive parsing; moving runtime checks into the parser; canonicalizing loader return bytes; allowing absent/non-object embedded frontiers to escape inventory quarantine; allowing non-object local frontier JSON to escape `_bootstrap_failure`; changing snapshot IDs or quarantine code families; forcing the tools scan through domain parsing; preserving relaxed tests as proof; or changing persisted schema.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: issue acceptance, current source, and user-confirmed parser decisions
statement: Delivery frontier JSON has one documented JSON-boundary round-trip path whose typed consumers preserve in-model semantics, frozen-state, schema, receipt, timezone, and extra-field validation, while DeliveryRuntime retains contract-relative validation.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: source inventory and user-confirmed snapshot decision
statement: Typed Delivery consumers use parse_delivery_frontier or an owning frontier-bearing wrapper; unrelated models and the shallow tools blocker scan remain unchanged.
```

```yaml target-contract
kind: commitment
id: COM-003
class: important-reviewed
provenance: audit comparison, maintained recovery tests, and durable reconciliation research
statement: Runtime, portfolio, Delivery-state, checkpoint-regression, bootstrap, and restartable-snapshot proof covers the canonical parser contract, with historical reconciliation recorded in `.owlbear/research/frontier-serialization-contract-baseline.md`.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: snapshot identity and diagnostics source
statement: Equivalent snapshot models preserve snapshot_id; malformed snapshots preserve quarantine code family and bounded non-sensitive detail, permitting a frontier location prefix or generic fallback.
```

```yaml target-contract
kind: commitment
id: COM-005
class: protected-request
provenance: startup reconciliation byte-comparison source
statement: "`_read_local_snapshot_frontier()` validates with the canonical parser but returns original raw bytes so noncanonical local bytes still fail byte-for-byte remote snapshot comparison; it catches `TypeError` together with `OSError` and `ValueError`, preserving the existing `_bootstrap_failure` route for non-object local frontier JSON."
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Canonical Delivery frontier round trip
promise: Delivery frontier state is written, read, and validated through one JSON-boundary contract without weakening safeguards, moving runtime-relative checks, or allowing consumer-specific typed parsing.
dependencies: []
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005]
acceptance:
  - "Given model-produced frontier JSON, `parse_delivery_frontier()` returns a semantically equivalent `DeliveryFrontier` and canonical bytes."
  - "Given malformed model data, the parser rejects at the model layer; given contract-relative mismatch through `DeliveryRuntime`, `_validate_frontier()` rejects at the runtime layer."
  - "Given a frontier-bearing `DeliveryStateSnapshot`, its wrapper validates and canonicalizes the embedded frontier before envelope construction; absent or non-object frontiers remain quarantined; equivalent models preserve `snapshot_id`; quarantine retains its code family and bounded detail."
  - "Given local snapshot frontier bytes, loader validation uses the canonical parser but returns the original bytes; `_read_local_snapshot_frontier()` catches `TypeError` together with `OSError` and `ValueError`, mapping non-object local frontier to `_bootstrap_failure`, so raw-byte drift and type failures remain detectable."
  - "Given the typed source inventory, loader, `_portable_frontier()`, portfolio, and three snapshot readers use the canonical parser or wrapper; the shallow tools scan remains unchanged."
  - "Given `test_remote_state_bootstrap_reconstructs_fresh_clone` and `test_target_sync_state_snapshot_is_restartable_after_branch_publication`, both pass while preserving frontier equivalence and recovery behavior."
  - "Given `.owlbear/research/frontier-serialization-contract-baseline.md`, it records lock parity, the 35-failure family, test relaxation, rerun evidence, and evidence limits without broad suppression."
```
