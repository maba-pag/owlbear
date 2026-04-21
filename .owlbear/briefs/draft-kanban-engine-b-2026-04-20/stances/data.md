# Data Panelist — Hardened Stance on Brief B (Kanban Engine API Contract)

## Data Quality Stance

Brief B's data model has nine pressure points. Six come from Q1–Q9; three are risks the brief hasn't named. This stance takes a position on each.

---

## 1. Section Model Shape (Q3, Q8)

### Position

Amend D7. The locked shape `{heading: str | None, content: str}` is lossy — it collapses `## Foo` and `### Foo` to the same Section. Add `level: int` to the model:

```
Section = {
    level:   int,          # 2 for ##, 3 for ###; 0 for preamble
    heading: str | None,   # heading text without ## prefix; None for preamble
    content: str           # everything after heading line until next heading at same or higher level
}
```

**Alternative (no D7 amendment):** Embed the prefix in `heading` — e.g., `heading: "## Foo"` vs `heading: "### Foo"`. Functionally equivalent but uglier; callers must strip prefixes for matching. I recommend `level` as the cleaner contract.

### Boundary Cases

| Case | Handling |
|------|----------|
| Empty body | `body: []` — empty list. Wire: `body: ""`. |
| Prose before first heading (preamble) | `Section(level=0, heading=None, content="...")` at index 0. |
| `heading: None` at index > 0 | **Impossible by parsing invariant.** Text between two headings belongs to the preceding section's `content`. This is a consequence of correct markdown parsing, not an imposed rule. |
| Nested heading levels (`##` vs `###`) | `###` sections appear as separate `Section` entries with `level=3`. Brief A's section filter (`show_task(section=...)`) matches on heading text case-insensitively across all levels. |
| Code blocks containing `## Heading` | Parser MUST track fenced code block state. Naive `^## ` regex splitting is a corruption vector. Brief B must specify: section splitting respects `` ``` `` fence boundaries. |
| Repeated headings (`## AC` twice) | Two separate `Section` entries in the list. Section filter returns both, concatenated in document order. `guidance` reports occurrence count (per AC12). |
| Heading order | Preserved — `list` is ordered. Semantically insignificant to the engine; order is a document concern. |

### Round-Trip Contract (Engine ↔ Markdown Storage)

Engine model is `list[Section]`. Wire format stays `body: str | null` (no Brief A change needed — Q8 answered: **NO**).

**Serialization:** `"\n\n".join(s.to_markdown() for s in sections)` where `to_markdown()` produces `{"#" * level} {heading}\n{content}` for headed sections, `{content}` for preamble.

**Normalization rules** (mandatory for deterministic round-trip):
- Heading line format: `{"#" * level} {heading}` — space after hashes required.
- Sections separated by exactly one blank line.
- Content internal whitespace preserved verbatim.
- Parser must handle `` ``` `` fenced blocks, not splitting on headings inside them.

**Shapes the engine can produce that markdown cannot represent:** None, given the preamble-at-index-0 invariant and normalization rules. Two sections with the same heading: fine in both representations. Leading whitespace in content: preserved in both.

### Landscape Gap

Landscape §Bucket 5 (A2) notes "No section extraction code exists." The parsing contract above is net-new — Brief B must specify it, not leave it to Brief C or implementation.

---

## 2. `archival_reason` Enum + `archival_refs` Rules

### Position

Brief A's enum and ref rules are sound. Brief B must specify the validation boundaries precisely:

**Cross-reference validation at write time:**
- `archival_refs` elements validated to exist (active or archived) at write time.
- Self-reference (`archival_refs` contains own task ID) → rejected.
- **Direct-cycle only:** If A lists B in refs and B already lists A in refs → rejected. Transitive cycle detection (A→B→C→A) is NOT performed. Rationale: Brief A explicitly states "the contract makes no promise about transitive following — a caller chasing a chain walks each hop themselves." Validating what we don't promise is inconsistent.
- **Ref validity is point-in-time.** After write, the referenced task's state may change (re-archived with different reason, etc.). The engine does NOT retroactively invalidate existing refs. Refs are historical pointers, not live constraints.

**Archive-of-archive:**
- `move_task(already_archived_id, "archived")` → `ToolError` — task is already archived, transition is invalid.
- `edit_task(archived_id, archival_reason=..., archival_refs=...)` → allowed (per Brief A §5.5). This is the correction path for archival metadata.

**Enum extensibility:** The 5-value enum (`completed | deprecated | dropped | duplicate | wontfix`) is closed. Adding a value is a Brief A revision, not a config change. Engine must reject unknown values at write time.

### Landscape Gap

Landscape §Bucket 1 confirms: `move_task` has no `archival_reason` or `archival_refs` parameters; `end_work` has no `archival_reason`. These are net-new engine parameters.

---

## 3. `dep_status` Computation

### Position

**Pure function. Computed on every read. No cache.**

```
dep_status(task, all_tasks) → "ok" | "redirect" | "blocked" | null
```

- No `depends_on` entries → `null`
- All deps active or archived-as-`completed` → `ok`
- Any dep archived as `deprecated` or `duplicate` → `redirect`
- Any dep archived as `dropped` or `wontfix` → `blocked`
- **Precedence:** `blocked` > `redirect` > `ok`. If one dep is `wontfix` and another is `deprecated`, result is `blocked`.

**Why no cache:**
- Laptop scale: 200 tasks × 5 avg deps = 1000 dict lookups in memory. Nanoseconds.
- Cache invalidation is expensive: archiving task Y requires invalidating dep_status for every task X where Y ∈ X.depends_on. Requires a reverse-dependency index. Complexity cost exceeds performance gain.
- The engine already holds all tasks in memory via `_task_cache` (landscape.md §Bucket 1).

**Missing dependency (corruption):** If a dep ID in `depends_on` references a task that doesn't exist (legacy data, deleted file), treat as `blocked`. This is defensive — a missing dep is at least as bad as a `wontfix` dep. `guidance` should warn: `"dep {id} not found — treating as blocked"`.

**`pick_tasks` integration:** `dep_status="blocked"` tasks are excluded from waves. `dep_status="redirect"` tasks are included (they're actionable — caller follows the ref chain). This matches Brief A §7 semantics.

### Landscape Gap

Landscape §Bucket 6 AC27/AC28 confirms dep_status is entirely absent from the engine. The entire computation is net-new.

---

## 4. `agent_map` Shape (Q6)

### Position

`dict[str, str]` — single agent name per status. Plus a `"_default"` key.

```yaml
agent_map:
  backlog: researcher
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
  _default: builder
```

**Rationale for single-string (not list):**
- Orchestrator dispatches one agent at a time per task. Multi-agent per status has no demonstrated consumer.
- Wave composition assigns one `agent` per `DispatchEntry`. A list would require a selection rule (first? random? round-robin?) — complexity without need.

**Unknown-status handling:**
- Status not in `agent_map` → use `_default` value.
- If `_default` absent from config → `agent` field is `null` on `DispatchEntry`, plus `guidance` warning: `"no agent mapped for status '{status}'"`.
- Engine does NOT error on unmapped status. Unmapped tasks are still dispatchable — the orchestrator can decide.

**Validation at config load:**
- All `agent_map` keys must be valid statuses in `config.statuses` (except `_default`).
- Values are free-form strings (agent names are not validated against a registry — agents are discovered at runtime).

### Landscape Gap

Landscape §Bucket 1 confirms: no `agent_map` on `BoardConfig`, no `wave_size` config. Both are net-new fields.

---

## 5. Optimistic Concurrency Token (Q1)

### Position

**Introduce `revision: int` as the concurrency token. Demote `updated` to informational timestamp.**

| Field | Purpose | Semantics |
|-------|---------|-----------|
| `revision` | Concurrency token | Monotonic integer. Increments on every mutation. Concurrency check: `if task.revision != expected → ConcurrencyError`. |
| `updated` | Informational timestamp | ISO 8601 `+00:00`. Records wall-clock time of last mutation. NOT used for concurrency. |

**Why not `updated` as token:**
- `updated` is a timestamp string. Comparing timestamps for equality is brittle: microsecond truncation, timezone normalization, string vs datetime comparison.
- Two rapid mutations in the same microsecond (theoretically possible) produce the same `updated` — silent concurrency hole.
- A revision counter is deterministic, monotonic, and immune to clock concerns.
- If Brief C picks DBMS, revision maps to a row version column — natural fit.

**Migration:** Existing tasks have no `revision`. Default to `1` on first read if field absent (Task model already uses `extra="allow"`). First mutation writes `revision: 2`. Zero migration cost.

**MCP opt-in (Q1 sub-question):** MCP callers should pass `revision` on `edit_task` and `move_task`. Today MCP doesn't — but with `revision`, the cost of opting in is trivial (pass the integer from the previous `show_task` response). Brief B should make `revision` **required** on `edit_task`, **optional** on `move_task` (move is typically preceded by a fresh read in orchestrator flows, but agents may move without prior read in `end_work` paths).

**Brief C interaction:** Revision counter is storage-agnostic. File backend stores it in frontmatter. DBMS stores it as a column. Both increment atomically on write.

---

## 6. AC29/AC30 Timestamp Wire Format

### Position

**Single canonical form: `YYYY-MM-DDTHH:MM:SS+00:00`.** No `Z`. No fractional seconds on the wire (truncate to seconds).

| Context | Format | Example |
|---------|--------|---------|
| `created`, `updated`, `claimed_at` | Full ISO, `+00:00` | `2026-04-20T14:30:00+00:00` |
| `append_body` timestamp prefix | Full ISO, `+00:00` | `2026-04-20T14:30:00+00:00 —` |
| Legacy `[[YYYY-MM-DD]]` in existing bodies | Preserved on read, not rewritten | `[[2026-04-18]]` |

**Why not `Z`:** `+00:00` is what Python's `datetime.now(tz=UTC).isoformat()` produces. Using `Z` would require post-processing the string. One canonical form, zero conversion.

**Why truncate fractional seconds:** Wire readability. Agents and humans read these timestamps. `.123456+00:00` is noise. Precision beyond seconds has no consumer.

**Parser tolerance:** Engine must accept `Z`, `+00:00`, and fractional seconds on READ (legacy data, external input). Canonical WRITE is `+00:00`, seconds precision.

**D20 alignment:** D20 says "full ISO 8601 with offset; accept inconsistent historical prefixes." This stance is consistent — it just pins the exact form.

---

## 7. `guidance: list[str]` — Projection and Cache Interaction

### Position

**`guidance` is response-envelope-only. Not on `TaskSummary`, not on `TaskFull`, not persisted, not cached.**

Brief A's projection schemas confirm: `guidance` appears on response envelopes (`ListTasksResponse`, `ShowTaskResponse`, `PickTasksResponse`, `SingleTaskResponse`) — never on `TaskSummary` or `TaskFull` themselves.

**Engine contract:** Engine methods return `(result, guidance: list[str])` or equivalent. Guidance is generated at response time from the operation's context:
- dep_status warnings ("dep {id} is archived as wontfix")
- Section match counts ("2 occurrences of ## AC found")
- Missing deps warnings
- Unmapped agent_map warnings

**Cache interaction:** None. `guidance` is never stored in `_task_cache`. It is computed fresh per operation. This keeps cache invalidation simple — cache only tracks task data, not derived commentary.

---

## 8. `revision` Counter Relationship to `updated`

### Position

Separate fields, separate concerns. See §5 for full specification.

| Concern | Field | Consumer |
|---------|-------|----------|
| "Has this task changed since I last saw it?" | `revision` | Cockpit optimistic lock, MCP edit/move |
| "When was this task last touched?" | `updated` | Human display, sort-by-date, audit |

The prep-brief's `revision` concept and the existing Cockpit `updated`-based lock converge here: `revision` replaces the lock role, `updated` keeps the timestamp role. Both are updated on every mutation, but only `revision` is used for concurrency checks.

---

## 9. Risks Beyond Q1–Q9

### Risk 1: dep_status + archival_reason semantic coupling

`dep_status` depends on the `archival_reason` of dependency targets. But `archival_reason` is mutable via `edit_task` on archived tasks (Brief A §5.5). If someone changes a dep's `archival_reason` from `completed` to `wontfix`, the dependent task's `dep_status` silently flips from `ok` to `blocked` on next read. No notification, no guidance.

**Recommendation:** When `edit_task` changes `archival_reason` on an archived task, engine should scan for dependents and include guidance: `"archival_reason change on task {id} may affect dep_status of tasks {x, y, z}"`. This is response-time computation, not stored.

### Risk 2: Section model + Cockpit edit path

Cockpit edits body as plain markdown text (textarea). Engine parses to `list[Section]`, stores, re-serializes. If the normalization rules (§1) are not enforced, a user who types `##Foo` (no space) or adds extra blank lines between sections will get a different body back after save. Brief B must specify that the engine normalizes on write and Cockpit displays the normalized result.

### Risk 3: `archival_refs` validation scope creep

Write-time existence checks on `archival_refs` require the engine to resolve IDs across both active and archived tasks. Today, `show_task` doesn't search archives (landscape.md: "Raises FileNotFoundError if not found (no archived handling)"). Brief B must ensure the engine can resolve any task ID regardless of active/archived status — this is a prerequisite for ref validation AND for AC1 (show archived task).

---

## Key Trade-offs

| Trade-off | Chosen | Rejected | Rationale |
|-----------|--------|----------|-----------|
| Section level tracking | `level: int` field | Embed prefix in heading string | Cleaner contract; callers don't parse |
| Cycle detection depth | Direct only (A↔B) | Full transitive DFS | Brief A doesn't promise transitive integrity |
| dep_status caching | Compute on read | Cached + reverse index | Laptop scale; cache complexity > perf gain |
| Concurrency token | `revision: int` counter | `updated` timestamp | Deterministic, immune to clock edge cases |
| Timestamp wire form | `+00:00` no `Z` | Allow both on write | One canonical form eliminates comparison ambiguity |
| guidance storage | Response-envelope only | Persisted on task | No cache invalidation; fresh per operation |
| agent_map cardinality | Single string per status | List per status | No multi-agent consumer exists |

---

## Warnings

1. **D7 needs amendment.** The locked Section shape `{heading, content}` is lossy without `level`. This stance proposes adding `level: int`. If the amendment is rejected, the fallback (prefix in heading string) works but is uglier.
2. **`revision` is a new field.** Every consumer that currently uses `updated` for concurrency must migrate to `revision`. Cockpit mutation routes are the primary migration site.
3. **Section parsing is non-trivial.** Code-block-aware heading extraction is more complex than regex splitting. Brief B must specify it clearly enough that Brief C (storage) can implement it correctly regardless of backend.
4. **dep_status + archival_reason coupling** creates a hidden data dependency. Changing archival metadata on one task silently affects the read-time computation of another task's fields. Brief B should document this explicitly as an expected behavior.

---

## Confidence

**0.85.** High confidence on the data-shape positions (Section, dep_status, revision, timestamps). Moderate confidence on the cycle-detection scope — direct-only is pragmatic but a future edge case could force revisiting. The Section `level` amendment is the most likely point of contention with the Architect panelist.
