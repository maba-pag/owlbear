# Data-Integrity Design Proposal — Memory Module Restructure

## Design Summary

Replace `store/memory/memory.db` (SQLite) with per-entry markdown files at `.owlbear/memory/entries/`. Each entry is a single `.md` file with YAML frontmatter (typed fields validated by Pydantic on every read/write) and a plain-text body containing the learning content. The MCP tool surface is preserved; the storage layer becomes git-native, human-readable, and diffable.

The design prioritises **data correctness over performance**, **lossless migration over speed**, and **explicit corruption handling over silent degradation**. At <200 entries, full in-memory load is acceptable — no indexing, no caching, no partial reads.

---

## Key Structural Choices

### 1. Data Model

```yaml
# Frontmatter schema (Pydantic-validated)
id: str                  # UUIDv4 (lowercase hex with hyphens, 36 chars)
category: Literal["preference", "knowledge", "context", "behavior", "goal"]
confidence: float        # [0.7, 1.0] — reject outside range at write time
created_at: str          # ISO 8601 UTC with timezone (e.g. 2026-05-02T14:30:00+00:00)
updated_at: str          # ISO 8601 UTC — MUST change on every mutation
source: str              # agent_id that created the entry (non-empty)
scope_agent: str | None  # narrows visibility to one agent
scope_project: str | None  # narrows visibility to one project
approval_state: Literal["pending", "approved", "deleted"]
deleted_at: str | None   # ISO 8601 UTC — set on transition to "deleted", cleared on restore
```

**Body:** Free-form markdown. MUST be non-empty (whitespace-only is invalid). This is the `content` field from the current SQLite schema.

**Invariants (must always hold):**

| # | Invariant | Enforcement |
|---|-----------|-------------|
| I1 | `id` in frontmatter == UUID prefix in filename | Validate on read; reject + quarantine on mismatch |
| I2 | `confidence ∈ [0.7, 1.0]` | Pydantic field validator; reject at write |
| I3 | `updated_at >= created_at` | Model validator; reject at write |
| I4 | `deleted_at` is set iff `approval_state == "deleted"` | Model validator; repair on read |
| I5 | `category` is one of the 5 literals | Pydantic Literal type; reject at write |
| I6 | Body is non-empty | Model validator; reject at write |
| I7 | No two files share the same `id` | Checked at load time; second file quarantined |

### 2. File Format

```
---
id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
category: knowledge
confidence: 0.85
created_at: "2026-05-01T10:00:00+00:00"
updated_at: "2026-05-01T10:00:00+00:00"
source: builder
scope_agent: null
scope_project: null
approval_state: pending
deleted_at: null
---

Starlette sync TestClient + SSE endpoints deadlock because `response_complete`
never fires for streaming responses. Use httpx.AsyncClient + ASGITransport for
tests that need stream content.
```

**Parsing rules:**
- File MUST start with `---\n` (opening fence)
- YAML block ends at the next `---\n` line (first occurrence after line 1)
- Use `YAML12SafeLoader` (no timestamp/bool implicit resolution) — same as kanban
- Body = everything after the closing `---` fence
- Trailing newline in body is preserved (no strip)

**What constitutes a valid entry:**
1. File has `.md` extension
2. Opens with `---` frontmatter fence
3. Frontmatter parses as valid YAML
4. All required fields present with correct types (Pydantic validates)
5. All invariants (I1–I7) hold
6. Body is non-empty after the closing fence

### 3. State Transitions

```
                ┌──────────┐
     (create)──▶│ pending  │
                └────┬─────┘
                     │
          ┌──────────┼──────────┐
          ▼                     ▼
    ┌──────────┐         ┌──────────┐
    │ approved │         │ deleted  │
    └──────────┘         └─────┬────┘
                               │
                               ▼
                         ┌──────────┐
                         │ pending  │ (restore)
                         └──────────┘
```

**Allowed transitions (unchanged from current):**

| From | To | Who | Side effects |
|------|----|-----|--------------|
| pending | approved | `set_approval_state` (curator/human) | `updated_at` refreshed |
| pending | deleted | `set_approval_state` or `mark_for_deletion` | `deleted_at` set, `updated_at` refreshed |
| deleted | pending | `set_approval_state` (curator/human) | `deleted_at` cleared, `updated_at` refreshed |

**Disallowed:** approved→deleted (must go approved→? — intentionally not permitted; delete only unvetted entries), approved→pending (no demotion), same-state transitions (no-op raises error in `set_approval_state`, no-op succeeds in `mark_for_deletion`).

**Deleted entries:**
- Files remain on disk with `approval_state: deleted` — soft delete only
- `get_knowledge` always excludes deleted entries (filter at load)
- `list_entries` excludes by default; `include_deleted=True` shows them
- Physical deletion is a manual `git rm` — never automated

### 4. ID Generation

**Strategy:** UUIDv4 (random), same as current.

**Collision avoidance:**
- UUIDv4 collision probability at 200 entries: ~10⁻³⁴ — no mitigation needed
- Defence in depth: at write time, check filesystem for existing file with same UUID prefix before `atomic_write`; raise `DuplicateIDError` if found

**Filename derivation:**
```
{uuid}.md
```

No slug component. Rationale:
- Memory entries have no title — the `content` body is the data
- Slugs derived from content would be unstable (content can't change without filename change)
- UUID-only filenames are unique by construction, stable across edits, and avoid the re-slug problem kanban has

Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890.md`

**Filename→ID validation:** On read, strip `.md` suffix from filename. Must match `id` field in frontmatter exactly (invariant I1).

### 5. Concurrency

**Model:** Last-writer-wins with atomic writes. No OCC (optimistic concurrency control).

**Rationale:** Memory entries are not collaboratively edited. One agent writes an entry; later a curator approves/deletes it. These operations target different entries. Simultaneous write to the SAME entry is possible only if two curators run in parallel — operationally prevented by claim semantics.

**Atomic write sequence** (identical to kanban `storage_io.py`):
1. `mkstemp` → `.tmp-{random}.md` in `.owlbear/memory/entries/`
2. Write full content (frontmatter + body) UTF-8, LF newlines
3. `fsync` file fd
4. `os.replace(tmp, target)` — atomic rename (POSIX guarantee)
5. `fsync` parent directory fd (crash consistency)
6. On error: unlink temp file, re-raise

**Partial-write safety:** If the process crashes between steps 1–3, only a `.tmp-*` orphan exists (cleaned on next load). The target file is never in an intermediate state because `os.replace` is atomic.

**Directory-level concurrency:** Two simultaneous `record_learning` calls create different files (different UUIDs) — no conflict. Two simultaneous `set_approval_state` calls on the SAME entry: last write wins, both are valid state transitions, `updated_at` reflects the winner. This is acceptable at this scale.

### 6. Migration

**Strategy:** Lossless one-shot export from SQLite → markdown files.

**Migration script (`migrate_to_files.py`):**

```python
def migrate(db_path: Path, target_dir: Path) -> MigrationReport:
    """Export all SQLite entries to per-file markdown."""
    # 1. Read ALL rows from memory_entries
    # 2. For each row:
    #    a. Validate with MemoryEntry Pydantic model (catch corrupt DB rows)
    #    b. Render as frontmatter + body
    #    c. Write to {target_dir}/{id}.md via atomic_write
    # 3. Return report: total, written, skipped (with reasons)
```

**Verification strategy:**
1. **Count match:** `SELECT COUNT(*) FROM memory_entries` == number of `.md` files created
2. **Round-trip validation:** For each written file, re-parse with the new `storage.py` loader → compare all fields to original row (field-by-field equality)
3. **Checksum:** SHA-256 of sorted `(id, content, category, confidence, approval_state)` tuples from SQLite must match SHA-256 of same tuples extracted from written files
4. **No-data-loss assertion:** Any row that fails Pydantic validation is written to `migration-errors.json` with full row data + error detail — never silently dropped

**Rollback plan:**
- The SQLite database is not deleted during migration — it remains at `store/memory/memory.db`
- If verification fails: delete the `.owlbear/memory/entries/` directory, fix the migration script, retry
- The MCP server reads from the NEW location only after a config flag (`MEMORY_STORAGE=files`) is set — default remains `sqlite` until migration is verified
- Rollback = unset `MEMORY_STORAGE` flag (or set to `sqlite`) — immediate, no data loss

**Migration invariant:** Every row in SQLite MUST produce exactly one valid `.md` file OR appear in `migration-errors.json`. The union of these two sets MUST equal the full row set. If `len(written) + len(errors) != total_rows`, migration FAILS.

### 7. Corruption Handling

**Corruption modes and responses:**

| Code | Condition | Detection | Response |
|------|-----------|-----------|----------|
| `ERR_NO_FRONTMATTER` | File doesn't start with `---` | At parse time | Quarantine |
| `ERR_UNCLOSED_FRONTMATTER` | No closing `---` delimiter | At parse time | Quarantine |
| `ERR_YAML_PARSE` | YAML syntax error in frontmatter | At parse time | Quarantine |
| `ERR_VALIDATION` | Pydantic validation failure (missing/wrong-type fields) | At parse time | Quarantine |
| `ERR_ID_MISMATCH` | Frontmatter `id` ≠ filename-derived ID | Post-parse check | Quarantine |
| `ERR_EMPTY_BODY` | Body is empty or whitespace-only | Post-parse check | Quarantine |
| `ERR_DUPLICATE_ID` | Two files claim the same `id` | At load (full scan) | Keep first (by mtime), quarantine second |
| `ERR_ORPHAN_TMP` | `.tmp-*` file exists in entries directory | At load | Delete silently (incomplete write) |

**Quarantine protocol:**
- Move corrupt file to `.owlbear/memory/quarantine/{filename}`
- Write `{filename}.reason` alongside it with corruption code + detail
- Log warning to stderr
- Continue loading remaining entries (never abort full load on single corruption)

**Load behaviour:**
- `load_all()` returns `(entries: list[MemoryEntry], errors: list[CorruptionReport])`
- Callers (MCP tools) use `entries` for queries; `errors` are logged but do not block operation
- A fully corrupt store (0 valid entries) is not treated specially — it returns an empty list, same as an empty store

**Repair (future):**
- `ERR_ID_MISMATCH`: auto-repairable by renaming file to match frontmatter `id`
- `ERR_VALIDATION` with missing `updated_at`: auto-repairable by copying `created_at`
- Other modes: require human intervention (entry stays in quarantine)

### 8. Deduplication

**Definition of duplicate:** Two entries are duplicates if they have the same `content` (case-sensitive, whitespace-normalized) AND the same `scope_agent`.

**Strategy:** Check-before-write in `record_learning`.

**Algorithm:**
1. At `record_learning` time, compute content fingerprint: `sha256(normalize(content) + "|" + (scope_agent or ""))`
2. Scan loaded entries for matching fingerprint
3. If match found AND existing entry is not deleted:
   - Return existing entry's `id` with a "duplicate" indicator (not an error — idempotent)
   - Update `confidence` if new confidence is higher (promotes existing entry)
   - Update `updated_at`
4. If match found but existing entry IS deleted:
   - Create new entry (deletion = intentional removal; re-recording is legitimate)

**Normalization:** Strip leading/trailing whitespace, collapse internal whitespace runs to single space. This prevents trivial reformatting from creating duplicates while preserving meaningful content differences.

**Performance:** At <200 entries, full scan with string comparison is <1ms. No index needed.

**Edge cases:**
- Same content, different `scope_agent` → NOT duplicates (scoped to different agents)
- Same content, same agent, different `category` → IS a duplicate (category is metadata about the same learning)
- Same content, same agent, different `confidence` → IS a duplicate (upsert confidence)

---

## Trade-offs

| Choice | Benefit | Cost |
|--------|---------|------|
| UUID-only filenames (no slug) | Stable across content edits, no rename cascade | Less human-readable in file listings |
| Last-writer-wins (no OCC) | Simpler implementation, no version tracking | Theoretical state loss if two curators race |
| Full in-memory load | Simple query logic, no index maintenance | Won't scale past ~500 entries without rethinking |
| Quarantine (not reject) | Preserves data for recovery, never loses bits | Quarantine dir accumulates if not cleaned |
| Soft delete only | Reversible, audit trail in git | Disk accumulates deleted entries forever (manual cleanup) |
| Dedup by content+agent fingerprint | Prevents the main duplication pattern (same agent re-recording) | Misses semantic duplicates (different wording, same insight) |
| SHA-256 migration verification | Provable lossless migration | Adds ~1s to migration for 200 entries |

---

## Domain Rationale

This design is shaped by three data-integrity convictions:

1. **Schema is the contract.** Every file on disk MUST pass Pydantic validation or it doesn't exist (from the tool's perspective). There is no "maybe valid" state. Invalid files go to quarantine immediately. This prevents NaN-equivalent propagation where a malformed entry silently corrupts query results.

2. **Validate between steps.** Migration validates at source (SQLite row → Pydantic model), at write (model → file), and at verification (file → model → field comparison). The `record_learning` path validates before write. The `load_all` path validates every file on every read. The cost is acceptable at <200 entries.

3. **Explicit failure over silent corruption.** A file with `confidence: "high"` (string instead of float) is not silently coerced — it's quarantined with `ERR_VALIDATION`. A file whose `id` doesn't match its filename is not silently trusted — it's quarantined with `ERR_ID_MISMATCH`. The system prefers serving fewer entries (valid ones) over serving all entries (some corrupt).

The kanban module proves this pattern works at this scale. The memory module has simpler semantics (no parent/child, no dependencies, no waves, no sections) — it's a strict subset of kanban's complexity with the same integrity guarantees.

---

## Confidence

**0.88** — High confidence in the core design (file format, validation, atomic writes, migration). Moderate uncertainty on deduplication semantics (the content+agent fingerprint catches the common case but semantic deduplication may surface as a need later). The "no OCC" decision is correct at current scale but would need revisiting if curation becomes concurrent.
