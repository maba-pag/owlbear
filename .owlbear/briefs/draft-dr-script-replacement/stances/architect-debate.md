# Architect — Critic Debate Log

## Cycle 1

### Critic Challenges (severity: critical unless noted)

1. **Hidden contract break in pick_tasks.** pick_tasks is a four-step wave planner. Making it mutate files, append task bodies, and move files means parse/write failures become dispatch failures. Orchestration explicitly separates housekeeping from planning.

2. **Resolve algorithm under-specified.** Live contract is a state machine: approved/completed unblock and move; needs-info stays blocked and resets; rejected unblocks with different body text. Position 2 reduces this to "check response, write, move."

3. **Validation-thin create_dr removes structure the resolver depends on.** If body shape is opaque at creation, resolver can't validate that `response` matches an offered option. Existing archive has malformed records.

4. **Missing block policy.** Live policy: T3 decisions block, T2 are advisory. Dropping urgency/impact_tier removes the signal that controls blocking.

5. **Board endpoint staleness.** Frontend fetches `/api/board` once on mount, only polls `/api/tasks`. DR indicator in board response would go stale.

6. **Dual resolution authority.** Cockpit resolve endpoint vs. pick_tasks side-effect — unclear which is authoritative. Could produce duplicate mutations or UI that appears to act but doesn't.

7. **Isolation inconsistency (moderate).** Position 6 says decisions.py takes only `decisions_dir`, but Position 2 passes the full engine for resolution (block/unblock/append).

8. **Duplicate semantics (moderate).** Multiple DRs per task with different concerns is valid. Task_id-only check would suppress legitimate second DRs.

### Blind Spots Raised

- No migration/coexistence story for existing 35 resolved files
- No concurrency/stale-write model for Cockpit DR endpoint
- No cache invalidation for decision-file changes in Cockpit
- No clarity on block:user exemption interaction

### Architect Response

**Challenge 1 — Accepted with mitigation.** Outcome #3 is locked (pick_tasks auto-resolves). My revised position: wrap resolve in a fail-safe boundary. `_try_resolve_drs()` is called at the top of pick_tasks, catches all exceptions, logs warnings, and returns without poisoning the dispatch pipeline. Partial resolution (some files processed, one fails) is acceptable — retry next cycle. This is the "side-effect in a guard" pattern, not "mutation in the planner."

**Challenge 2 — Accepted, position refined.** The resolve function must implement a proper state machine:
- `response: approved` / `response: completed` → unblock task, append resolution to body, move to resolved/
- `response: needs-info` → keep blocked, keep in pending/, append clarification request to body
- `response: rejected` → unblock task, append rejection note to body, move to resolved/
- Missing/empty `response:` → skip (not yet responded)

This is still deterministic — the state machine is bounded and fully specified by the response field value.

**Challenge 3 — Partially accepted, mostly stood firm.** The body contains the decision options as prose. The resolver does NOT validate that the user's response matches an option heading — it never did reliably (scribe used LLM matching, which was the unreliable path). The new contract: `response:` is a free-text field filled by the user. If they write "approved" or "Option A" or anything else, it's recorded verbatim. Structural correctness is a user responsibility, not an engine concern. This is simpler and more robust than template validation.

**Challenge 4 — Stood firm.** Always-block is the correct simplification. An advisory DR that doesn't block the agent is functionally a comment — the agent proceeds, gets dispatched, works on the task, and the "decision" becomes a historical note nobody reads. If an agent genuinely needs a decision to proceed correctly, it must be blocked. If it doesn't need one, don't create a DR. The T2/advisory path was a complexity sink that added no value (agents continued working regardless). The new model: `create_dr` always blocks. Period.

**Challenge 5 — Accepted, position revised.** DR status gets its own lightweight polled endpoint: `GET /api/decisions/pending` returns count + summary. Frontend polls this on an interval (same as task polling). Not folded into `/api/board`.

**Challenge 6 — Accepted, clarified.** Resolution authority model:
- **Cockpit `POST /api/decisions/{id}/resolve`** is the primary user path. It does full immediate resolution: writes response to frontmatter, executes the state machine (unblock/append/move), returns success.
- **pick_tasks fallback** detects files where `response:` was filled via direct file edit (fallback path). It runs the same state machine. This is idempotent — if Cockpit already resolved, the file is in resolved/ and pick_tasks finds nothing.
- No dual-authority conflict: Cockpit is immediate, pick_tasks is a sweep for file-edit stragglers.

**Challenge 7 — Accepted, revised.** decisions.py takes `decisions_dir: Path` and an interface (protocol class or callback tuple) for engine side-effects: `block_task(task_id)`, `unblock_task(task_id)`, `append_to_body(task_id, text)`. Not the full engine. The engine passes itself (satisfying the protocol) but the module only sees the narrow interface. Testable with a mock.

**Challenge 8 — Noted but locked.** D8 is a locked decision: drop semantic matching, accept duplicates. The filename includes a slug derived from the body's first line, providing minimal disambiguation. Multiple DRs for the same task with different concerns will have different slugs and coexist. Task_id-only dedup check is dropped entirely — just allow creation freely.

### Blind Spot Responses

- **Migration:** Leave existing 35 resolved/ files as-is. Reader code handles both old (full frontmatter) and new (simplified) formats. No rewrite migration.
- **Concurrency:** Single-user laptop system. No OCC needed. Last-write-wins for file edits. Cockpit resolve is effectively single-threaded (one user).
- **Cache:** Decisions are outside the task cache. `GET /api/decisions/pending` reads directly from disk on each call (glob of a tiny directory). No cache layer needed.
- **block:user:** DR-created blocks use the standard `blocked: true` mechanism. `block:user` tag is for Cockpit-initiated manual blocks (unrelated to DRs). No interaction conflict.

### Revised Confidence

0.78 → proceeding to final stance.
