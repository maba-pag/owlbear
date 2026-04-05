---
id: 567
title: Add dedup key to ErrorJournal entries
status: todo
priority: someday
created: 2026-03-04T07:39:09.7566652+01:00
updated: 2026-03-21T14:35:08.8209432+01:00
started: 2026-03-07T04:35:02.5427717+01:00
tags:
    - audit
    - resilience
    - scope:core
    - type:build
depends_on:
    - 828
class: standard
---

I-3: ErrorJournal.log() currently appends duplicate retry incidents. Implement the dedup change inside src/owlbear/memory/error_journal.py and keep the existing synchronous ErrorJournal API and bootstrap construction intact. See docs/research/error-journal-dedup.md. Depends on #828 (RED).

## AC
- [ ] ErrorEntry adds a dedup_key field with a default empty string and existing JSONL lines without the field still load successfully through JsonlStore.load().
- [ ] ErrorJournal.log() computes dedup_key internally as the first 16 hex characters of a SHA-256 fingerprint over (error_type, tool_name, exc_message) using UTF-8 encoding; the caller-facing log() parameters stay unchanged.
- [ ] Dedup suppression uses a monotonic in-memory 60-second window by default; repeated log() calls with the same fingerprint inside that window do not append a second persisted entry.
- [ ] Calls with a different fingerprint, or the same fingerprint after the window expires, still append a new persisted entry.
- [ ] The dedup cache is in-memory only, bounded to 128 fingerprints, and does not scan the JSONL file before each write.
- [ ] ErrorJournal.__init__ remains backward-compatible with current call sites ErrorJournal(workspace, *, max_entries=...); any dedup tuning is optional keyword-only.
- [ ] query() adds optional dedup_key filtering without changing existing tool_name, error_type, and last_n behavior; filtering still happens before last_n.
- [ ] Rotation semantics stay unchanged: when persisted entry count exceeds max_entries, the journal keeps the most recent max_entries stored entries.
- [ ] Scope stays in src/owlbear/memory/error_journal.py and related tests; do not change daemon async offload, bootstrap wiring, or config.py for this task.
- [ ] All RED tests from #828 pass.

Architecture notes:
- Keep ErrorJournal and JsonlStore synchronous; the contract in tests/test_daemon_async_contract.py remains valid.
- Preserve current bootstrap construction in src/owlbear/bootstrap/__init__.py: ErrorJournal(workspace).

## Architecture Review
See docs/scratch/567-architect.md for full review.
