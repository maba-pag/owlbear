# Target Cutover Integrity Repair - 2026-08-02

## Scope

This bundle preserves evidence removed from active or receipt-bound paths while repairing target
cutover receipt `dd07d374140348cdbf97c665aae76b5c1234976f28e0b85d4e3df83d88c7ac7b`.

## Preserved Evidence

- `drifted/`: 16 post-publication file versions that no longer matched the cutover manifests:
  14 delivery plans, `job-sequence.yaml`, and `jobs/116.yaml`.
- `reappeared-sources/changes/`: 75 files recreated after cutover under the retired bootstrap source
  path.
- `reappeared-sources/kanban/`: 233 files recreated after cutover under the retired bootstrap source
  path. The latest attempt events were 58 succeeded, 27 released, and one failed; no jobs, requests,
  or nonterminal attempts remained.
- `context/`: the cutover request, receipt, and both original snapshot manifests.

## Repair

The 16 receipt-bound files were restored byte-for-byte from copies whose SHA-256 values matched the
original manifests. The recreated source directories were moved here intact so the receipt-required
source paths are absent. No file under `.owlbear/target/` was replaced or removed.

After repair:

- both snapshot manifest digests matched the cutover receipt;
- target mutation authorization succeeded;
- completed-cutover replay returned `replayed=True`;
- the live MCP exposed the completed `target-runtime-canary` change;
- the affected regression suite reported 71 passing tests.
