# owlbear-delivery

`owlbear-delivery` is the transport-free control plane for Change delivery. It projects semantic work
items from admitted Design authority, owns deterministic Planning and Build transitions, coordinates
bounded execution and writer capacity, publishes reviewed Change checkpoints, observes user-owned
pull-request acceptance, and projects recoverable completed history. It retains legacy Target cutover
and evidence contracts for historical consumers; canonical Change delivery does not use them.

Parent project: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Embedded callers use its public stores, runtimes, and
`PortfolioApplication`; agent clients use the `owlbear-delivery-mcp` adapter documented in
[serve/delivery-mcp/README.md](../delivery-mcp/README.md). The adapter is the public tool and startup
configuration reference.

The main public areas are:

| Area | Contracts |
|------|-----------|
| Authored Specification | `DesignPackageStore` create, verified read, compare-and-swap revision, and checkpoint |
| Compilation and admission | Deterministic contract derivation, validation, package binding, and atomic runtime admission |
| Operational Delivery | `DeliveryRuntime` and `PortfolioApplication` outcome stages, frontier acquisition, typed role contexts, publication, worker transitions, requests, and exact-claim recovery |
| Work projection | Portfolio work items with dependency readiness, typed attention, requests, blocks, and task progress |
| Coordination | Per-change writers, separate execution/writer capacity, warm worktrees, and reviewed source boundaries |
| Publication and acceptance | Change-branch checkpoints, draft pull-request reconciliation, finalization, acceptance observation, and publication supersession |
| Completed history | Receipt-backed completed Change projections with bounded list, search, and exact lookup |
| Legacy compatibility | Typed Integration attention/recovery and `TargetRuntime` evidence remain public for historical consumers |

Assembly is not a live Delivery stage or public Change authority. Historical runtime captures may
still contain reducible Assembly metadata, and legacy completed-history records retain their
historical schema for validation. New Changes use sequential Planning and Build outcomes directly.

## Configuration

The package reads no environment variables. The canonical loader reads optional ignored host-local
capacity configuration from `.owlbear/delivery/runtime/host.json` (`writer_capacity` and
`execution_capacity`, both defaulting to `1`); it writes the derived writer ledger to
`capacity.json`. MCP and Cockpit load tracked project policy and compose owners over canonical
Delivery roots; setup seeds that policy but does not create host-local capacity configuration.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public Delivery application, stores, and coordinators rather than
writing authority or runtime files directly.
