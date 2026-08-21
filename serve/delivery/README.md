# owlbear-delivery

`owlbear-delivery` is the transport-free control plane for Change delivery. It projects semantic work
items from admitted Design authority, owns deterministic Planning and Build transitions, coordinates
bounded execution and writer capacity, publishes reviewed Change checkpoints, observes user-owned
pull-request acceptance, and projects recoverable completed history. It retains legacy Target cutover
and evidence contracts for historical consumers; canonical Change delivery does not use them.

**Use this guide when:** you need to extend or integrate the core Change authority, understand its
worktree and publication boundaries, or call its public stores and runtimes.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Embedded callers use its public stores, runtimes, and
`PortfolioApplication`; agent clients use the `owlbear-delivery-mcp` adapter documented in
[serve/delivery-mcp/README.md](../delivery-mcp/README.md). The adapter is the public tool and startup
configuration reference.

The main public areas are:

| Area | Contracts |
| --- | --- |
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

The package reads no environment variables. Canonical MCP and Cockpit startup uses the tracked
project policy and optional host-local runtime settings below. Embedded callers may provide the
same typed configuration directly.

| File | Optional? | Fields and defaults | Ownership |
| --- | --- | --- | --- |
| `.owlbear/delivery/config.json` | Required for canonical MCP/Cockpit startup | `schema_version` must be `2`; `remote`, `target_branch`, and `github_repository` are required and have no loader defaults. `setup/init.py` defaults `remote` to `origin`, uses `main` as the non-interactive target-branch fallback, suggests the current branch interactively, and infers `github_repository` from the configured remote. | Tracked project policy |
| `.owlbear/delivery/runtime/host.json` | Optional and ignored | When absent, `writer_capacity` and `execution_capacity` both default to `1`. When present, `schema_version` must be `1`; both capacities must be positive integers. Unknown keys and non-integer values are rejected at startup. | Host-local configuration |
| `.owlbear/delivery/runtime/capacity.json` | Generated; do not edit | `schema_version` is `1`; `capacity` is the effective `writer_capacity`; `change_ids` lists active writer holders and defaults to an empty list. | Derived writer ledger |

The two host capacities control different limits. `execution_capacity` is the maximum number of
active Planner or Builder claims across the portfolio. `writer_capacity` is the maximum number of
concurrent Builder worktrees; a Builder needs both an execution slot and a writer slot. For example,
the optional host file can allow two writers and three total claims:

```json
{"schema_version": 1, "writer_capacity": 2, "execution_capacity": 3}
```

`setup/init.py` creates the tracked project policy but does not create `host.json`; the absence of
that file therefore preserves the defaults above.

## Dependencies

| Package | Purpose |
| --- | --- |
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public Delivery application, stores, and coordinators rather than
writing authority or runtime files directly.
