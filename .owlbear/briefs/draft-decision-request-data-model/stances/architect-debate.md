# Architect Debate Log — Decision Request Data Model

## Cycle 1

### Draft Position Summary

- Split models from operations (`decision_models.py` + `decisions.py`)
- Strict downward dependency flow, models at bottom
- API: create/resolve/list/get returning full `DecisionRequest`
- Filename = `{request_id}.md` (UUID4)
- Inline resolution primary, sweep as degraded fallback
- Option IDs: agent-provided slug-safe strings
- Action resolution states: `completed`, `blocked`, `rejected`
- Phase mapping: Phase 1 = models + engine, Phase 2 = interfaces, Phase 3 = frontend

### Critic Challenges (Cycle 1)

**Critical:**

1. **Lifecycle boundary undefined.** Cockpit currently owns file-write semantics (rewrite frontmatter, stamp resolved_by, append summary, move file). Draft's "engine owns all writes" is aspirational without stating Cockpit stops mutating directly.

2. **Unified model permits illegal states.** `resolve_request(status: str, selected_option_id: str | None, free_text: str | None)` leaves all fields optional and untyped by kind. Can represent `kind=action` with `selected_option_id`, or `kind=decision` with `status=completed`.

3. **`blocked` collision.** Action resolution state `blocked` reuses the word reserved for task-level blocking semantics. Creates ambiguity: does "resolved as blocked" leave the task blocked?

4. **Sweep idempotency unspecified.** If inline resolution crashes mid-sequence and sweep runs later, nothing prevents double-append to task body. Summary presence check is content-based and brittle.

**Moderate:**

5. **UUID filename weakens manual-edit path.** Task affinity invisible at filesystem layer. Lexicographic order is random. Degrades the exact escape hatch being preserved.

6. **Option ID integrity rules missing.** No duplicate rejection, no immutability guarantee, no membership validation on resolution.

7. **Shared contract overstated.** Cockpit already needs a presentation model with `body_preview` — one model cannot serve all layers equally.

8. **Concurrency semantics missing.** No behavior for already-resolved, stale, or duplicate submissions.

9. **Phase mapping contradicts brief.** Brief says First Useful Step = data + engine + MCP/API interfaces. Draft put interfaces in Phase 2.

**Blind spots:** Who can resolve (active tension left unaddressed), Option shape not defined, list ordering undefined, post-resolution immutability unstated, package boundary for presentation models.

### Revisions Made

- Cockpit explicitly loses file-write authority; all writes through engine
- Discriminated validation by kind with explicit invariant table
- Renamed `blocked` → `failed` for action resolution
- ID-marker-based idempotency (`<!-- dr:{request_id} -->`) instead of content matching
- Defined `AlreadyResolved` error + idempotent same-resolution retry
- Corrected phasing to align with brief's First Useful Step
- Took position on who can resolve (both humans and agents)
- Defined full Option shape with integrity rules
- Added size limits
- Stated multi-request blocking semantics

---

## Cycle 2

### Critic Challenges (Cycle 2)

**Critical:**

1. **Multi-request blocking unspecified.** Task has one boolean `blocked`. Multiple pending requests possible. Resolving one could premature-unblock while others remain pending. Draft didn't address.

2. **"Atomic" claim unsupportable.** Resolution spans 4 independent writes (rewrite frontmatter, move file, append task, unblock). Existing tests prove crash windows exist. Claiming atomicity is false.

3. **Error surface too narrow.** Task body append can fail (500 KB ceiling). Route already models stale/conflict. Engine contract only names happy-path returns.

**Moderate:**

4. **Idempotency guard brittle if content-based.** Deduping by "summary already present" is unstable across human edits and repeated wording.

5. **Cross-surface retry semantics contradictory.** If MCP treats already-resolved as success but Cockpit treats it as conflict, retry behavior is nondeterministic.

**Blind spots:** Concurrent different-resolution race (first-writer-wins undefined), size limits absent, `resolved_by` identity schema unspecified, performance envelope for directory scanning.

### Revisions Made

- Added explicit multi-request blocking rule: unblock only when no other pending requests remain
- Dropped "atomic" claim; described as ordered sequence with crash-recovery semantics
- Added `TaskMutationFailed` to error surface
- Changed idempotency to request-ID-based marker (stable, content-independent)
- Unified retry semantics: identical resolution = idempotent success on both surfaces
- Added size limits table
- Stated `resolved_by` as plain audit string
- Acknowledged directory scanning is adequate for expected volume

### Position Stability

After Cycle 2, the Critic's remaining challenges were addressed structurally. The position moved from 0.44 to 0.78 confidence. Key strengthening areas: multi-request safety, non-atomicity acknowledgment, ID-based idempotency, and discriminated validation.

No further cycles needed — the position is solid on structural grounds.
