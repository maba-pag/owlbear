# Mode-6 Rename Collision Guard in `attempt_repair`

> **Owning task:** #1108 — Mode-6 rename collision guard in attempt_repair
> **Date:** 2026-04-23  **Status:** Complete

## 1. Context and Question

Mode-6 corruption (ID/filename mismatch) repair in `attempt_repair` computes a
canonical filename from frontmatter `id` + `title`, then calls
`path.replace(new_path)`. Python's `Path.replace()` **silently overwrites** the
destination if it already exists. If a valid task file already occupies
`new_path`, it is destroyed without warning.

**Question:** What guard should be added, and does the broader rename surface
(`move_to_quarantine`, `move_to_archive`) need the same treatment?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/corruption.py:384-408` | Codebase | 1.0 — the vulnerable code |
| 2 | `serve/kanban/src/owlbear_kanban/storage.py:417-426` | Codebase | 0.7 — `move_to_quarantine` same pattern |
| 3 | `serve/kanban/src/owlbear_kanban/storage.py:394-415` | Codebase | 0.6 — `move_to_archive` same pattern |
| 4 | `serve/kanban/src/owlbear_kanban/corruption.py:530-591` | Codebase | 0.8 — `scan_and_repair` dedup-before-repair flow |
| 5 | `serve/kanban/tests/test_storage_1050.py:972-985` | Codebase | 0.9 — only mode-6 repair test (happy path) |
| 6 | Python 3.12 `pathlib.Path.replace` docs | Stdlib | 1.0 — confirms silent overwrite semantics |

## 3. Analysis

### 3.1 Vulnerable Code Path

```
attempt_repair(path, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)
  → make_task_filename(fm_id, title) → new_path
  → path.replace(new_path)  ← NO EXISTENCE CHECK
```

### 3.2 Failure Scenario

1. File `999-wrong.md` has frontmatter `id: 42, title: "my task"`.
2. File `42-my-task.md` already exists as a valid task.
3. Mode-6 repair renames `999-wrong.md` → `42-my-task.md`, overwriting the valid file.
4. Data loss: original `42-my-task.md` content is gone.

### 3.3 Mitigation by `scan_and_repair`

`scan_and_repair` detects duplicate IDs (mode 2) **before** per-file repair,
using filename-prefix extraction. However:
- It extracts file-ID from filename prefix, not frontmatter. File `999-wrong.md`
  has file-ID 999, not 42. The dedup pass sees IDs 999 and 42 — no duplicate.
- `attempt_repair` is a public API callable standalone, without `scan_and_repair`.

**Conclusion:** `scan_and_repair`'s dedup does NOT prevent this collision.

### 3.4 Fix Options

| Option | Description | Complexity | Data Safety | KISS |
|--------|-------------|------------|-------------|------|
| A — exists-guard + quarantine | Check `new_path.exists()` before rename; quarantine on collision | 3 LOC | High | Yes |
| B — TOCTOU-safe link/unlink | Use `os.link()` + `os.unlink()` to avoid race | ~15 LOC | Highest | No |
| C — generate unique suffix | Rename to `{id}-{slug}-{n}.md` on collision | ~10 LOC | Medium | No — non-canonical names |

### 3.5 Broader Rename Surface

| Function | Same Bug? | Risk Level | In Scope? |
|----------|-----------|------------|-----------|
| `attempt_repair` mode-6 | Yes | **High** — overwrites valid task | Yes (#1108) |
| `move_to_quarantine` | Yes | Low — quarantine is last-resort storage | No — separate task if needed |
| `move_to_archive` | Yes | Low — same filename, different dir; true collision = mode-2 already caught | No — protected by file locks |

## 4. Recommendation

**Option A: exists-guard + quarantine.** Confidence: **0.90**

Before `path.replace(new_path)`, add `if new_path.exists(): return _quarantine()`
with detail `f"rename collision: {new_path.name} already exists"`.

Rationale:
- 3 lines of code. KISS-aligned.
- TOCTOU window is irrelevant: single-user, laptop-resident tool with no concurrent writers.
- Quarantine (not fail) preserves the corrupt file for manual inspection while protecting the valid destination.
- Option B over-engineers for a non-existent concurrency scenario.
- Option C introduces non-canonical filenames that would confuse other code paths.

Challenge: SKIPPED — trivial single-option bug fix with no design trade-off ambiguity.

## 5. Follow-Up Tasks

- **Implementation task:** Add `new_path.exists()` guard to mode-6 repair in `attempt_repair`, plus test for collision scenario. T1 — autonomous bug fix.
