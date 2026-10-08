# Memory Writer Safety Design

> Status: candidate architecture; decisions resolved; challenger findings of packages 10f1ca66, 2a9e8855, and 26747d81 repaired; admission gates pending

## Current Ownership (observed, dev 48f263325)

- `serve/memory/src/owlbear_memory/engine.py` `MemoryEngine`: per-instance `RLock`, `MtimeScanCache`
  (directory `st_mtime_ns` only), `_load` (duplicate IDs keep later `updated_at`), `get_entry` via
  cached `get_entries`, `_validate_occ` against the cached entry, `_write_updated_entry` (new
  entries at `<id>.md`, updates at the existing path), `_write_agent_lifecycle_changes` (PR #397
  tombstone semantics and rollback that rewrites original snapshots), `purge`, `health`.
- `serve/memory/src/owlbear_memory/storage.py`: `write_entry` atomic `mkstemp` + `fsync` +
  `replace`; `read_entry_strict` (rejects symlinks and non-regular files), `read_entry_bytes_strict`
  (bytes only, no path guards), `delete_entry`; 8,192-byte file limit.
- `serve/memory/src/owlbear_memory/models.py`: `MemoryEntry` (`extra="forbid"`, UUIDv4 `id`, no
  title length limit, content up to 1,024 characters), `MemoryHealth.duplicate_paths`.
- `serve/memory/src/owlbear_memory/errors.py`: `ConcurrencyError`, `ValidationError`,
  `TransitionError`, `NotFoundError`, `LifecycleRecoveryError`.
- Engine instances: Memory MCP lifespan (`serve/memory-mcp/src/owlbear_memory_mcp/server.py`) and
  Cockpit (`serve/cockpit/src/owlbear_cockpit/main.py`).
- MCP tools (`serve/memory-mcp/src/owlbear_memory_mcp/tools.py`): mutation tools pass
  `expected_updated_at=current.updated_at` from their own prior read. Catch boundaries differ:
  `save_memory` maps only Pydantic `ValidationError`; `curate_memory`, `delete_memory`, and
  `approve_memory` map `TransitionError`, `NotFoundError`, `ConcurrencyError`;
  `rename_agent_memories` and `delete_agent_memories` map `LifecycleRecoveryError` and
  `ValidationError`; `assess_memories` returns per-entry `success: false` results for
  `NotFoundError`, `TransitionError`, `ConcurrencyError`, `ValidationError` and continues;
  `commit_memory_batch` maps `ValueError`, `CalledProcessError` (with the
  `memory batch commit failed` prefix), and `OSError`. Recall returns only approved, curated, and
  contested entries; `list_memories` shows pending entries.
- `serve/memory-mcp/src/owlbear_memory_mcp/git.py` `commit_batch`: `_load_entries` validation via
  `read_entry_strict`, staged-pending rejection, deletion validation (before staging since PR #397;
  only HEAD states pending or deleted may be physically deleted), per-path `git add`,
  `git diff --cached --quiet`, `git commit -m ... -- <paths>` (Git partial-commit semantics: Git
  builds a temporary index from HEAD plus the listed working-tree paths, runs hooks with that
  index, and rereads it after hooks, so a hook that runs `git add` can change committed content or
  add paths).
- Cockpit (`main.py`) maps `ConcurrencyError` to 409 `MEM_CONFLICT`; `ValidationError` is unmapped
  (generic 500).
- Package boundary: memory-mcp and Cockpit may import `owlbear_memory`; Memory must not import
  Delivery (`tests/test_package_boundary.py`), so Delivery's `flock` helpers cannot be reused.
- Delivery already uses `fcntl.flock` (`serve/delivery/src/owlbear_delivery/storage_io.py`).
  `flock` on a directory descriptor is exclusive across open descriptions on macOS (observed in a
  scratch probe 2026-10-06); Linux `flock(2)` applies to any open file descriptor (documented).
- Existing real-Git fixtures: `tests/test_memory_git.py`, `serve/memory-mcp/tests/test_server.py`
  (`git init` in `tmp_path`, executable hooks). No multi-process memory tests exist today
  (observed).
- Live store size: 85 entry files in `.owlbear/memory/` (observed).

## Proposed Architecture

### Memory writer lock (Memory core, new public interface)

- New module in `owlbear_memory` exporting one writer-lock context manager for a memory directory
  (name chosen in build, for example `memory_writer_lock(memory_dir, timeout=...)`) and
  `MemoryBusyError(ConcurrencyError)` from `errors.py`; both re-exported from `owlbear_memory`.
- Mechanism: `fcntl.flock(LOCK_EX)` on an `O_RDONLY` descriptor of the resolved memory directory,
  so no lock file appears in the tracked memory directory.
- Reentrancy: a per-process registry keyed by the resolved directory owns one descriptor, an
  `RLock`, and a depth count. The thread that holds it can re-enter (nested engine calls such as
  `record_assessment` -> `try_stale_transition`, or repair inside a mutation); other threads and
  other engine instances in the same process serialize on the `RLock`; other processes serialize
  on `flock`. The descriptor is released and closed when depth returns to zero.
- Bounded wait: one deadline (default 30 seconds, parameterized for tests) covers both the
  in-process `RLock.acquire(timeout=...)` and `flock` polling with `LOCK_NB` and short backoff.
  Exceeding it raises `MemoryBusyError` without writing, whether the holder is another thread or
  another process.

### Fresh-read OCC

- `MemoryEngine` mutations replace their private-lock section with the writer lock. Inside it they
  refresh the cache (signature check below), run duplicate repair when the refreshed state has any
  duplicate ID, and compare `expected_updated_at` with the fresh entry. A mismatch raises
  `ConcurrencyError`; the losing call writes nothing.
- New `updated_at` values are strictly different from the prior value (advance by one microsecond
  when the clock returns the prior value).
- `save` takes the lock so new files never interleave with a commit's validated snapshot.
- Multi-entry operations (`rename_agent`, `delete_agent`, `purge`) hold the lock across fresh read,
  repair, computation, writes, and the existing rollback and reload, so no other writer observes
  or writes during rollback.
- Same-thread nested calls reuse the held lock; the existing per-instance `RLock` is removed or
  subsumed so there is one lock order.

### Cache freshness

- Replace `MtimeScanCache` with a stat-signature cache: a tuple of `(name, inode, size, mtime_ns)`
  for `*.md` entries from one `os.scandir` pass. Any difference triggers the existing full `_load`.
  Unchanged signatures return cached entries without parsing.
- Supported contract: an external write that changes a file's inode, size, or mtime is visible on
  the next read; `load()` remains the explicit force refresh. Atomic replacement always changes the
  inode.
- Build measures signature cost on a synthetic store of at least 100 entries (above the observed 85)
  and records the result and bound in `serve/memory/README.md`.

### Automatic duplicate-ID repair (D2 Option C)

- `_load` records every readable path per ID; reads keep returning one entry per ID (the canonical
  copy below) and never write. `health()` is unchanged and reports duplicates until repaired.
- One repair routine in the Memory core, callable only with the writer lock held, exposed for
  `commit_batch` (for example `repair_duplicate_ids(memory_dir)` or an engine method) and run by
  every engine mutation when the refreshed state has duplicates:
  1. Canonical copy per duplicated ID: latest `updated_at`; tie: the file named `<id>.md`; then
     lexicographically first relative path.
  2. Copies whose parsed `MemoryEntry` equals the canonical entry are deleted.
  3. Each differing copy is written as a new entry: new UUIDv4 `id` at `<new-id>.md`, state
     `pending`, `approved_at` and `contested_by_task` cleared, assessment counters zero,
     `score = confidence`, `created_at` preserved, `updated_at` now, same content, categories,
     confidence, source and scope agents, and title prefixed with a stable marker naming the
     original ID (exact wording chosen in build, for example `[duplicate of <id>] `). The new file
     is written before the old file is deleted. A warning log records original ID, old path, and
     new ID. Reuse after an interrupted earlier repair: if a `pending` entry already exists whose
     preserved fields all equal what this step would write (marked `title`, `content`,
     `categories`, `confidence`, `source_agent`, `scope_agents`, and `created_at`), that entry is
     reused and no new copy is written; only the old file is deleted. An entry that differs in any
     preserved field is never reused, so a copy is never replaced by one with different scope or
     provenance.
  4. If any step fails (write limit, I/O), the routine raises `DuplicateEntryError` naming the ID and
     relative paths; already-written new copies are kept (no content loss), the triggering
     mutation is not applied, and the next repair reuses those copies through step 3.
- Consequences: P16 (older approved copy plus newer tombstone) becomes the tombstone under the
  original ID plus a non-recallable pending copy; the curator sees marked pending entries through
  the normal `list_memories` queue.
- `delete_agent` after repair applies existing retirement policy to the new pending copy (a pending
  orphan of the retired agent is hard-deleted), consistent with PR #397.

### Batch commit (D1 Option A)

`commit_batch(memory_dir, session_type)` after this change:

1. Acquire the Memory writer lock for `memory_dir` (busy -> `ValueError`-class diagnostic through
   the existing CLI and MCP error paths; no Git mutation).
2. Run duplicate repair.
3. Snapshot: for each `*.md` path, apply the same guards as `read_entry_strict` (reject symlinks
   and non-regular files; open without following symlinks), read the bytes once, and validate those
   bytes with `read_entry_bytes_strict`. If duplicates are still present, refuse naming the paths.
4. Existing staged-pending rejection and PR #397 deletion validation, with one narrow exception for
   a deleted tracked path whose HEAD entry ID is carried by another validated working-tree file:
   - survivor non-pending (committed in the same batch): the deletion is committed;
   - survivor pending (not committed): the deletion is deferred, meaning left unstaged and out of
     this commit, so HEAD keeps one file carrying the ID; the deferred path is reported to the
     caller and is committed by a later batch once the survivor is no longer pending.
   Every other deletion keeps the PR #397 refusal and restore guidance.
5. Staged-divergence refusal: for each memory path to commit, if the index blob differs from both
   HEAD and the validated bytes' blob, refuse naming the path and change nothing.
6. Stage with `git add` (existing); return the no-op result when nothing differs (existing).
7. Recheck: each committed path's working-tree bytes must equal the validated bytes (deleted paths
   must still be absent); otherwise refuse naming the path before committing.
8. `git commit -m <message> -- <paths>` (existing; hooks run).
9. Verify the commit against the intended change set: the set of paths changed between the
   recorded pre-commit HEAD and the new HEAD (`git diff-tree -r --no-renames`, or the root tree
   when there was no HEAD) must equal exactly the intended set, each added or modified path's blob
   must equal the validated blob, and each intended deletion must be absent. Any extra path,
   missing path, or differing blob (for example a hook that re-stages a memory file or runs
   `git add -A`) raises a typed failure naming the paths and stating that HEAD contains unvalidated
   changes and how to inspect them; nothing is reset automatically.
10. Release the lock in all paths.

Result: `commit_batch` returns the commit SHA (or the no-op result) plus the deferred deletion
paths; the CLI prints deferred paths as a note, and `commit_memory_batch` adds them to its result
(for example `deferred_deletions`) with a hint to curate the surviving pending entry. Failure after
staging keeps the documented state: memory paths may remain staged; unrelated staged paths are
untouched.

### Error routing

- Memory MCP: `save_memory`, `curate_memory`, `delete_memory`, `approve_memory`,
  `rename_agent_memories`, and `delete_agent_memories` map `ConcurrencyError` (including
  `MemoryBusyError`) and `DuplicateEntryError` to `ToolError` with the typed message;
  `assess_memories` reports them as per-entry `success: false` results and continues with the next
  item (existing per-entry contract); `commit_memory_batch` maps commit refusals through its
  existing `ValueError` path and keeps the `memory batch commit failed` prefix for Git failures.
- Cockpit: `ConcurrencyError` and `MemoryBusyError` -> 409 `MEM_CONFLICT` (existing handler);
  `DuplicateEntryError` -> 409 `MEM_DUPLICATE_ID` (new handler).

## Interfaces And Failure Semantics

- New public Memory interfaces: writer-lock context manager, `MemoryBusyError(ConcurrencyError)`,
  `DuplicateEntryError` (raised only when repair cannot complete), duplicate repair routine.
- Changed: every `MemoryEngine` mutation may raise `MemoryBusyError` or `DuplicateEntryError` and may
  perform duplicate repair writes; `ConcurrencyError` now reflects fresh disk state. `commit_batch`
  raises `ValueError` diagnostics for busy, unsafe path, post-validation change, staged divergence,
  remaining duplicates, and post-commit mismatch; it may commit or defer duplicate-copy deletions
  and reports deferred paths.

## Alternatives Rejected

- Finer timestamps or revision tokens alone: do not serialize read-check-write (#238).
- Option B isolated snapshot commit (user decision D1).
- Manual or identical-only duplicate repair (user decision D2).
- Re-ID'ing a differing copy while keeping its state: resurrects retired content under a new ID.
- Refusing the whole batch when a duplicate survivor is pending: blocks curation for a rare case;
  deferral keeps HEAD consistent without user action.
- A provenance schema field for repaired copies: schema change across storage, MCP, and Cockpit for
  a rare repair; the title marker and log suffice.
- All-or-nothing repair with rollback of written pending copies: deleting a written copy on failure
  risks losing the only preserved version; keeping it and reusing it on retry is simpler and safe.
- Reusing a marked pending copy matched on title and content alone: a copy with different scope or
  provenance could stand in for the deleted version, and agent retirement could then erase it.
- Lock file inside `.owlbear/memory/`: adds an untracked artifact in every consumer workspace;
  directory `flock` avoids it.
- Full content scan on every read: unmeasured cost (#240); stat signature suffices for the
  supported contract.

## Known Weaknesses

- `flock` is advisory: raw editors and Git operations do not take it.
- Engine writers wait, or get `MemoryBusyError` after the bounded wait, while a commit and its hooks
  run.
- A raw edit in the milliseconds between recheck and Git's read, or a hook that changes the commit,
  is detected after commit, not prevented; the commit then exists and must be inspected by the user.
- A stale MCP assessment is rejected rather than merged (D3).
- Repair can produce Git changes (a new pending file and a removed path) during an unrelated
  mutation; the pending copy is not committed until curated, so the committed tip drops that
  version until then (it remains in history and the working tree).
- The newest duplicate copy keeps the ID even if an older copy was the intended version; the curator
  judges the preserved pending copy.
- Repair is not all-or-nothing: a failure after a pending copy is written leaves that copy and the
  old file until the next mutation or batch commit retries. The retry reuses the copy only when all
  preserved fields still match; if any was changed in between, the retry writes a second marked
  pending copy. Content is preserved either way and the curator removes the extra copy.
- Lifecycle rollback proof uses failure injection inside the operating process's storage call to
  force a mid-operation failure; the lock and the second process are real.
- Directory replacement (delete and recreate `.owlbear/memory`) while engines run is not guarded.

## Proof Approach

- Real processes: `multiprocessing` with the `spawn` start method (or `subprocess` running the
  workspace interpreter) and `Barrier`/`Event` synchronization at synchronous read, validation, or
  hook boundaries (not sleep-based scheduling) against one `tmp_path` memory directory. Each
  process constructs its own `MemoryEngine`. No mocks of the lock, engine coordination, or Git.
- Real Git: `git init` in `tmp_path`, including real executable `pre-commit` hooks used as the
  interleaving point (signal file, then wait for a release file with a timeout) or as the
  misbehaving actor (re-stage, `git add -A`, non-zero exit).
- Focused suites: `tests/test_memory_*.py`, `tests/test_cockpit_memory_routes.py`,
  `serve/memory-mcp/tests/`, `tests/test_package_boundary.py`, run with `uv run pytest <paths>`.

```yaml target-contract
kind: outcome
id: OUT-001
title: Cross-process serialized memory mutations
promise: Memory MCP, Cockpit, and any other MemoryEngine instance can mutate memory at the same time without silently losing an accepted change; a stale or blocked writer gets a concurrency result.
dependencies: []
commitments: [COM-001, COM-005, COM-006, COM-007]
acceptance:
  - "AC-001: Given two separate operating-system processes, each with its own MemoryEngine on one temporary memory directory, that both read entry E and obtain the same updated_at token and then, after a barrier, both call edit on E with that token and different content, exactly one call succeeds, the other raises ConcurrencyError, and a fresh MemoryEngine in a third process reads E with exactly the winner's content."
  - "AC-002: Given one process holding the Memory writer lock for a directory, a mutation started in a second process with its own MemoryEngine does not change the entry file until the first process releases the lock, and then succeeds when its token matches the fresh on-disk entry or raises ConcurrencyError leaving the file byte-identical when it does not."
  - "AC-003: Given at least four concurrent processes each performing at least 25 record_assessment calls on the same entry, each retrying after ConcurrencyError with a freshly read token, the entry's final outstanding_count equals the total number of calls that returned success."
  - "AC-004: Given another process, or another thread of the same process, holds the writer lock longer than a short configured timeout, each of save, edit, approve, resolve, delete, purge, record_assessment, record_factually_wrong, rename_agent, and delete_agent raises MemoryBusyError, a subclass of ConcurrencyError, within that timeout plus a small margin and changes no memory file."
  - "AC-005: Given a Cockpit TestClient backed by a real MemoryEngine and a separate process using a real MemoryEngine on the same directory, a Cockpit edit carrying a token made stale by the other process's completed edit returns HTTP 409 with code MEM_CONFLICT and the other process's content remains on disk; given a busy lock, the Cockpit route also returns 409 MEM_CONFLICT."
  - "AC-006: Given a real MemoryEngine whose writer lock is held by another process past the timeout, save_memory, curate_memory, delete_memory, approve_memory, rename_agent_memories, and delete_agent_memories each raise ToolError carrying the busy message, and assess_memories returns success false with that message for the blocked item while still processing later items; given an entry changed by another process between curate_memory's read and its mutation, the tool raises ToolError with the concurrency message and the other process's content remains on disk."
  - "AC-007: Given record_assessment that triggers the stale auto-transition, and two MemoryEngine instances in one process used sequentially and from two threads, all calls complete without deadlock, and existing same-instance OCC tests pass unchanged."
  - "AC-008: Given a mutation whose clock returns exactly the entry's prior updated_at, the written updated_at differs from the prior value and a writer holding the prior token is rejected."
  - "AC-009: Given a delete_agent in one process whose storage write is forced to fail partway and which pauses inside its rollback, a mutation started by a second process during that pause does not change any file until the first process finishes rollback and releases the lock, and afterwards the second process observes the restored original entries."
  - "AC-010: Given the change, uv run pytest tests/test_memory_engine.py tests/test_memory_state_machine.py tests/test_memory_primitives.py tests/test_cockpit_memory_routes.py tests/test_package_boundary.py serve/memory-mcp/tests plus the new race test files passes, and no file other than entry files is created in the memory directory."
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Fresh reads and automatic duplicate repair
promise: A running engine shows externally repaired memory on the next read, and duplicate entry IDs are repaired automatically and safely without user action, losing no content and resurrecting nothing into recall.
dependencies: [OUT-001]
commitments: [COM-003, COM-004, COM-006, COM-007]
acceptance:
  - "AC-011: Given a live MemoryEngine that has already returned entry E, when another process rewrites E's file in place (same path and inode, changed content and mtime), the next get_entries and get_entry calls on the live engine return the new content without calling load()."
  - "AC-012: Given an unchanged memory directory, repeated get_entries calls do not reparse entry files, and the measured per-call freshness cost for a 100-entry synthetic store is recorded with its bound in serve/memory/README.md."
  - "AC-013: Given two files with byte-identical content for one ID, get_entries and health() before any mutation write nothing and health() lists both paths; the next mutation of any entry removes the copy not named <id>.md, after which health() reports no duplicate and the mutation's own result is correct."
  - "AC-014: Given the P16 layout, an older approved file and a newer age-eligible deleted tombstone sharing one ID, purge leaves no file carrying that ID in an approved state, recall_memory for every scope agent of the approved copy does not return its content, and list_memories shows a pending entry with a new ID whose title marker names the original ID and whose content equals the approved copy's content."
  - "AC-015: Given two differing copies of one ID and a reader holding the token of the newest copy, edit with that token succeeds on the newest copy, and the older copy's content survives as a pending entry with a new ID and the title marker; no content of either copy is lost."
  - "AC-016: Given two differing copies with equal updated_at, repair keeps the file named <id>.md as the canonical copy; given rename_agent or delete_agent touching a duplicated ID, repair runs first and the operation then applies its existing policy to the canonical and repaired entries."
  - "AC-017: Given a duplicated ID whose repair cannot write (memory directory made non-writable on the real filesystem), the triggering mutation raises DuplicateEntryError naming the ID and paths, applies nothing, deletes no copy, the Cockpit mutation route returns HTTP 409 with code MEM_DUPLICATE_ID, and the Memory MCP curate_memory tool raises ToolError naming the paths."
  - "AC-018: Given two separate processes that both observe the same duplicate and both start mutations, repair happens exactly once: afterwards exactly one file carries the original ID and at most one pending copy exists per differing copy."
  - "AC-029: Given a duplicated ID whose differing older file is still present alongside a marked pending entry whose title, content, categories, confidence, source_agent, scope_agents, and created_at all equal the repair output for that file (left by an interrupted repair), the next mutation removes the older file without writing another pending copy and health() reports no duplicate; given instead a marked pending entry with the same title and content but different scope_agents, repair writes a new pending copy carrying the older file's own scope_agents, leaves that other entry unchanged, and a later delete_agent of the other entry's scope agent does not remove the new copy."
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Validated-snapshot memory batch commit
promise: A curator batch commit records exactly the memory changes it validated, never a concurrent, post-validation, or hook-added change, never consumes or resets a user's unrelated or divergent staging, and commits duplicate repairs without losing an ID from HEAD.
dependencies: [OUT-001, OUT-002]
commitments: [COM-002, COM-004, COM-005, COM-006, COM-007]
acceptance:
  - "AC-019: Given a real temporary Git repository, reproducing P12 by replacing a valid memory file with different valid bytes immediately after commit_batch validation causes commit_batch to raise a ValueError naming that path before committing, and HEAD is unchanged."
  - "AC-020: Given a real temporary Git repository with a real pre-commit hook that signals and then waits, a separate process calling MemoryEngine.edit during the hook does not change the file until commit_batch returns, the committed HEAD blob of every memory path equals the validated bytes, and afterwards the working tree contains the other process's edit."
  - "AC-021: Given a memory path whose staged blob differs from both HEAD and the working tree, commit_batch refuses naming the path and leaves that index entry unchanged; given an unrelated staged non-memory path, a successful commit_batch does not include it and it remains staged."
  - "AC-022: Given a real pre-commit hook that rewrites and re-stages a validated memory file, and separately a real pre-commit hook that runs git add -A while an unrelated file and a pending memory file are present, commit_batch reports a failure naming the differing or extra paths and stating that HEAD contains unvalidated changes, and does not reset HEAD or the index."
  - "AC-023: Given a real pre-commit hook that exits non-zero after staging, commit_batch raises a failure carrying the bounded delimited hook output, HEAD is unchanged, memory paths may remain staged as documented, and a MemoryEngine mutation in another process succeeds afterwards (lock released)."
  - "AC-024: Given a tracked approved memory file and a differing copy with the same ID whose newest copy is non-pending, commit_batch repairs the duplicate, commits the removal of the non-canonical tracked path together with the canonical file, does not commit the new pending copy, and leaves exactly one file in HEAD carrying the original ID."
  - "AC-025: Given a tracked approved memory file and a newer pending copy with the same ID, commit_batch repairs the duplicate, defers the removal of the tracked path (not staged, not committed, reported as deferred by commit_batch, the CLI, and commit_memory_batch), and HEAD still contains exactly one file carrying the original ID; after the surviving entry is curated, the next commit_batch commits the survivor and the deferred removal."
  - "AC-026: Given a deleted tracked approved file whose ID is carried by no other file, the PR #397 refusal and restore guidance are unchanged; given no memory changes, commit_batch returns the no-op result; given a pending entry, it is not committed; given a staged pending entry, the existing refusal is unchanged; given a memory path that is a symlink, commit_batch refuses naming it and creates no commit."
  - "AC-027: Given the change, serve/memory/README.md, serve/memory-mcp/README.md, and share/skills/h-mcp-memory/SKILL.md describe the supported writer model, busy and stale results, freshness contract, automatic duplicate repair and its title marker, and commit lock, recheck, change-set verification, deletion exception and deferral, and index-state semantics consistently with the code."
  - "AC-028: Given the change, uv run pytest tests/test_memory_git.py serve/memory-mcp/tests plus the new Git race test file passes."
```
