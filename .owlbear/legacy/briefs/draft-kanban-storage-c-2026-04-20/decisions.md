# Brief C — Decisions

**Status:** M5 complete (post-amendments; ready for M6 handoff)

Decisions are numbered C1, C2, … (Brief C-local). References to Brief B decisions use Brief B's D-prefix (D11, D14, etc.).

---

## C1 — Axis A: Task body shape

**Decision:** Body is `list[Section]`. Each `Section = {heading: str | None, level: int, content: str}`. Storage parses Markdown body into `list[Section]` at read time and validates structural well-formedness at write time. Predicate DSL (D64 + extensions) operates on `list[Section]` objects, not regex over rendered Markdown. Implementation per Brief B D7/D26.

**Source:** M4-1 (architect + data unanimous, panel confidence 0.98). User locked.

## C2 — Axis B: Persistence backend

**Decision:** Filesystem — YAML frontmatter + Markdown body files in `.owlbear/kanban/tasks/*.md`, archive in `.owlbear/kanban/archive/*.md`. SQLite is rejected. Atomic write primitive: `mkstemp(dir=parent) → write → os.fsync(fd) → close → os.replace(tmp, target) → os.fsync(dir_fd)`. The fsync additions (~5 LOC) close the only structural advantage SQLite had over the current code. Three filesystem advantages (git diff-reviewability, cross-branch mergeability, structure-via-JSON) are permanently forfeited by SQLite and are actively used.

**Source:** M4-2 (architect + data unanimous, panel confidence 0.98). User locked.

## C3 — `archival_reason` / `archival_refs` in frontmatter

**Decision:** Both fields are part of the canonical frontmatter schema, per Brief B D37. `archival_reason: str | None` (enum from `BoardConfig.archival_reasons`), `archival_refs: list[int]` (default `[]`). Migration adds these as null/empty if absent in active task files.

**Source:** M4-7 (data explicit, architect silent — not opposed). User locked.

## C4 — D40 body round-trip normalisation: canonical headings, minimal content mutation

**Decision:** Storage always normalises line endings (CRLF → LF) and canonicalises headings to ATX on write. Setext headings are recognised on read and converted to ATX on write. Everything else stays as close to source as the `Section(heading, level, content)` model allows:
- Within-section content is byte-exact modulo CRLF → LF, including trailing whitespace, blank lines within content, and indentation.
- Inter-section blank-line counts are preserved.
- `##Heading` (no space) is content of the current section, never a heading.

After the first write through Brief C storage, byte-identical reads are guaranteed in the canonical ATX form. `edit_task(append_body=...)` concatenates and re-parses; new headings in the appended block create new sections.

**Rationale:** The body model cannot preserve heading-marker style, so heading canonicalisation is intentional. Outside that boundary, mutation stays minimal and predictable.

**Source:** M4-3 (DIS-1, panel split). User chose Data's minimal-mutation position over Architect's canonical-output and Mediator's lean.

## C5 — Predicate DSL extensions: none

**Decision:** Brief C ships **no new predicate DSL keys** beyond the three locked in Brief B D64 (`required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag`). The substantive change in Brief C is that these existing keys now operate on `list[Section]` objects (per C1) instead of regex over rendered Markdown — this IS the structural reliability win stated in Outcome 3.

Future extensions (including `required_frontmatter_field`, `section_not_empty`, regex matchers) are added as discrete D64 extension tasks when a demonstrated pipeline failure justifies them. No speculative schema surface.

**Rationale:** YAGNI. Both candidate keys (Data's `required_frontmatter_field`, `section_not_empty`) are clean and addable later with zero schema change. No current pipeline failure demands them, and Brief B §6 explicitly authorises incremental additions.

**Source:** M4-4 (DIS-2, panel split, Mediator proposed split-decision). User chose full Architect YAGNI position.

## C6 — Corruption modes: 9 modes (strict enum validation)

**Decision:** Storage detects NINE corruption modes at read time, each surfaced as `CorruptionError(code, user_message, file_path | None)`:

1. **`ERR_CORRUPT_DELIMITERS`** — missing or malformed `---` frontmatter delimiters.
2. **`ERR_CORRUPT_DUPLICATE_ID`** — two task files claim the same `id` (D19). Hard raise even in `list_tasks` — never silently loaded.
3. **`ERR_CORRUPT_MISSING_FIELD`** — required frontmatter field absent (id, title, status, priority, created, updated).
4. **`ERR_CORRUPT_TYPE_MISMATCH`** — field present but wrong type (e.g. `id: "1034"` as string, `blocked: "true"` as string).
5. **`ERR_CORRUPT_YAML_PARSE`** — YAML itself malformed.
6. **`ERR_CORRUPT_ID_FILENAME_MISMATCH`** — filename `{N}-slug.md` has `id: M` with `N ≠ M` in frontmatter.
7. **`ERR_CORRUPT_DUPLICATE_LOCATION`** — same task file present in both `tasks/` and `archive/` (crash-recovery leftover).
8. **`ERR_CORRUPT_INVALID_STATUS`** — `status` not in `BoardConfig.statuses` (plus `"archived"`).
9. **`ERR_CORRUPT_INVALID_PRIORITY`** — `priority` not in `BoardConfig.priorities`.

**Resolution of Data's internal contradiction:** Data's stance contained both "warn-on-unknown-enum, don't reject" and "`ERR_CORRUPT_INVALID_STATUS`/`_PRIORITY`". The contradiction is resolved in favour of the **strict** reading: unknown enum values ARE corruption. The "lenient-read" rule is dropped. Legacy archive files (sampled in M3) already use current enum values (`status: archived`, `priority: nice-to-have`, etc.) so no existing-data regression is created. Any future `BoardConfig` enum reshape must include migration of existing files to the new enum as part of its own migration script.

**Source:** M4-5 (DIS-3, panel split). User chose Data's stricter position.

## C7 — Corruption handling: auto-fix + quarantine + AR, triggered by explicit two-phase repair

**Decision:** Storage handles the 9 C6 corruption modes via a two-path model, not via API envelope reporting. Trigger: **explicit** — repair runs only when the user triggers `engine.repair_storage()` via Cockpit; it never runs implicitly inside startup `sweep()`. Runtime reads tolerate corruption:

- `list_tasks` skips corrupt files silently and omits them from the returned list for 8 of the 9 modes; `ERR_CORRUPT_DUPLICATE_ID` is the carve-out and hard-raises from `list_tasks` per AM-2.
- `show_task(corrupt_id)` raises `CorruptionError` (user-visible, not silently swallowed).
- No separate repair-log file is written. Git diff remains the file-level provenance trail for auto-fixes, and mutating repair operations are recorded on the board-level `activity.jsonl` stream per C10.

The repair is a **two-phase split** to avoid a circular import (`engine.py` imports `storage`; `storage` cannot import back into `engine`):

- **Phase 1 — `storage.scan_and_fix(kanban_dir, config)`:** handles detection, auto-fix (writes), and quarantine (file moves). Returns `list[RepairOutcome]`; `action="quarantined"` items need AR creation.
- **Phase 2 — `engine.repair_storage()`:** calls `storage.scan_and_fix()`, then for each `action="quarantined"` outcome calls `self.create_task(...)` to create the Action Request. AR creation is always an engine responsibility (it respects entry_status predicates and ID allocation).

The Cockpit also exposes `scan_corruption()` (read-only) which calls `storage.detect_corruption(path, config)` for all files and returns the aggregated `list[CorruptionError]` without modifying anything. Intended for Cockpit health-check polling: shows a badge/count when issues are found.

### Per-mode disposition table

| # | Mode | Auto-fix rule | Quarantine rule |
|---|---|---|---|
| 1 | `DELIMITERS` missing | — | Quarantine (AR at engine layer) |
| 2 | `DUPLICATE_ID` (D19) | — | Quarantine both files (AR at engine layer) |
| 3 | `MISSING_FIELD` | Fix if safe default exists: `priority` → `config.priorities[0]`, `tags` → `[]`, `depends_on` → `[]`, `blocked` → `false`, `block_reason` → `null`, `claimed_at` → `null`, `archival_reason` → `null`, `archival_refs` → `[]`, `parent` → `null`. If `id`/`title`/`created` missing → quarantine. | Quarantine (AR at engine layer) if unfixable |
| 4 | `TYPE_MISMATCH` | Coerce if trivially safe: digit-only string-int (`"1034"` → `1034`), string-bool (`"true"` → `True`, `"false"` → `False`). Otherwise quarantine. | Quarantine (AR at engine layer) if ambiguous |
| 5 | `YAML_PARSE` | — | Quarantine (AR at engine layer) |
| 6 | `ID_FILENAME_MISMATCH` | **Auto-fix**: rename file to match frontmatter `id` (content wins over naming). | — |
| 7 | `DUPLICATE_LOCATION` (both `tasks/` + `archive/`) | **Auto-fix**: `archive/` wins (terminal state). Remove from `tasks/`. | — |
| 8 | `INVALID_STATUS` | — | Quarantine (AR at engine layer) |
| 9 | `INVALID_PRIORITY` | **Auto-fix**: coerce to `config.priorities[0]`. | — |

### Quarantine mechanism

`storage.scan_and_fix` moves quarantined files to `.owlbear/kanban/quarantine/{original-filename}` (directory auto-created). The engine then creates an Action Request task via `self.create_task(...)` with:
- `tags: ["type:user-action"]` (tag list from `BoardConfig.non_impl_tags` per D64)
- Title: `"Quarantined task file: {filename}"`
- Body section `## Quarantined file`: contains `code`, quarantine path, inferred reason, and — if recoverable — suggested manual fix.

The user resolves manually: edits the quarantined file, moves it back to `tasks/` or `archive/`, and closes the AR.

### Repair surface shape

Brief B `sweep()` remains claim-only and keeps its existing `list[int]` return type. Corruption repair is exposed separately as a two-phase engine method `repair_storage() -> list[RepairOutcome]`:

```python
class RepairOutcome(BaseModel):
    task_id: int | None  # None if file unparseable enough to extract ID
    file_path: str
    code: str  # ERR_CORRUPT_* code from C6
    action: Literal["fixed", "quarantined", "failed"]
    detail: str | None  # e.g. "renamed to match id=1034", "AR #1042 created"
```

No `sweep()` return-type expansion is needed. Startup-safe claim maintenance and explicit storage repair are separate surfaces by design.

### DR-1 killed

The envelope-extension Decision-Request that the panel flagged (adding a `corrupted` field to `ListTasksResponse`) is **not needed** under C7. Storage never returns corrupt data to the engine — it either auto-fixes (engine sees healed data) or quarantines (file leaves the scanned directory). The engine envelope stays untouched. Brief B's response envelopes are preserved.

**Source:** M4-6 (user reframed from Architect/Data envelope debate into auto-fix/quarantine model). User-driven decision.

## C8 — Implementation details (panel-unanimous, batch lock)

The following items had unanimous architect + data panel agreement and no user disagreement. Locked as a block.

### C8.1 — Atomic write primitive (steady-state)

Every task-file write uses the POSIX-portable sequence:

```python
fd, tmp = tempfile.mkstemp(dir=target.parent)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(content)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, target)
# Persist the rename in the directory entry (POSIX; no-op on Windows)
dir_fd = os.open(str(target.parent), os.O_RDONLY)
try:
    os.fsync(dir_fd)
finally:
    os.close(dir_fd)
```

This closes the only structural atomicity gap SQLite had over the current code (~5 LOC addition to `task_io.write_task`).

### C8.2 — ID allocation

Use the existing `.next_id.lock` flock (Unix) / `msvcrt.locking` (Windows) mechanism, but with the corrected order: `acquire lock → load_config → task_id = config.next_id → save_config(next_id += 1) → release lock → write_task`. Burned IDs after a crash are acceptable; stale `next_id` leading to duplicate allocation is not. Lock file lives at `{kanban_dir}/.next_id.lock`.

### C8.3 — YAML library convergence

Drop PyYAML entirely. Use `ruamel.yaml` for both read and write:
- **Read:** `YAML(typ='safe')` (fast; Pydantic re-validates immediately after, so round-trip metadata loss is acceptable).
- **Write:** `YAML(typ='rt')` (round-trip — preserves comments/order where present).

Both instances strip the YAML timestamp resolver so ISO-8601 strings survive verbatim (same rationale as current `task_io.py:46-89`).

### C8.4 — Persistent index

None. The existing per-instance mtime-keyed cache (`_task_cache`, `_archive_cache`, `_id_to_filename`) in `engine.py:380-416` is retained. At ~150 active tasks, `os.scandir` is ~1ms; a persistent index would be YAGNI.

### C8.5 — Locking strategy (beyond ID allocation)

No additional cross-process locking. Steady-state write atomicity comes from C8.1 (atomic rename + fsync). Cockpit OCC (Brief B D46) handles read-modify-write races from Cockpit. Agent-vs-agent races are prevented by the claim/`start_work` + `claim_timeout` mechanism (engine-layer, not storage-layer). Single-laptop concurrency reality (M1 finding: three races in three months, all intentional) does not justify more.

### C8.6 — Canonical frontmatter order

The canonical field order on disk (post-migration):

```
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

Notes:
- `claimed_by` removed per Brief B D11.
- `claimed_at` retained (claim timestamp only; no identity).
- `archival_reason` and `archival_refs` added per C3 + Brief B D37.
- All timestamp fields (`created`, `updated`, `claimed_at`) are strings in ISO-8601 UTC with explicit `+00:00` offset per Brief B D14.
- `extra="allow"` on the Pydantic `Task` model is retained so vendor fields in legacy archive files (`class`, `started`, `completed`) survive round-trip without schema enforcement.

### C8.7 — Archive layout

Flat sibling directory `.owlbear/kanban/archive/` (fixed path; no `archive_dir` config field in the approved contract). Archived tasks carry `status: "archived"` in frontmatter AND live in the archive directory (the "both" reality documented in M3 landscape §a). `repair_storage()` reconciles orphans (status=archived in `tasks/` moves to archive; duplicate-location per C7 resolves to archive-wins).

### C8.8 — CorruptionError class shape

```python
class CorruptionError(KanbanError):
    code: str  # one of the 9 C6 ERR_CORRUPT_* codes
    user_message: str
    file_path: str | None  # absolute path; None if corruption pre-parses filename
```

Subclass of the existing Brief B `KanbanError` hierarchy (D27/D57). Maps to HTTP 500 via Cockpit adapter per Brief B D27.

## C9 — Migration script

One Python script, invocable via `uv run kanban-migrate` (entry point in `serve/kanban/pyproject.toml`). Scope is **three lanes**:

- **Active task files** — `.owlbear/kanban/tasks/*.md`: full migration to the Brief B + Brief C active-task shape.
- **Archive files** — `.owlbear/kanban/archive/*.md`: metadata-only normalization of the contract-critical archive fields required by Brief A (`archival_reason`, `archival_refs`). Archive body text and legacy vendor fields are not otherwise normalised.
- **Config file** — `.owlbear/kanban/config.yml`: rewrite from the legacy schema to the new `BoardConfig` contract, including config-first rehearsal and manual-action checkpoints before final task cutover.

**Per-file transformation — active lane:**

1. Read frontmatter via ruamel-safe (C8.3).
2. Remove `claimed_by` field if present (D11).
3. Add `archival_reason: null` if absent (C3).
4. Add `archival_refs: []` if absent (C3).
5. Normalize all timestamp fields to UTC ISO-8601 with explicit `+00:00` offset (D14). If an existing timestamp has a non-UTC offset (e.g. `+02:00`), convert to UTC with offset.
6. Parse body into `list[Section]` per C1 and validate; if unparseable, skip and record in the summary.
7. Serialize frontmatter back in C8.6 canonical order via ruamel `typ='rt'`.
8. Write via C8.1 atomic primitive.

**Per-file transformation — archive lane:**

1. Read frontmatter via ruamel-safe (C8.3).
2. If `archival_reason` and `archival_refs` are already present and valid, skip as already migrated.
3. If contract-critical archive metadata is missing, apply the strict defaulting policy:
    - Preserve existing `archival_reason` / `archival_refs` when already valid.
    - Auto-set `archival_reason: completed` and `archival_refs: []` only when archive provenance is explicit and deterministic.
    - Otherwise record the file as a migration failure for manual triage; do not guess.
4. Preserve archive body text verbatim; no archive body rewrite, section parsing, or canonical vendor-field cleanup is required.
5. Write via C8.1 atomic primitive.

**Idempotency:** running the script twice is a no-op on a migrated board. The script applies lane-specific checks: active tasks are skipped when they already match the active-task shape (no `claimed_by`; timestamps already UTC `+00:00`; frontmatter already in canonical order with archive fields present), and archive files are skipped when `archival_reason` / `archival_refs` are already present and valid.

**Partial-failure recovery:** the script processes files one at a time; each per-file write is atomic (C8.1). A crash mid-run leaves already-migrated files migrated and un-migrated files untouched. Re-run resumes from where it left off via the idempotency check. No lockfile, no state file — the board itself is the checkpoint.

**Output:** console summary of (files scanned, files migrated, files skipped (already migrated), files failed) + stderr-printed per-file reasons for failures. No log file written (D43 respected).

**Verification:** user runs `git diff .owlbear/kanban/config.yml .owlbear/kanban/tasks/ .owlbear/kanban/archive/` and reads the per-file diffs. This is the "migration is one command, idempotent, verifiable" outcome (§5 outcome 4).

**Source:** C9 is a synthesis of the handoff item #4 (kickoff brief) + data panel stance + M3 landscape §c finding "Brief C is greenfield on migration tooling."

## C10 — Board-level activity stream + session derivation

**Decision:** Storage owns a single gitignored board-level runtime file, `.owlbear/kanban/activity.jsonl`, containing structured JSONL `ActivityEvent` records. Every mutating engine operation appends an event to this stream. `list_activity(...)` reads filtered raw events from the file; `list_sessions(filter=...)` is **derived at call time** from the same stream. There is **no separate session table**.

Canonical `ActivityEvent.source` values are `agent`, `cockpit`, and `engine`. `orchestrator` is retired with Brief B's role-view cleanup. Existing pre-Brief-C `activity.jsonl` files are not migrated or read compatibly; rollout deletes the old runtime file and starts a fresh canonical stream.

The activity stream is first-class admin data, not diagnostic logging. This keeps the persistent source layout honest:

- task files + archive remain the canonical board state,
- `activity.jsonl` is the canonical operational history surface for cockpit/admin use,
- session views are derived from `activity.jsonl`, not from task-frontmatter heuristics.

Compaction is part of the contract, but it must be semantic rather than arbitrary: `compact_activity_log(...)` preserves open sessions and recent raw events, while older closed-session spans may be compacted only in ways that preserve cockpit-visible history semantics.

**Source:** M4-Critic-BS1 (Brief B D31/D45 and Brief B paper §5 `list_sessions(filter="active")` resolve the gap). User-independent derivation.

---

## M4 Critic amendments (post-lock)

The M4 Critic pass surfaced 8 findings. Per-finding disposition recorded below; where amendments are material they are prefixed to the relevant decision at read time via this section (source of truth) rather than rewriting the C1-C9 text.

### AM-1 (Critic #1, superseded by Issue 3 split)

The original DR-2 expansion is withdrawn. Startup `sweep()` no longer performs repair/quarantine file-system mutations or AR creation. Those side effects move to explicit `repair_storage()`, which returns `list[RepairOutcome]` directly. Claim-only expiration handling remains on `sweep()`.

### AM-2 (Critic #2, accept) — C7 `list_tasks` carve-out for DUPLICATE_ID

C7's "list_tasks skips corrupt files silently" rule has ONE exception: **`ERR_CORRUPT_DUPLICATE_ID` hard-raises** per C6 mode 2 and Brief B D19. Rationale: duplicate IDs break cross-task reference integrity (depends_on, archival_refs, etc.) — silently skipping one of the duplicates would produce subtly-wrong result sets. The other 8 modes are local-file failures; skipping-with-omission is safe because refs to those tasks will naturally fail at the referring task.

C7 text should be read as: *"`list_tasks` skips corrupt files silently for 8 of 9 modes; `DUPLICATE_ID` raises `CorruptionError` from `list_tasks` itself."*

### AM-3 (Critic #3, reject) — New ERR_CORRUPT_* codes are authorised

Brief B D27 explicitly states: *"Storage I/O failure modes are out of Brief B scope (Brief C decides whether to surface them by mapping to a Brief B subclass or by defining a new layer)."* Brief B D57 is additive (D59 already added `ERR_TERMINAL_STATUS_INVALID`). Brief C adding 9 new `ERR_CORRUPT_*` codes under the existing `CorruptionError` subclass matches the pattern Brief B anticipates. **No DR-3 needed.** The 9 codes in C6 + C8.8 are recorded in Brief C paper as D57-extension codes; Brief B reviewers see them at paper merge.

### AM-4 (Critic #4, reject fix; minor clarification) — Quarantine sequence is graceful

C7 implies but does not state the quarantine-then-AR order explicitly. Locked order:

1. `os.replace(tasks/N-slug.md, quarantine/N-slug.md)` via C8.1 atomic primitive.
2. Attempt `create_task(title, body, tags=["type:user-action"])` via the Brief B engine API.
3. If step 2 raises (predicate failure, concurrent state, etc.), catch the exception and record `RepairOutcome(task_id, file_path, code, action="failed", detail=str(exc))`. The file **stays quarantined** — it will not leak back into `tasks/`. User sees the failure in `repair_storage()` output but must recover manually (file is already out of the scanned set).

No bootstrap hole: quarantine is irreversible from sweep's POV; AR failure is non-fatal; sweep continues to the next file. Storage does NOT bypass engine predicates to write ARs directly — predicate evaluation is Brief B's concern and Brief C respects the boundary (Brief B D15 default `non_impl_tags` includes `type:user-action`, so the predicate permits the AR).

### AM-5 (Critic #5, partial accept) — C9 idempotency check extension

C9 "already migrated" check extends to include:
- No `claimed_by` field (existing)
- All timestamps end in `+00:00` (existing)
- Frontmatter fields in C8.6 canonical order (existing)
- **`archival_reason` field present** (may be `null`; new)
- **`archival_refs` field present** (may be `[]`; new)

Body validation remains read-time only, not a migration transform — nothing to make idempotent for body.

### AM-6 (Critic #6, accept) — C1 heading grammar lock

C1 reference parser: **`markdown-it-py` with CommonMark defaults, no custom extensions.** This locks heading grammar transitively: ATX headings require a space (`## Heading`); `##Heading` (no space) is content, not a section boundary. Setext headings (underline-style) are also valid section boundaries per CommonMark. C4's "`##Heading` preserved verbatim" still holds — it's preserved as content of the current section, not promoted to a new section.

### AM-7 (Critic #7, reject) — No recursion hazard

Claim: a corrupt AR triggers quarantine→AR recursion. Analysis:
- Quarantined files live in `quarantine/`, outside sweep's `tasks/` scan — they are never re-scanned.
- Freshly-created ARs (AM-4 step 2) are written via C8.1 with valid Pydantic-validated frontmatter; they cannot be corrupt by construction.
- The only path to a "corrupt AR" is a user or external process mutating the AR file after creation. Each such mutation produces at most one new AR per sweep run, proportional to user-induced corruption events. This is correct behaviour, not an unbounded loop.

No `type:corruption-ar` exemption tag is added. No code changes to C7.

### AM-BS1 (Critic BS1, accept as C10) — See C10 above

### Summary of Critic pass

- **Accepted as amendments** (4): AM-1, AM-2, AM-5, AM-6.
- **Accepted as new C-decision** (1): C10.
- **Clarifications only, no material change** (1): AM-4.
- **Rejected on merit with argument** (2): AM-3 (D27 authorises), AM-7 (no recursion path).

No further Critic round needed — remaining disagreements are dispositioned with reasoning. Ready for M5 (Brief writing).

---

## M5 Critic amendments (post-assembled-brief review)

The M5 Critic pass on the assembled brief (paper-c.md + brief.md + decisions.md) surfaced 8 findings, all valid against Brief B contracts that the M4 Critic could not see (M4 had only decisions.md). Per-finding disposition recorded as AM-9..AM-16.

### AM-9 (M5 #1, accept) — ID allocation order locked

C8.2 is amended to lock the order: `acquire flock → load_config → save_config(next_id += 1) → release flock → write_task`. Rationale: if a crash occurs between `save_config` and `write_task`, the next_id is "burned" (no task at that ID; the next `create_task` uses the following ID). Burn is benign — no duplicate IDs are possible. The reverse order (write_task before save_config) would leave next_id stale, allowing a subsequent `create_task` to collide with an existing ID. Multi-file atomicity is impossible with two files; the chosen order makes crash recovery converge to a safe state.

Paper-c.md §3.3 is the source of truth; C8.2 is rewritten to match.

### AM-10 (M5 #2, accept) — AR create_task call corrected to Brief B signature

Paper §4.4 quarantine sequence is amended to call Brief B `create_task` with its locked signature (Brief B paper-integration.md §1.4):

```python
ar_body_str = render_body(
    [
        Section(heading=None, level=0, content=""),
        Section(heading="Quarantined file", level=2, content=f"- code: {C}\n- path: {dest}\n- detail: {detail}\n"),
    ]
)
response = engine.create_task(
    title=f"Quarantined task file: {F.name}",
    body=ar_body_str,  # str, not list[Section]
    priority="needed",
    tags=["type:user-action"],
    # NO status arg — tasks created at BoardConfig.entry_status per Brief B D50
)
```

Brief B's `create_task` takes `body: str` (markdown), not `list[Section]`, and returns the created task envelope rather than a bare ID. Storage renders the section list to a markdown string before calling; if it needs the created task ID, it reads `response.id`. No status parameter exists.

### AM-11 (M5 #3, accept) — Predicate matching is case-insensitive, whitespace-stripped

Brief B D56 + paper-integration.md line 45 lock section/heading matching as **case-insensitive, whitespace-stripped**. Paper §6.1 and AC-C39 are amended:

- `required_sections`: matches `Section.heading` case-insensitively, with surrounding whitespace stripped, per Brief B D56.
- `require_list_in_section`: same matching rules for the heading lookup.

Brief C does NOT change Brief B D64 semantics — the substrate changes from regex-over-rendered-markdown to AST-traversal-over-`list[Section]`, but the comparison rule (case-insensitive, whitespace-stripped) is preserved verbatim from Brief B.

### AM-12 (M5 #4, accept as new C11) — Engine-init migration check

**Decision (C11):** On `KanbanEngine.__init__`, the engine scans active task files (`tasks/*.md`) and raises `MigrationRequiredError` if any file contains a `claimed_by` field in its frontmatter. The error message points the user to `uv run kanban-migrate`.

```python
class MigrationRequiredError(KanbanError):
    """Raised at engine init if active board has unmigrated files.

    code = "ERR_MIGRATION_REQUIRED"
    user_message includes pointer to `uv run kanban-migrate`.
    """
```

`ERR_MIGRATION_REQUIRED` is added to the Brief C ERR_* code set (paper §4.1 + Brief B D57 extension via the same lineage as ERR_CORRUPT_*).

This converts the "pull new code, forget migration" silent-failure path into a loud, actionable error at first engine instantiation. It runs once per process startup (no per-call overhead).

### AM-13 (M5 #5, accept) — Archive exempt from claimed_by-forbidden rule

**Amend C7 / paper §4.1 mode 3:** `claimed_by`-present detection fires ONLY for files in `tasks/`. Files in `archive/` may carry `claimed_by` as a legacy artifact; on read, the field is **silently stripped** before passing to the `Task` model.

Implementation: `read_task` accepts a `from_archive: bool = False` flag (or detects via path); if true, frontmatter is filtered to drop `claimed_by` before Pydantic construction. The `Task` model itself does not change — `extra="allow"` continues to handle legacy vendor fields (`class`, `started`, `completed`); `claimed_by` is a special-case strip because it is in the canonical schema as forbidden.

Active-board `claimed_by` remains forbidden legacy state in `tasks/`: `detect_corruption` reports mode 3, `KanbanEngine.__init__` surfaces `ERR_MIGRATION_REQUIRED` per C11, and runtime `sweep()` never fixes it. Canonical remediation is task-lane migration, not opportunistic repair during normal runtime.

### AM-14 (M5 #6, accept) — sweep does not append to body

Paper §4.5 step 1 is amended: expired-claim release clears `claimed_at` and advances `updated` per Brief B D14 + Brief B paper §5 `sweep()` contract. **It does NOT append a release event to the task body.** Body-append was Brief C drift; Brief B's sweep contract has no body mutation. Activity events belong in the board-level `activity.jsonl` stream, not inside task bodies.

### AM-15 (M5 #7, accept) — Session derivation made implementable

Paper §7.2 is amended:

1. **`SessionRecord` defined explicitly in paper §7.2** (not by ref to current dataclass; the current dataclass is the implementation, not the contract).
2. **`claim_timeout` parsed from `Ns/Nm/Nh/Nd` string format** per Brief B D29:

3. **Canonical session shape** is `task_id`, `task_status_at_start`, `state`, `started_at`, `ended_at`, `outcome`, `duration_s`. `state` is the cockpit/history classifier for one claim cycle; task-level claimed state remains on task projections. Stale `agent` and `fail` terminology are removed.

Per security panel suggestion in Brief B (stances/security.md line 184): claim_timeout validation is eager — `_parse_duration` is also called at config load time so a typo surfaces at startup, not at first claim.

### AM-16 (M5 #8, accept) — Round-trip promise softened

Paper §2.5 + C4 are amended:

- **Within-section content** is byte-exact on round-trip (modulo CRLF→LF normalisation). This includes trailing whitespace, blank lines within content, indentation.
- **Heading style is normalised to ATX**. Setext headings (text underlined by `===` or `---`) are still recognised on read and converted to ATX on write. The Section model carries `(heading, level, content)`; it does not preserve heading-marker style by design.
- **Inter-section blank lines** are preserved (count of blank lines between sections survives round-trip).
- **`##Heading` (no space)** is content of the current section — never a heading. C4's "##Heading preserved verbatim" claim holds because it lives inside `Section.content`.

The C4 claim "byte-identical reads guaranteed after first write" is amended to: "byte-identical reads guaranteed after first write, given that all headings are ATX-style (the post-first-write canonical form)."

### Activity.jsonl story unified (BS3)

Single statement, propagated to all three files: **`activity.jsonl` is promoted to a first-class, gitignored board-level runtime activity stream. Storage owns append/query/compaction semantics; cockpit/admin history and `list_sessions(filter=...)` derive from it. It is not a diagnostic log and it is not left inert post-migration.**

### Summary of M5 Critic pass

- **Accepted as amendments to existing decisions** (6): AM-9, AM-10, AM-11, AM-13, AM-14, AM-16.
- **Accepted as new C-decision** (1): C11 (AM-12 introduces it).
- **Accepted as scope clarification** (1): AM-15 (paper §7.2 made implementable).
- **Documentation unification** (1): activity.jsonl story.
- **Rejected**: 0.

Paper-c.md is amended inline per AM-9..AM-16. Brief.md gains a single line in §3 referencing the M5 amendments. Decisions C1..C11 + amendments AM-1..AM-16 are the locked decision set. Ready for M6 handoff.
