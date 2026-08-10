# Brief C — M3 Landscape Findings

**Status:** M3 — locked
**Source:** Explore subagent forced code-read of `serve/kanban/src/owlbear_kanban/`, on-disk task scan of `.owlbear/kanban/`, and ecosystem scan. All citations are 1-indexed.

---

## (a) Current storage implementation

- **Write path:** `KanbanEngine.create_task / edit_task / move_task / claim_task / release_task / end_work` → `task_io.write_task(path, Task)` (`task_io.py:217-260`). `write_task` serialises to YAML+body, writes via `tempfile.mkstemp(dir=path.parent)` + `os.fdopen` + `Path(tmp_path).replace(path)` — **atomic-rename within the same dir, but NO `os.fsync` on file or directory**.
- **Atomicity primitives:** atomic rename only. `flock` (Unix) / `msvcrt.locking` (Windows) is used **only for ID allocation** via `_exclusive_file_lock(".next_id.lock")` (`engine.py:189-220`, `engine.py:498-528`). `activity_log.py:28-30` uses `f.write + f.flush` (no fsync). `move_task` archives by `write_task` then `_move_file` (`engine.py:170-188`) — two-step, not atomic.
- **ID allocation:** `config.next_id` field in `config.yml` (currently `next_id: 1039`). Allocation inside `_exclusive_file_lock`: `load_config → task_id = config.next_id → write_task → config.next_id += 1 → save_config`. Race-safe across processes via flock; lock does NOT cover the body-write fsync.
- **Frontmatter parser/writer:** Hybrid impedance mismatch. **Reading**: PyYAML with custom `YAML12SafeLoader` (`task_io.py:46-72`) — strips timestamp resolver (so Go 7-digit-ns survives as string), adopts YAML 1.2 bool semantics. **Writing**: ruamel.yaml round-trip (`_make_yaml`, `task_io.py:74-89`) with timestamp resolver scrubbed from `_version_implicit_resolver`. Round-trip preservation of order/comments is best-effort because reads go through PyYAML→Pydantic dump→ruamel.
- **Body parsing:** **Free-form blob.** `read_task` does `body = "\n".join(lines[closing_idx+1:])` (`task_io.py:202-211`). `Task.body: str = ""` (`models.py:88`). `edit_task`'s `append_body` concatenates with `"\n" + prefix + append_body` (`engine.py:633-640`). No section parsing, no structured fields.
- **Archive layout:** Flat sibling directory `.owlbear/kanban/archive/` (`BoardConfig.archive_dir = "archive"`, `models.py:50`). `archived` is **both** a status string AND a folder move (`engine.py:736-744`, `engine.py:944-948`). `sweep()` reconciles orphans (`engine.py:973-1005`).
- **Read path / `list_tasks`:** O(n) `os.scandir` per call (`engine.py:380-411`). In-memory mtime-keyed cache `_task_cache: dict[str, tuple[int, Task]]`; entries unchanged by mtime are reused, missing files evicted. `_id_to_filename` rebuilt as sorted dict (`engine.py:413-416`). **No persistent index** — caches are per-engine-instance and cleared on `refresh_config`.
- **Corruption / duplicate-ID handling:** **None as a first-class concept.** `read_task` raises plain `ValueError` for missing `---` delimiters (`task_io.py:198-211`); `list_tasks` silently swallows `(ValueError, KeyError)` and skips the file (`engine.py:404-408`). **No `CorruptionError` class exists.** Duplicate-ID detection: **none** — `_id_to_filename = dict(sorted(...))` silently keeps the last-sorted filename per id; `glob(f"{task_id}-*.md")[0]` in `_find_task_path` (`engine.py:1128`) and `show_task` (`engine.py:489`) takes the first match. Only race protection is the `.next_id.lock` flock.

## (b) On-disk format reality

Representative live task `.owlbear/kanban/tasks/1034-p2-10-ideation-panel-diagram.md:1-20` frontmatter (field name : type, in observed write order):

```
id: int                    (1034)
title: str                 ('P2-10: Ideation panel diagram')
status: str                (in-progress)
priority: str              (important)
created: str (ISO-8601 UTC, +00:00 offset, 6-digit µs)
updated: str (ISO-8601 UTC, +00:00 offset, 6-digit µs)
tags: list[str]
parent: int | null
depends_on: list[int]
blocked: bool
block_reason: str | null   (empty/null on disk)
claimed_by: str | null     ('odd-rook' or empty)
claimed_at: str | null     (ISO-8601 UTC or empty)
```

Same field set & order in `1036-p2-12-doc-audit-gate-run.md`. No tasks observed missing required fields.

**Variation in archive (older Go-engine era):** files like `509-…md`, `696-…md`, `733-…md` carry **extra fields** absent from current writes:
- `started: 2026-04-02T00:14:13.1396376+02:00` — **Go 7-digit nanosecond, non-UTC offset (+02:00)**
- `completed: ...` (same shape)
- `class: standard` — vendor field, mirrors `defaults.class: standard` still in `config.yml:19`

These survive round-trip via Pydantic `extra="allow"` on `Task` (`models.py:75-77`) — invisible to the model, written back unchanged.

**Timestamps mixed reality.** New writes always UTC `+00:00` 6-µs. Archive contains Go-format 7-ns local-offset (`+02:00`). `task_io.py:46-72` exists specifically because both shapes coexist. **Brief B D14 (UTC + offset) is partially satisfied by new writes, violated by every archive file.**

**`claimed_by` presence:** Yes — actively written. `Task.claimed_by` (`models.py:94`), `claim_task` writes it (`engine.py:782-784`), every active task file shows the field (sometimes empty value). **Brief B D11 wants it gone — requires schema change + migration sweeping all 200-500 archive files plus all active files.**

**Body section conventions:** Inconsistent but real. Live tasks show `## Acceptance Criteria`, `## Files`, `## Notes`, `## Builder Guidance`, plus auto-appended `[[YYYY-MM-DD]]\n## Architecture Review` blocks from `edit_task --append-body --timestamp`. **Order, presence, and naming vary task-to-task. Nothing in code parses or validates these — free-form Markdown.** This is the empirical pressure for Axis A "structured shape."

## (c) Existing migration scripts

**Zero scripts touch task files.** Scan of `.owlbear/scripts/`:
- `clean_scratch.py` — deletes files >30d old from `.owlbear/scratch/`. Idempotent (mtime-bounded), no tests, never touches kanban.
- `e2e_smoke.py` — manual full-stack smoke; creates one temp task via legacy `kanban-md.exe`, dispatches, deletes. Not idempotent (UUID titles), no migration semantics.
- `validate_skills.py`, `validate_agents.py`, `skills_ref/*` — operate on `share/skills/` and `share/agents/`, not kanban.

**Brief C will be writing the first kanban-storage migration script.** Greenfield on this axis.

## (d) Ecosystem scan

- **Atomic-rename + fsync (Python).** Standard portable pattern: write to `tempfile.mkstemp(dir=target_dir)`, write contents, `os.fsync(fd)`, close, `os.replace(tmp, target)`, then open the target *directory* and `os.fsync(dir_fd)` to persist the rename in the directory entry. Current code does step 1 (rename) but **skips both fsyncs** (`task_io.py:248-260`). Cross-platform: directory fsync is a no-op on Windows; `os.replace` is atomic on both POSIX and NTFS within the same volume.
- **SQLite WAL for low-concurrency single-process+subprocess.** Buys: free transactional D41 atomicity, durable fsync, multi-reader/single-writer concurrency, `INTEGRITY_CHECK`. Costs: opaque binary diffs (Axis B differentiator #2), unmergeable across branches (#3), agents can't `cat` a task. Atomicity-correct but the current problem is structural, not contention.
- **Python YAML frontmatter libraries.** `python-frontmatter` (Hugo-style, simple, lossy on key order/comments), vs `ruamel.yaml` (true round-trip preservation, YAML 1.2 by default). **Current code's PyYAML-read + ruamel-write split is a known impedance mismatch**; converging on ruamel-only would simplify the YAML 1.1/1.2 handling currently spread across two custom resolvers.
- **Structured-section libraries.** `markdown-it-py` is the modern choice (CommonMark-spec, AST tokens, plugin ecosystem). For typed sections at write time: parse body to AST, walk for `## SectionName` headings, slice block tokens between headings, validate against Pydantic schema, serialise back via same AST. **Axis A "structured shape" is feasible with markdown-it-py + Pydantic without inventing new tooling.**
- **Git-friendly DB formats.** Dolt (MySQL-wire, per-row versioned, true diff/merge) is mature but heavyweight for ~1000 rows. Lighter pattern: SQLite + `sqlite-utils dump` text committed alongside binary `.db` for diff-readability — but gives diff readability only, not mergeability. **No tooling matches Markdown-files for both diff *and* merge at this size.**

---

## Headlines for M4 panel

1. **D41 today is a half-promise.** Atomic-rename without fsync survives a clean shutdown but not a power loss; current code is "best-effort durable." Brief C must close this.
2. **ID allocation is correct.** `.next_id.lock` flock around `read-write-save` of `config.yml.next_id` is race-safe. No regression risk if Brief C keeps this primitive.
3. **Body is free-form.** No section parser exists. Axis A is genuinely open — there's no installed base of structure code to break.
4. **Migration scope is minimal (corrected).** Per user: archive is not migrated. D11 (drop `claimed_by`) and D14 (UTC + offset) and any Axis-A structural reshape touch **only the ~150 active task files**. Archive files keep their current Go-era shape; the read path already tolerates extra fields via Pydantic `extra="allow"`. **"Archive migration cost" is not a valid argument for or against any panel decision.**
5. **No CorruptionError exists.** D27/D19 contracts from Brief B require Brief C to introduce the class, define the modes, decide the surfacing point.
6. **No persistent index.** `list_tasks` cache is in-memory per-instance. Whether to add a persistent index is a Brief C decision, not a frozen contract.
7. **Hybrid YAML parser is technical debt.** Read=PyYAML, Write=ruamel — Brief C should converge.
8. **Greenfield migration tooling.** Brief C writes the first kanban migration script. No prior pattern to inherit.
