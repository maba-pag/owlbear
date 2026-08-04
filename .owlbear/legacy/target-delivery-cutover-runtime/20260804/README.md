# Target Delivery Intermediate Runtime Archive - 2026-08-04

## Scope

This archive preserves the pre-cutover `target-delivery-cutover` runtime that was generated while
the legacy target adapter still owned execution. It was removed from the active target root after
the reviewed Delivery cutover landed.

## Source Paths

- `.owlbear/target/changes/target-delivery-cutover/`
- `.owlbear/target/target-runtime/coordination/target-delivery-cutover.json`

The cutover target manifest declares empty `authority_paths` and `runtime_paths`, so neither source
was bound by the target-cutover receipt.

## Reason

The runtime state uses intermediate fields removed by the reviewed Delivery contract, including
`parked_request_id`, `parked_candidate_commit`, `task_rulings`, and the retired planned-task status.
The integrated legacy `TargetRuntime` correctly rejects that state. Keeping it below the active
`.owlbear/target/changes/` namespace would present invalid runtime evidence as current authority.

## Preservation

- Runtime tree: 133 physical files, including one ignored `.storage.lock`; 132 Git-visible files.
- Aggregate digest: `88234eb2457993a8d9c56c74d5c591d2ba3f06da346d2398f953494ef6e93f41`.
- The stale per-change coordination record is preserved alongside the runtime tree.

The aggregate digest is the SHA-256 of the sorted per-file SHA-256 values. Before and after the move,
physical file counts and this digest matched.

## Validation

After archival, target-cutover authorization succeeded, the old target registry contained only the
committed `target-runtime-canary`, and the live Delivery MCP assembled exactly 23 tools.
