# Data Panelist — Critic Debate Log

## Cycle 1: Initial Position → Critic Challenge

### Initial Position (pre-Critic)

1. **Section model**: Add `level: int` to `Section`. Constrain `heading: None` to index 0 only. Require code-block-aware parsing.
2. **archival_reason/refs**: Direct-cycle-only validation at write time. Write-time-only ref existence. Archive-of-archive edits allowed, re-move rejected.
3. **dep_status**: Pure function computed on every read. No cache. Missing dep → `blocked`.
4. **agent_map**: `dict[str, str]` with `default` key. Unknown status → default, not error.
5. **Concurrency token**: Replace `updated` with `revision: int`. Keep `updated` as informational timestamp.
6. **Section round-trip**: `heading: None` only valid at index 0. Document code-block parsing requirement.
7. **Timestamp format**: Single canonical form `+00:00`, never `Z`.
8. **guidance**: Response-envelope-only, not persisted.
9. **revision**: Separate from `updated`, increments on every mutation.

### Critic Challenges

**C1: "You propose adding `level: int` to Section, but D7 locks `{heading: str | None, content: str}`. You're changing a locked decision."**

**Response:** D7 specifies the general shape. The aperture is wide (D3) and Brief A is mutable (context.md §User-Brought Direction point 3). Adding `level` is a refinement, not a contradiction — `heading: str | None` without level is lossy for round-trip. I frame this as a D7 amendment proposal with justification: without level, `## Foo` and `### Foo` collapse to the same Section, and the engine cannot reconstruct the original markdown. The alternative — storing the `##` prefix inside `heading` — is uglier but avoids a schema change. I'll present both options and recommend `level`.

**C2: "Compute-on-read for dep_status with 200 tasks × 5 deps = 1000 lookups. Is that viable?"**

**Response:** 1000 dict lookups in memory is nanoseconds. The engine already loads all tasks into cache (landscape.md confirms `_task_cache` keyed by filename with mtime). This is laptop-scale. If Brief C picks DBMS, dep_status becomes a SQL join — still fast. Caching dep_status would require a reverse-dependency index and cache invalidation on every archive operation — strictly more complex for zero performance gain at this scale.

**C3: "Direct-cycle-only for archival_refs misses A→B→C→A. Acceptable?"**

**Response:** Brief A explicitly says "the contract makes no promise about transitive following — a caller chasing a chain walks each hop themselves." If we don't promise transitive integrity to callers, we shouldn't validate it at write time either. Direct-cycle check (A refs B, B already refs A) catches the obvious human error. Longer cycles are pathological and self-correcting — a caller walking the chain will encounter the loop. Full DFS cycle detection on the archival graph is disproportionate engineering for laptop-scale.

**C4: "`revision: int` creates migration burden on existing task files."**

**Response:** Zero migration cost. Default `revision` to 1 on first read if field absent. The existing Task model uses `extra="allow"` (landscape.md, models.py). New field materializes on first write. No file rewrite needed.

**C5: "guidance is response-envelope-only, but engine must generate guidance that depends on task state (e.g., 'dep is stale'). Doesn't this duplicate dep_status computation?"**

**Response:** No duplication. Guidance generation happens at the same call site as dep_status computation — same code path. Engine computes dep_status, then generates guidance strings from the result. Both are response-time, both are uncached. Single pass.

**C6 (genuine gap): "Engine model is `list[Section]` but Brief A wire format is `body: str`. Where does serialization happen? What's the contract?"**

**Response:** Good catch — I hadn't specified this. The engine model is `list[Section]` for internal operations (section filtering, structured access). The wire format stays `body: str | null` per Brief A's `TaskFull`. The engine serializes sections to markdown string at method-return time. MCP/Cockpit never see `list[Section]` — they get `body: str`.

Serialization contract: `"\n\n".join(section.to_markdown() for section in sections)` where `to_markdown()` reconstructs `{"#" * level} {heading}\n{content}` for headed sections and just `{content}` for preamble.

Q8 answer: No. Keep `body: str` on the wire. Engine-internal structured model is an implementation detail, not a wire contract change.

### Position Refinements After Cycle 1

- Added: D7 amendment framed as proposal, not override. Present alternative (prefix in heading string).
- Added: Explicit serialization contract for Section → markdown.
- Added: Q8 resolution — wire stays `body: str`.
- Confirmed: compute-on-read, direct-cycle-only, revision default.

---

## Cycle 2: Refined Position → Critic Challenge

### Refined Position

(Incorporates all Cycle 1 refinements)

### Critic Challenges

**C7: "You say `heading: None` only valid at index 0. But what if the user edits a task body in Cockpit and inserts plain text between two headed sections? The engine's Section parser would either (a) attach it to the previous section's content, losing the boundary, or (b) create a `heading: None` section at index > 0, violating your constraint."**

**Response:** This is a real tension. The parsing rule must be deterministic: text between `## A` and `## B` belongs to section A's content. There is no "interstitial" — markdown doesn't have that concept at the `##` level. So (a) is correct: text after a heading and before the next same-or-higher-level heading is that section's content. The constraint `heading: None` at index 0 only is a *consequence* of correct markdown parsing, not an arbitrary rule. If the parser is correct, this situation cannot arise. I'll document this as a parsing invariant, not a validation rule.

**C8: "You haven't addressed what happens when the engine model produces a `list[Section]` that the *Cockpit editor* cannot edit losslessly. Cockpit uses a textarea for body editing. If the user edits raw markdown, the engine re-parses on save. Are you sure this round-trips?"**

**Response:** Cockpit body editing is plain-text markdown in a textarea (landscape.md: `edit_task` with `body: str`). User edits markdown → engine parses to `list[Section]` → stores → user reads back → engine serializes to markdown. Round-trip is lossless IF the parser is deterministic and the serializer is the inverse. The risk: extra blank lines, trailing whitespace, or heading formatting variations (`##Foo` vs `## Foo`). Brief B should specify normalization rules: heading format is `## {heading}` (space required), content preserves internal whitespace, sections separated by exactly one blank line. This makes round-trip deterministic.

**C9: "You proposed `+00:00` not `Z` for timestamps. But `datetime.now(tz=UTC).isoformat()` in Python produces `+00:00`. Are you sure existing code doesn't produce `Z` anywhere?"**

**Response:** Confirmed by landscape.md: all write sites use `datetime.now(tz=UTC).isoformat()`, which produces `+00:00` in Python 3.12. No `Z` in existing output. My position aligns with existing behavior. Brief B should specify `+00:00` as canonical and document that parsers must accept `Z` as equivalent for reading legacy or external data.

**Critic assessment: "Position is solid. The serialization contract addition was the main gap. Parsing invariants and normalization rules are good hardening. No further material flaws."**

### Position Refinements After Cycle 2

- Added: Parsing invariant documentation requirement (heading: None at index 0 is consequence, not rule).
- Added: Normalization rules for round-trip fidelity (heading format, section separation).
- Added: Parsers must accept `Z` on read even though canonical write is `+00:00`.
- Position declared solid by Critic.
