# Data Integrity Stance — The Modeler

**Panel:** cockpit ideation | **Panelist:** ideation-data (The Modeler)
**Scope:** Polling, optimistic UI, staleness, running-state derivation, write ordering, risk
**Critic cycles:** 3 (GPT-5.4) | **Confidence:** 0.78

---

## 1. Polling / Staleness Model

**The `revision` counter is per-instance and useless for cross-process change detection.** Each `KanbanEngine` instance initialises `_revision = 0` and increments only on its own writes. The cockpit process and MCP agent processes each have isolated instances. Polling the cockpit's own revision tells it nothing about agent activity.

**Required approach — two-tier polling at 3 s:**

| Tier | Source | Data | Purpose |
|------|--------|------|---------|
| Board poll | `list_tasks()` | status, priority, blocked, `claimed` bool | Card-level diff, column layout |
| Claim enrichment | `show_task()` per claimed task | `claimed_by`, `claimed_at` | Running-state derivation (§4) |
| Config watch | `stat()` on `config.yml` | mtime | Detect column/priority/timeout changes |

- **Fast-path skip:** `stat()` both the tasks directory mtime and `config.yml` mtime before full re-read. If both unchanged, skip the cycle. Directory mtime is reliable because the engine writes via `os.replace()` which modifies directory entries.
- **Claim enrichment runs every cycle** for all tasks where `claimed == True`. Ownership can transfer while the boolean stays true (agent A expires, agent B claims), so flipping `claimed` is not a reliable invalidation signal.
- **Config refresh:** When `config.yml` mtime changes, call `refresh_config()` to reload columns, priorities, `valid_transitions`, and `claim_timeout`. This triggers a full board layout rebuild. If config YAML fails to parse (mid-write by another process), catch the error, hold previous config, retry next cycle, and map to **yellow** traffic light.
- **Post-mutation confirmation:** After body or YAML field edits, call `show_task()` on the mutated task. Board poll handles card-level reconciliation; `show_task` handles detail-level confirmation.
- **Cost bound:** Claimed task count is bounded by concurrent agent activity (~5–20 in practice), not total task count. At 200 total tasks with 20 claimed, enrichment adds ~20–40 ms of local disk reads per cycle.

## 2. Optimistic UI + Rollback

**Qualified safety.** All six v1 mutations (move, reprioritise, block/unblock, unclaim, edit body, edit allowlisted YAML) can use optimistic UI — the cockpit updates immediately and reconciles on the next poll.

**However:** the engine does whole-record read-modify-write. Two concurrent writes to the *same task* clobber ALL fields — even if they touch different fields. A cockpit user editing tags while an agent appends to body = one write is silently lost.

**Reconciliation rules:**

| Mutation type | Reconciliation source | Mechanism |
|--------------|----------------------|-----------|
| Card-level (move, reprioritise, block/unblock, unclaim) | Board poll | Server state wins. If poll shows unexpected status/priority/blocked/claimed, revert card and notify inline. |
| Detail-level (body, YAML fields) | Post-mutation `show_task()` | Confirms the cockpit's own fields landed. **Cannot** detect silent clobber of other fields by concurrent writers. |

**Skip window:** Suppress the first poll within 500 ms of a local mutation to prevent echo-clobber (poll sees pre-mutation state before the write completes). The next poll after the skip window is the reconciliation checkpoint.

**Pre-release safety check:** Before calling `release_task()`, the cockpit re-reads the task. If the claim is now fresh (different agent or refreshed `claimed_at` since the UI rendered "stuck"), warn the user before proceeding. This is a destructive-action safety check per O6, not per-task conflict detection. **Acknowledged TOCTOU race:** a claim can land between the re-read and the release call. The pre-read narrows the window from seconds to milliseconds but does not eliminate it. Full elimination requires engine-level compare-and-swap, which is out of scope.

## 3. Stale-View Handling

**Traffic light is necessary but has a known blind spot.** The scenario:

1. User opens task editor (green light — fresh poll)
2. Agent writes to the same task's body or other fields
3. User saves → agent's changes silently overwritten (whole-record write semantics)

**Requirements tension — needs explicit user resolution:**

| Constraint | Source | Implication |
|-----------|--------|-------------|
| "Errors surface inline without silent data loss" | O6 | Silent data loss from concurrent writes violates this |
| User rejected per-task conflict detection | O6 | The mechanism that would prevent silent data loss is excluded |
| Engine does whole-record read-modify-write | Engine code | Concurrent same-task writes are inherently destructive |

**The cockpit cannot satisfy all three simultaneously.** The user must choose:

- **(a) Narrow O6's scope:** "Without silent data loss" refers to engine errors (write failures, validation rejects), not concurrent-write races. Traffic light is sufficient. The race risk is accepted and documented.
- **(b) Lightweight pre-write check:** The cockpit adapter compares the task's `updated` timestamp at write time against the value it read when the editor opened. If mismatched, surface a warning (not a block). This is a single-field comparison, not full conflict detection.

**Additional data-quality signal:** If a known task ID disappears from `list_tasks()` without a preceding archive move, the cockpit should log this for diagnostics. However, `list_tasks()` silently swallows malformed task files (`ValueError`/`KeyError`), so absence alone cannot distinguish corruption from archival from deletion. This is an informational signal, not a reliable detection mechanism.

## 4. Running-State Derivation

Classification from `claimed_by`, `claimed_at`, `claim_timeout` (all from `show_task()` enrichment):

| State | Condition |
|-------|-----------|
| **Free** | `claimed_by is None` |
| **Running** | `claimed_by` set, `claimed_at` set, `now < parse(claimed_at) + claim_timeout` |
| **Stuck** | `claimed_by` set, `claimed_at` set, `now ≥ parse(claimed_at) + claim_timeout` |
| **Anomalous** | `claimed_by` set but `claimed_at` missing; or `claimed_by` missing but `claimed_at` present; or `claimed_at` unparsable |

- `claim_timeout` is **global** (from `BoardConfig`), not per-task. Refreshed when `config.yml` mtime changes.
- **Clock skew:** negligible — cockpit and agents run on the same laptop using system UTC.
- **Freshness:** every poll cycle (3 s). Sufficient — claim timeouts are measured in hours/minutes.
- **Anomalous states** must be surfaced to the user, not silently classified. They indicate data corruption or an engine bug.

## 5. Write Ordering / Atomicity

**Engine-level guarantees:**
- Atomic writes (`tempfile` + `os.replace()`) prevent **torn files** (no half-written YAML).
- No per-task file locking for edits → **lost updates** on concurrent same-task writes. These are different guarantees; the team must not conflate them.

**Cockpit HTTP layer:**
- Serialize writes per-task within the cockpit process (per-task `asyncio.Lock` keyed by task ID). Prevents intra-cockpit races (two browser tabs, rapid double-clicks).
- Cross-process races (cockpit vs. agent MCP) remain unguarded. Same lost-update semantics as §3 — accepted per user's decision on conflict detection.

**Config write hazard:** `config.yml` writes may not use atomic replacement (unlike task files). A poller reading config mid-write could observe partial YAML. The cockpit must catch parse errors on config reads and retry next cycle (see §1).

## 6. Highest-Risk Data Assumptions

### Risk #1 — Revision counter as cross-process signal (FACTUALLY WRONG)
Research notes state: "Polling the `revision` counter @ 3 s satisfies the staleness budget." The counter is per-instance (`_revision = 0` on init, incremented only by the instance's own writes). If the cockpit backend polls its own revision, **100% of external agent writes are invisible.**

**Validation:** First integration test: (a) agent writes a task via MCP in a separate process, (b) cockpit detects the change within one poll cycle. This test fails immediately if polling uses the revision counter.

### Risk #2 — Atomic writes ≠ lost-update prevention
The team must understand: `os.replace()` prevents half-written files. It does NOT prevent one writer's changes from being silently overwritten by another writer who read the file before the first write landed.

### Risk #3 — Requirements tension (unresolved)
O6's "without silent data loss" is incompatible with rejecting all write-time checks when the engine does whole-record read-modify-write. This must be resolved by the user before implementation; see §3 for the two options.

---

## Warnings

1. **Do not build polling on the revision counter.** Use filesystem re-reads with mtime fast-path.
2. **Do not assume atomic writes prevent data loss.** They prevent data corruption. Different problem.
3. **Resolve the O6 tension before building the editor save path.** Silent overwrites will happen; the question is whether the cockpit is allowed to let them happen silently.
4. **Unclaim has a TOCTOU race** that narrows but doesn't close. Document this in the cockpit's safety model.
5. **`TaskSummary` lacks claim detail fields.** The activity panel cannot be built on `list_tasks()` alone — it requires `show_task()` enrichment for all claimed tasks.
