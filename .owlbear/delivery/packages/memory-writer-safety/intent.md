# Memory Writer Safety

> Status: candidate Design authority; decisions resolved; admission gates pending

## Problem

OwlBear Memory persists entries as Markdown files under `.owlbear/memory/`. Several independent
writers act on that directory: the Memory MCP server (one process per VS Code window), Cockpit's
memory routes, and the curator batch commit (`commit_memory_batch` MCP tool and
`python -m owlbear_memory_mcp.git`). Three open defects let a writer silently lose or misrepresent
memory state:

- **#238 lost updates.** `MemoryEngine` serializes mutations with an in-process `RLock` only.
  Each mutation reads through the instance cache, compares `expected_updated_at`, and writes.
  Two engine instances (MCP and Cockpit, or two MCP processes) can both pass the check and both
  succeed; the later atomic replace silently discards the other change (observed in
  `serve/memory/src/owlbear_memory/engine.py` on `dev` 48f263325; audit probe P02).
- **#241 unvalidated commit bytes.** `commit_batch` validates files with `_load_entries`, then runs
  `git add` per path and `git commit -m ... -- <paths>`. No lock or recheck spans validation to
  commit, and `git commit -- <paths>` takes the working-tree content of those paths at commit time,
  so bytes changed after validation can reach HEAD (observed in
  `serve/memory-mcp/src/owlbear_memory_mcp/git.py`; audit probe P12). PR #397 (commit 6a6b06757)
  moved deletion validation before staging and added restore guidance; the validation-to-commit
  gap is unchanged (observed).
- **#240 stale cache and duplicate IDs.** `MtimeScanCache` keys only on the directory mtime, so an
  in-place external edit can stay invisible to a live engine. When two files carry the same entry
  ID, `_load` keeps the later `updated_at` and leaves the other file; `purge`, `delete`, and other
  mutations act on the selected path, which can resurrect the older, hidden entry (observed;
  audit probes P03 and P16). `health()` already reports duplicate paths (observed). The engine
  never creates duplicates itself: new entries are written to `<id>.md` and updates replace the
  existing path (observed); duplicates come from external copies, sync-tool conflict copies, or
  merge leftovers.

## Product Promise

1. **No silent lost update.** Two supported writers in different processes or engine instances can
   never both report success for conflicting changes to one entry while one change disappears. A
   stale writer receives a concurrency result; the winning entry stays unchanged and readable.
2. **Every mutation is covered.** `save`, `edit`, `approve`, `resolve`, `delete`, `purge`,
   `record_assessment`, `record_factually_wrong`, the stale auto-transition, `rename_agent`, and
   `delete_agent` all run their fresh-read, check, write, and any rollback inside one
   cross-process critical section with a bounded wait.
3. **Committed changes are validated changes.** A successful memory batch commit contains exactly
   the memory paths and bytes it validated; a change after validation, or a path or blob added by
   a hook, is rejected before commit or reported as a typed failure after commit, never silently
   reported as success. Unrelated staged paths and user staging choices for memory paths are
   neither consumed nor reset.
4. **Fresh reads after external repair.** A supported external edit or repair of a memory file
   becomes visible to a running engine on its next read without restarting MCP or Cockpit.
5. **Duplicate IDs repair themselves safely.** When an entry ID maps to more than one file, the
   first mutation or batch commit that observes it repairs it under the writer lock with no user
   action: the newest copy keeps the ID, identical copies are removed, and each differing copy is
   preserved as a new `pending` entry with a new ID and a title marker naming the original ID, so
   the curator reviews it. No content is lost, no older or retired copy becomes recallable, no
   operation silently acts on an arbitrary copy, and HEAD never loses the ID while its surviving
   file is still pending. Reads never write; until repair, `health()` keeps reporting the
   duplicate.
6. **Real proof.** Acceptance uses real multi-process race tests against one temporary directory
   and a real temporary Git repository with real hooks, not mocks of the coordination or Git.

## Normal Workflows

- An agent saves or assesses memory through Memory MCP while the user edits, approves, resolves,
  or deletes entries in Cockpit. Both succeed when they do not conflict; when they conflict, the
  stale one is rejected (Cockpit 409 `MEM_CONFLICT`, MCP `ToolError`, or a per-entry failure in
  `assess_memories`) and can retry after a fresh read.
- The memory curator finishes a curation or review session and calls `commit_memory_batch`. Other
  writers that act during the commit wait for it or are reported busy after a bounded wait; the
  commit contains exactly the validated change set.
- A user repairs a memory file by hand (or restores it with Git). The next MCP recall or Cockpit
  list shows the repaired content.
- A sync tool or manual copy leaves two files with one ID. Cockpit health shows both paths until the
  next memory mutation or batch commit repairs them automatically; any differing copy then appears
  as a marked `pending` entry in the curator's normal review queue. If the surviving file is itself
  pending, the batch commit defers removing the old tracked path and reports it until the survivor
  is curated.

## Operating Context

- **Actors and trust (inferred):** the local user via Cockpit and editors/Git (trusted); agents via
  Memory MCP, possibly several server processes at once (trusted but fallible); the curator batch
  commit via MCP tool or CLI (trusted but fallible); Git hooks configured in the workspace (trusted
  configuration, fallible behavior); sync tools or copies that create duplicate files (trusted but
  fallible).
- **Exposure (inferred):** none added. Local filesystem only; Cockpit binds `127.0.0.1`. Hook output
  in commit diagnostics stays delimited as untrusted text (existing).
- **Stakes (inferred):** silent loss of reviewed memory content or lifecycle state, resurrection of a
  retired memory into agent recall, and unvalidated bytes reaching shared Git history. Uncommitted
  edits are not recoverable once overwritten.
- **Guarded:** concurrent `MemoryEngine` instances in one or many processes and threads; batch
  commit against engine writers; working-tree changes to committed memory paths between validation
  and commit; hooks that re-stage or add paths; symlinked memory paths in the commit snapshot;
  in-place external edits; duplicate-ID files.
- **Not guarded:** hostile local processes that bypass the coordination or tamper deliberately
  (outside the trusted set); network filesystems whose `flock` semantics differ; Windows
  (documented unsupported in `setup/setup-guide.md`); raw file writers that bypass `MemoryEngine`
  racing an engine mutation of the same entry (they are external repair, not supported concurrent
  writers); a raw edit or hook change landing after the pre-commit recheck (detected by post-commit
  verification, not prevented); editors that preserve file mtime, inode, and size on in-place
  edit; choosing the semantically correct version among differing duplicate copies (the newest
  keeps the ID; the curator judges the preserved copies); crash consistency of multi-entry
  lifecycle operations beyond existing rollback.

## Scope

- Cross-process writer coordination owned by the Memory core and used by every engine mutation
  and by `commit_batch` (one locking protocol, per #241).
- Fresh-read OCC inside the critical section; typed concurrency and busy results; distinct
  `updated_at` per mutation.
- Cache freshness contract for external edits.
- Automatic duplicate-ID repair under the writer lock, run by engine mutations and by
  `commit_batch`, and the narrow batch-commit deletion rule it needs, including deferral while the
  survivor is pending.
- Batch commit held under the writer lock with guarded snapshot reads, pre-commit recheck,
  post-commit change-set verification, staged-divergence refusal, deferred-deletion reporting, and
  documented index state on failure.
- Cockpit and MCP mapping of the new typed results for every mutation tool;
  `serve/memory/README.md`, `serve/memory-mcp/README.md`, and `share/skills/h-mcp-memory/SKILL.md`
  documentation of the supported writer model, freshness contract, duplicate repair, and commit
  semantics.

## Accepted Exclusions (issue-stated, confirmed at approval)

- Feedback revision/idempotency semantics: a stale `record_assessment` is rejected, not merged or
  retried automatically (#238 exclusion; D3).
- Agent-retirement deletion policy and rollback semantics (#238, #241 exclusions; PR #397 behavior
  is a precondition).
- Cockpit UI conflict presentation beyond the existing error envelope (#238 exclusion).
- Automatic Git index or HEAD reset or recovery after a failed commit (#241 exclusion).
- Defensive copies of cached model objects (#240 exclusion).
- A new memory schema field for duplicate provenance; the origin is carried in the title marker
  and a warning log.

## Preserved Behavior

- Atomic replacement in `storage.write_entry`, size limits, symlink and containment guards.
- Same-instance locking and reentrancy; existing OCC semantics for matching tokens.
- `health()` reports unreadable and duplicate paths without changing files.
- Reads return one entry per ID (the newest copy) and never write.
- Cockpit `409 MEM_CONFLICT`, `404 MEM_NOT_FOUND`, `422 MEM_INVALID_TRANSITION` envelopes.
- `assess_memories` per-entry result contract.
- Batch commit: pending entries never committed; symlinked or non-regular memory paths refused;
  state-aware deletion validation and restore guidance from PR #397 for every deletion other than
  a duplicate copy whose ID survives; bounded, delimited Git failure diagnostics with the
  `memory batch commit failed` MCP prefix; only memory `.md` paths are committed; Git hooks run as
  today; no-op returns empty.
- Reads (`get_entries`, recall, list) do not take the cross-process writer lock.

## Decisions

- **D1 (user-confirmed 2026-10-06): Option A.** `commit_batch` holds the shared Memory writer lock
  from reading and validation through `git commit`; it rechecks working-tree bytes against the
  validated bytes immediately before committing and verifies the committed change set in HEAD
  after committing. Other writers wait or receive a busy result for the commit and hook duration.
  Rejected: Option B isolated snapshot via temporary index (more plumbing; HEAD-move risk).
- **D2 (user-confirmed 2026-10-06): Option C, full automatic repair.** Under the writer lock, the
  newest copy (latest `updated_at`; tie: the file named `<id>.md`, then lexicographic path) keeps
  the ID; content-identical copies are removed; each differing copy is re-saved as a new `pending`
  entry with a new ID and a title marker naming the original ID, then its old file is removed.
  Batch commit allows physical deletion of a tracked memory file when another validated memory
  file carries the same ID, committing it with a non-pending survivor and deferring it while the
  survivor is pending. Rejected: A fail-closed manual repair (needs a person each time; user
  challenged why a user should fix it); B identical-copies-only (sync conflict copies still
  manual). Superseded: the earlier draft recommendation of manual file repair.
- **D3 (issue-stated, confirmed at approval):** a stale assessment is rejected like any other stale
  mutation.
- **Designer resolutions of challenger findings (package 10f1ca66, 2026-10-06):** post-commit
  verification covers the exact changed path set, not only blobs; a pending duplicate survivor
  defers the tracked-path deletion; snapshot reads keep symlink and regular-file guards; one
  deadline bounds both in-process and cross-process lock waits; every MCP mutation tool maps the
  new results, with `assess_memories` keeping per-entry results; rollback runs inside the lock and
  is proven against a second process.
- **Designer resolution of challenger findings (packages 2a9e8855 and 26747d81, 2026-10-07):** an
  interrupted repair keeps the pending copy it already wrote, and the retry reuses a marked pending
  copy only when every preserved field (title, content, categories, confidence, source agent, scope
  agents, created time) matches, so a copy with different scope or provenance is never
  substituted; a copy changed in between is a visible known limit. Superseded: reuse matched on
  title and content alone (package 26747d81).

## Success

Running two real processes that interleave the P02 ordering against one memory directory yields
exactly one success and one concurrency result with the winner intact; a many-process counter
stress run loses no successful increment; a real temporary Git repository commit contains exactly
the validated change set while a concurrent engine writer waits, a post-validation raw edit is
rejected, and hook-added changes are reported; an in-place edit becomes visible without restart;
and the P16 layout is repaired so the older approved copy survives only as a non-recallable pending
entry and is never resurrected.

## Technically Done But Wrong

- A finer timestamp or revision token without serializing the read-check-write (explicitly rejected
  by #238).
- A lock that only serializes calls on one object or one process, or whose in-process wait is
  unbounded.
- OCC compared against the cached entry instead of a fresh read inside the critical section.
- A second, independent locking protocol for the batch commit.
- Committing via `git commit -- <paths>` after validation with nothing preventing or detecting
  working-tree changes in between.
- Verifying only intended blobs while a hook can add extra paths to the commit.
- Overwriting a user's divergent staged memory blob, or committing unrelated staged paths.
- Making every read parse every file without measurement, or leaving in-place edits invisible
  until restart.
- Giving a differing duplicate copy a new ID while keeping its approved or curated state, which
  makes it recallable (the P16 resurrection under another name).
- Deleting a differing duplicate copy, or repairing duplicates from a read path or outside the
  writer lock.
- Writing another pending copy on every retry of an interrupted repair, or reusing a pending copy
  whose scope, provenance, or other preserved field differs from the version being removed.
- Committing a duplicate-copy deletion whose only survivor is pending, leaving HEAD with no file
  for that ID.
- Loosening batch-commit deletion validation beyond files whose ID survives in another validated
  file, or dropping the symlink guard when reading snapshot bytes.
- Race tests that mock the lock, use one engine object, or simulate Git.
- Treating the issues as closed before the Change is merged.

## Completion Follow-Up

Delivery has no issue-closing operation (observed: no issue-closing path in `serve/delivery` or
`serve/delivery-github`). When the Change completes, the operator closes GitHub issues #238, #240,
and #241 in `maba-pag/owlbear` with a comment linking the merged pull request.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: "GitHub issue #238 and user request 2026-10-06"
statement: "Two supported writers in different processes or MemoryEngine instances can never both succeed on conflicting changes to one memory entry while one change is silently lost; the stale writer receives a ConcurrencyError result and the winning entry stays unchanged and readable."
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: "GitHub issue #241 and user request 2026-10-06"
statement: "A successful memory batch commit contains exactly the memory paths and bytes it validated; a change after validation, or a path or blob added during the commit, is rejected before commit or reported as a typed failure after commit; unrelated staged paths and divergent user-staged memory blobs are neither committed nor reset."
```

```yaml target-contract
kind: commitment
id: COM-003
class: important-reviewed
provenance: "GitHub issue #240 and user request 2026-10-06"
statement: "An external edit that changes a memory file's inode, size, or modification time is visible to a running MemoryEngine on its next read without restart; load() remains an explicit force refresh; per-read freshness cost is measured and documented without parsing unchanged files."
```

```yaml target-contract
kind: commitment
id: COM-004
class: dealbreaker
provenance: "GitHub issue #240, user request 2026-10-06, and user decision D2 Option C"
statement: "An entry ID that maps to more than one memory file is repaired automatically under the writer lock by the first mutation or batch commit that observes it, never by a read; the newest copy keeps the ID, identical copies are removed, and each differing copy is preserved as a new pending entry with a new ID and a title marker naming the original ID; no content, scope, or provenance is lost, no older or retired copy becomes recallable, and HEAD keeps a file carrying the ID while its survivor is pending; when repair cannot complete, the triggering operation raises a typed result naming the paths and applies none of its own change, any pending copy already written is kept, and a later repair reuses a marked pending copy only when all its preserved fields match the version being removed."
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: "user decision D1 Option A (2026-10-06) and issue #241 single-protocol constraint"
statement: "The Memory core owns one cross-process writer lock, an exclusive advisory flock on the memory directory with one bounded wait covering in-process and cross-process contention and raising a ConcurrencyError subclass when busy; every MemoryEngine mutation takes it around a fresh read, check, write, and rollback, and commit_batch holds the same lock from reading and validation through git commit, rechecking working-tree bytes before and verifying the committed change set after; no lock file is added to the memory directory and no second locking protocol exists."
```

```yaml target-contract
kind: commitment
id: COM-006
class: protected-request
provenance: "user request 2026-10-06"
statement: "Acceptance proof uses real concurrent operating-system processes, each with its own MemoryEngine, against one temporary memory directory, and a real temporary Git repository with real hooks; the lock, engine coordination, and Git are not mocked in these tests, and failure injection is limited to forcing a storage failure inside the operating process."
```

```yaml target-contract
kind: commitment
id: COM-007
class: protected-request
provenance: "source-observed existing behavior and issue preservation clauses"
statement: "Atomic file replacement, storage symlink and containment guards (including in the batch-commit snapshot), same-instance reentrancy, matching-token OCC, health diagnostics, lock-free non-writing reads, existing Cockpit memory error envelopes, the assess_memories per-entry result contract, PR 397 deletion validation and restore guidance for every deletion other than a duplicate copy whose ID survives, PR 397 agent-retirement semantics, pending-entry exclusion from commits, bounded delimited Git diagnostics, and normal Git hook execution are preserved."
```
