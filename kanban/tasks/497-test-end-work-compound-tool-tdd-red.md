---
id: 497
title: 'Test: end_work compound tool (TDD RED)'
status: todo
priority: needed
created: 2026-03-31T07:18:55.9553279+02:00
updated: 2026-03-31T07:19:14.881847+02:00
tags:
    - scope:mcp
    - ' type:test'
    - ' phase-2'
    - ' test'
depends_on:
    - 470
class: standard
---

## Acceptance Criteria

- [ ] Tests in packages/mcp-kanban/tests/test_server.py (extend existing test module)
- [ ] Test end_work with outcome=success: verify edit called with -a NOTE -t --status NEXT_STATUS --release --json
- [ ] Test end_work with outcome=success at done status: verify edit + archive sequence (two _run_kanban calls)
- [ ] Test end_work with outcome=fail: verify edit called with -a NOTE -t --release --json (no status change)
- [ ] Test end_work with outcome=block: verify edit called with -a NOTE -t --block REASON --release --json
- [ ] Test end_work with outcome=block without block_reason: verify error returned (validation)
- [ ] Test end_work with outcome=reject: verify edit called with -a NOTE -t --status move_to --release --json
- [ ] Test end_work with outcome=reject using default move_to=ideation
- [ ] Test optional claim parameter: when provided, passed to --claim; when absent, read from show --json
- [ ] Test AppContext.statuses populated from config --json at lifespan
- [ ] Test next-status derivation: statuses[current_index + 1]
- [ ] Test JSON response returned from final CLI call
- [ ] All tests follow existing mock patterns in test_server.py (_make_app_context, _make_mcp_ctx, _mock_proc)
- [ ] All tests FAIL in RED phase (test-writer writes tests before implementation)
