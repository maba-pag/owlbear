---
id: 1001
title: Add CancelSlot and wire tool-invoked cancellation to daemon shutdown
status: archived
priority: nice-to-have
created: 2026-03-25 04:41:37.504823+01:00
updated: 2026-03-25 06:37:17.328478+01:00
tags:
- scope:core
- type:build
depends_on:
- 870
- 1002
class: standard
archival_reason: completed
archival_refs: []
---

**Source:** #877 research (docs/research/tool-invoked-cancellation.md)

**AC:**

1. Add `CancelSlot` class to `owlbear.memory.knowledge.cancellation` satisfying `CancelSignal` protocol: `set_source(source: CancelSignal) -> None` for late binding; `is_set() -> bool` returns `False` when no source linked, delegates to source when linked.
2. `KnowledgeToolset`, `KnowledgeSourceToolset`, and `BookmarkToolset` accept optional `cancel: CancelSignal | None = None` at construction and pass it to pipeline calls in `_ingest_document`, `_refresh_source`, `_bookmark_source`.
3. `_build_knowledge_toolset`, `_build_bookmark_toolset`, and `_build_knowledge_source_toolset` in `bootstrap/knowledge.py` accept and forward a `cancel` param; `build_toolsets` in `bootstrap/toolsets.py` creates a `CancelSlot`, passes it to all 3 helpers, and stores the slot on `BootstrapResult.cancel_slot`.
4. `run_daemon()` accepts `cancel_slot: CancelSlot | None = None` and calls `slot.set_source(LinkedCancelSignal(shutdown_event))` after creating `shutdown_event`.
5. Non-daemon callers remain unchanged (`CancelSlot.is_set` returns `False` when unlinked, matching today's behavior).
6. All RED tests from #1002 pass (GREEN) after implementation.

[[2026-03-25]] Wed 06:37

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

- AC1 (CancelSlot): Refined with method signatures and return semantics. Precise.
- AC2 (Toolset cancel param): Precise as-is. Named classes, methods, pipeline targets.
- AC3 (Bootstrap wiring): Refined to name _build_*_toolset helpers and BootstrapResult.cancel_slot.
- AC4 (Daemon wiring): Refined to add cancel_slot param on run_daemon.
- AC5 (Non-daemon unchanged): Clear behavioral constraint, testable.
- AC6 (Tests): Replaced vague 'focused tests' with explicit #1002 RED test reference.

### Architecture Notes

- CancelSlot maps to .NET CancellationTokenSource/Token (.90 confidence).
- cancellation.py already owns CancelSignal + LinkedCancelSignal; CancelSlot co-locates.
- Toolset constructors follow optional-param pattern; backward-compatible.
- BootstrapResult is non-frozen dataclass (bootstrap/_types.py:93); safe to extend.
- Existing precedent: RetrospectiveHook receives LinkedCancelSignal from bootstrap.
- No security surface: internal-only, read-only access, single-threaded event loop.
- No failure mode risk: unlinked CancelSlot returns False (same as today).

### TDD Dependency Fix

- Added depends_on #1002 to #1001.
- WARNING: #1002 has depends_on [1001, 870] creating circular dep. Architect reviewing #1002 must remove depends_on 1001.

### Changes Made

- Refined AC1, AC3, AC4, AC6
- Added depends_on: 1002 (TDD compliance)

[[2026-03-25]] Wed 06:37

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

- AC1 (CancelSlot): Refined with method signatures and return semantics. Precise.
- AC2 (Toolset cancel param): Precise as-is. Named classes, methods, pipeline targets.
- AC3 (Bootstrap wiring): Refined to name _build_*_toolset helpers and BootstrapResult.cancel_slot.
- AC4 (Daemon wiring): Refined to add cancel_slot param on run_daemon.
- AC5 (Non-daemon unchanged): Clear behavioral constraint, testable.
- AC6 (Tests): Replaced vague 'focused tests' with explicit #1002 RED test reference.

### Architecture Notes

- CancelSlot maps to .NET CancellationTokenSource/Token (.90 confidence).
- cancellation.py already owns CancelSignal + LinkedCancelSignal; CancelSlot co-locates.
- Toolset constructors follow optional-param pattern; backward-compatible.
- BootstrapResult is non-frozen dataclass (bootstrap/_types.py:93); safe to extend.
- Existing precedent: RetrospectiveHook receives LinkedCancelSignal from bootstrap.
- No security surface: internal-only, read-only access, single-threaded event loop.
- No failure mode risk: unlinked CancelSlot returns False (same as today).

### TDD Dependency Fix

- Added depends_on #1002 to #1001.
- WARNING: #1002 has depends_on [1001, 870] creating circular dep. Architect reviewing #1002 must remove depends_on 1001.

### Changes Made

- Refined AC1, AC3, AC4, AC6
- Added depends_on: 1002 (TDD compliance)
