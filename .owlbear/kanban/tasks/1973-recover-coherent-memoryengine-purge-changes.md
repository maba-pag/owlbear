---
id: 1973
title: Recover coherent MemoryEngine purge changes
status: collect
priority: high
created: 2026-07-21T16:06:04.774848+02:00
updated: 2026-07-21T16:18:54.810891+02:00
tags:
  - scope:memory
  - data-safety
  - concurrency
  - baseline-repair
parent:
depends_on: []
ac:
  - 'AC-1: Given deleted entries at the UTC cutoff and newer than it plus a non-deleted
    entry, `MemoryEngine.preview_purge()` classifies eligible, too_recent, and deleted_total
    without changing the filesystem.'
  - 'AC-2: Given eligible tombstones where one unlink fails and one file is already
    absent, `MemoryEngine.purge()` continues, reconciles purged, skipped, and failed
    counts, removes successful entries from cache and index, and retains the failed
    entry for retry.'
  - 'AC-3: Given purge or an ordinary lifecycle mutation interleaved with an mtime-triggered
    reload, both public calls complete and subsequent reads expose the persisted entries
    without index loss or duplication.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The previously verified core work from archived tasks #1946 and #1947 has durable commit ownership: tombstone purge and ordinary lifecycle mutation share one coherent MemoryEngine cache and index.

## Scope
In scope: the existing dirty changes in `serve/memory/src/owlbear_memory/engine.py` and `serve/memory/src/owlbear_memory/models.py`; typed purge results; age eligibility; protected best-effort deletion; instance-lock serialization of reload, purge, and lifecycle mutations.

Out of scope: Cockpit routes, frontend behavior, Memory MCP changes, new persistence formats, and unrelated workspace cleanup.

## Contract Authorities
- Archived core purge contract: #1946.
- Archived coherent cache mutation contract: #1947.
- Physical deletion owner: `owlbear_memory.storage.delete_entry`.

## Proof Guidance
Exercise the public MemoryEngine boundary with temporary files and controlled lower-layer scheduling or deletion outcomes, then run maintained memory lifecycle suites and Ruff on the owned files.

[[2026-07-21T16:16:29+02:00]]
## Builder Notes

Verdict: DONE.

Change envelope: adopted only the existing dirty `MemoryEngine` and purge result-model changes from archived #1946 and #1947; no Cockpit, MCP, persistence-format, or frontend file was included.

Behavior: typed age-gated preview and best-effort purge use protected storage deletion and reconcile absent/failing entries; one instance `RLock` serializes mtime checks, reload/index replacement, purge, and ordinary lifecycle mutations.

Proof: 198 maintained lifecycle/state/assessment/migration tests passed; Ruff lint passed; both files were formatted. A temporary public-engine probe froze the UTC clock, verified preview immutability and exact-cutoff classification, returned `purged=2, skipped=1, failed=1` under absent/failure injection, retained the failed entry, and completed a forced purge/read interleaving coherently. The probe was deleted after execution.

Durable-test decision: no new test committed. The maintained lifecycle suite plus deterministic task proof cover this recovered behavior without adding timing-sensitive test rent.

Builder-challenger: decision pass after independently rerunning all proof; no blocker, scope drift, or auto-fix.

[[2026-07-21T16:18:54+02:00]]
## Verify Notes

Verdict: PASS.

Exact revision: `e0d86e33f2eb02866eab0449df27ecba357c592b` in the clean prepared worktree.

Authority: archived #1946 core purge and #1947 coherent cache mutation; `storage.delete_entry` remains the protected deletion owner.

Proof at exact revision: 198 maintained memory lifecycle/state/assessment/migration tests passed; Ruff lint and format passed. A fresh temporary public-engine probe verified immutable exact-cutoff preview, absent/failure reconciliation (`purged=2`, `skipped=1`, `failed=1`), failed-entry retry retention, and an event-controlled purge/read interleaving. The expected injected OSError was logged and did not abort purge. The probe was removed and the worktree returned clean.

No durable test was added: deterministic public-boundary proof plus maintained suites cover the risk without timing-sensitive test rent.

Verifier-challenger: decision pass; no scope, lock-coverage, purge-safety, proof, or unresolved-AC finding.
