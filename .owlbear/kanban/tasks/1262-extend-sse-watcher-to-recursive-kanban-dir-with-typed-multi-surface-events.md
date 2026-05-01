---
id: 1262
title: Extend SSE watcher to recursive kanban_dir with typed multi-surface 
  events
status: research
priority: someday
created: 2026-05-01T09:53:38.519349+00:00
updated: 2026-05-01T09:54:00.057299+00:00
tags:
- cockpit
- backend
parent: 1236
depends_on:
- 1234
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

After #1234 (tasks-only SSE) lands, refactor the watcher from `awatch(tasks_dir, recursive=False)` to `awatch(kanban_dir, recursive=True)` with path-based classification. Emit typed events: `tasks-changed`, `decisions-changed`, `activity-changed`. Add watch filter that accepts tasks/*.md (not .tmp-), decisions/pending/*.md, and activity.jsonl. See .owlbear/research/1236-extend-sse-decisions-activity.md