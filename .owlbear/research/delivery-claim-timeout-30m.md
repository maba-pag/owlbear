# Delivery Claim Timeout And Recovery Plan

> **Owning task:** none - Delivery engine reliability investigation
> **Date:** 2026-08-27
> **Question:** Why do canonical Delivery claims remain active indefinitely, and how should the local recovery timeout and Builder workspace reuse be configured for a single-user laptop installation?
> **Status:** Implemented. Tracked `host.json` supplies the baseline, ignored `host.local.json` supplies per-host overrides, and the default timeout is 60 minutes.

## 1. Context And Question

The reported claim was persisted in the frontier for
[`delivery-capacity-consolidation`](../delivery/runtime/changes/delivery-capacity-consolidation/frontier.json)
with `started_at: 2026-08-23T11:41:50Z`, and matching Builder writer custody in
[`coordination/changes/delivery-capacity-consolidation.json`](../delivery/runtime/coordination/changes/delivery-capacity-consolidation.json).
The managed worktree was clean at the reviewed commit, so exact recovery preserved the reviewed
commit, released writer custody, and left the worktree unchanged.

The canonical claim already persists `started_at`. The missing behavior was age comparison during
acquisition. The tracked baseline is `.owlbear/delivery/runtime/host.json`; the optional ignored
`.owlbear/delivery/runtime/host.local.json` contains per-host overrides.
`capacity-ledger.json` is generated capacity-ledger state and must not be repurposed as configuration.

Goals:

- Recover canonical Planner and Builder Outcome claims that are at least 60 minutes old by default at
  the next explicit acquisition call.
- Allow a host to override `claim_timeout_seconds` and capacity values without synchronizing those
  overrides through Git.
- Preserve the existing exact workspace recovery behavior for clean, dirty, and mismatched Builders.
- Report automatic recovery results so a clean Builder reset is visible to the caller.
- Keep the change small enough for the single-user laptop topology.

Non-goals:

- No `.local` rename of `capacity-ledger.json`; it remains derived writer custody state.
- No persisted `lease_expires_at` field, frontier schema migration, heartbeat, process-liveness probe,
  background scheduler, or distributed lease service.
- No automatic Integration-repair recovery, MCP/Cockpit expiry redesign, or broad worktree cleanup.
- Builder-owned triage may reuse compatible task work or discard clearly disposable, task-scoped
  artifacts with explicit paths; it must escalate ambiguous custody.

## 2. Sources Studied

| Source | Load-bearing fact | Evidence limit |
| --- | --- | --- |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | `PortfolioApplication` owns the application clock, acquisition lock, timeout policy, and workspace-aware exact recovery. | The module does not own host-file parsing. |
| [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py) | `DeliveryHostConfig` is strict schema-1 baseline configuration; an optional partial local model is merged over it and composed into `PortfolioApplicationConfig`. | Loader tests establish startup behavior; they do not measure real task duration. |
| [`delivery_runtime.py`](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | `DeliveryActiveClaim` persists `started_at`; active claims remain canonical frontier occupancy until explicitly removed. | Runtime has no clock-based claim expiry itself. |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | `ChangeWriter`, `recovery_snapshot()`, and `restart()` protect exact Builder custody and preserve recoverable work. | Git/worktree safety is sampled and remains a bounded local risk during hard timeout recovery. |
| [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py) | Tests cover default/override loading, strict local validation, inclusive timeout, clean Builder recovery, dirty Builder retention, and cross-instance preservation. | Tests use controlled clocks and temporary repositories. |
| [`serve/delivery/README.md`](../../serve/delivery/README.md) | Tracked `host.json` is the baseline, ignored `host.local.json` is the override, and `capacity-ledger.json` is generated capacity-ledger state. | Package documentation is not runtime proof. |
| [`serve/delivery-mcp/README.md`](../../serve/delivery-mcp/README.md) | Canonical MCP startup loads baseline plus local overrides; local settings are not synchronized through Git. | Does not define the core application object. |
| [`setup/init.py`](../../setup/init.py) and [`test_setup_init_settings.py`](../../tests/test_setup_init_settings.py) | Setup seeds the visible baseline, preserves local overrides on rerun, and migrates the ignore rule so only `host.json` is trackable in the runtime directory. | Setup tests use temporary consumer projects. |
| [`w-packet-building`](../../share/skills/w-packet-building/SKILL.md) | Worker guidance already requires scoped commits and clean exact proof; a commit alone does not release a claim. | Guidance cannot run after a crash or cancellation. |
| Git history: `0d10eb230`, `ca2f3aea2`, `b81fdd5c7` | Earlier code had 30-minute TTL recovery; age-blind acquisition recovery was removed first, then the TTL method. Removal commits have no explanatory body. | History establishes prior behavior, not a complete policy rationale. |
| Live runtime state, investigated 2026-08-27 | The stale Builder claim consumed writer capacity and was cleanly recoverable; exact recovery completed successfully. | Point-in-time operational evidence. |

No external source was needed.

## 3. Analysis

### 3.1 Current claim path

1. `_new_claim()` creates an active claim with `started_at`.
2. `DeliveryRuntime.activate_claim()` persists it in the frontier.
3. `acquire_frontier_work()` counts every active claim as occupied and `_candidates()` skips it.
4. Worker context and transition operations require exact claim identity, but not age.
5. Only successful transition or explicit `recover_claim()` removes the claim.

### 3.2 Root cause and history

The root cause was missing age-gated recovery. The timestamp was present, but acquisition had no
comparison, so an abandoned session could permanently consume execution and writer capacity.

`0d10eb230` previously added a 30-minute TTL recovery method and an age-blind acquisition recovery
pass. `ca2f3aea2` removed the age-blind pass; `b81fdd5c7` later removed the TTL method and tests.
Their commit bodies are empty, so the reason cannot be stated more strongly than the observed
behavioral reversal. The implemented fix restores only age-gated recovery and delegates to the
current exact recovery path.

### 3.3 Configuration placement

`.owlbear/delivery/config.json` is tracked project policy shared by the workspace. Tracked
`.owlbear/delivery/runtime/host.json` is the discoverable host baseline. Optional ignored
`.owlbear/delivery/runtime/host.local.json` is a partial overlay for one machine.
`capacity-ledger.json` is rewritten transactionally when writer custody changes and remains generated
state.

The baseline contains all supported settings:

```json
{
  "schema_version": 1,
  "writer_capacity": 1,
  "execution_capacity": 1,
  "claim_timeout_seconds": 3600
}
```

A machine that needs changes creates only the overrides it needs:

```json
{
  "claim_timeout_seconds": 1800,
  "execution_capacity": 2
}
```

The loader merges the local values over the baseline. The overlay may omit `schema_version`, but any
supplied schema version must be `1`; all supplied numeric values must be positive integers. Existing
files without the new field retain code defaults.

### 3.4 Real laptop risks

The stale-claim incident and global writer blockage are observed risks. Dirty or mismatched worktrees
are also a real data-loss boundary, and the existing recovery path retains them rather than resetting
them.

The hard-timeout tradeoff is explicit: if a second acquisition session starts after the configured
deadline, a clean Builder that is still running may be recovered and restarted. There is no OS process
identity or heartbeat today. That is acceptable for the requested single-user policy, but it is not a
claim that the engine can prove the owner is dead.

Distributed lease races, cross-host coordination, and a background scheduler are theoretical for this
topology and remain out of scope.

### 3.5 Alternatives

| Alternative | Decision | Reason |
| --- | --- | --- |
| Agent instructions only | Supporting follow-up | Helps normal completion but cannot run after crashes and does not release claims. |
| Put timeout in tracked `config.json` | Reject | Makes a host-local execution policy part of shared project authority. |
| Rename `capacity-ledger.json` into a mixed settings/ledger file | Reject | Combines configuration with generated custody state and risks ambiguous writes. |
| Tracked `host.json` baseline plus ignored partial `host.local.json` overlay | **Selected** | Discoverable defaults propagate to new checkouts while host-specific changes remain local. |
| Heartbeat/inactivity lease | Defer | Requires a new operation and cadence; no evidence yet that normal work exceeds the configured limit. |
| Background scheduler | Reject for now | Overbuilt for a library with explicit user/orchestrator acquisition calls. |

## 4. Recommendation And Limits

Keep the implementation in the existing Delivery application boundary:

- `DeliveryHostConfig` reads tracked `host.json`, then merges optional `host.local.json` values.
- The baseline default for `claim_timeout_seconds` is `3600` seconds (60 minutes).
- `PortfolioApplication` converts the merged value once to a `timedelta`.
- Acquisition compares fresh active-claim `started_at` values against one clock reading under the
  existing acquisition lock.
- Clean Planning and Builder claims use existing exact recovery. Dirty or mismatched Builders retain
  claim/custody and recovery attention.
- `capacity-ledger.json` remains generated state, and existing explicit recovery remains available.

Confidence is high for the configuration placement and implementation boundary. Confidence is medium
for the hard-timeout policy because no task-duration measurement exists; the 60-minute requirement is
the user's policy input. Revisit heartbeat only after observing legitimate work exceed the configured
limit.

## 5. Implementation Record

### Step 1 - Configurable local timeout

Implemented in [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py)
and [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py):

- Added positive integer `claim_timeout_seconds` to the tracked baseline and partial local overlay.
- Changed the default to `3600` seconds (60 minutes).
- Passed merged host-local values into the application and replaced the hardcoded recovery duration.
- Kept schema version `1`; existing host files without the field continue to load.

### Step 2 - Recovery, reporting, and configuration proof

Implemented in [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py):

- Default timeout is 60 minutes.
- Local five-second configuration overrides baseline capacity and timeout values.
- Zero, string, null schema, and unknown local values fail strict startup validation before ledger mutation.
- Automatic recovery results include exact claim identity, preserved commit, and preserved attempt ref
  when applicable.
- Recovery subprocess failures become bounded acquisition failures and do not prevent independent
  Changes from launching.
- Inclusive timeout, clean Builder, dirty Builder, committed Builder preservation, and cross-instance
  recovery behavior are covered by focused tests.

### Step 3 - Operator documentation and setup

Updated [`serve/delivery/README.md`](../../serve/delivery/README.md),
[`serve/delivery-mcp/README.md`](../../serve/delivery-mcp/README.md), and
[`setup/operating-owlbear.md`](../../setup/operating-owlbear.md). Setup seeds tracked baseline
`host.json`, preserves `host.local.json`, and keeps generated runtime state ignored.

### Step 4 - Builder workspace hygiene

Updated [`w-packet-building`](../../share/skills/w-packet-building/SKILL.md) so a Builder may inspect
and reuse compatible task-owned work, or discard clearly disposable task-owned artifacts with
explicit path-scoped Git commands. Foreign, ambiguous, or custody-mismatched state still routes to
exact recovery. The procedure never prescribes broad `git clean` or an unconditional reset.

The Builder has the tools needed for this decision: `show_build_context`, terminal inspection, read,
and edit access in the assigned managed worktree. A successful Builder result still requires a scoped
commit, exact proof, publication, and transition; a Git commit alone does not release claim or writer
custody. The Builder may reset only reviewed task-scoped artifacts after preserving relevant committed
state through the existing recovery convention. It must not reset another branch, clean broadly, or
adopt foreign or ambiguous changes.

## 6. Acceptance Scenarios

| ID | Scenario | Expected result |
| --- | --- | --- |
| AC1 | No `host.local.json` | Application uses tracked `3600`-second default. |
| AC2 | `host.local.json` contains `claim_timeout_seconds: 5` | Application uses a five-second timeout. |
| AC3 | Local overlay changes capacity values | Local values override baseline without changing generated ledger semantics. |
| AC4 | Claim age is below configured boundary | Claim and custody remain unchanged. |
| AC5 | Claim age equals configured boundary | Exact recovery is attempted. |
| AC6 | Expired clean Builder claim | Existing restart/release path preserves reviewed boundary, records the preserved attempt ref, reports the recovery, and releases custody. |
| AC7 | Expired dirty or mismatched Builder claim | Bytes, claim, and custody remain; recovery attention is retained. |
| AC8 | One recovery fails while another Change is independent | The failure is reported and the independent Change can launch. |
| AC9 | New checkout | Setup supplies visible tracked defaults; local overrides are not synchronized. |

## 7. Validation Commands

```text
uv run pytest serve/delivery/tests/test_portfolio_application.py -q --tb=short
uv run pytest tests/test_setup_init_settings.py tests/test_setup_init_scaffold.py tests/test_setup_init_uninstall.py -q --tb=short
uv run test serve/delivery
```

Run the package test boundary after related Delivery changes. The acquisition result now reports
automatic claim recoveries, so run the Delivery MCP contract tests when that public response changes;
no Cockpit or npm validation is needed because no Cockpit response or frontend contract changed.

## 8. Follow-Up And Limits

- Add heartbeat/inactivity renewal only if legitimate work exceeds the configured timeout.
- Add per-operation stale-worker fencing only if post-recovery stale writes are observed; current
  claim identity checks and frontier CAS remain sufficient for the observed workflow.
- Add a scheduler only if exact wall-clock cleanup without a user or orchestrator call becomes a
  requirement.
- Revisit Integration-repair expiry only when current code produces or depends on those claims.

The final conclusion is intentionally small: tracked `host.json` makes the baseline discoverable,
ignored partial `host.local.json` keeps host-specific overrides local, `capacity-ledger.json` remains
derived state, the configurable 60-minute default controls the existing age-gated recovery path, and
automatic recovery is reported without weakening dirty-worktree protection.
