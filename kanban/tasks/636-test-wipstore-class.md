---
id: 636
title: Test WipStore class
status: archived
priority: needed
created: 2026-03-07T06:34:45.9821111+01:00
updated: 2026-03-07T18:08:28.9393725+01:00
started: 2026-03-07T06:55:50.331825+01:00
completed: 2026-03-07T18:08:28.9393725+01:00
tags:
    - scope:core
    - agent
    - test
depends_on:
    - 614
class: standard
---

TDD test task for WipStore.\n\nAC:\n- [ ] test_save_load_roundtrip: save(agent, task_id, summary) then load(agent, task_id) returns summary\n- [ ] test_load_empty_returns_none: load() on nonexistent file returns None\n- [ ] test_multiple_saves_returns_latest: save three entries, load returns the third summary\n- [ ] test_clear_deletes_file: save then clear, file no longer exists, load returns None\n- [ ] test_file_path_structure: saved file lives at {workspace}/.owlbear/wip/{agent}_{task_id}.jsonl\n- [ ] test_entry_model_fields: WipEntry has timestamp (str), agent (str), task_id (str), summary (str)\n- [ ] test_append_only_jsonl: save three entries, file has exactly 3 non-empty lines\n\nNotes:\n- Use tmp_path fixture for workspace\n- Follow ErrorJournal test patterns (test_error_journal.py)
