# Frontier Serialization Contract Design

> Status: candidate architecture; formal gates pending
> Issue: #215
> Governing research: `.owlbear/research/frontier-serialization-contract-baseline.md`

## Current Ownership

`delivery_runtime.py` owns `DeliveryFrontier`, canonical bytes, `parse_delivery_frontier()`, and `DeliveryRuntime._validate_frontier()`. The parser owns JSON shape, schema version, model validation, and canonicalization. `_validate_frontier()` separately owns contract-relative bindings and lifecycle consistency.

`delivery_application_loader.py`, `_portable_frontier()` in `delivery_state.py`, and `portfolio_application.py` are typed standalone frontier consumers. `delivery_state.py` owns `DeliveryStateSnapshot` and its three remote readers. Existing runtime, admission, discovery, history, portfolio, and work-item paths already use the canonical parser.

`serve/tools/src/owlbear_tools/delivery_config.py` remains a shallow marker-based blocker scan outside typed authority parsing.

## Architecture

Keep `parse_delivery_frontier()` as the single standalone typed JSON boundary. Its `strict=False` handles JSON arrays and datetime strings; strict/frozen/extra-forbid model configuration and in-model validators remain active. Parser-only consumers do not gain runtime-relative validation.

Add `parse_delivery_state_snapshot(content)` in `delivery_state.py`:

1. Decode the outer JSON object.
2. Require an embedded `frontier` object; absent or non-object values raise `TypeError` or `ValueError` that the snapshot wrapper maps into the error family already handled by inventory quarantine.
3. Canonicalize and validate that payload with `parse_delivery_frontier()`.
4. Replace the raw payload with the canonical frontier model representation.
5. Construct `DeliveryStateSnapshot`, retaining metadata, authority, lifecycle, timezone, identity, and digest validation.

The wrapper preserves `snapshot_id` for equivalent models. Inventory errors remain `snapshot-invalid` or `snapshot-identity-invalid`, with bounded non-sensitive detail. Nested errors may gain a `frontier.` prefix; bare parser errors use the generic fallback.

Route loader, `_portable_frontier()`, and portfolio through the canonical parser. `_read_local_snapshot_frontier()` validates through that parser but returns original input bytes; it catches `TypeError` together with its current `OSError` and `ValueError` handling so non-object local JSON still maps to `_bootstrap_failure`. Route all three snapshot readers through the wrapper. Add inventory proof covering direct calls and frontier-bearing models, with the tools scan as a negative control.

## Failure Ownership

- Parser/model layer: malformed JSON object, schema version, field shape, extra fields, timezone, and in-model semantics.
- Runtime layer: contract-relative binding and lifecycle consistency through `_validate_frontier()`.
- Snapshot layer: envelope authority, lifecycle, identity, digest, and quarantine mapping.
- Loader reconciliation: original-byte comparison after validation, with `TypeError | OSError | ValueError` mapped to `_bootstrap_failure`.

## Alternatives

- **Selected:** preserve representation and unify typed parser ownership while retaining raw-byte comparison.
- **Rejected:** canonicalize loader return bytes; this weakens drift detection.
- **Rejected:** silently accept missing/malformed embedded frontiers; this breaks quarantine isolation.
- **Rejected:** force shallow tooling through typed parsing.
- **Rejected:** strict Python normalization or persisted representation migration.
- **Rejected:** exclude snapshot envelopes.

## Migration And Compatibility

No persisted migration. Typed consumers change parser call paths only. Snapshot IDs, canonical bytes, OCC, transaction recovery, raw-byte comparison, and quarantine code families remain compatible. Diagnostic detail remains bounded and non-sensitive but may gain a location prefix or generic fallback. Runtime-relative checks remain at `_validate_frontier()`.

## Proof Boundary

Proof crosses real runtime frontier bytes, startup raw-byte reconciliation, and remote snapshot reads. Tests cover canonical round trip; malformed, extra, timezone-naive, and runtime-relative failures; absent/non-object nested frontier; loader `TypeError` mapping; raw-byte mismatch; snapshot digest; quarantine code/detail; pending checkpoints; publication history; source inventory; and the four affected suites. `test_remote_state_bootstrap_reconstructs_fresh_clone` and `test_target_sync_state_snapshot_is_restartable_after_branch_publication` provide assembled recovery proof. `.owlbear/research/frontier-serialization-contract-baseline.md` owns historical reconciliation evidence.

## Known Limits

- Parser-only consumers do not gain runtime-relative checks.
- Raw validation exception shapes may change only through owning bounded mappings.
- Green suites require source-inventory proof to establish parser ownership.
- Remote Git, retry budgets, outage remediation, and new receipts remain outside scope.
