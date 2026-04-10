---
id: 637
title: Implement WipStore class in owlbear.memory.wip
status: archived
priority: needed
created: 2026-03-07T06:35:00.1496982+01:00
updated: 2026-03-07T18:08:29.4755777+01:00
started: 2026-03-07T07:41:16.6555692+01:00
completed: 2026-03-07T18:08:29.4755777+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 636
class: standard
---

Implement WipStore as a JsonlStore subclass under src/owlbear/memory/wip.py.\n\nAC:\n- [ ] WipEntry(BaseModel): timestamp (str, ISO-8601), agent (str), task_id (str), summary (str)\n- [ ] WipStore(JsonlStore[WipEntry]) with workspace-based constructor: WipStore(workspace: Path)\n- [ ] save(agent: str, task_id: str, summary: str) -> None: appends WipEntry with current UTC timestamp to per-task file at {workspace}/.owlbear/wip/{agent}_{task_id}.jsonl\n- [ ] load(agent: str, task_id: str) -> str | None: returns most recent entry summary, or None if file missing/empty\n- [ ] clear(agent: str, task_id: str) -> None: deletes the per-task JSONL file (Path.unlink(missing_ok=True))\n- [ ] Internal: _task_path(agent, task_id) -> Path computes the file path\n- [ ] Internal: each save/load/clear instantiates or reuses a JsonlStore for the specific task file\n- [ ] Module exports: WipEntry, WipStore via __all__\n- [ ] All 7 tests from #636 pass\n- [ ] ruff check clean\n\nArchitecture notes:\n- Follow ErrorJournal pattern (src/owlbear/memory/error_journal.py)\n- No rotation needed (files are short-lived, deleted on task completion)\n- WipStore constructor takes workspace Path, not individual file path. It manages multiple per-task files under .owlbear/wip/\n- This differs from ErrorJournal: ErrorJournal is one file, WipStore manages N files. Internally, create a JsonlStore per task_path on each operation (lightweight; no caching needed).
