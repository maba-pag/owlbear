# Route Engine Task I/O Through Storage Surface

> **Owning task:** #1097 — Route engine task I/O through storage surface
> **Date:** 2026-04-22 **Status:** Complete

## 1. Context and Question

Task #1097 was created during the C-05 (#1050) review cycle as a follow-up for routing `engine.py` and `dispatch.py` imports from `task_io` to `storage`. The task arrived with an empty body — this research determines whether it is valid standalone work or already subsumed by existing Brief C tasks.

**Core question:** Can the import re-routing be done as an isolated mechanical refactoring, or does it entail behavioral changes that belong in existing Brief C tasks?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `paper-c.md` §1.4, §8.10 (AC-C45) | 0.95 — defines the architectural boundary |
| 2 | `engine.py` lines 47, 508–1089 (19 claimed_by uses, 10 read_task, 8 write_task) | 0.95 — current engine I/O surface |
| 3 | `storage.py` lines 175–281, 431–460 (write_task strips claimed_by; __all__) | 0.95 — target storage surface |
| 4 | C-14 #1059 AC: "task_io.py removed; all imports redirected to storage" | 0.90 — explicit scope overlap |
| 5 | C-17 #1062 AC-C47/C52: migration guard, sweep claim-only semantics | 0.90 — covers claim model transition |
| 6 | C-18 #1063: engine activity/session wiring | 0.85 — covers activity-derived claim state |
| 7 | C-19 #1064 AC-C45: boundary test enforcement | 0.85 — test-side enforcement |
| 8 | `dispatch.py` line 20, 166–181 (imports read_task, globs tasks_dir, checks claimed_by) | 0.80 — additional consumer |

## 3. Analysis

### 3.1 Why the import swap is NOT mechanical

| Concern | task_io behavior | storage behavior | Impact |
|---------|-----------------|-----------------|--------|
| `write_task` signature | `(path, record)` | `(task, kanban_dir)` | 8 call sites need adaptation |
| `claimed_by` on write | Written to disk | **Stripped** (`data.pop("claimed_by")`) | Breaks claim semantics |
| `claimed_by` on read (archive) | Preserved | **Stripped** | Changes archive read behavior |
| Config reload | None (path-based) | Reloads `config.yml` per call | Performance delta |
| Path construction | Caller-owned | Storage-internal | Engine loses `make_task_filename` |
| Archive move | `git mv` preferred | `Path.replace()` only | Git-tracking behavioral change |

**Critical finding:** The engine sets `record.claimed_by = self._agent_name` before `write_task()` in 5 methods (claim, release, end_work, sweep, move). Storage's `write_task` strips `claimed_by` — so routing through storage silently breaks the claim model. This is a semantic change, not a mechanical one.

### 3.2 Scope overlap with existing Brief C tasks

| Brief C task | What it covers of #1097's scope |
|--------------|-------------------------------|
| C-14 (#1059) | "task_io.py removed; all imports redirected to storage" — covers the redirect |
| C-17 (#1062) | Engine storage-integration edits, migration guard (AC-C47), sweep claim-only (AC-C52) — covers claim model transition |
| C-18 (#1063) | Activity/session wiring — covers activity-derived claim state replacing claimed_by |
| C-19 (#1064) | Boundary test AC-C45 — covers enforcement that engine no longer imports task_io |

The entire scope of #1097 is distributed across these four existing tasks in the Brief C dependency chain: C-14 → C-17 → C-18 → C-19.

### 3.3 Dependency sequence analysis

```
C-14 (#1059) removes task_io.py → engine MUST import from storage
C-17 (#1062) adapts engine claim model + corruption + repair
C-18 (#1063) wires activity log + session state (replaces claimed_by with activity-derived state)
C-19 (#1064) enforces boundary tests (AC-C45)
```

#1097 cannot be inserted as a standalone prerequisite because:
1. The import swap requires the claim model transition (otherwise claims break)
2. The claim model transition is C-17 + C-18's scope
3. C-14 already includes "all imports redirected"

## 4. Recommendation

**Close #1097 as subsumed by existing Brief C tasks.** Confidence: **0.88**.

The work #1097 describes is fully covered by the C-14 → C-17 → C-18 → C-19 sequence. Creating a standalone intermediate task would:
- Duplicate scope with C-14's "all imports redirected" AC
- Risk breaking claim semantics if done before C-17/C-18's claim model transition
- Create confusion about ownership boundaries between tasks

**Challenge:** `block` (confidence in original: 0.37). Challenger correctly identified that claimed_by semantics, create-task crash ordering, and dispatch filesystem access make this a behavioral change, not a mechanical import swap. Original recommendation revised accordingly — from "keep as T1 prerequisite" to "close as subsumed."

## 5. Follow-up Tasks

No new follow-up tasks needed. The existing Brief C decomposition (#1059, #1062, #1063, #1064) already covers the full scope with proper ACs, RED tests, and dependency ordering.

**Recommended action on #1097:** Advance to backlog with a note that the scope is subsumed, then the orchestrator should archive or close it during the next sweep.
