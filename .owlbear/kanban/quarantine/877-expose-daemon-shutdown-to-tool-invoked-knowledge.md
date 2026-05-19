---
id: 877
title: Expose daemon shutdown to tool-invoked knowledge cancellation
status: archived
priority: nice-to-have
created: 2026-03-20T15:43:45.5123636+01:00
updated: 2026-03-25T06:12:44.6395657+01:00
started: 2026-03-25T06:12:44.6395657+01:00
completed: 2026-03-25T06:12:44.6395657+01:00
tags:
    - scope:core
    - type:build
depends_on:
    - 870
class: standard
---

**Source:** #870 cancellation-signal research. Agent turns currently have no shutdown-aware dependency surface, so tool calls cannot link per-operation cancellation with daemon shutdown. **AC:** 1. Add a read-only shutdown or cancel dependency at the agent or bootstrap boundary without importing daemon internals into memory modules. 2. Wire knowledge refresh, bookmark, or ingest tool entry points to compose per-operation cancellation with daemon shutdown during agent turns. 3. Keep non-daemon callers unchanged and add focused tests for shutdown-driven early exit in a tool-invoked path.

[[2026-03-25]] Wed 04:42

## Research

Doc: docs/research/tool-invoked-cancellation.md
Attribution: docs/sources/overview.md updated.

Key findings:

- CancelSlot pattern (10 LOC, satisfies CancelSignal) enables late-binding of daemon shutdown to toolset cancel signals
- Maps to .NET CancellationTokenSource/Token split: write-side in daemon, read-side in toolsets
- 3 toolsets need cancel passthrough: KnowledgeToolset, KnowledgeSourceToolset, BookmarkToolset
- BootstrapResult stores the slot; run_daemon wires it after creating shutdown_event
- Non-daemon callers unchanged (is_set returns False when unlinked)

Follow-up tasks created:

- #1001 Add CancelSlot and wire tool-invoked cancellation to daemon shutdown (ideation)
- #1002 RED tests for tool-invoked cancellation wiring (ideation)

[[2026-03-25]] Wed 06:12

## Architecture Review

**Verdict:** MERGE (delete as superseded)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: read-only shutdown/cancel dependency | Vague: does not name CancelSlot, cancellation.py, or set_source | Superseded by #1001 AC1 |
| AC2: wire tool entry points | Vague: does not name the 3 toolsets or methods | Superseded by #1001 AC2-AC4 |
| AC3: keep non-daemon unchanged + add tests | Bundles tests with impl (TDD violation) | Superseded by #1001 AC5 + #1002 |

### Architecture Notes

Research doc and CancelSlot design are sound:

- CancelSlot (~10 LOC) satisfies CancelSignal protocol via is_set(); set_source() for late binding
- Module layering clean: CancelSlot in memory/knowledge/cancellation.py (alongside existing protocol); toolsets receive via constructor DI; bootstrap wires
- No upward imports; non-daemon callers unchanged (is_set returns False when unlinked)
- BootstrapResult has no cancel field today; adding one is a clean extension
- _build_bookmark_toolset,_build_knowledge_toolset, _build_knowledge_source_toolset all construct toolsets without cancel; adding optional param is mechanical

# 877 served as a research vehicle. The researcher properly decomposed it into #1001 (impl) + #1002 (RED test) with refined AC. Approving #877 would duplicate #1001 scope

### Changes Made

- Fixed #1002 depends_on: #877 replaced with #870 (prerequisite, already archived)
- Deleted #877 (superseded by #1001 + #1002)

### Dependencies

- #870 (archived): prerequisite cancellation implementation (satisfied)
- #1001 (ideation): implementation task with refined AC (note: AC6 bundles focused tests; when it reaches backlog, architect should clarify as builder-discovered only since #1002 covers RED)
- #1002 (ideation): RED test task (when it reaches backlog, architect should add #1001 depends_on #1002 for TDD ordering)
