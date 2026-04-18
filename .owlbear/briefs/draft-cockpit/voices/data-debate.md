# Critic Debate Log — The Modeler

**Panel:** cockpit ideation | **Panelist:** ideation-data
**Critic model:** GPT-5.4 (copilot) | **Cycles:** 3

---

## Cycle 1

### Critic Challenges

1. **Critical — TaskSummary can't support running-state derivation.** Position says poll via `list_tasks()` but running-state needs `claimed_by`, `claimed_at`, `updated` — all dropped by `TaskSummary`. Internal mismatch between polling model (§1) and state model (§4).

2. **Critical — Whole-record clobber understated.** "All six mutations safe for optimistic UI" and "last os.replace() wins" understates the hazard. Engine mutators read the entire Task, modify a subset, write the entire record. Concurrent writes to DIFFERENT fields on the same task still clobber each other.

3. **Critical — Body reconciliation impossible via list_tasks.** "Server state always wins on next poll" but `list_tasks` doesn't return body or `updated`. Can't reconcile the most collision-prone edit paths (body, YAML fields) via the board poll.

4. **Moderate — "Changed externally" notification is unresolved policy.** Position proposes it then concedes it "may fall under the user's rejection." Not a settled integrity position.

5. **Critical — Collision probability claim is weak.** "Low in v1 due to status-based workflow separation" doesn't hold. Humans edit body/tags/priority on tasks agents also touch. Whole-record semantics make any concurrent same-task access destructive.

6. **Moderate — Config changes not covered by directory mtime.** `config.yml` changes (statuses, priorities, claim_timeout) don't update tasks directory mtime. Cockpit could serve stale config while the task-directory mtime stays unchanged.

7. **Moderate — claimed_at=None + claimed_by≠None treatment.** Treating as "stuck" may conflict with engine dispatch semantics that treat missing claimed_at as an active claim.

8. **Moderate — list_tasks silently swallows malformed tasks.** A corrupt task file disappears from the board with no alarm. Diff shows "task removed" when the reality is "task corrupt."

**Blind spots identified:** Concurrent cockpit requests (two browser tabs) not addressed. Data-shape problems conflated with timing problems.

### Modeler Response

- **Accepted #1:** Split polling into board poll (`list_tasks`) + claim enrichment (`show_task` for claimed tasks). Added post-mutation `show_task` confirmation for body/YAML edits.
- **Accepted #2:** Requalified "safe for optimistic UI" — acknowledged whole-record clobber explicitly.
- **Accepted #3:** Post-mutation confirmation via `show_task` for detail-level edits. Board poll handles card-level only.
- **Accepted #4:** Reframed as "recommend surfacing to user as explicit risk-acceptance item."
- **Accepted #5:** Revised probability assessment upward. Documented that status separation is weak mitigation.
- **Accepted #6:** Added `config.yml` mtime to the stat check set. Full config refresh on change.
- **Partially accepted #7:** Changed to "anomalous" rather than "stuck." Surface to user.
- **Accepted #8:** Weakened claim — track known IDs, flag disappearances, but acknowledge this is informational only.
- **Accepted blind spot:** Added per-task `asyncio.Lock` for intra-cockpit write serialisation.

---

## Cycle 2

### Critic Challenges

1. **Critical — O6 "without silent data loss" contradicts accepted silent clobber.** Position accepts the silent-overwrite scenario as documented risk, but O6 explicitly says "without silent data loss." Post-mutation `show_task` confirmation cannot detect that a concurrent writer's changes to OTHER fields were destroyed.

2. **Moderate — Claim enrichment cache has no reliable invalidation.** Proposed cache refreshes when `claimed` boolean flips or on periodic cadence. But ownership can transfer while `claimed` stays true (agent A expires, agent B claims). Cache misses ownership changes.

3. **Moderate — Config handling is narrower than cockpit depends on.** Position only ties config mtime refresh to `claim_timeout`. Cockpit also needs config for column ordering, priority ordering, and valid transitions.

4. **Moderate — "Task disappeared without archiving" can't be proven.** `list_tasks` can't distinguish malformed, deleted, or archived. The heuristic overclaims.

**Blind spots identified:** Unclaim (`release_task`) inherits the same stale-write race — can wipe a fresh claim from stale UI. Other anomalous claim states not covered (claimed_at present with no owner, unparsable timestamps). Config writes may not be atomic.

### Modeler Response

- **Accepted #1:** Identified this as a requirements tension. O6 "without silent data loss" is incompatible with rejecting per-task conflict detection when the engine does whole-record writes. Framed as user must explicitly choose scope-narrowing (a) or lightweight check (b).
- **Accepted #2:** Changed to always refresh claim enrichment every cycle (not just on boolean flip).
- **Accepted #3:** Broadened config refresh to cover columns, priorities, valid_transitions, and claim_timeout. Full board layout rebuild on config change.
- **Accepted #4:** Weakened to "informational signal, not reliable detection."
- **Accepted blind spot (unclaim race):** Added pre-release safety check — re-read task before `release_task()`, warn if claim freshened.
- **Accepted blind spot (anomalies):** Added three anomalous states to running-state derivation.
- **Accepted blind spot (config writes):** Added defensive YAML parse error handling for config reads.

---

## Cycle 3

### Critic Challenges

1. **Critical — Pre-release safety check has TOCTOU race.** Between the cockpit's re-read and the engine's `release_task()` call, another process could claim the task. The engine's release path has no compare-and-release guard — it reads, clears, writes unconditionally.

2. **Critical — Post-mutation show_task cannot detect silent clobber.** If cockpit and agent both write from the same base snapshot touching different fields, the later writer's `show_task` confirms its own fields but the earlier writer's changes are gone. Confirmation proves write success, not absence of data loss.

3. **Moderate — Claim enrichment polling cost is unbounded.** `show_task()` reads full task (including body) for each claimed task, every 3 s. No bound given on claimed-task count or body size against the 200-task bar.

**Blind spots identified:** Partial poll failure (board succeeds, claim enrichment or config fails) not mapped to traffic-light states. MCP server health indicator (per O3) not addressed in polling model.

### Modeler Response

- **Accepted #1 (with qualification):** Acknowledged TOCTOU race. Pre-read narrows window from seconds to milliseconds but cannot eliminate it. Full elimination requires engine-level CAS (out of scope). Documented as known limitation.
- **Accepted #2:** Acknowledged explicitly — post-mutation confirmation catches engine errors but cannot detect silent field clobber. This feeds back into the §3 requirements tension.
- **Accepted #3:** Bounded the cost — claimed tasks in practice ≈ 5–20, bounded by concurrent agent activity not total task count. ~20–40 ms additional disk I/O per cycle.
- **Accepted blind spot (partial failure):** Config parse failure → yellow traffic light + hold previous config. Claim enrichment failure → yellow for affected tasks.
- **Noted blind spot (MCP health):** MCP servers are stdio processes managed by VS Code. The cockpit doesn't connect to them directly — it imports the engine. MCP server health monitoring requires infrastructure beyond the current engine surface. This is a design question for the architect, not a data-integrity concern.

---

## Convergence Assessment

After 3 cycles, the Critic's challenges shifted from structural flaws to fundamental limitations of the engine's concurrency model (no per-task locks, whole-record writes, no CAS). These are genuine but not fixable at the cockpit layer without engine changes that are out of v1 scope. The position now accurately describes what the cockpit CAN and CANNOT guarantee, and surfaces the requirements tension for user resolution.

**Final confidence:** 0.78 — technically sound, three unresolved tensions escalated to user.
