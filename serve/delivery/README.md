# owlbear-delivery

`owlbear-delivery` is the transport-free control plane for Change delivery. It projects semantic work
items from admitted Design authority, owns deterministic Planning and Build transitions, coordinates
bounded execution, publishes reviewed Change checkpoints, observes user-owned
pull-request acceptance, and projects recoverable completed history from current receipt-backed
runtime records. Completed history is informational and is not Delivery runtime authority.

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
| Work projection | Portfolio work items with dependency readiness, typed attention, requests, blocks, task progress, and bounded Delivery health diagnostics |
| Coordination | Per-Change writer custody under `runtime/coordination/changes`, one shared execution budget, warm worktrees, and reviewed source boundaries |
| Publication and acceptance | Change-branch checkpoints, draft pull-request reconciliation, review-repair preparation, finalization, acceptance observation, and publication supersession |
| Completed history | Receipt-backed completed Change projections plus read-only Git-backed historical package search |
| Integration attention | Typed Integration attention and exact repair-claim recovery remain current public operations |

Assembly is not a live Delivery stage or public Change authority. Historical runtime captures may
still contain reducible Assembly metadata, and legacy completed-history records retain their
historical schema for validation. New Changes use sequential Planning and Build outcomes directly.

## Admission And Portfolio Freshness

Persisted Delivery authority is held by the canonical `contract.json`, `admission.json`,
`frontier.json`, and coordination records under `.owlbear/delivery/runtime/changes/`. The
`PortfolioApplication` runtime map is process-local actionable membership, not a second authority.

Before portfolio reads and direct Change runtime lookups, `PortfolioApplication` reconciles
persisted Change discovery. It retains an unchanged runtime, composes a runtime for a newly
discovered or replaced contract when the persisted evidence is actionable, and removes runtime
membership when persisted authority is removed. Frontier access remains read-through. A read-side
reconciliation does not publish authority, allocate worktrees, or rewrite a valid frontier.

Startup reads remote snapshots and local Change entries independently. A malformed snapshot, identity
mismatch, missing per-Change authority file, or Change-specific coordination failure is quarantined
as bounded health attention; valid sibling Changes remain available. Quarantined Changes stay visible
in status and health projections when a last-known view exists, but they are excluded from work-item
queues, claims, acquisition, and dispatch. Use the read-only `delivery_health()` operation through
the MCP adapter, or the Cockpit Delivery health section, to inspect the source, code, Change ID, and
bounded detail. Workspace, Git, configuration, and unsupported persisted-state failures remain
startup-fatal.

The operating projection exposes explicit status axes instead of inferring lifecycle from runtime
map membership: `admission`, `stage`, `actionable_runtime`, `diagnostic_code`, and
`diagnostic_detail`. Its active status population is built from verified package IDs plus persisted
discovery observations, including admitted observations and the unadmitted entries needed to keep
genuine Design packages visible. Completed history remains a separate surface.

| Persisted state | Portfolio projection |
| --- | --- |
| Genuinely unadmitted package | `admission=unadmitted`, `stage=design`, and `actionable_runtime=false`; it is included in `draft_design_change_ids`. |
| Admitted Planning Change, including `tasks: []` | A normal Change group with Planning progress labeled `Task plan not published`; it is not a draft Design entry. |
| Admitted Change explicitly returned to Design | `admission=admitted` and `stage=design`; it is included in `design_required_change_ids`, not the draft list. |
| Admitted Change without an actionable runtime | Admission remains visible with `actionable_runtime=false` and the generic `runtime_unavailable` diagnostic; it is never recast as unadmitted Design. |

The Delivery MCP operation inventory includes the read-only `delivery_health` projection. Current
runtime readers accept only the current persisted schema; unsupported state is a startup failure and
requires a fresh current workspace. `delivery_health` reports remote evidence plus local
reconciliation; it does not mutate or repair persisted state. `list_work_items` remains a pure list
and does not become a health response.

Current per-Change custody records live under `.owlbear/delivery/runtime/coordination/changes/`.
The sibling `.owlbear/delivery/runtime/claims/` namespace is reserved for acquisition, publication,
verification locks, and the acceptance reconciler's host-local round-robin cursor is stored under
`claims/acceptance-reconciliation/cursor.json`; the cursor is scheduling state, not Delivery
authority, and a missing or invalid cursor safely starts a new rotation. Recoverable runtime
transaction manifests live under
`.owlbear/delivery/runtime/transactions/`.

## Configuration

The package reads no environment variables. Canonical MCP and Cockpit startup uses the tracked
project policy and optional host-local runtime settings below. Embedded callers may provide the
same typed configuration directly.

| File | Optional? | Fields and defaults | Ownership |
| --- | --- | --- | --- |
| `.owlbear/delivery/config.json` | Required for canonical MCP/Cockpit startup | `schema_version` must be `2`; `remote`, `target_branch`, and `github_repository` are required and have no loader defaults. `delivery_state_branch` defaults to `owlbear/delivery-state` and is written by setup. `setup/init.py` defaults `remote` to `origin`, uses `main` as the non-interactive target-branch fallback, suggests the current branch interactively, and infers `github_repository` from the configured remote. | Tracked project policy |
| `.owlbear/delivery/runtime/host.json` | Seeded and trackable | Shared baseline defaults: `execution_capacity` defaults to `3`, and `claim_timeout_seconds` defaults to `3600` (60 minutes). Setup preserves existing values on rerun. `schema_version` must be `1`; both values must be positive integers. | Tracked baseline configuration |
| `.owlbear/delivery/runtime/host.local.json` | Optional and ignored | Any subset of the three host settings may override the tracked baseline for one machine. The file may omit `schema_version`; supplied values must be positive integers, and unknown keys are rejected at startup. | Host-local override configuration |

`execution_capacity` is the maximum number of active Planner or Builder outcome claims across the
portfolio. Each acquired Change has exact per-Change writer custody; there is no separate global
`writer_capacity` admission limit. The tracked baseline allows three active claims:

```json
{"schema_version": 1, "execution_capacity": 3, "claim_timeout_seconds": 3600}
```

When upgrading an existing workspace, remove the obsolete `writer_capacity` field from
`.owlbear/delivery/runtime/host.json` and any `.owlbear/delivery/runtime/host.local.json` override
before starting Delivery. `setup/init.py` preserves an existing `host.json` on rerun, and startup
rejects the stale field instead of rewriting it. If no host-specific values are needed, recreate
`host.json` from the baseline above. Do not edit historical `capacity-ledger.json` data.

Put machine-specific execution or timeout changes in the ignored local overlay instead of editing the
tracked baseline:

```json
{"execution_capacity": 2, "claim_timeout_seconds": 1800}
```

An active Planner or Builder claim is eligible for recovery after the configured
`claim_timeout_seconds` (3600 seconds by default), measured from its persisted `started_at` value.
The loader merges `host.local.json` over `host.json` when the overlay exists. Recovery runs lazily at
the next `acquire_frontier_work()` call. Clean matching Builder custody is restarted and released
through the normal recovery path; dirty or mismatched worktrees remain retained with recovery
attention and continue to consume capacity.

`setup/init.py` creates the tracked project policy and seeds `host.json` with the defaults above. It
does not create `host.local.json`; create that ignored file only when this host needs overrides. The
loader still accepts an absent baseline or local file for older or manually managed workspaces.

### Portability And Recovery

Authored `intent.md` and `design.md` remain local drafts until admission. When a Change is admitted,
Delivery commits the verified `authority.json`, `design.md`, `intent.md`, and `manifest.json` to the
managed `owlbear/change/<change-id>` branch before opening its first draft pull request. Later Design
revisions are rejected for that Change; a semantic change starts a new or superseding Change.

Sparse semantic checkpoints are published to the configured `delivery_state_branch` at admission,
meaningful task or Outcome progress, finalization, and acceptance. They retain resumable authority
and terminal evidence, but never live claims, locks, capacity ledgers, process identifiers, or local
paths. A fresh clone can therefore recover the last published checkpoint and requeue incomplete work.
The local `refs/owlbear/packages/*` refs remain useful package history, but are not a remote backup.

If the remote package branch, state snapshot, contract, or local state disagree, startup reports
bounded Delivery attention and does not choose a side silently. Do not copy hidden `.git` refs or
ignored runtime files between machines; restore from the normal remote branches and the configured
state branch.

## Dependencies

| Package | Purpose |
| --- | --- |
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public Delivery application, stores, and coordinators rather than
writing authority or runtime files directly.
