# End-User Stance — Structured Task Specification

## User Experience Stance

Moving `ac` (list[str]) and `proof_bundle` (enum string) to frontmatter is a **net UX win for agents** with a **manageable regression for human readers**, provided three blocking requirements are met: search must include frontmatter AC, body-coupled gates must migrate, and proof_bundle normalization must be model-level.

## Usability Reasoning

### 1. AC readability in raw YAML

Block-style YAML sequences are acceptable for humans who read task files "occasionally." The visual downgrade from markdown bullets under a heading is real but minor given agents are the primary consumer.

**Blocking requirement:** `list_tasks(search=...)` currently searches title and body. After migration, AC text moves out of the body and becomes invisible to search. Search must be extended to include frontmatter `ac` entries. This is not a polish item — it makes AC content disappear from a documented query surface.

### 2. MCP tool ergonomics (add_ac / remove_ac)

Exact string matching for removal is the right approach — consistent with the `tags` pattern and avoids the ambiguity of fuzzy matching. Index-based removal is worse (reordering silently changes targets).

**Critical UX safety net:** When `remove_ac` fails to match, the error response must list all existing AC entries. This turns a dead-end into an actionable correction. Without this, agents hit a wall and must call `show_task` to find the right string — an unnecessary round-trip.

**AC equivalence rule:** Trimmed whitespace, case-preserved, exact match after trim. No normalization beyond whitespace. Agents and humans need predictable identity.

### 3. AC naming convention

With list[str] storage, the AC string prefix is the only stable handle for review references, evidence mapping, and mutation targeting. Semantic prefixes (`AC-lint:`, `AC-tests:`) are preferable to ordinal (`AC1:`, `AC2:`) because they are self-documenting at every reference site — a reviewer writing "AC-tests: met" doesn't require a lookup table.

This is a convention recommendation, not a schema enforcement requirement. The data shape supports either. But if ordinal naming becomes the de facto convention, every downstream reference becomes an indirection that increases cognitive load.

### 4. Proof bundle display and normalization

**MCP output:** Return the normalized string value. Agents know the taxonomy from their skills. Adding explanatory text to every MCP response is noise for the primary consumer.

**Normalization must be model-level** (Pydantic validator on write), not surface-specific. All task-returning surfaces — `show_task`, `start_work`, `create_task` response, mutation responses — must return the same canonical form. Canonical order: `base+challenge+reader` (base first, modifiers alphabetical). Input `challenge+smoke+reader` normalizes to `smoke+challenge+reader`.

### 5. Forward-only migration

**proof_bundle migration is non-optional.** proof_bundle controls test-writing scope, challenger dispatch, and reviewer depth. During transition, tasks without frontmatter proof_bundle receive different proof obligations — that is a correctness issue, not a UX inconvenience. Provide the migration script and run it at launch.

**AC migration is acceptable as forward-only** because agents already handle "read AC from wherever it appears." But there is a hard blocker:

**Body-coupled gates must migrate.** The dispatch clarity gate (`pick_tasks`) requires bullet/numbered AC lines in the body. Status predicates inspect body sections. These gates will break for tasks that have AC in frontmatter but not in body. The design must update these gates to check frontmatter `ac` before or instead of body inspection. This is not "verify before migration" — the code proves the dependency.

### 6. AC and proof_bundle in list_tasks / pick_tasks

- **proof_bundle in TaskSummary (list_tasks):** Yes. Single string, aids triage at a glance.
- **AC full list in TaskSummary:** No. When browsing a board, you want status/priority/title/tags/proof_bundle. AC is detail for `show_task`.
- **proof_bundle in DispatchEntry (pick_tasks):** Recommended but not blocking. Current orchestration obtains full context at `start_work` claim time, so the workflow functions without it. Including it would save a round-trip for scope-aware dispatch.
- **AC in DispatchEntry:** No. Already rejected in decisions (user M3 correction).
- **ac_count:** No. A count without content is false signal.

### 7. Error messages

Errors must be actionable — include the attempted value, the reason for rejection, and enough context for self-correction.

- **Duplicate AC:** `"AC already exists: 'AC-tests: all unit tests pass'"`
- **Invalid proof_bundle:** `"Invalid proof_bundle 'smoke+lint'. Valid bases: skip, existing, smoke, behavioral, critical. Valid modifiers: +challenge, +reader."`
- **Remove AC not found:** `"No matching AC for 'AC-tsts: pass'. Existing entries:\n  - AC-tests: all unit tests pass\n  - AC-lint: ruff clean"`
- **Malformed frontmatter:** Invalid proof_bundle values written directly to disk must not silently hide tasks from board/list/pick views. Graceful degradation: load the task with a warning annotation, don't drop it.

### 8. Default for missing proof_bundle

`None` (absent), not a silent default like `behavioral`. A silent default masks omissions — a task intended as `skip` or `critical` would silently receive standard-depth proof obligations if the planner forgot to set it.

Caveat: current skills tolerate absence and continue with normal flow, so `None` does not enforce anything by itself. Recommend that skill updates treat `None` as "must set before dispatch" to close the enforcement gap. But the schema choice of `None` over a default is correct regardless — explicit is better than implicit.

## Key Trade-offs

| Dimension | Win | Cost |
|-----------|-----|------|
| Agent clarity | AC and proof_bundle are typed, queryable, separate from work logs | Human readability slightly worse in raw YAML |
| Tool ergonomics | Consistent with tags pattern, atomic ops | String matching for multi-word AC entries requires good error messages |
| Migration | Clean forward path | proof_bundle migration is non-optional; body gates must migrate |
| Search | Frontmatter fields are structured | Search contract must broaden (documented change) |
| Normalization | Canonical proof_bundle form across all surfaces | Validator complexity for modifier grammar |

## Warnings

1. **Body-gate breakage is proven, not speculative.** Dispatch clarity gate and status predicates inspect body text for AC. Migrating AC to frontmatter without updating these gates will break task dispatch. This must be addressed in the design, not deferred.

2. **Search regression is silent.** AC text disappearing from search results produces no error — users simply don't find what they're looking for. This is the worst kind of UX failure because it looks like the system is working.

3. **Malformed frontmatter can hide tasks.** A bad proof_bundle value written directly to disk (human edit, merge conflict) could cause Pydantic validation failure on load, silently dropping the task from all views. The model must handle invalid values gracefully.

4. **AC naming convention will calcify fast.** Whatever pattern emerges in the first few tasks becomes the de facto standard. If the team wants semantic prefixes, establish the convention before launch, not after.

## Confidence

**0.78** — Position is well-grounded after two Critic cycles. The three blocking requirements (search extension, body-gate migration, model-level normalization) are evidence-based. Remaining uncertainty is in how quickly the migration transition completes and whether skill updates to enforce proof_bundle presence will actually land.
