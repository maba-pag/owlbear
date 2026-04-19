# End-User Critic Debate Log

## Round 1 — Initial Position

### Position Summary
9-tool surface: rename `show_task` → `get_task`, add `sections` param for body projection, `ids` on `list_tasks` for batch lookup, new `create_tasks`, `archival_reason` as free-form string on output shapes, transparent archived reads, `include_archived` boolean on `list_tasks`, override `archival_reason` on `end_work` success path.

### Critic Challenges (5 challenges, 3 blind spots)

1. **CRITICAL — `archival_reason` not typed as enum.** Surface exposes it as free-form string. Typos and synonyms become valid values, violating the "one-field lookup" contract. **Accepted.** Switched to enum-validated: `completed|deprecated|dropped|duplicate|wontfix`. ToolError on invalid values.

2. **CRITICAL — Silent section projection failure.** Missing sections are indistinguishable from "projection failed." Agents use sections for workflow decisions (doc-writer, auditor, architect). **Accepted.** Added `missing_sections: list[str]` on response — explicitly surfaces what was requested but not found.

3. **MODERATE — `list_tasks` contract incoherent.** Four overlapping modes: `ids`, `include_archived`, `status="archived"`, `archival_reason`. Undefined interactions (e.g., `status="todo"` + `include_archived=true`). **Accepted.** Dropped `include_archived`. Simplified to: default = non-archived; `status="archived"` = archived only; `ids` = direct lookup bypassing default exclusion. Defined complete interaction matrix.

4. **MODERATE — Rename rationale applied selectively.** `show_task` → `get_task` for "programmatic API" purity, but `ids` and `sections` use CLI-style comma-separated strings. Broad churn across agent files for naming purity. **Accepted.** Kept `show_task` — rename churn unjustified for marginal improvement.

5. **MODERATE — `end_work` blurs archive semantics.** `archival_reason` override on `outcome="success"` allows incoherent states like success+duplicate. Overlapping archive behavior with `move_task`. **Accepted.** Removed override from success path. Success at terminal always = `completed`. Non-completed archives use `move_task` or `end_work(outcome="reject", move_to="archived")`.

### Blind Spots Addressed
- `create_tasks` failure contract: added `{"failed_index": int, "reason": str}` on ToolError.
- `pick_tasks` return shape mismatch: aligned with orchestration skill docs.
- Section projection semantics: fully specified (matching, ordering, duplicates, missing).

**Critic confidence: 0.34 → Reject**

---

## Round 2 — Refined Position

### Key Refinements
- `end_work` reject path (`move_to="archived"`) handles non-completed archives atomically
- `create_tasks` batch supports intra-batch dependencies via `depends_on_batch: list[int]` (positional refs)
- `ids` lookup fully specified: missing IDs absent, requested order, deduplicated
- Identified scribe append+unblock as agent-skill bug (surface already supports it)

### Critic Challenges (5 challenges, 3 blind spots)

1. **CRITICAL — `deprecated` and `duplicate` lack successor reference.** Agent learns why the task died but not what replaced it. **Accepted.** Added `archival_ref: int | null` — successor/target task ID for deprecated/duplicate. Null for completed/dropped/wontfix.

2. **MODERATE — `archival_reason` mutability weakens audit trail.** Can be set during archive, rewritten after via `edit_task`. Downstream consumers can't treat as stable truth. **Partially accepted.** Kept editability (one-call correction > 2-call un-archive/re-archive), but acknowledged as a trade-off. Audit history is a Brief C (storage) concern.

3. **MODERATE — Silent-ignore semantics still present.** `ids` silently ignores other filters; `archival_reason` silently ignored on non-archive moves. **Accepted.** Adopted no-silent-ignore policy: params that don't apply are FORBIDDEN (ToolError). Eliminates all ambiguity.

4. **MODERATE — `create_tasks` three relationship encodings.** `depends_on` (string), `depends_on_batch` (positional), `parent` (ambiguous — existing ID or batch position?). **Accepted.** Clarified: `parent` = existing task ID only. No `parent_batch`. Rare intra-batch parent-child via follow-up `edit_task`.

5. **MINOR — `task_id` vs `id` inconsistency.** `pick_tasks` uses `task_id`, everything else uses `id`. **Accepted.** Switched to `id` throughout.

### Blind Spots Addressed
- Multi-task section projection acknowledged as follow-up, not in-scope.
- `archival_reason` presence rules: specified for active (null), newly archived (non-null, enforced), legacy (may be null, migration = Brief C).

**Critic confidence: 0.47 → Reconsider**

---

## Round 3 — Hardened Position

### Key Refinements
- `archival_ref` added to all output shapes
- No-silent-ignore policy applied everywhere
- `parent` in batch: existing-ID only
- Complete interaction matrices for all param combinations

### Critic Challenges (4 challenges, 2 blind spots)

1. **CRITICAL — `completed` label loses gating.** `move_task(status="archived", archival_reason="completed")` valid from ANY status. A research-status task can be archived as "completed." Breaks the semantic contract that completed = went through full pipeline. **Accepted.** Added: `archival_reason="completed"` only valid when task is currently in `done` status. ToolError otherwise.

2. **CRITICAL — Archived metadata mutable after terminal state.** `edit_task` on archived tasks allows rewriting reason/ref. Weakens audit trail. **Evaluated, kept with trade-off.** From End-User (agent) perspective: one-call correction (`edit_task`) is better UX than 2-call un-archive/re-archive cycle. Audit history tracking is a Brief C concern (storage can log field changes). The MCP surface optimizes for the caller, not the historian.

3. **CRITICAL — `archival_ref: int = 0` sentinel conflict.** Default 0 is ambiguous: "not provided" vs "explicitly set to 0." Conflicts with no-silent-ignore policy. Also: no validation that ref points to an existing task. **Accepted.** Switched to `archival_ref: str = ""` (string param, coerce to int server-side). Empty = not provided. Non-empty = must be valid existing task ID. Follows existing `depends_on` pattern.

4. **MODERATE — Multi-task section projection still absent.** Section-as-schema is the biggest context-window sink per the brief. Single-task projection helps but N+1 across tasks remains. **Acknowledged as follow-up.** Brief A scope is archive reads + archival reason + surface coherence. Multi-task section extraction is a separate design problem.

### Blind Spots Noted
- Completion confidence still body-only. Section projection on `show_task` gives agents `## Audit` extraction — sufficient for now.
- Session visibility: out of scope, listed as follow-up.

**Critic confidence: 0.46 → Reject** (slight regression from 0.47 — new challenges offset prior improvements)

---

## Round 4 — Final Hardening (internal refinement, no Critic invocation)

Applied Round 3 accepted changes:
- `completed` gated to `done` status
- `archival_ref` switched to `str = ""` with validation
- Existence validation on archival_ref

Position finalized for stance publication.
