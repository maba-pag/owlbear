# Data Person — Final Position

## Data Quality Stance

The native Python kanban engine must treat the filesystem as an untrusted, crash-prone persistence layer. Every read validates; every write is atomic per-file; the YAML round-trip path preserves data the engine doesn't understand. The core principle: **schema is the contract between the Go past and the Python future — data that survives migration unchanged is data that works.**

Nine positions follow, hardened through five Critic cycles.

## Schema and Validation Reasoning

### 1. YAML Parsing: ruamel.yaml Round-Trip Mode

Use `ruamel.yaml` with `YAML(typ='rt')` and `preserve_quotes=True`.

- **Why ruamel.yaml:** Round-trip fidelity — preserves field order, comments, quoting style on untouched fields, and unknown fields. strictyaml rejects valid YAML constructs. PyYAML loses formatting and ordering.
- **Contract:** No data loss on read/write. Cosmetic quoting normalization may occur on fields the engine actively mutates — this is formatting change, not data corruption. Consuming parsers interpret YAML semantically.
- **Safety:** Pin ruamel.yaml version in `pyproject.toml`. No arbitrary tag constructors — only built-in scalar types (with timestamp resolver explicitly removed; see Position 5). No `yaml.load()` with unsafe loaders.
- **Unknown fields:** Survive in the `CommentedMap`. Dropped Go fields (`class`, `assignee`, `due`, `estimate`) remain in persistence but are not part of the typed API.

### 2. Writer Serialization + Reader Resilience

**Writers:** All mutations acquire `.owlbear/kanban/.board.lock` via `filelock` (cross-platform, MIT). Every file write uses temp-file-in-same-directory + `os.replace()` (atomic rename on both NTFS and POSIX).

**Crash model:** If the process crashes mid-compound-operation:
- **config.yml:** Atomic rename means either old or new version exists. Worst case: next_id incremented but task file not written → leaked ID (harmless).
- **Task file:** Atomic rename → either old or new version. Worst case: task updated but activity.jsonl not appended → mutation happened but isn't logged. Recoverable by diffing task mtimes against log.
- **activity.jsonl:** Append is the last step. Missing log entry is the likely crash artifact — audit gap, not data corruption.

This is writer serialization, NOT transactional crash atomicity. It matches kanban-md's current crash model (the Go binary provides no ACID guarantees either).

**Readers:** Do NOT acquire the lock. Resilience by design:
- Task files and config.yml: `os.replace()` guarantees readers see a consistent per-file state (old or new, never partial).
- **activity.jsonl:** On Windows, append atomicity is not guaranteed. All consumers of activity.jsonl MUST handle a potentially truncated last line — skip any line that fails `json.loads()`. This is a **migration requirement** for existing consumers (e.g., the retro workflow's `ConvertFrom-Json` pipeline).

### 3. activity.jsonl: Preserve Existing Vocabulary

**Format:** `{"timestamp": "ISO8601+tz", "action": str, "task_id": int, "detail": str}` — one JSON object per `\n`-terminated line. Written as a single `write()` call under the board lock, followed by flush.

**Action vocabulary** (from live corpus analysis): `create`, `edit`, `move`, `claim`, `release`, `block`, `unblock`, `handoff`, `delete`. There is no `archive` action — the engine's archive operation logs as `move` with detail `"<status> -> archived"`, matching existing Go behavior exactly.

**`detail` is freeform text.** Its content varies by action type: agent names, task titles, status transitions, field change descriptions, reason text. No strict schema enforced — the engine populates it contextually.

### 4. File Identity: Frontmatter `id` Is Truth

**Frontmatter `id`** is the canonical task identity. Filename `<id>-<slug>.md` is a human-readability convenience.

**Two-tier lookup:**
- **Fast path:** Extract ID from filename prefix for single-task access by known ID.
- **Integrity scan:** At engine initialization (or first mutation per session), parse frontmatter of all task files to build a validated `{id: filepath}` index. For 700 files, frontmatter-only parsing (first `---` to second `---`) completes in under 100ms.

**Validation rules:**
- **Filename/frontmatter mismatch:** Log warning, use frontmatter `id`, continue operating. The engine is resilient to hand-renamed files.
- **Duplicate frontmatter IDs:** Hard ERROR — unresolvable ambiguity. Refuse to load until a human resolves the conflict.

**Frontmatter/body boundary:** The FIRST `---` on its own line opens frontmatter; the SECOND `---` on its own line closes it. Everything after is body. Body content containing `---` on its own line is not a problem — only the first two delimiters are significant.

**Title edits do NOT rename files.** Slug is frozen at creation time.

**Slug generation:** `re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')` — must match kanban-md's Go slugification for existing files. Truncate to ~80 chars. The `<id>-` prefix guarantees filename uniqueness.

**tasks_dir resolution:** Engine resolves `tasks_dir` from config.yml relative to the config file's parent directory. Resolved path must stay within the board root — do not follow symlinks that escape the boundary.

### 5. Timestamp String Preservation in YAML

Disable `tag:yaml.org,2002:timestamp` from ruamel.yaml's implicit resolver list. Timestamps remain as raw strings in the `CommentedMap` throughout YAML read/write. Bool, int, and float resolvers are unaffected (they use different resolver tag entries).

**Why:** Go's timestamps use 7-digit fractional seconds (nanoseconds). Python's `datetime` has 6-digit precision (microseconds). If ruamel.yaml auto-parses timestamps to `datetime`, round-trip re-serialization silently truncates precision — a diff on every `read → write` cycle for unchanged tasks. Keeping timestamps as strings eliminates this.

**Parsing:** `datetime.fromisoformat()` in Python 3.12 handles 1–9 digit fractional seconds (PEP 3120). Used only in the domain/validation layer, never in the persistence layer.

### 6. Date Generation for New Timestamps

New timestamps: `datetime.now(tz=timezone.utc).astimezone().isoformat()` → local time with UTC offset, 6-digit microsecond precision (e.g., `2026-04-08T14:30:00.123456+02:00`).

Existing Go-originated timestamps (7-digit nanoseconds) are preserved as raw strings through the YAML layer (Position 5). No precision drift on round-trip.

### 7. Canonical TaskRecord — Engine Boundary Type

Single `TaskRecord` Pydantic model is the engine's API surface. **All timestamps as `str`.**

| Category | Fields |
|----------|--------|
| **Identity** | `id: int`, `title: str`, `file: str` (relative path) |
| **Lifecycle** (engine-managed) | `status: str`, `priority: str`, `created: str`, `updated: str`, `started: str \| None`, `completed: str \| None`, `claimed_by: str \| None`, `claimed_at: str \| None`, `blocked: bool`, `block_reason: str \| None` |
| **Relational** | `tags: list[str]`, `parent: int \| None`, `depends_on: list[int]` |
| **Content** | `body: str` (Markdown below frontmatter) |

**Consumer adaptation is expected and scoped.** The orchestrator's `Task` model (datetime-typed fields, `class` alias) is a consumer projection. When migrating from kanban-md JSON to the engine API, the orchestrator adapts its own model — `str→datetime` parsing, `class` field removal. This is migration scope, not a design flaw.

### 8. Claim Invariants + Engine-Owned Identity

- `claimed_by` and `claimed_at` are always set/cleared as an atomic pair. The engine enforces: you cannot set one without the other.
- `claim_timeout` parsed from config.yml duration string (e.g., `"1h"` → `timedelta`).
- **Session-stable identity:** The engine generates a claim identity (agent name) once per engine instance via `generate_agent_name()`. This identity is reused for all claim/release operations within that instance's lifetime. The engine instance IS the session boundary — consumers do not manage identity independently. This ensures TASK_CLAIMED retry semantics are coherent: the same identity retries the same claim.

### 9. Config.yml Shape Preservation

Config statuses are stored as `list[dict]` (each entry: `{name: str}`), not a plain string list. The engine reads AND writes this shape via ruamel.yaml round-trip — no flattening to `list[str]` in the persistence layer.

`next_id` is read-increment-written under the board lock with temp + `os.replace()`. The lock ensures no concurrent increment races.

## Key Trade-offs

| Choice | Cost | Avoided Failure |
|--------|------|----------------|
| ruamel.yaml (not PyYAML/strictyaml) | Heavier dependency, more complex API | Silent data loss on round-trip, unknown field dropping |
| Board-level lock for ALL mutations | Lock contention on rapid concurrent calls | Interleaved partial writes, config corruption |
| Timestamps as strings in model | Consumer must parse to datetime themselves | Precision drift, silent truncation on round-trip |
| No file rename on title edit | Stale slugs in filenames | Broken references, rename complexity |
| Frontmatter id as truth (not filename) | Slightly slower lookup (parse vs. regex) | Mutation routed to wrong task after hand-rename |
| Engine-owned claim identity | Identity tied to engine instance lifecycle | Incoherent retry semantics across calls |

## Warnings

1. **Retro workflow is a migration casualty.** The `w-retro` skill streams `activity.jsonl` through `ConvertFrom-Json` with no malformed-tail guard. Under the accepted crash model, a truncated last line will break this consumer. Must be hardened as a migration task.
2. **Slug algorithm parity is unverified.** The Go slugification must be reverse-engineered from the existing 700+ filename corpus. Any divergence means "file not found" on existing tasks during the first load. Run a validation pass before cutting over.
3. **`class` field removal from typed API** will surface as a type error in the orchestrator's `Task` model (which aliases `class` to `task_class`). This is a known migration seam.
4. **Duplicate frontmatter IDs** are a hard-stop error. If the existing corpus contains any duplicates (e.g., from manual file copying), the engine will refuse to load until resolved. Run a pre-migration validation scan.
5. **`os.replace()` on Windows** requires that no other process holds the target file open. If an editor or tool has config.yml open, the atomic rename will fail. The board lock mitigates concurrent engine instances but not external file handles.

## Confidence

0.82
