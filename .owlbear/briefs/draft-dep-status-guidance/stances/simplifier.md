# Simplifier Stance — Dep-Status Guidance in start_work

## Verdict

The proposal is already small, but it smuggles in unnecessary resolution depth. Three cuts.

## Cut 1: Drop "redirect" from v1

"Redirect" means all deps are archived — the work is *done*, just not the way you hoped. The agent isn't about to collide with in-flight work. "Blocked" (deps still active) is the only dangerous state. Adding redirect doubles the message-formatting branches and forces a decision about what "redirect" guidance even says. Defer redirect to a follow-up if anyone ever asks for it.

**Impact:** Removes one trigger path, one message template, and the archival-reason classification from scope.

## Cut 2: Skip per-dep detail in the message

The context says "included if low-effort," but it isn't low-effort — it requires the same N+1 `show_task` loop that `show_task()` uses to build `active_ids` and `archived_reasons`. A flat message — *"This task has unresolved dependencies (IDs: 42, 78). Confirm intent before proceeding."* — is sufficient. The agent can call `show_task` on each dep itself if it needs detail. Per-dep status classification in the guidance string is gold-plating for a soft gate.

**Impact:** Eliminates the dep-iteration loop; `_compute_dep_status` alone gives the go/no-go signal.

## Cut 3: Reuse the `show_task` call already in `start_work`

`start_work` already calls `engine.show_task()` (line 986). Switch to `self.show_task(task_id)` (the agent_view method, which already computes `dep_status`). Read the status off the returned payload. No new dep-resolution code in `start_work` at all — just an `if dep_status == "blocked"` guard that appends one guidance string.

**Impact:** Change drops from ~15 LoC to ~5 LoC. Zero duplication of dep-resolution logic.

## Decomposition Pressure

If Cut 3 introduces unwanted coupling (e.g., `self.show_task` has side-effects you don't want in the claim path), extract the dep-resolution loop into a private helper called by both `show_task` and `start_work`. But do that *only* if reuse doesn't work — don't pre-extract.

## Confidence

**0.85** — all three cuts reduce scope without losing the safety signal. Cut 3 depends on whether `self.show_task()` is safe to call in the claim path (it should be — it's read-only), but verify before committing to it.
