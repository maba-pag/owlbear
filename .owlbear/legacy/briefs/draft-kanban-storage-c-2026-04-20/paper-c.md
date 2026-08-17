# Paper C — Storage Layer Integration (Brief B → Brief C)

**Status:** M5 draft — normative source for engine-implementation decomposition.

This paper is the planner-decomposable contract for the kanban storage layer (`serve/kanban/src/owlbear_kanban/storage.py` and supporting modules). Brief C cannot revisit Brief B decisions; it can only specify how Brief B's storage assumptions become concrete on-disk and in-memory behaviour.

References:

- `decisions.md` — Brief C decisions C1..C11 plus AM-1..AM-16.
- `../draft-kanban-engine-b-2026-04-20/paper-integration.md` — Brief B normative source.
- `../draft-kanban-engine-b-2026-04-20/decisions.md` — Brief B decisions D1..D65.

---

## §1 — Storage Module Surface

### 1.1 Module location and import

```
serve/kanban/src/owlbear_kanban/storage.py        # public surface
serve/kanban/src/owlbear_kanban/storage_io.py     # atomic-write primitive (private)
serve/kanban/src/owlbear_kanban/body_parser.py    # markdown-it-py wrapper (private)
serve/kanban/src/owlbear_kanban/activity_store.py # activity.jsonl append/query/compaction helpers
serve/kanban/src/owlbear_kanban/corruption.py     # CorruptionError + 9 codes
serve/kanban/src/owlbear_kanban/migrate.py        # kanban-migrate entry point
```

`task_io.py` is removed (its responsibilities split across `storage.py`, `storage_io.py`, `body_parser.py`).

### 1.2 Public types

```python
class Section(BaseModel):
    heading: str | None  # None for preamble (content before first heading)
    level: int  # 0 for preamble; 1..6 for ATX/Setext heading depth
    content: str  # body text under the heading, verbatim except CRLF→LF


class CorruptionError(KanbanError):
    code: str  # one of the 9 ERR_CORRUPT_* codes (§4.1)
    user_message: str
    file_path: str | None  # absolute path; None if pre-parse failure with no file context


class RepairOutcome(BaseModel):
    task_id: int | None  # None if file unparseable enough to extract id
    file_path: str
    code: str  # ERR_CORRUPT_* code
    action: Literal[
        "fixed", "quarantined", "failed"
    ]  # failed = repair pass incomplete, including AR-creation failure after quarantine
    detail: str | None  # human-readable note


class ActivityEvent(BaseModel):
    timestamp: str  # ISO-8601 UTC
    task_id: int | None  # None allowed for board-level maintenance events (e.g. sweep)
    action: str  # structured event verb, e.g. claim/edit/move/end_work/sweep
    source: str  # "agent" | "cockpit" | "engine"
    detail: str  # human-readable structured detail payload


class ActivityCompactionResult(BaseModel):
    before_bytes: int
    after_bytes: int
    records_compacted: int
```

`Task.body: list[Section]` per Brief B D7/D26 + Brief C C1.

### 1.3 Public functions (storage.py)

```python
def read_task(path: Path) -> Task: ...
def write_task(task: Task, kanban_dir: Path) -> Path: ...
def write_task_if_unchanged(task: Task, expected_updated: str, kanban_dir: Path) -> Path: ...
def write_task(task: Task, kanban_dir: Path) -> Path: ...
def list_task_files(kanban_dir: Path) -> list[Path]: ...
def list_archive_files(kanban_dir: Path) -> list[Path]: ...
def move_to_archive(task_id: int, kanban_dir: Path) -> Path: ...
def move_to_quarantine(file_path: Path, kanban_dir: Path) -> Path: ...
def allocate_next_id(kanban_dir: Path) -> int: ...
def load_config(kanban_dir: Path) -> BoardConfig: ...
def save_config(config: BoardConfig, kanban_dir: Path) -> None: ...
def parse_body(markdown: str) -> list[Section]: ...
def render_body(sections: list[Section]) -> str: ...
def append_activity_event(event: ActivityEvent, kanban_dir: Path) -> None: ...
def list_activity_events(
    kanban_dir: Path,
    *,
    task_id: int | None = None,
    action: str | None = None,
    source: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[ActivityEvent]: ...
def compact_activity_log(kanban_dir: Path, before_dt: datetime | None = None) -> ActivityCompactionResult: ...
def scan_and_fix(kanban_dir: Path, config: BoardConfig) -> list[RepairOutcome]: ...
def detect_corruption(path: Path, config: BoardConfig) -> CorruptionError | None: ...
def attempt_repair(path: Path, code: str, config: BoardConfig) -> RepairOutcome: ...
```

### 1.4 Engine consumption boundary

The engine (`engine.py`) imports only from `storage`. No engine code touches `task_io`, raw YAML, or filesystem primitives directly. `KanbanEngine.__init__` resolves all paths through `storage.list_task_files` / `storage.read_task`. This is the boundary that `tests/test_package_boundary.py` enforces (the boundary test gains a new rule: only `engine.py` may import from `storage`).

### 1.5 Engine-init migration check (per C11 + AM-12)

`KanbanEngine.__init__` performs a one-time scan of `tasks/*.md`. If ANY active task file contains a `claimed_by` field in its frontmatter, the engine raises:

```python
class MigrationRequiredError(KanbanError):
    """Active board has unmigrated files.

    code = "ERR_MIGRATION_REQUIRED"
    user_message includes pointer to `uv run kanban-migrate`.
    """
```

This check converts the silent-failure path ("pull new code, forget migration" → list_tasks silently skips most tasks per AM-2) into a loud, actionable error at first engine instantiation. Runs once per process startup; no per-call overhead. `ERR_MIGRATION_REQUIRED` is added to the Brief C ERR_* code set (extends Brief B D57 via the same lineage as ERR_CORRUPT_*; see §9.2).

---

## §2 — On-Disk Layout

### 2.1 Directory structure

```
.owlbear/kanban/
├── config.yml                  # BoardConfig (existing file; Lane C rewrites legacy schema in place)
├── activity.jsonl              # gitignored board-level runtime activity stream
├── tasks/
│   ├── 1001-some-slug.md
│   ├── 1002-another.md
│   └── ...
├── archive/
│   ├── 0001-old-task.md
│   └── ...
├── quarantine/                 # NEW (created lazily on first quarantine event)
│   └── 1042-broken.md
└── .next_id.lock               # ID allocation flock (existing, unchanged)
```

`quarantine/` directory is auto-created by `move_to_quarantine` on first use; not pre-created.

### 2.2 Filename grammar

`{id}-{slug}.md` where `id` matches frontmatter `id` exactly (post-AM-2 carve-out: ID/filename mismatch is one of the 9 corruption modes and is auto-fixable). `slug` is lowercase ASCII with `-` separators; storage does not enforce the slug — agents may rename freely as long as `{id}-` prefix is preserved. ID/filename mismatch detection compares the integer prefix only.

### 2.3 Canonical frontmatter order (per C8.6)

```yaml
---
id: 1042
title: "Task title"
status: todo
priority: needed
created: "2026-04-20T10:00:00+00:00"
updated: "2026-04-20T10:00:00+00:00"
tags: [tag1, tag2]
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
```

- `claimed_by` is FORBIDDEN on disk in active task files (`tasks/`) per Brief B D11; archive files are exempt legacy inputs and are stripped on read per AM-13. Detection: see §4.1 mode 3.
- `claimed_at` is the only claim-related field; ISO-8601 UTC `+00:00` per Brief B D14.
- `extra="allow"` on the Pydantic `Task` model: legacy archive vendor fields (`class`, `started`, `completed`) round-trip without enforcement (per C8.6 note).
- `archival_reason` enum from `BoardConfig.archival_reasons`; `null` for non-archived tasks.

### 2.4 Body grammar

The Markdown body following the closing `---` is parsed by `markdown-it-py` with CommonMark defaults, no custom extensions, no plugins. Section boundaries:

- ATX headings (`# H1`, `## H2`, ..., `###### H6`) — REQUIRE space after `#` per CommonMark.
- Setext headings (text underlined by `===` or `---`) — also valid section boundaries.
- Lines starting with `##Heading` (no space) are content of the current section, NOT a new section.
- Content before the first heading is a `Section(heading=None, level=0, content=...)`.
- Code-block-fenced content is never treated as a heading even if it contains heading-like lines (markdown-it-py handles this natively).

`Section.content` is the verbatim text under the heading (excluding the heading line itself), with CRLF normalised to LF (C4). Trailing whitespace within content is preserved (it is meaningful Markdown — `<br>` semantics).

### 2.5 Round-trip guarantee (per AM-16)

After the first write through Brief C storage, the file content is byte-identical on subsequent unmodified reads + writes, **given that all headings are ATX-style** (the post-first-write canonical form). Specifically:

- **Within-section content** is byte-exact (modulo CRLF→LF). Trailing whitespace, blank lines within content, and indentation are preserved.
- **Heading style is normalised to ATX on write.** Setext headings (text underlined by `===` or `---`) are recognised on read and converted to ATX on write. The `Section` model carries `(heading, level, content)` only; it does not preserve heading-marker style.
- **Inter-section blank lines** preserved (count survives round-trip).
- **`##Heading` (no space)** is content of the current section, never a heading per CommonMark; preserved verbatim inside `Section.content`.

`parse_body(render_body(sections)) == sections` for all `sections` produced by `parse_body`.

---

## §3 — Atomic Write Primitive

### 3.1 The sequence

Every content-writing task-file operation — `write_task`, migration rewrites, and AR file creation — uses:

```python
fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=".md")
try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)
    if hasattr(os, "O_DIRECTORY"):  # POSIX
        dir_fd = os.open(str(target.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
except Exception:
    if Path(tmp).exists():
        Path(tmp).unlink()
    raise
```

Lives in `storage_io.py:atomic_write(target: Path, content: str) -> None`. All higher-level content-write functions (`write_task`, `save_config`, migration rewrites, AR file creation) call it. Quarantine moves use `os.replace` into `quarantine/` with the same atomic-rename semantics, but they do not rewrite file content via `atomic_write`.

### 3.2 Concurrency guarantees

Single-laptop reality: cockpit (FastAPI) and the MCP server are typically the two writer processes; multi-agent autonomous runs can produce real cross-process write contention against the same task file. The atomic primitive guarantees:

- A reader that opens `target` always sees either the pre-write content or the post-write content — never partial bytes.
- A crash mid-write (between `mkstemp` and `os.replace`) leaves `target` untouched and a `.tmp-XXXX` file in the parent directory; `list_task_files` filters out `.tmp-*` patterns.
- Directory entry fsync ensures the rename survives a power loss on POSIX systems.

**Per-task CAS via `write_task_if_unchanged`.** For read-modify-write windows that need consistency across concurrent writers (engine OCC on Cockpit edits/moves; lazy-release of expired claims in `start_work`), `write_task_if_unchanged(task, expected_updated, kanban_dir)`:

1. Acquires `flock(LOCK_EX)` on `tasks/.<id>.lock` (or `archive/.<id>.lock` for archive writes).
2. Re-reads the on-disk file via `read_task`.
3. Compares `current.updated == expected_updated`. Mismatch → release lock, raise `ConcurrencyError(code="ERR_STALE", user_message="task {id} changed since read; reload and retry")`.
4. Otherwise calls `write_task` (which uses the atomic primitive) and releases the lock.

The lock file lives next to the task file and is created on demand. Lock files are gitignored (paper-c §2.1) and never quarantined. Engine consumers (`AgentView` writes that don't take an `expected_updated` parameter) continue to use plain `write_task` directly, accepting last-writer-wins semantics by design (per Brief B D46 — OCC is Cockpit-only).

### 3.3 ID allocation flow (per AM-9)

Locked order. Flow per `create_task`:

```
acquire flock(.next_id.lock)
config = load_config(kanban_dir)
new_id = config.next_id
config.next_id += 1
save_config(config, kanban_dir)        # uses atomic_write
release flock
write_task(Task(id=new_id, ...), kanban_dir)   # uses atomic_write
```

**Crash semantic.** Multi-file atomicity is impossible across `config.yml` and the new task file. The chosen order makes crash recovery converge to a safe state:

- Crash between `save_config` and `write_task`: the next_id is **burned** (no task at that ID exists). The next `create_task` allocates the following ID. **No duplicate IDs are possible.** Burn is benign — ID space is unbounded; observability of burns is via gaps in `tasks/` filenames.
- Reverse order (write_task before save_config) is REJECTED: a crash there would leave next_id stale, allowing a subsequent `create_task` to collide with an existing ID. Burn is preferred over collision.

Flock is `fcntl.flock(LOCK_EX)` on Unix, `msvcrt.locking(LK_LOCK)` on Windows (cross-platform shim already exists in current code; preserved).

### 3.4 Failure modes

- `OSError` during `mkstemp` (disk full, permission) → propagates as `OSError`; engine surfaces as 500.
- `OSError` during `os.replace` (target read-only, etc.) → `OSError` propagates; `.tmp-*` file is cleaned up.
- ID allocation flock acquisition timeout: not currently bounded; future tightening may add a 5s timeout. Out of scope for Brief C.

---

## §4 — Corruption Detection and Handling

### 4.1 The 9 corruption modes

Each mode is detected at read time (inside `read_task` or `detect_corruption`). Codes extend Brief B D57 under the `CorruptionError` subclass per Brief B D27 authorisation.

| # | Code | Detection algorithm | Disposition |
|---|---|---|---|
| 1 | `ERR_CORRUPT_DELIMITERS` | File does not start with `---\n` OR no closing `---\n` line within first 200 lines | Quarantine + AR |
| 2 | `ERR_CORRUPT_DUPLICATE_ID` | Two files in `tasks/` resolve to same `id` after frontmatter parse | Quarantine BOTH + AR; **hard-raise from `list_tasks`** (carve-out per AM-2) |
| 3 | `ERR_CORRUPT_MISSING_FIELD` | Required field absent (`id`, `title`, `status`, `priority`, `created`, `updated`); also fires for forbidden field present (`claimed_by` **in `tasks/` only** per AM-13; archive files are exempt) | Auto-fix if safe default exists (see §4.2); else quarantine + AR. Special case: `claimed_by` in `tasks/` is treated as legacy unmigrated state and triggers the engine-init migration gate per §1.5 / AC-C47. |
| 4 | `ERR_CORRUPT_TYPE_MISMATCH` | Pydantic validation fails on field type (`id: "1034"`, `blocked: "true"`, etc.) | Coerce if trivially safe (see §4.2); else quarantine + AR |
| 5 | `ERR_CORRUPT_YAML_PARSE` | ruamel.yaml raises during frontmatter parse | Quarantine + AR |
| 6 | `ERR_CORRUPT_ID_FILENAME_MISMATCH` | Filename `{N}-slug.md` has frontmatter `id: M` with `N ≠ M` | Auto-fix: rename file to match frontmatter (content wins) |
| 7 | `ERR_CORRUPT_DUPLICATE_LOCATION` | Same task ID present in both `tasks/` and `archive/` | Auto-fix: archive wins (terminal state); remove from `tasks/` |
| 8 | `ERR_CORRUPT_INVALID_STATUS` | `status` not in `BoardConfig.statuses` ∪ `{"archived"}` | Quarantine + AR |
| 9 | `ERR_CORRUPT_INVALID_PRIORITY` | `priority` not in `BoardConfig.priorities` | Auto-fix: coerce to `config.priorities[0]` |

### 4.2 Auto-fix matrix

| Mode | Field | Safe default | Source |
|---|---|---|---|
| 3 | `priority` | `config.priorities[0]` (first/highest priority) | BoardConfig |
| 3 | `tags` | `[]` | hardcoded |
| 3 | `depends_on` | `[]` | hardcoded |
| 3 | `blocked` | `false` | hardcoded |
| 3 | `block_reason` | `null` | hardcoded |
| 3 | `claimed_at` | `null` | hardcoded |
| 3 | `archival_reason` | `null` | hardcoded (per C3) |
| 3 | `archival_refs` | `[]` | hardcoded (per C3) |
| 3 | `parent` | `null` | hardcoded |
| 3 | `id`, `title`, `created` | NO SAFE DEFAULT | quarantine instead |
| 4 | string `id` | `int(value)` if `value.isdigit()` else quarantine | coerce |
| 4 | string `bool` | `True` if `value.lower() == "true"` else `False` if `value.lower() == "false"` else quarantine | coerce |

If `claimed_by` is present on disk in `tasks/` (forbidden per Brief B D11), `detect_corruption` reports mode 3 with `detail="forbidden field claimed_by present"`. Normal engine startup then surfaces `MigrationRequiredError(code="ERR_MIGRATION_REQUIRED")` per §1.5 / AC-C47; runtime `sweep()` does not remove the field. Canonical remediation is `kanban-migrate --lane tasks`.

**Archive exemption (per AM-13):** files in `archive/` may carry `claimed_by` as a legacy artifact. On read, `read_task` for archive files silently strips `claimed_by` from the frontmatter before Pydantic construction. The `Task` model itself is unchanged — `extra="allow"` continues to handle vendor fields (`class`, `started`, `completed`); `claimed_by` is a special-case strip because it is in the canonical schema as forbidden. Implementation: `read_task(path, from_archive: bool = False)` or path-based detection.

### 4.3 Trigger model

Repair fires ONLY inside `repair_storage()`. Runtime read paths behave as follows:

| Caller | Mode 1, 3-9 | Mode 2 (DUPLICATE_ID) |
|---|---|---|
| `list_tasks` | Skip silently; omit from result | Hard-raise `CorruptionError` (AM-2 carve-out) |
| `show_task(id)` | Hard-raise `CorruptionError` | Hard-raise `CorruptionError` |
| `storage.scan_and_fix()` (called by `engine.repair_storage()`) | Apply auto-fix or quarantine | Quarantine both files |
| `engine.repair_storage()` (after storage phase) | Creates AR tasks for each `action="quarantined"` outcome | Creates AR tasks for both quarantined outcomes |
| `engine.scan_corruption()` | Returns `CorruptionError` entries (read-only, no writes) | Returns `CorruptionError` entry |

No corruption is repaired outside `repair_storage()`. This is the explicit-repair architecture — runtime paths tolerate or escalate; startup `sweep()` remains lightweight claim maintenance.

### 4.4 Quarantine + AR sequence (per AM-4 + AM-10)

The repair is split across two layers to avoid a circular import (`engine.py` imports `storage`; `storage` cannot import back into `engine`).

**Phase 1 — `storage.scan_and_fix(kanban_dir, config)` (file operations only):**

```
for each file F in tasks/ + archive/:
    error = detect_corruption(F, config)
    if error is None:
        continue
    outcome = attempt_repair(F, error.code, config)
    # attempt_repair handles: auto-fix (write healed file) or
    # quarantine (os.replace F → quarantine/, create quarantine/ if absent)
    # action is "fixed" | "quarantined" | "failed"
    # AR tasks are NOT created here
    outcomes.append(outcome)
return outcomes   # action="quarantined" items need AR creation at engine layer
```

**Phase 2 — `engine.repair_storage()` (AR creation):**

```
phase1_outcomes = storage.scan_and_fix(self._kanban_dir, self._config)
for outcome in phase1_outcomes:
    if outcome.action != "quarantined":
        continue
    try:
        ar_body_str = render_body([
            Section(heading=None, level=0, content=""),
            Section(
                heading="Quarantined file",
                level=2,
                content=f"- code: {outcome.code}\n- path: {outcome.file_path}\n",
            ),
        ])
        response = self.create_task(
            title=f"Quarantined task file: {Path(outcome.file_path).name}",
            body=ar_body_str,
            priority="needed",
            tags=["type:user-action"],
            # NO status arg — Brief B D50 locks creation at BoardConfig.entry_status
        )
        outcome.detail = f"AR #{response.id} created"
    except Exception as exc:
        outcome.action = "failed"
        outcome.detail = f"AR creation failed: {exc}"
return phase1_outcomes
```

The quarantined file is **always** moved before AR creation is attempted. AR creation failure does not restore the file. The file is out of the active set regardless.

`type:user-action` is in `BoardConfig.non_impl_tags` default per Brief B D15, so the test-section predicate does not fire on the AR.

### 4.5 sweep() contract

```python
def sweep(self) -> list[int]:
    """Reconcile claim timeouts only.

    Behaviour (per AM-14: no body mutation):
       1. Walk active tasks/. For each task with claimed_at expired
           per BoardConfig.claim_timeout, remember the observed expired
           claimed_at value and perform compare-and-clear per Brief B D36:
           clear claimed_at and advance updated per Brief B D14 only if
           the task still carries that same expired claim when written.
           Append id to released only when the clear actually occurs.
           (No body mutation; no quarantine; no AR creation.)
       2. Return released.
    """
```

### 4.6 scan_and_fix() contract (storage layer)

```python
def scan_and_fix(kanban_dir: Path, config: BoardConfig) -> list[RepairOutcome]:
    """Phase 1 of the two-phase repair.

    Scans tasks/ and archive/ for corruption. For each file:
    - Auto-fixable modes: apply fix and write healed file (action="fixed").
    - Quarantinable modes: move file to quarantine/ (action="quarantined").
    - Unquarantinable: record failure (action="failed").

    Does NOT create AR tasks. AR creation is Phase 2 and lives in
    engine.repair_storage() to avoid a circular import.
    Returns list[RepairOutcome] where action="quarantined" items need AR.
    """
```

### 4.7 repair_storage() contract (engine layer)

```python
def repair_storage(self) -> list[RepairOutcome]:
    """Two-phase user-triggered repair exposed via CockpitEngineView.

    Phase 1: calls storage.scan_and_fix(kanban_dir, config).
    Phase 2: for each action="quarantined" outcome, calls
             self.create_task(...) to create the Action Request task.
             Updates outcome.detail with AR id on success; sets
             action="failed" with detail on AR creation failure.
    Returns merged list[RepairOutcome].
    """
```

### 4.8 CorruptionError shape (C8.8)

```python
class CorruptionError(KanbanError):
    """Raised when storage detects unrepairable on-disk state.

    Subclass of KanbanError per Brief B D27 + D57. HTTP 500 via
    Cockpit adapter. Always carries a code from the 9 ERR_CORRUPT_*
    set defined in §4.1.
    """

    def __init__(self, code: str, user_message: str, file_path: str | None = None):
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message
        self.file_path = file_path
```

---

## §5 — Migration Script

### 5.1 Entry point

Add to `serve/kanban/pyproject.toml` `[project.scripts]`:

```toml
kanban-migrate = "owlbear_kanban.migrate:main"
```

Invocation: `uv run kanban-migrate [--dry-run] [--lane tasks|archive|config|all] [--kanban-dir PATH]`. Default `--kanban-dir` resolves via the same logic as `KanbanEngine` (CWD walk for `.owlbear/kanban/`). Default lane is `all`.

### 5.2 Scope (per C9)

- Active task files: `{kanban_dir}/tasks/*.md` — full migration to the Brief B + Brief C active-task shape.
- Archive files: `{kanban_dir}/archive/*.md` — metadata-only normalization of the contract-critical archive fields required by Brief A (`archival_reason`, `archival_refs`). Archive body text and legacy vendor fields are not otherwise normalised.
- Config file: `config.yml` — schema format migration (Lane C). Legacy dict-statuses, dropped fields, new required fields.
- Activity stream: existing legacy `activity.jsonl` is **not migrated**. It is runtime data, not canonical board state. If present at cutover, remove it and let the new engine/backend recreate a fresh canonical file on first append.
- Quarantine untouched (it shouldn't exist at migration time, but if it does, ignored).

Lane selection is controlled by `--lane`. `tasks`, `archive`, and `config` run only the named lane. `all` runs all three lanes in the documented order.

### 5.3 Per-file algorithm

**Lane A — active tasks.** For each `*.md` in `tasks/`:

1. Read frontmatter via `ruamel.yaml.YAML(typ='safe')`.
2. **Idempotency check (per AM-5):** if ALL of the following hold, skip and report "already migrated":
   - No `claimed_by` field.
   - All timestamp fields end with `+00:00`.
   - `archival_reason` field is present (may be `null`).
   - `archival_refs` field is present (may be `[]`).
   - Frontmatter fields are in C8.6 canonical order.
3. Otherwise apply transformations:
   - Remove `claimed_by` field if present (D11).
   - Add `archival_reason: null` if absent (C3).
   - Add `archival_refs: []` if absent (C3).
   - Normalise timestamp fields (`created`, `updated`, `claimed_at`) to UTC ISO-8601 with explicit `+00:00`. Use `datetime.fromisoformat` then `astimezone(timezone.utc)` then `isoformat()`.
4. Validate body via `parse_body`. If unparseable (markdown-it-py errors are extremely rare with CommonMark defaults; this is a sanity gate), record failure and skip without writing.
5. Reorder frontmatter per C8.6 via ruamel `typ='rt'` (preserve any vendor comments).
6. Render `frontmatter + "---\n" + body_text` and call `storage_io.atomic_write(target, content)`.

**Lane B — archive metadata normalization.** For each `*.md` in `archive/`:

1. Read frontmatter via `ruamel.yaml.YAML(typ='safe')`.
2. If `archival_reason` and `archival_refs` are already present and valid, skip and report "already migrated".
3. Otherwise apply the strict defaulting policy:
    - Preserve existing `archival_reason` / `archival_refs` when already valid.
    - Auto-set `archival_reason: completed` and `archival_refs: []` only when archive provenance is explicit and deterministic.
    - Otherwise record failure for manual triage and skip without writing.
4. Preserve archive body text verbatim; no archive body parse or rewrite is required beyond reusing the existing body bytes when persisting the updated frontmatter.
5. Write via `storage_io.atomic_write(target, content)`.

### 5.4 Lane C — config.yml migration

The existing `config.yml` uses a legacy schema incompatible with the new `BoardConfig`. Lane C transforms it in-place using a simple Python dict-to-dict rewrite — no complex tooling.

1. Read `config.yml` via `ruamel.yaml.YAML(typ='rt')` (round-trip to preserve comments).
2. **Idempotency check:** report "already migrated" and skip only if `statuses` is already a list of strings, all required new-schema keys are present (`entry_status`, `wave_size`, `agent_map`, `agent_types`, `agent_compatibility`, `non_impl_tags`, `archival_reasons`, `status_predicates`, `claim_timeout`, `next_id`, `priorities`), and no removed legacy keys (`board`, `version`, `tasks_dir`, `archive_dir`, `defaults`, `activity_log`) remain.
3. Apply transformations:
   - `statuses`: extract the status name string from each dict entry (first string value or `entry['name']` key). E.g. `[{name: research, ...}, ...]` → `["research", ...]`.
   - `priorities`, `claim_timeout`, `next_id`: kept as-is.
   - **Dropped fields** (`board`, `version`, `tasks_dir`, `archive_dir`, `defaults`, `activity_log`): removed. Directory layout is now implicit (`kanban_dir/tasks/`, `kanban_dir/archive/`); other fields are replaced by the new schema.
   - **New fields with empty stubs** (require manual fill-in): `agent_map: {}`, `agent_types: {}`, `agent_compatibility: {}`.
    - **New fields with defaults**: `entry_status: <first status in statuses list>`, `wave_size: 4`, `non_impl_tags: ["research", "docs", "type:config", "type:docs", "test", "type:test", "agent", "quality", "type:user-action"]`, `archival_reasons: ["completed", "deprecated", "dropped", "duplicate", "wontfix"]`, `status_predicates: {}`.
4. Write via `atomic_write(config_path, new_yaml_content)`.
5. Print a post-migration warning if any stub fields were written:
   ```
   WARNING: config.yml migrated. agent_map, agent_types, and agent_compatibility
   are empty stubs — populate them before starting the engine.
   See serve/kanban/README.md for the standard pipeline configuration.
   ```

**Lane C idempotency:** If Lane C is re-run after the new fields are manually populated, step 2 detects the already-migrated schema only when the full new-schema key set is present and legacy-only keys are gone, then skips without overwriting user edits. Partially migrated configs continue through Lane C until they satisfy the full schema shape.

### 5.4a Cutover sequence

For the dev/main dual-checkout workflow, migration is not treated as a single opaque step:

1. Rehearse `--lane config --dry-run` early.
2. Run `--lane config` before final cutover so config incompatibilities are discovered while task files are still untouched.
3. Run `--lane archive` when archive metadata normalisation is needed.
4. Delete any pre-Brief-C `activity.jsonl` file. The activity stream is reset at cutover rather than migrated.
5. If the config or archive lanes emit unresolved manual actions (for example empty config stubs or ambiguous archive metadata), materialise them as visible `type:user-action` tasks before running the final task migration.
6. Run `--lane tasks` last, immediately before merge/cutover.

**Note on `config.defaults.priority`** in the Brief C corruption auto-fix matrix (§4.2, C7): since `defaults` is dropped from `BoardConfig`, the auto-fix for `MISSING_FIELD priority` uses `config.priorities[0]` (first declared priority = highest priority = safest default).

### 5.5 Output

Stdout summary on completion:

```
Scanned:       154
Migrated:        92
Already up-to-date: 60
Failed:           2
```

For each failed file, stderr line: `FAIL {path}: {reason}`. No log file (D43 respected). Exit code 0 if `Failed == 0`, else 1.

### 5.6 Partial-failure recovery

Each per-file write is atomic (§3.1). A crash mid-run leaves migrated files migrated and untouched files untouched. Re-running the script resumes via the §5.3 step 2 idempotency check — already-migrated files are skipped, untouched files are processed. No lockfile, no state file: the board itself is the checkpoint.

### 5.7 Dry-run mode

`--dry-run` performs steps 1-2 of §5.3 for each file, prints what WOULD be migrated, and writes nothing.

### 5.8 Verification

User runs `git diff .owlbear/kanban/config.yml .owlbear/kanban/tasks/ .owlbear/kanban/archive/` and reads the per-file diffs. The diff is the human-readable migration report.

---

## §6 — Predicate DSL Over `list[Section]`

### 6.1 The three Brief B D64 keys (per AM-11)

Matching is **case-insensitive, whitespace-stripped** per Brief B D56 + paper-integration.md line 45. Brief C does NOT change Brief B D64 semantics; only the substrate changes (regex → AST traversal). The comparison rule is preserved verbatim from Brief B.

| Key | Brief B regex semantics (today) | Brief C structured semantics (Brief C delivery) |
|---|---|---|
| `required_sections` | regex `^##\s+{name}` over rendered body | match on `Section.heading` (case-insensitive, whitespace-stripped) per D56 |
| `require_list_in_section` | regex pair (heading + markdown list item) over rendered body | walk matching `Section` (case-insensitive heading lookup), parse content with markdown-it-py, assert at least one CommonMark list child (`bullet_list` or `ordered_list`) |
| `test_section_or_non_impl_tag` | combination of `required_sections=["Tests"]` + tag-set check | combination of structured `required_sections` + tag-set check (unchanged at the predicate level) |

### 6.2 Why no new keys (per C5)

Both Data's candidates (`required_frontmatter_field`, `section_not_empty`) are clean schema additions but no current pipeline failure demands them. Brief B §6 explicitly authorises incremental extension as separate decomposition tasks. Adding them speculatively in Brief C violates YAGNI.

### 6.3 Implementation note

The predicate engine (`predicates.py` in current code) takes a `Task` instance with `body: list[Section]`. The shift from "regex over rendered Markdown" to "AST traversal over `list[Section]`" is the structural reliability win cited in Brief C Outcome 3 — `##Heading` vs `## Heading` no longer affects predicate truth (one is a heading, the other is content; only headings are sections; predicates only see sections).

---

## §7 — Activity Stream and Session Derivation

### 7.1 `activity.jsonl` contract (per C10)

`activity.jsonl` is a **gitignored board-level runtime activity stream**, not a diagnostic log. One JSON object per line, each matching `ActivityEvent` (§1.2). Storage owns three responsibilities for this file:

There is **no backward-compatibility contract** for older activity-log shapes. Pre-Brief-C `activity.jsonl` files that lack the canonical `source` field are dropped at cutover and replaced by a fresh canonical stream. Readers and compaction logic may assume the file matches `ActivityEvent` exactly.

1. **Append** — every mutating engine operation appends one or more structured activity events.
2. **Query** — `list_activity_events(...)` filters by task, action, source, and time window for cockpit/admin reads.
3. **Compaction** — `compact_activity_log(kanban_dir, before_dt=None)` rewrites the file under a concrete retention rule:
   - **Cutoff:** `before_dt` (explicit ISO-8601 datetime) or, when `None`, the `ended_at` timestamp of the most recently closed session (safe auto-default).
   - **Open-session guard:** any entry that belongs to a session where `ended_at` is `None` (open session) is always retained, regardless of its timestamp.
   - **Hard floor:** always retain the last 500 entries by timestamp regardless of cutoff or session state (prevents catastrophic compaction on a small board).
   - Algorithm: (1) read all entries; (2) resolve `before_dt`; (3) mark retained = `entry.dt >= before_dt` OR entry is in an open session; (4) also mark retained if total retained count < 500 (extend from oldest kept forward); (5) write survivors via `atomic_write`; (6) return `ActivityCompactionResult`.

The stream is append-only between compactions. Task files remain the authoritative board state; `activity.jsonl` is the authoritative operational history surface for cockpit/admin use.

**Compaction triggers:**

1. **Engine init (opportunistic, automatic).** `KanbanEngine.__init__` checks `activity.jsonl` size; if > 1 MB, calls `compact_activity_log(kanban_dir)` once. Failures are caught and logged; init never raises on compaction failure (it is best-effort housekeeping, not a correctness gate).
2. **Cockpit `compact_activity()` (manual, on-demand).** `CockpitEngineView.compact_activity()` invokes `compact_activity_log(kanban_dir)` unconditionally and returns the `ActivityCompactionResult`. For operator use independent of the size threshold.

No cron, no scheduled task, no CLI script. The two triggers above are exhaustive.

### 7.2 `list_sessions(filter=...)` algorithm (per C10 + AM-15)

`SessionRecord` is defined explicitly here (the current `engine.py` dataclass is the implementation reference, not the contract):

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal


@dataclass
class SessionRecord:
    task_id: int
    task_status_at_start: str
    state: Literal[
        "running",
        "stuck",
        "completed",
        "blocked",
        "rejected",
        "released",
        "expired",
    ]
    started_at: str
    ended_at: str | None
    outcome: Literal["success", "block", "reject", "release", "expired"] | None
    duration_s: int | None
```

`list_sessions(filter="active")` is derived from `activity.jsonl`, not from task frontmatter. It groups claim→close cycles by task, using `start_work` events to open a session and `release`, `sweep-release`, or `end_work` events to close it. Open sessions are classified as `running` vs `stuck` using `claim_timeout` and the most recent in-session activity timestamp. Closed sessions are classified as `completed` (`outcome="success"`), `blocked` (`outcome="block"`), `rejected` (`outcome="reject"`), `released` (`outcome="release"`), or `expired` (`outcome="expired"`). Supported filters are:

- `"active"` — running + stuck only (default)
- `"all"` — every derived session
- `"blocked-or-rejected"` — `blocked` + `rejected`
- `"released"` — released sessions only

`task_status_at_start` comes from the `start_work` event detail written by the engine at claim time; derivation does not re-read task files. `state` is a session-level cockpit/history classifier and does not replace task-level `claimed_at` / `claimed` semantics. `claimed_by` remains removed from task state per Brief B D11.

**Eager validation** (per Brief B security panel, stances/security.md line 184): `_parse_duration` is also called at config load time so a typo in `claim_timeout` surfaces at startup, not at first claim attempt.

There is no separate session table on disk. Sessions are a read model over the activity stream.

### 7.3 What is NOT delivered by Brief C

- Cockpit-specific presentation/grouping rules for activity feeds.
- Arbitrary diagnostic/dev logging outside the board-level activity stream.
- Cross-process transactional guarantees stronger than plain-file append + rewrite semantics.

---

## §8 — Acceptance Criteria

Each AC has a unique ID `AC-C{N}` and cites the C-decision or AM-disposition it implements. Tests live under `serve/kanban/tests/`.

### 8.1 Atomic write & ID allocation

- **AC-C1.** `storage_io.atomic_write(target, content)` writes to a `mkstemp`-allocated `.tmp-*` sibling, fsyncs the file, replaces the target, and fsyncs the parent directory on POSIX. Source: C8.1.
- **AC-C2.** `atomic_write` cleans up the `.tmp-*` file on any exception path; target file is unaffected. Test: simulated `os.replace` failure.
- **AC-C3.** `list_task_files` filters out `.tmp-*` files. Source: §3.2.
- **AC-C4.** `allocate_next_id` holds `.next_id.lock` during read+increment+save sequence. Concurrent test: 50 threads × 1 ID each yields 50 distinct IDs. Source: C8.2.
- **AC-C4a.** `write_task_if_unchanged(task, expected_updated, kanban_dir)` acquires `flock(LOCK_EX)` on `tasks/.<id>.lock`, re-reads the on-disk task, and either (i) writes when `current.updated == expected_updated` and returns the new path, or (ii) raises `ConcurrencyError(code="ERR_STALE")` when stale. Concurrent test: 20 threads racing on the same `(id, expected_updated)` produce exactly one success and 19 `ERR_STALE`s; the survivor write is intact. Source: §3.2.
- **AC-C4b.** Lock files live at `tasks/.<id>.lock` (and `archive/.<id>.lock` for archive writes), are gitignored, are never returned by `list_task_files`/`list_archive_files`, and are never quarantined. Source: §3.2.

### 8.2 Body round-trip

- **AC-C5.** `parse_body(render_body(sections)) == sections` for all `sections` produced by `parse_body`. Source: C1, C4, AM-6.
- **AC-C6.** CRLF in input is normalised to LF in `Section.content`. Source: C4.
- **AC-C7.** `##Heading` (no space) is preserved verbatim as content of the current section, never promoted to a section boundary. Source: AM-6.
- **AC-C8.** `## Heading` (with space) creates a `Section(heading="Heading", level=2, ...)`. Source: AM-6.
- **AC-C9.** Setext headings (`Heading\n===`) create level-1 sections. Source: AM-6.
- **AC-C10.** Code-fenced content containing `## Looks-like-heading` does NOT create a section. Source: §2.4.
- **AC-C11.** Trailing whitespace within section content is preserved. Source: C4.
- **AC-C12.** Inter-section blank lines preserved on round-trip. Source: C4.

### 8.3 Frontmatter

- **AC-C13.** Written frontmatter follows C8.6 canonical order. Source: C8.6.
- **AC-C14.** Pydantic `Task` model has `extra="allow"` (vendor archive fields survive). Source: C8.6.
- **AC-C15.** All timestamps written are ISO-8601 UTC with explicit `+00:00`. Source: Brief B D14.
- **AC-C16.** `detect_corruption` on a `tasks/` file containing `claimed_by` reports mode 3 with `detail="forbidden field claimed_by present"`; archive files are exempt per AC-C48. Source: Brief B D11, AM-13.

### 8.4 Corruption detection (9 modes)

- **AC-C17.** Each of the 9 ERR_CORRUPT_* modes (§4.1) has at least one positive-detection unit test. Source: C6.
- **AC-C18.** `read_task` raises `CorruptionError(code=...)` for every detected mode (outside sweep context). Source: C6, C7.
- **AC-C19.** `list_tasks` SKIPS files failing modes 1, 3-9 silently. Source: AM-2.
- **AC-C20.** `list_tasks` HARD-RAISES `CorruptionError(code="ERR_CORRUPT_DUPLICATE_ID")` for mode 2. Source: AM-2.
- **AC-C21.** Each ERR_CORRUPT_* code is a subclass of `CorruptionError` per C8.8 shape. Source: C8.8.
- **AC-C22.** Auto-fix matrix (§4.2) is exhaustively unit-tested per (mode, field, default) triple. Source: C7.

### 8.5 Claim sweep and explicit repair

- **AC-C23.** `sweep()` returns `list[int]` of released claim IDs only. Source: §4.5.
- **AC-C24.** `repair_storage()` quarantines corrupt files via §4.4 sequence. File is moved BEFORE AR creation attempt. Source: AM-4.
- **AC-C25.** `repair_storage()` records `RepairOutcome(action="failed")` if AR creation fails; file remains quarantined. Source: AM-4.
- **AC-C26.** `repair_storage()` resolves `ERR_CORRUPT_DUPLICATE_LOCATION` by archive-wins. Source: §4.1 mode 7.
- **AC-C27.** `sweep()` reconciles claim timeouts independently of corruption repair. Source: C7.

### 8.6 Quarantine

- **AC-C28.** `move_to_quarantine` creates `quarantine/` directory if absent. Source: §2.1.
- **AC-C29.** Quarantined file path: `quarantine/{original-filename}`. Source: C7.
- **AC-C30.** AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` with `code`, path, detail. Source: §4.4.

### 8.7 Migration script

- **AC-C31.** `uv run kanban-migrate` is registered in `serve/kanban/pyproject.toml`. Source: §5.1.
- **AC-C32.** `kanban-migrate --lane tasks|archive|config|all` runs only the selected lane; `--lane all` runs all three lanes defined in §5.2. Source: §5.2.
- **AC-C33.** Per-lane algorithms for `tasks`, `archive`, and `config` match §5.3 and §5.4 exactly. Source: C9.
- **AC-C34.** Idempotency: re-running on a fully migrated board reports `Migrated: 0`. Source: AM-5.
- **AC-C35.** Idempotency checks follow the lane-specific rules in §5.3, including contract-critical archive fields on archive files and canonical active-task fields on `tasks/`. Source: AM-5.
- **AC-C36.** `--dry-run` writes nothing; only prints. Source: §5.7.
- **AC-C37.** Crash mid-migration leaves no partial files; resume converges. Source: §5.6.
- **AC-C38.** Exit code 1 if any file failed; 0 otherwise. Source: §5.5.
- **AC-C38a.** When the `config` or `archive` lanes leave unresolved manual work, `kanban-migrate` emits a manual-action summary intended to be materialized as visible `type:user-action` tasks before final `--lane tasks` cutover. Source: §5.4a.

### 8.8 Predicate DSL

- **AC-C39.** `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped, per §6.1 / AM-11.
- **AC-C40.** `require_list_in_section` uses the same case-insensitive, whitespace-stripped heading lookup as AC-C39, then returns true iff the matched section's content parses to at least one CommonMark list (`bullet_list` or `ordered_list`). Source: §6.1.
- **AC-C41.** Predicate behaviour matches Brief B D64 semantically; only the implementation substrate changed. Source: C5, C1.

### 8.9 Activity stream and sessions

- **AC-C42.** `append_activity_event(...)` writes structured `ActivityEvent` JSONL entries to the gitignored board-level `activity.jsonl`, and `list_activity_events(...)` applies the declared filters without scanning task frontmatter. Source: C10, §7.1.
- **AC-C43.** `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl`, with `active`/`all`/`blocked-or-rejected`/`released` semantics matching §7.2. Source: C10, §7.2.
- **AC-C44.** No separate session table exists on disk; the board-level `activity.jsonl` stream is the only persistent history substrate for cockpit/admin history and derived session views. Source: C10, Brief B D43.
- **AC-C44a.** `compact_activity_log(kanban_dir, before_dt=None)`: (a) `before_dt=None` auto-resolves to the `ended_at` of the most recently closed session; (b) entries in open sessions (no matching end event) are always retained; (c) at least the last 500 entries by timestamp are always retained; (d) the file is rewritten atomically via `atomic_write`; (e) re-running with no new appends and same `before_dt` produces identical output (idempotent). Source: C10, §7.1.

### 8.10 Boundary

- **AC-C45.** `tests/test_package_boundary.py` enforces: no engine code imports from `task_io` (deleted); only `engine.py` may import from `storage`. Source: §1.4.
- **AC-C46.** `tests/test_deny_code_writes.py` extension: storage tests prohibited from writing outside `tmp_path`. Source: existing convention.

### 8.11 Migration safety (M5 amendments)

- **AC-C47.** `KanbanEngine.__init__` raises `MigrationRequiredError(code="ERR_MIGRATION_REQUIRED")` if any file in `tasks/` contains a `claimed_by` frontmatter field. Source: C11 / AM-12.
- **AC-C48.** Archive files containing `claimed_by` are read successfully (field silently stripped); they do NOT raise `CorruptionError` and they do NOT trigger `MigrationRequiredError`. Source: AM-13.
- **AC-C49.** `_parse_duration("30m")` returns `timedelta(minutes=30)`; malformed inputs raise `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT")`. Source: AM-15.
- **AC-C50.** `BoardConfig` validation calls `_parse_duration(claim_timeout)` at config load time (eager validation). Source: AM-15.
- **AC-C51.** ID allocation: simulate crash between `save_config` and `write_task`; verify next `create_task` allocates `original_next_id + 2` (one ID burned), no duplicate ID created. Source: AM-9.
- **AC-C52.** `sweep()` releasing an expired claim does NOT mutate the task body; only `claimed_at` is cleared and `updated` is advanced. Source: AM-14.
- **AC-C53.** Setext-heading input round-trips through write as ATX-heading output (with same `Section` model). Source: AM-16.
- **AC-C54.** Brief B `create_task` integration: AR creation called by `repair_storage()` uses `body=str` (markdown), no `status` argument; verify against Brief B `create_task` signature. Source: AM-10.

---

## §9 — DR and Upstream Amendments

### 9.1 No DR-2 needed after sweep/repair split

No Brief B `sweep()` expansion is required.

- `sweep()` remains claim-only startup-safe maintenance.
- Quarantine and AR side effects live on explicit `repair_storage()`.
- Brief B consumers keep the existing `sweep() -> list[int]` contract.

**Authorisation lineage:** Brief B D27 explicitly delegates storage-side repair surfacing to Brief C. The split keeps Brief B `sweep()` stable while letting Brief C expose repair outcomes on a separate surface.

**Action:** Brief B reviewer keeps `sweep()` claim-only and documents `repair_storage()` as the explicit admin repair surface.

### 9.2 No DR-3 needed for new error codes

Per AM-3: Brief B D27 + D57's additive pattern (D59 already added a new code) authorise Brief C to add 9 new `ERR_CORRUPT_*` codes under the existing `CorruptionError` subclass, plus `ERR_MIGRATION_REQUIRED` (under `MigrationRequiredError` per C11/AM-12) and `ERR_INVALID_CLAIM_TIMEOUT` (under `ConfigError` per AM-15). All are recorded in §4.1 / §1.5 / §7.2 / §8.11 here; Brief B reviewer sees them at paper merge.

---

## §10 — Out of Scope

Brief C does NOT deliver:

- **Archive body and vendor-field normalisation beyond required contract metadata.** Brief C backfills `archival_reason` / `archival_refs` for rollout, but does not otherwise canonicalise archive bodies or legacy vendor fields.
- **Persistent index.** Brief C C8.4: per-instance mtime cache only. SQLite or any persistent index is out of scope.
- **New predicate DSL keys.** Brief C C5: only the three Brief B D64 keys, now operating on `list[Section]`.
- **Cockpit-specific presentation logic.** Feed grouping, tab structure, and UI-only filtering remain cockpit concerns; Brief C only supplies the activity/query substrate.
- **Diagnostic/dev logging distinct from the board-level activity stream.** Brief C's `activity.jsonl` is product data for cockpit/admin history, not a general debug log sink.
- **Multi-process write coordination.** Single-laptop single-process reality (M1 finding) does not justify it. Atomic-write primitive (§3.1) is the only concurrency surface.
- **Backwards compatibility shim for legacy callers of `task_io`.** Per project standard "no legacy, no backwards compatibility": consumers update or break.

---

## §11 — Implementation Map

For planner reference. Each row is a candidate atomic task seed (NOT a final task list — planner decomposes from §8 ACs).

Planner note: the structured-body rewrite is a dedicated workstream. `body_parser.py` and `predicates.py` should be budgeted as explicit implementation tracks, not buried inside a generic storage refactor task.

| Module / file | Responsibility | Primary ACs |
|---|---|---|
| `storage_io.py` | atomic_write primitive | AC-C1, AC-C2, AC-C3 |
| `body_parser.py` | parse_body, render_body via markdown-it-py | AC-C5..AC-C12 |
| `corruption.py` | CorruptionError + 9 codes + detect_corruption + auto-fix matrix | AC-C17..AC-C22 |
| `storage.py` | public surface; composes above + read/write/list/move | AC-C13..AC-C16, AC-C28..AC-C29, AC-C45 |
| `engine.py` | edits: import from storage; claim-only sweep; explicit repair_storage; list_tasks carve-out; emit/query activity stream; list_sessions derivation | AC-C19, AC-C20, AC-C23..AC-C27, AC-C30, AC-C42, AC-C43 |
| `activity_store.py` | append/query/compact board-level activity stream | AC-C42..AC-C44a |
| `predicates.py` | edits: traverse list[Section] instead of regex | AC-C39..AC-C41 |
| `migrate.py` | kanban-migrate entry point | AC-C31..AC-C38a |
| `pyproject.toml` (serve/kanban) | register kanban-migrate script | AC-C31 |
| `tests/` | unit + integration tests for every AC | all |
| `tests/test_package_boundary.py` | extend boundary rules | AC-C45 |

---

**End paper-c.md.**
