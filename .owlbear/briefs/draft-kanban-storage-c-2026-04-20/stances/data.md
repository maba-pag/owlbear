# Data Modeler Stance — Brief C Kanban Storage Layer

**Panelist:** The Modeler (ideation-data)
**Confidence:** 0.88
**Critic cycles:** 5 (converged at cycle 5)

---

## 1. Canonical Task Schema

The persistent task shape (frontmatter + structured body). Every field is explicit on disk for self-documentation. Pydantic model is the single source of truth.

### Frontmatter Fields

| Field | Type | Required | Default | Validation Rule | Validation Timing |
|---|---|---|---|---|---|
| `id` | int | yes | — | Positive integer, unique across board, monotonic | Write: engine ID allocator. Read: Pydantic + ID-filename cross-check |
| `title` | str | yes | — | Non-empty string | Write: Pydantic. Read: Pydantic |
| `status` | str | yes | — | Value in `BoardConfig.statuses ∪ {"archived"}` | Write: engine enum check. Read: Pydantic (warn on unknown, don't reject — legacy tolerance) |
| `priority` | str | yes | — | Value in `BoardConfig.priorities` | Write: engine enum check. Read: Pydantic (warn on unknown) |
| `created` | str | yes | — | ISO 8601 UTC with explicit offset (`+00:00`). Regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}` (prefix match; sub-second and offset vary across eras) | Write: `datetime.now(tz=UTC).isoformat()`. Read: string presence check (Go-era 7-ns + local offset tolerated via string storage) |
| `updated` | str | yes | — | Same as `created` | Same as `created` |
| `tags` | list[str] | no | `[]` | Each element: non-empty string | Write: Pydantic. Read: Pydantic |
| `parent` | int \| null | no | `null` | If set: must reference existing task ID | Write: engine cross-ref validation (ERR_PARENT_NOT_FOUND). Read: no cross-ref check (stale ref is degraded, not corrupt) |
| `depends_on` | list[int] | no | `[]` | Each element: must reference existing task ID | Write: engine cross-ref (ERR_DEP_NOT_FOUND). Read: no cross-ref check |
| `blocked` | bool | no | `false` | YAML 1.2 boolean (true/false only) | Write: Pydantic. Read: Pydantic |
| `block_reason` | str \| null | no | `null` | If `blocked=false`: must be null. If `blocked=true`: should be non-empty (engine warns, doesn't reject) | Write: engine semantic check. Read: Pydantic |
| `claimed_at` | str \| null | no | `null` | If set: ISO 8601 UTC with offset | Write: engine sets on `start_work`. Read: Pydantic |
| `archival_reason` | str \| null | no | `null` | If set: value in `{"completed", "deprecated", "dropped", "duplicate", "wontfix"}` per D37 | Write: engine D37 validation. Read: Pydantic (null tolerated on legacy archive files) |
| `archival_refs` | list[int] | no | `[]` | Per D37 matrix: required/forbidden based on archival_reason. Each element must reference existing task | Write: engine D37 validation. Read: Pydantic |

**Dropped from current schema:** `claimed_by` (D11).

**Not persisted (computed at read time):** `claimed` (bool, from `claimed_at is not None`), `dep_status` (from dep states per D38), `agent` (from `BoardConfig.agent_map`).

### Body

The body is stored on disk as Markdown text (one section per `##`/`###`/etc. heading). The engine parses it to `list[Section]` per D7/D26 on read. Section model:

```python
Section = {heading: str | None, level: int, content: str}
```

- `heading=None, level=0`: body preamble (text before any heading). Allowed only as first element.
- `level`: heading rank (2 for `##`, 3 for `###`).
- `content`: section body text, Markdown-formatted, opaque to storage.
- Code blocks containing `## Heading` text in content: NOT parsed as sections (parser is code-block aware per D26).

**Storage validates structural well-formedness on every write:** the body string must parse into a valid `list[Section]`. Malformed Markdown that the parser can't section-split is rejected. This is distinct from engine-level predicate validation (D15), which checks semantic requirements (required sections, list items, etc.) on status transitions only.

### Projection Coverage

All Brief B projection fields are derivable from this schema:

- **TaskSummary**: all frontmatter fields except `created`/`updated` + computed `claimed`/`dep_status`
- **TaskFull**: all frontmatter fields + `body` (serialized from `list[Section]` per D30)
- **DispatchEntry**: `id`, `status`, `priority`, `title`, `tags` + computed `agent`
- **Wave**: computed envelope, not persisted

---

## 2. Frontmatter / Field Discipline

### Canonical Field Order (post-Brief-C)

```yaml
id
title
status
priority
created
updated
tags
parent
depends_on
blocked
block_reason
claimed_at
archival_reason
archival_refs
```

Changes from current: `claimed_by` removed (D11). `archival_reason` and `archival_refs` added at end of the claim/archive group.

### Type Discipline

- Integers: bare YAML integers (`id: 1034`, not `id: "1034"`)
- Strings: YAML strings, quoted only when YAML-ambiguous
- Booleans: YAML 1.2 only (`true`/`false`; YAML 1.1 aliases `yes`/`no`/`on`/`off` rejected)
- Lists: YAML sequences (flow `[a, b]` or block `- a\n- b`)
- Nulls: YAML `null` or absent key (absent = Pydantic default)
- Timestamps: plain strings (no YAML timestamp tag resolution — per current `YAML12SafeLoader` and ruamel config)

### Parser Convergence

**Converge on ruamel.yaml-only for both read and write.** The current PyYAML-read + ruamel-write split is a known impedance mismatch (landscape §a, headline #7). Ruamel in round-trip mode (`typ="rt"`) preserves key order, comments, and formatting. The custom `YAML12SafeLoader` behaviors (timestamp-as-string, YAML 1.2 bools) are replicated in ruamel's resolver configuration, which is already partially done in `_make_yaml()`.

### Ordering Rules

- **New files:** written in canonical field order (model field declaration order).
- **Existing files:** ruamel round-trip preserves source key order. Fields added by migration or edit are appended in canonical position.

### Validation Timing

- **Write-time (every write through engine):** Pydantic model validation on all fields. Type enforcement, enum checks, cross-reference validation, body structural parse.
- **Read-time:** Pydantic model validation with `extra="allow"` for legacy tolerance. Type mismatches and missing required fields surface as `CorruptionError`. Unknown extra fields (Go-era `class`, `started`, `completed`) preserved silently.

---

## 3. Migration Plan

**Scope:** ~150 active task files in `.owlbear/kanban/tasks/` only. Archive is NOT migrated.

### Script: `migrate_brief_c.py`

**Operations per file (in order):**

1. **Parse** frontmatter via ruamel round-trip (not PyYAML — migration is the convergence point).
2. **Drop `claimed_by`** field if present. (D11)
3. **Validate `created`/`updated` timestamps** are ISO 8601. If non-UTC offset detected (shouldn't exist in active files per landscape, but defensively): convert to UTC + `+00:00`. If malformed: log warning, skip file, continue.
4. **Add `archival_reason: null`** if absent (only relevant if an active task is somehow archived — defensive).
5. **Add `archival_refs: []`** if absent.
6. **Normalize YAML to ruamel round-trip output** — this converges the parser and establishes canonical formatting going forward.
7. **Normalize body line endings** to LF.
8. **Write** via atomic tempfile + rename (same primitive as `write_task`).

### Idempotency Guarantee

Every operation is idempotent:
- Dropping an absent field: no-op.
- Reformatting a correct timestamp: no-op (string comparison).
- Adding an already-present field: no-op.
- Re-normalizing normalized YAML: no-op (ruamel deterministic output).
- Re-normalizing LF: no-op.

Running the script twice produces identical output. The script compares pre-write content to post-write content and skips the atomic write if unchanged (no spurious mtime bumps).

### Partial-Failure Recovery

- Each file is migrated independently. Failure on file N does not affect files 1..N-1 or N+1..150.
- Atomic write per file: if the process crashes mid-file, the temp file is orphaned (cleaned on next run or by OS), and the original file is untouched.
- Re-run after crash: already-migrated files are detected as no-ops; failed file is retried.
- Exit code: 0 if all files migrated, 1 if any file skipped (with per-file error log to stderr).

### Verification

Post-migration: `git diff .owlbear/kanban/tasks/` shows per-task changes. Each change is human-reviewable in PR. Expected diffs: `claimed_by` removal, possible field additions, YAML formatting convergence.

---

## 4. Corruption Surfacing

### Corruption Modes

| Mode | Code | Detect | Severity | Engine Behavior |
|---|---|---|---|---|
| Missing required field (`id`, `title`, `status`, `priority`, `created`, `updated`) | `ERR_CORRUPT_MISSING_FIELD` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| Type mismatch (e.g., `id: "1034"` string instead of int) | `ERR_CORRUPT_TYPE_MISMATCH` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| ID-filename mismatch (`717-foo.md` with `id: 718`) | `ERR_CORRUPT_ID_MISMATCH` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| Invalid status enum value | `ERR_CORRUPT_INVALID_STATUS` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| Invalid priority enum value | `ERR_CORRUPT_INVALID_PRIORITY` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| Malformed timestamp (unparseable) | `ERR_CORRUPT_MALFORMED_TIMESTAMP` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| Duplicate frontmatter ID (D19) | `ERR_CORRUPT_DUPLICATE_ID` | Read (list-level) | Global | **Raise immediately** — even in `list_tasks`. ID uniqueness is a global invariant. |
| Missing YAML frontmatter delimiters | `ERR_CORRUPT_PARSE_FAILURE` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |
| Body unparseable to sections | `ERR_CORRUPT_BODY_PARSE` | Read | File-level | Skip in `list_tasks`; raise in targeted ops |

### What is NOT Corruption

- **Broken cross-references** (parent/depends_on pointing to non-existent ID): degraded data, not structural corruption. Validated at write-time (Brief B §3.4). At read-time: surfaced as guidance, not CorruptionError. Refs can go stale through legitimate operations (archival, deletion).
- **Missing optional fields**: Pydantic defaults apply. Not corruption.
- **Extra/unknown fields** (Go-era `class`, `started`, `completed`): preserved via `extra="allow"`. Not corruption.
- **Missing predicate-required sections**: predicate failure (D15), not corruption. Caught at status-transition time.
- **Legacy archive timestamps** (Go 7-ns, local offset): valid variant, not corruption. String storage tolerates both formats.

### Surfacing Strategy

- **Targeted ops** (`show_task`, `edit_task`, `move_task` on a specific ID): raise `CorruptionError(code, user_message)` immediately. The user_message names the file and describes the problem.
- **`list_tasks`**: skip corrupt files. Surface corruption details as `guidance` entries with `[CORRUPT]` prefix (e.g., `"[CORRUPT] 717-foo.md: id-filename mismatch (frontmatter id=718, filename id=717)"`). This keeps the board queryable while making corruption visible.
- **`list_tasks` + duplicate ID (D19)**: raise `CorruptionError` immediately. Cannot skip because ID uniqueness is a global invariant — returning either file under the disputed ID would be silently wrong.

### CorruptionError Shape

```python
class CorruptionError(KanbanError):
    code: str        # ERR_CORRUPT_* from table above
    user_message: str  # Human-readable: "file {path}: {description}"
    file_path: str | None  # The offending file, if identifiable
```

---

## 5. Predicate DSL Extensions Beyond D64

D64 locks: `required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag`.

### Proposed New Keys

#### `required_frontmatter_field: list[str]`

- **Semantics:** Each named frontmatter field must be present and non-null/non-empty on the task. Empty string counts as empty; empty list counts as empty; `null` counts as empty.
- **When:** Write-time, on status transition (same trigger as D15 predicates).
- **Error:** `ERR_PREDICATE_FAILED` with `detail="missing frontmatter: <field>"`.
- **Rationale:** Enables gates like "tasks entering `todo` must have `tags`" or "tasks entering `review` must have `parent`". Currently there's no way to require frontmatter completeness by status — only body-section presence.
- **Example config:**
  ```yaml
  status_predicates:
    todo:
      required_frontmatter_field: [tags]
    review:
      required_frontmatter_field: [tags, parent]
  ```

#### `section_not_empty: list[str]`

- **Semantics:** Each named section (case-insensitive heading match per D26/D56) must exist AND have non-empty `content` (after whitespace stripping). A section with only whitespace or blank lines fails.
- **When:** Write-time, on status transition.
- **Error:** `ERR_PREDICATE_FAILED` with `detail="section empty: <name>"`.
- **Rationale:** `required_sections` checks existence but not content. Agents commonly scaffold empty sections (e.g., `## Acceptance Criteria\n\n`) to pass the gate, then fill them later. `section_not_empty` closes this gap without introducing regex.
- **Example config:**
  ```yaml
  status_predicates:
    in-progress:
      required_sections: [acceptance criteria]
      section_not_empty: [acceptance criteria]
  ```

### Rejected Extensions

| Key | Why Rejected |
|---|---|
| `regex_in_section` | Contradicts the structured-body philosophy. The whole point of Axis A structured is to eliminate regex over rendered Markdown. Reintroducing regex in the DSL undermines the design. |
| `frontmatter_value_in_set` | YAGNI. No current config requires constraining frontmatter values to specific sets by status. Can be added in a future Brief if the need materialises. |
| `max_body_sections` | YAGNI. No evidence of section-count bloat as an operational problem. |

---

## 6. D40 Body Round-Trip Data Integrity

### Round-Trip Definition

For the structured body model, "round-trip" means:

1. Agent calls `create_task(body=md_string)` or `edit_task(body=md_string)`.
2. Engine parses `md_string` → `list[Section]`.
3. Storage writes sections back to Markdown on disk.
4. Later, `show_task` reads the file, parses to `list[Section]`, serializes to `body: str` on the wire.
5. The wire `body` compared to the original `md_string` is **identical after LF normalization.**

### Normalization Applied

- **Line endings:** CRLF → LF. The only normalization. This is a boundary normalization, not a content mutation.

### NOT Normalized

- **Trailing whitespace per line:** preserved (Markdown `  \n` line breaks are valid).
- **Inter-section blank lines:** preserved as-is.
- **Section heading level:** preserved (`##` stays `##`).
- **Section heading text:** preserved verbatim.
- **Section content:** preserved verbatim (opaque to storage).
- **Section order:** document order preserved. Sections are NOT re-ordered to any canonical ordering.
- **Leading/trailing blank lines in body:** preserved.

### Idempotency Property

After one write-read cycle, the content is LF-normalized. Subsequent write-read cycles produce byte-identical output. Formally: `write(read(write(read(x)))) == write(read(x))` for any input `x`.

### `edit_task(append_body=...)` Semantics

1. Read current body as Markdown string.
2. Concatenate: `current_body + "\n" + (timestamp_prefix if timestamp=true) + append_body`.
3. Re-parse the combined string into `list[Section]`.
4. If the append text contains heading markers (`##`, `###`, etc.), new sections are created in the parsed result.
5. Write the full `list[Section]` back to disk via Markdown serialization.
6. **Round-trip guarantee:** existing content is not reordered or mutated. Appended content survives exactly as written (modulo LF normalization). New sections created by the append are appended to the section list in document order.

### `edit_task(body=...)` (Full Replace) Semantics

1. New body string is parsed into `list[Section]`.
2. Validated against storage structural well-formedness (parseable sections).
3. Engine evaluates write-time predicates if this is part of a status transition (D15).
4. Written to disk. Round-trip: same LF normalization rule.

---

## Key Trade-Offs

| Decision | Trade-off | Why Accepted |
|---|---|---|
| All fields explicit on disk | Slightly larger files; migration writes fields that Pydantic could default | Self-documenting format; prevents drift between model defaults and file reality; git diffs show actual state |
| LF-only normalization (not byte-exact) | First write to a CRLF file mutates it | CRLF hasn't been seen in active files (landscape §a); LF is the platform norm; one-time cost absorbed by migration |
| Skip corrupt files in list_tasks | Corruption surfaced via guidance, not CorruptionError raise | Raising halts the entire board for one bad file — operationally catastrophic. Guidance prefix `[CORRUPT]` is machine-parseable. D19 duplicates still raise. |
| Lenient read for archive files | Archive tasks may have null `archival_reason` despite status=archived | Archive is not migrated (locked finding). D37 write-time rules prevent new inconsistencies. Legacy data tolerance is essential. |
| Converge on ruamel-only | Migration reformats YAML output of all active files | One-time cost; eliminates the PyYAML/ruamel impedance mismatch permanently; enables true round-trip key-order preservation |

## Warnings

1. **Response envelope extension may be needed.** Surfacing corruption via `guidance` conflates severity levels. If the panel consensus wants a dedicated `corruption` field on `ListTasksResponse`, that requires a Decision-Request against Brief B's frozen envelope schema.
2. **Body structural validation on `edit_task(body=...)`** is a new validation surface not in Brief B. Brief B's D15 predicates fire only on status transitions. Storage validating structural parsability on every body write is a layer below D15 — it catches malformed Markdown, not missing predicate requirements. The Mediator should confirm this distinction is clear to the planner.
3. **Archive archival_reason gap.** Legacy archived tasks will read as `archival_reason=None`. Any code that assumes archived tasks always have an archival_reason must handle the null case. This is a read-path contract that builders must be aware of.
