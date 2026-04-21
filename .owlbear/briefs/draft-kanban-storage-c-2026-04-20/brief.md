# Brief C — Kanban Storage Layer

**Status:** M5 complete (post-amendments; M6-ready).
**Upstream:** Brief B (engine API, decisions D1..D65) — frozen contract.
**Normative source:** [`paper-c.md`](paper-c.md) — 11 sections, 56 acceptance criteria.

## §1 — Vision

The kanban storage layer is the bytes-on-disk substrate for the Brief B engine. Brief C delivers a storage module that is:

- **Atomic.** Every write survives crash/power-loss via `mkstemp → fsync → replace → fsync(dir)`.
- **Structured.** Task body is `list[Section]`, parsed once at read time via markdown-it-py/CommonMark; predicates traverse the AST instead of regex over rendered Markdown.
- **Self-healing on demand.** `engine.repair_storage()` triggers a two-phase repair: storage `scan_and_fix()` handles detection, auto-fix, and quarantine; the engine then creates Action Request tasks for each quarantined file. Runtime reads tolerate or escalate; `sweep()` remains claim-only startup-safe maintenance.
- **Migratable in one command.** `uv run kanban-migrate` brings the existing active task files to the Brief B + Brief C shape, metadata-normalises legacy archive files for Brief A's archived-task contract, and rewrites `config.yml` to the new BoardConfig schema, idempotently and verifiable via `git diff`.
- **Operationally observable via a board-level activity stream.** Storage owns a single gitignored `.owlbear/kanban/activity.jsonl` runtime file for cockpit/admin history and derived session views, plus semantic compaction that bounds runtime-history growth without breaking cockpit-visible history semantics. Diagnostic/dev logging remains out of scope.

Storage is bytes; the engine is the state machine. The boundary is enforced by `tests/test_package_boundary.py`.

## §2 — Surface

Public module: `serve/kanban/src/owlbear_kanban/storage.py`. Engine code imports from `storage` only.

Functions:

```python
def read_task(path: Path) -> Task
def write_task(task: Task, kanban_dir: Path) -> Path
def write_task_if_unchanged(task: Task, expected_updated: str, kanban_dir: Path) -> Path
def list_task_files(kanban_dir: Path) -> list[Path]
def list_archive_files(kanban_dir: Path) -> list[Path]
def move_to_archive(task_id: int, kanban_dir: Path) -> Path
def move_to_quarantine(file_path: Path, kanban_dir: Path) -> Path
def allocate_next_id(kanban_dir: Path) -> int
def load_config(kanban_dir: Path) -> BoardConfig
def save_config(config: BoardConfig, kanban_dir: Path) -> None
def parse_body(markdown: str) -> list[Section]
def render_body(sections: list[Section]) -> str
def append_activity_event(event: ActivityEvent, kanban_dir: Path) -> None
def list_activity_events(kanban_dir: Path, *, task_id: int | None = None, action: str | None = None, source: str | None = None, since: str | None = None, until: str | None = None, limit: int | None = None) -> list[ActivityEvent]
def compact_activity_log(kanban_dir: Path, before_dt: datetime | None = None) -> ActivityCompactionResult
def scan_and_fix(kanban_dir: Path, config: BoardConfig) -> list[RepairOutcome]
def detect_corruption(path: Path, config: BoardConfig) -> CorruptionError | None
def attempt_repair(path: Path, code: str, config: BoardConfig) -> RepairOutcome
```

Types:

- `Section(heading, level, content)` — body building block (paper §1.2).
- `CorruptionError(code, user_message, file_path)` — extends `KanbanError` per Brief B D27/D57 (paper §4.8).
- `RepairOutcome(task_id, file_path, code, action, detail)` — outcome of one file’s repair pass. `action` values: `"fixed"` (auto-repaired in place), `"quarantined"` (file moved; AR creation still pending or already delegated to the engine layer), `"failed"` (the repair pass did not complete cleanly; e.g. quarantine failed or AR creation failed after quarantine).
- `ActivityEvent(timestamp, task_id, action, source, detail)` — structured board-level runtime activity record. `source` is one of `"agent"` | `"cockpit"` | `"engine"`, populated by the engine based on which role view (or auto-operation) performed the mutation. Legacy pre-Brief-C `activity.jsonl` history is not migrated; rollout starts a fresh canonical stream.
- `SessionRecord(task_id, task_status_at_start, state, started_at, ended_at, outcome, duration_s)` — derived work session view for Cockpit admin surfaces. `state` exposes the claim-cycle classifier used by cockpit history (`running`, `stuck`, `completed`, `blocked`, `rejected`, `released`, `expired`) without replacing task-level claimed state. Derived by the engine from the activity stream by pairing `start_work` events with their corresponding close events per task_id. `task_status_at_start` is stored in the `start_work` event’s `detail` field at write time.
- `ActivityCompactionResult(before_bytes, after_bytes, records_compacted)` — semantic compaction telemetry for the activity stream.

Module shape (paper §1.1):

```
storage.py        # public surface
storage_io.py     # atomic_write primitive
body_parser.py    # markdown-it-py wrapper
activity_store.py # activity.jsonl append/query/compaction helpers
corruption.py     # CorruptionError + 9 codes
migrate.py        # kanban-migrate entry point
```

`task_io.py` deleted.

## §3 — Key Decisions (C1..C11 + AM-1..AM-16)

See [`decisions.md`](decisions.md) for full rationale and source attribution.

| # | Decision | Substance |
|---|---|---|
| C1 | Body shape | `list[Section]` per Brief B D7/D26 |
| C2 | Backend | Filesystem (YAML frontmatter + Markdown body); SQLite rejected |
| C3 | Archival fields | `archival_reason`, `archival_refs` part of canonical frontmatter |
| C4 | Round-trip | Within-section content verbatim (LF-normalised); heading style normalised to ATX (per AM-16) |
| C5 | DSL extensions | None — only the three Brief B D64 keys, now AST-based, case-insensitive per AM-11 |
| C6 | Corruption modes | 9 modes, strict enum validation |
| C7 | Corruption handling | Auto-fix or quarantine + AR; trigger = explicit two-phase `engine.repair_storage()` / `storage.scan_and_fix()` only |
| C8 | Implementation details | Atomic write primitive, ID alloc (save-then-write order per AM-9), ruamel convergence, no persistent index, canonical frontmatter order, archive layout, CorruptionError shape |
| C9 | Migration script | `uv run kanban-migrate`, lane-scoped (`tasks` / `archive` / `config` / `all`), supporting config-first rehearsal, task-last cutover, and explicit manual-action checkpoints when follow-up is still required |
| C10 | Activity stream + sessions | single gitignored board-level `activity.jsonl`; `list_activity`, `list_sessions`, and semantic compaction operate on it; no separate session table |
| C11 | Engine-init migration check (per AM-12) | `KanbanEngine.__init__` raises `MigrationRequiredError` if any active file has `claimed_by`; converts silent-failure to loud-error |

M4 + M5 Critic amendments:

- **M4 amendments (AM-1..AM-7, AM-BS1):** DR-2 scope, DUPLICATE_ID carve-out, error-code lineage, quarantine sequence, idempotency check, CommonMark heading grammar, no recursion hazard, activity-stream-backed session derivation (became C10).
- **M5 amendments (AM-9..AM-16):** ID alloc order locked, AR call uses Brief B sig, case-insensitive matching, engine-init migration check (became C11), archive `claimed_by` exemption, sweep no body mutation, session derivation made implementable with duration parser, round-trip promise softened to ATX-normalised heading style.

## §4 — Acceptance Criteria

56 ACs, enumerated in [`paper-c.md`](paper-c.md) §8. Grouped:

- §8.1 (4 ACs) — atomic write & ID allocation
- §8.2 (8 ACs) — body round-trip
- §8.3 (4 ACs) — frontmatter
- §8.4 (6 ACs) — corruption detection
- §8.5 (5 ACs) — sweep() and repair split
- §8.6 (3 ACs) — quarantine
- §8.7 (9 ACs) — migration script
- §8.8 (3 ACs) — predicate DSL
- §8.9 (4 ACs) — activity stream and sessions
- §8.10 (2 ACs) — boundary
- §8.11 (8 ACs) — migration safety (M5 amendments: C11 + AM-9/10/13/14/15/16)

Every AC cites a C-decision or Brief B D-decision. Every C-decision is referenced by at least one AC.

## §5 — Implementation Map (planner seed)

Per [`paper-c.md`](paper-c.md) §11:

Planner note: treat the structured-body rewrite as its own implementation stream. `body_parser.py` and `predicates.py` are not incidental helpers under generic storage work; together they are the contract-carrying migration from free-form markdown handling to section-aware semantics.

| Module / file | Responsibility | Primary ACs |
|---|---|---|
| `storage_io.py` | atomic_write | AC-C1, AC-C2, AC-C3 |
| `body_parser.py` | parse_body, render_body | AC-C5..AC-C12 |
| `corruption.py` | 9 codes + detect + auto-fix | AC-C17..AC-C22 |
| `storage.py` | public surface | AC-C13..AC-C16, AC-C28..AC-C29, AC-C45 |
| `engine.py` (edits) | import from storage; claim-only sweep; `scan_corruption` + two-phase `repair_storage`; list_tasks carve-out; emit/query activity stream; list_sessions | AC-C19, AC-C20, AC-C23..AC-C27, AC-C30, AC-C42, AC-C43 |
| `activity_store.py` | append/query/compact board-level activity stream | AC-C42..AC-C44a |
| `predicates.py` (edits) | AST traversal | AC-C39..AC-C41 |
| `migrate.py` | kanban-migrate (three lanes: active tasks, archive, config.yml) | AC-C31..AC-C38a |
| `serve/kanban/pyproject.toml` (edit) | register entry point | AC-C31 |
| `tests/test_package_boundary.py` (edit) | enforce storage boundary | AC-C45 |
| `tests/` (new) | per-AC unit + integration | all |

The planner uses [`paper-c.md`](paper-c.md) §8 + §11 as the decomposition source — NOT this brief.

## §6 — Out of Scope

Per [`paper-c.md`](paper-c.md) §10:

- Archive body and vendor-field normalisation beyond the contract-critical metadata backfill.
- Persistent index / SQLite (C8.4).
- New predicate DSL keys (C5).
- Diagnostic/dev logging distinct from the board-level activity stream.
- Multi-process write coordination beyond ID allocation (C8.5).
- `task_io` backwards compatibility shim.

## §7 — Sweep Contract

No upstream `sweep()` expansion is required.

- `sweep()` stays the Brief B claim-only maintenance surface.
- Corruption detection, quarantine, and AR creation live on the two-phase `engine.repair_storage()` / `storage.scan_and_fix()` split.
- Startup hooks may continue calling `sweep()` safely because repair side effects are no longer bundled into it.
- Planner scope for Brief C should be read together with Brief B's downstream rollout matrix, especially for cockpit/admin history, maintenance surfaces, activity append/query/compaction, and test migration.

## §8 — Open Questions

None blocking. Brief C is M6-ready.

Optional follow-ups (do NOT block M6):

- **`required_frontmatter_field` predicate.** Data panel proposed; deferred per C5/§6.2. File as a backlog task if a future pipeline failure demands it.
- **`section_not_empty` predicate.** Same deferral.
- **Archive full normalisation.** A future task could migrate archive files to the same canonical frontmatter order and remove remaining legacy vendor artifacts. Contract-critical metadata is backfilled in rollout; deeper cleanup is optional.

## §9 — Handoff

On approval:

1. **Parent kanban task** created via the board-management MCP create-task tool (not Brief A `create_task`):
   - Title: `Brief C — Kanban Storage Layer`
   - Board column: `backlog`
   - Tags: `phase:storage`, `brief:c`
   - Body: link to `paper-c.md` and `brief.md`; cite Brief B as upstream contract.
2. **`planner` subagent** invoked to decompose the parent into atomic TDD-paired implementation tasks, sourced from paper-c.md §8 ACs and §11 implementation map.

---

**End brief.md.**
