# Delivery Claim Timeout And Recovery Plan

> **Owning task:** none - Delivery engine reliability investigation
> **Date:** 2026-08-27
> **Question:** Why do canonical Delivery claims remain active indefinitely, and how should the 30-minute recovery timeout be configured for a single-user laptop installation?
> **Status:** Implemented. The timeout is configurable through trackable host-local `host.json`; the observed stale claim was recovered through the exact Delivery operation.

## 1. Context And Question

The reported claim was persisted in the frontier for
[`delivery-capacity-consolidation`](../delivery/runtime/changes/delivery-capacity-consolidation/frontier.json)
with `started_at: 2026-08-23T11:41:50Z`, and matching Builder writer custody in
[`claims/changes/delivery-capacity-consolidation.json`](../delivery/runtime/claims/changes/delivery-capacity-consolidation.json).
The managed worktree was clean at the reviewed commit, so the exact claim recovery preserved the
reviewed commit, released writer custody, and left the worktree unchanged.

The canonical claim already persists `started_at`. The missing behavior was a comparison between that
timestamp and the current clock during acquisition. The local runtime settings file is
`.owlbear/delivery/runtime/host.json`; `capacity.json` is generated writer-ledger state and must not
be repurposed as configuration.

Goals:

- Recover canonical Planner and Builder Outcome claims that are at least 30 minutes old at the next
  explicit acquisition call.
- Allow the timeout to be overridden per local runtime through positive integer
  `claim_timeout_seconds`, defaulting to `1800`.
- Preserve the existing exact workspace recovery behavior for clean, dirty, and mismatched Builders.
- Keep the change small enough for the single-user laptop topology.

Non-goals:

- No rename of `capacity.json`; it remains derived writer custody state.
- No persisted `lease_expires_at` field, frontier schema migration, heartbeat, process-liveness probe,
  background scheduler, or distributed lease service.
- No automatic Integration-repair recovery, MCP/Cockpit response change, or unconditional worktree
  reset.

## 2. Sources Studied

| Source | Load-bearing fact | Evidence limit |
| --- | --- | --- |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | `PortfolioApplication` owns the application clock, acquisition lock, timeout policy, and workspace-aware exact recovery. | The module does not own host-file parsing. |
| [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py) | `DeliveryHostConfig` is strict schema-1 host-local configuration; it is composed into `PortfolioApplicationConfig`. | Loader tests establish startup behavior; they do not measure real task duration. |
| [`delivery_runtime.py`](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | `DeliveryActiveClaim` persists `started_at`; active claims remain canonical frontier occupancy until explicitly removed. | Runtime has no clock-based claim expiry itself. |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | `ChangeWriter`, `recovery_snapshot()`, and `restart()` protect exact Builder custody and preserve recoverable work. | Git/worktree safety is sampled and remains a bounded local risk during hard timeout recovery. |
| [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py) | Existing tests preserve fresh active claims and dirty Builder custody; new tests cover the inclusive timeout and clean/dirty recovery paths. | Tests use controlled clocks and temporary repositories. |
| [`serve/delivery/README.md`](../../serve/delivery/README.md) | `host.json` is seeded trackable host-local configuration; `capacity.json` is generated writer-ledger state. | Package documentation is not runtime proof. |
| [`serve/delivery-mcp/README.md`](../../serve/delivery-mcp/README.md) | The same host-local file is used by canonical MCP startup and the generated capacity file is not editable configuration. | Does not define the core application object. |
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
timeout comparison, so an abandoned session could permanently consume execution and writer capacity.

`0d10eb230` previously added a 30-minute TTL recovery method and an age-blind acquisition recovery
pass. `ca2f3aea2` removed the age-blind pass; `b81fdd5c7` later removed the TTL method and tests.
Their commit bodies are empty, so the reason cannot be stated more strongly than the observed
behavioral reversal. The implemented fix restores only the age-gated behavior and delegates to the
current exact recovery path.

### 3.3 Configuration placement

`.owlbear/delivery/config.json` is tracked project policy shared by the workspace. The ignored
`.owlbear/delivery/runtime/host.json` already owns host-local capacity overrides and is the correct
place for a per-machine timeout. `capacity.json` is rewritten transactionally when writer custody
changes; adding policy there would mix mutable ledger state with user settings and could make a
configuration edit look like a custody mutation.

The setting is an integer number of seconds rather than a JSON `timedelta` encoding:

```json
{"schema_version": 1, "claim_timeout_seconds": 1800}
```

The field is optional, strictly positive, and backward-compatible with existing `host.json` files.
The application converts it once to a `timedelta`; the recovery predicate remains inclusive at the
configured boundary.

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
| Rename `capacity.json` into a mixed settings/ledger file | Reject | Combines configuration with generated custody state and risks ambiguous writes. |
| Persisted absolute timeout in `host.json`, recovered at next acquisition | **Selected** | Small, backward-compatible, directly satisfies the requested 30 minutes, and reuses current recovery. |
| Heartbeat/inactivity lease | Defer | Requires a new operation and cadence; no evidence yet that normal work exceeds the configured limit. |
| Background scheduler | Reject for now | Overbuilt for a library with explicit user/orchestrator acquisition calls. |

## 4. Recommendation And Limits

Keep the implementation in the existing Delivery application boundary:

- `DeliveryHostConfig` reads `claim_timeout_seconds` from trackable `host.json`, default `1800`.
- `PortfolioApplicationConfig` carries the validated value and `PortfolioApplication` converts it to
  one `timedelta`.
- Acquisition compares fresh active-claim `started_at` values against one clock reading under the
  existing acquisition lock.
- Clean Planning and Builder claims use existing exact recovery. Dirty or mismatched Builders retain
  claim/custody and recovery attention.
- `capacity.json` remains generated state, and existing explicit recovery remains available.

Confidence is high for the configuration placement and implementation boundary. Confidence is medium
for the hard-timeout policy because no task-duration measurement exists; the 30-minute requirement is
the user's policy input. Revisit heartbeat only after observing legitimate work exceed the configured
limit.

## 5. Implementation Record

### Step 1 - Configurable local timeout

Implemented in [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py)
and [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py):

- Added positive integer `claim_timeout_seconds` to both configuration layers.
- Preserved default `1800` seconds.
- Passed the host-local value into the application and replaced the hardcoded recovery duration.
- Kept schema version `1`; existing host files without the field continue to load.

### Step 2 - Recovery and configuration proof

Implemented in [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py):

- Default timeout remains 30 minutes.
- Host-local five-second configuration is loaded and reaches the application.
- Zero and string timeout values fail strict startup validation before ledger mutation.
- Existing inclusive timeout, clean Builder, dirty Builder, and cross-instance recovery behavior remains
  covered.

### Step 3 - Operator documentation

Updated [`serve/delivery/README.md`](../../serve/delivery/README.md) and
[`serve/delivery-mcp/README.md`](../../serve/delivery-mcp/README.md) with the host-local setting and
the generated-state boundary.

### Step 4 - Optional worker hygiene

The existing Builder procedure already requires scoped commit and clean exact proof. A separate future
agent-config change may add startup inspection of branch, HEAD, status, diff, and writer custody. It
must never prescribe unconditional `git reset --hard` or adoption of ambiguous work.

## 6. Acceptance Scenarios

| ID | Scenario | Expected result |
| --- | --- | --- |
| AC1 | No `host.json` timeout override | Application uses `1800` seconds. |
| AC2 | `host.json` contains `claim_timeout_seconds: 5` | Application uses a five-second timeout. |
| AC3 | Claim age is below the configured boundary | Claim and custody remain unchanged. |
| AC4 | Claim age equals the configured boundary | Exact recovery is attempted. |
| AC5 | Expired clean Builder claim | Existing restart/release path preserves the reviewed boundary and releases custody. |
| AC6 | Expired dirty or mismatched Builder claim | Bytes, claim, and custody remain; recovery attention is retained. |
| AC7 | Existing `capacity.json` | It remains generated writer-ledger state and is not used for timeout configuration. |

## 7. Validation Commands

```text
uv run pytest serve/delivery/tests/test_portfolio_application.py -q --tb=short
uv run pytest serve/delivery/tests/test_delivery_runtime.py serve/delivery/tests/test_work_items.py -q --tb=short
uv run test serve/delivery
```

Run the package test boundary after related Delivery changes. No MCP/Cockpit or npm validation is
needed for this setting-only change because no public response contract changed.

## 8. Follow-Up And Limits

- Add heartbeat/inactivity renewal only if legitimate work exceeds the configured timeout.
- Add per-operation stale-worker fencing only if post-recovery stale writes are observed.
- Add a scheduler only if exact wall-clock cleanup without a user or orchestrator call becomes a
  requirement.
- Revisit Integration-repair expiry only when current code produces or depends on those claims.

The final conclusion is intentionally small: `host.json` is the right local override location,
`capacity.json` should not be renamed, and the configurable timeout now controls the existing
age-gated recovery path without adding a new persistence or service layer.
