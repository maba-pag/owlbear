# Brief C — Synthesis

**Synthesizer:** Pragmatist
**Sources:** context.md, decisions.md, landscape.md, stances/architect.md, stances/data.md
**Date:** 2026-04-20

---

## Convergences

The two panelists align on every structural axis and most implementation details. This is an unusually high-convergence panel.

### Axis A — Structured body via `list[Section]`

Both land on the same model. Architect: "The body is `list[Section]` per D7/D26 — this is not Brief C's invention but its implementation obligation." Data: "The engine parses it to `list[Section]` per D7/D26 on read." Identical section shape: `{heading: str | None, level: int, content: str}`. Both specify code-block awareness per D26, preamble-only-as-first-element, and content opaque to storage.

### Axis B — Filesystem

Both choose filesystem over SQLite. Architect: "SQLite's atomicity advantage is real but narrow — closing the gap costs ~5 lines of fsync code. The three filesystem advantages are structural and two of them (diff, merge) are permanently forfeited by choosing SQLite." Data's entire schema is built around YAML frontmatter + Markdown body files, implicitly endorsing the same choice.

### Atomic write primitive

Both: `mkstemp → write → os.fsync(fd) → close → os.replace(tmp, target) → open(dir) → os.fsync(dir_fd)`. Architect states it explicitly. Data references "atomic tempfile + rename" for migration and defers to the same pattern.

### ruamel.yaml convergence

Architect: "Converge to ruamel.yaml only. Drop PyYAML." Data: "Converge on ruamel.yaml-only for both read and write." Both cite landscape headline #7 (impedance mismatch). Architect specifies `typ='safe'` for read, `typ='rt'` for write. Data specifies `typ='rt'` for both.

### No persistent index

Architect: "Not needed… YAGNI." Data does not propose one. Agreed at ~150 active tasks.

### CorruptionError class

Both define `CorruptionError` with code + user_message. Both agree D19 (duplicate ID) is a hard raise even in `list_tasks`. Both agree no auto-repair. Shape converges: `CorruptionError(code: str, user_message: str, file_path: str | None)`.

### Migration

Both: ~150 active files only, archive untouched, idempotent, atomic per-file, safe re-run on partial failure. Both include `claimed_by` removal (D11). Both include ruamel convergence as part of migration.

### No additional locking

Architect explicitly states "No additional locking beyond the ID flock." Data does not propose any. Converged.

### Predicate evaluation on structured objects

Both agree predicates operate on `list[Section]` objects, not regex over rendered Markdown. This delivers Outcome 3.

---

## Disagreements

### DIS-1: D40 Body Round-Trip Normalisation Level

**Architect vs. Data.**

- **Architect:** Heading format normalised (single space after `#`), inter-section spacing normalised (exactly one blank line), trailing newline always present, leading blank lines stripped. Section content is byte-exact.
- **Data:** ONLY CRLF → LF normalisation. Everything else — heading format, inter-section blank lines, leading/trailing blank lines — preserved verbatim. Section content is byte-exact.

**Material weight: HIGH.** This directly governs what agents can rely on after a write-read cycle. The Architect's approach produces canonical output and eliminates whitespace-variant drift; the Data approach minimises mutation and makes round-trip near-trivial to reason about. Agents that write `##Heading` (no space) would see it changed under the Architect's rule, unchanged under Data's.

### DIS-2: Predicate DSL Extensions

**Architect vs. Data.**

- **Architect:** "No new keys beyond D64. YAGNI now." Future extensions are discrete decisions when a pipeline failure demonstrates the need.
- **Data:** Proposes two new keys: `required_frontmatter_field` (gate on frontmatter completeness by status) and `section_not_empty` (gate on non-empty section content). Argues these close concrete gaps — agents scaffolding empty sections to pass `required_sections`, and no way to require frontmatter completeness by status.

**Material weight: MEDIUM.** Both keys are clean and non-speculative, but neither has a demonstrated pipeline failure today. The question is: does Brief C proactively close gaps the panel can see, or wait for the failure? Context §1 Outcome 3 focuses on section *presence* checks, which D64 already covers.

### DIS-3: Corruption Mode Granularity

**Architect vs. Data.**

- **Architect:** 7 modes. Does NOT treat invalid status/priority enum values as corruption. Does not include `ERR_CORRUPT_BODY_PARSE` or `ERR_CORRUPT_MALFORMED_TIMESTAMP`.
- **Data:** 9 modes. Adds `ERR_CORRUPT_INVALID_STATUS`, `ERR_CORRUPT_INVALID_PRIORITY`, `ERR_CORRUPT_MALFORMED_TIMESTAMP`, `ERR_CORRUPT_BODY_PARSE`. Merges Architect's `ERR_CORRUPT_DELIMITERS` into `ERR_CORRUPT_PARSE_FAILURE`.

**Internal tension in Data's stance:** The schema table says "Read: Pydantic (warn on unknown, don't reject — legacy tolerance)" for status/priority, but the corruption table lists `ERR_CORRUPT_INVALID_STATUS` and `ERR_CORRUPT_INVALID_PRIORITY` as corruption modes. These two positions are contradictory — one says warn-and-tolerate, the other says skip-as-corrupt.

**Material weight: MEDIUM.** The practical question is: if a task has `status: foo` (not in `BoardConfig.statuses`), is that corruption (skip in `list_tasks`) or degraded data (surface with warning)? Archive files with Go-era statuses may trigger this.

### DIS-4: `archival_reason` / `archival_refs` in Frontmatter Schema

**Data vs. Architect (by omission).**

- **Data:** Explicitly adds `archival_reason: str | null` and `archival_refs: list[int]` to the frontmatter schema per D37. Includes them in migration (add as null/empty if absent).
- **Architect:** Does not mention these fields. The Architect's stance covers body shape, backend, atomicity, corruption, and round-trip — but does not provide a complete frontmatter schema.

**Material weight: LOW.** D37 exists in Brief B. These fields must appear somewhere. Data is more explicit; Architect simply didn't enumerate the full schema. Likely an omission, not a disagreement.

### DIS-5: ruamel Read Mode

**Architect vs. Data.**

- **Architect:** Read with `YAML(typ='safe')` (fast, no round-trip overhead), write with `YAML(typ='rt')`.
- **Data:** Read with `typ='rt'` for both read and write (round-trip mode everywhere).

**Material weight: LOW.** Performance difference is small at this scale. `typ='safe'` loses comment/order metadata on read, which is fine since Pydantic re-serialises anyway. `typ='rt'` preserves everything, which matters only if the in-memory representation ever needs to reflect source formatting. Functionally equivalent for the engine's purposes.

### DIS-6: `append_body` Section-Awareness

**Architect vs. Data.**

- **Architect:** Section-aware merge: "If append starts without a heading → content appended to the last existing section. If append starts with a heading → appended as new section(s)."
- **Data:** String concatenation first (`current_body + "\n" + append_body`), then re-parse combined string into `list[Section]`, then write.

**Material weight: LOW.** These are functionally equivalent — Data's concat-then-reparse produces the same structural result as Architect's explicit merge rules. The Architect describes the behaviour at a higher abstraction level; Data describes the implementation. No actual conflict.

---

## Decision-Request Candidates Against Brief B

### DR-1: Corruption Surfacing Envelope Field

**Source:** Data, Warning #1.

Data's surfacing strategy puts corruption details in `guidance` entries with a `[CORRUPT]` prefix. Data explicitly warns: "If the panel consensus wants a dedicated `corruption` field on `ListTasksResponse`, that requires a Decision-Request against Brief B's frozen envelope schema."

Brief B's response envelope shape (including `guidance`) is frozen per context §2. Overloading `guidance` with corruption prefixes is a semantic stretch — `guidance` per Brief B (D39 + paper §3.6) is for pipeline coaching, not structural error reporting.

**Recommendation:** File a Decision-Request against Brief B to add an optional `corrupted: list[CorruptionDetail]` field to `ListTasksResponse`. This is a clean extension (additive, not breaking) and keeps corruption reporting separate from pipeline guidance. If the user rejects this, the `[CORRUPT]` prefix in `guidance` is the fallback — functional but semantically overloaded.

### DR-2: Body Structural Validation as New Error Surface

**Source:** Data, Warning #2.

Storage validating body structural parsability on every write (not just status transitions) introduces a new failure mode for `edit_task(body=...)` and `create_task(body=...)`. Brief B's error taxonomy (D27 + D57) may not include a code for "body failed structural parse at write time."

**Recommendation:** This is borderline. If the error code is `ERR_CORRUPT_BODY_PARSE` (a Brief C corruption code), it arguably lives below the engine's error taxonomy. If it needs to surface as a user-visible engine error, it may need a D27 extension. Flag for Mediator awareness; likely resolvable within Brief C's scope by framing it as a storage-layer rejection (pre-engine), not an engine error.

---

## Recommendation

**Confidence: 0.85** — High convergence on both axes and most structural decisions. Five open tensions, but only two (DIS-1 and DIS-2) carry real weight.

### Concrete Decisions for M4

| # | Decision | Architect Position | Data Position | Recommended Resolution | Confidence |
|---|---|---|---|---|---|
| **M4-1** | Axis A: structured body | `list[Section]` with parsed Markdown | `list[Section]` with parsed Markdown | **Lock: `list[Section]` per D7/D26.** Unanimous. | 0.98 |
| **M4-2** | Axis B: persistence backend | Filesystem (YAML + Markdown) | Filesystem (YAML + Markdown) | **Lock: filesystem.** Unanimous. | 0.98 |
| **M4-3** | D40 normalisation level | Heading + spacing normalisation, content-preserved | LF-only, everything else verbatim | **User must decide.** Architect's canonical output prevents drift but mutates more on first write. Data's minimal-mutation is simpler to reason about. Lean Data (minimal) — normalisation is a one-way ratchet that's hard to undo if wrong. | 0.55 |
| **M4-4** | Predicate DSL extensions | No new keys (YAGNI) | Two new keys: `required_frontmatter_field`, `section_not_empty` | **User must decide.** Data's keys are clean and non-speculative, but no pipeline failure demands them today. Lean Architect (YAGNI) — both keys can be added as discrete D64 extensions later with zero schema change. | 0.55 |
| **M4-5** | Corruption mode granularity | 7 modes (no enum validation) | 9 modes (enum validation as corruption) | **User must decide.** Data's internal contradiction (warn-on-unknown vs. corrupt-on-unknown) needs resolving first. Lean Architect (7 modes) — unknown status/priority in archive files is degraded data, not corruption. | 0.60 |
| **M4-6** | Corruption surfacing in `list_tasks` | CorruptionError raised to engine | Skip + guidance with `[CORRUPT]` prefix | **Lock Data's approach** (skip + guidance). Raising for every corrupt file halts the whole board. But **file DR-1** against Brief B for a dedicated envelope field. | 0.80 |
| **M4-7** | `archival_reason` / `archival_refs` in schema | Not addressed | Included per D37 | **Lock: include per D37.** D37 is a Brief B decision; storage must implement it. Architect's omission is not opposition. | 0.90 |

---

## Open Questions

1. **D40 normalisation level (DIS-1).** Must the storage writer produce canonical heading format and inter-section spacing (Architect), or only normalise line endings (Data)? The choice affects what agents see after a write-read cycle and whether first-write reformatting is acceptable. **Resolution required before M4 lock.**

2. **Predicate DSL scope (DIS-2).** Does Brief C ship `required_frontmatter_field` and `section_not_empty` now (Data), or defer to a future Brief when a pipeline failure justifies them (Architect)? **Resolution required before M4 lock.**

3. **Enum validation as corruption (DIS-3).** Is `status: foo` (not in `BoardConfig.statuses`) corruption or degraded data? Data's stance has an internal contradiction that must be resolved before this can be locked. **Resolution required before M4 lock.**

4. **DR-1: Brief B envelope extension.** Does `ListTasksResponse` get a dedicated `corrupted` field, or does corruption piggyback on `guidance`? This is a Decision-Request against Brief B. **Resolution required before Brief C can lock corruption surfacing.**
