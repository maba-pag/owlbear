---
id: 1819
title: Triage kanban config path validation tests
status: research
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:23:21+02:00
tags:
  - scope:kanban-engine
  - security
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The symlink-escape refresh failure is classified as stale test, missing runtime defense, or fixture issue.
  - The nested archive subdirectory move failure is traced to current path-containment behavior.
  - Any security-sensitive path validation change has focused tests before implementation.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has two failures in `tests/test_kanban_config_path_validation.py`, covering refresh-time symlink escape rejection and moving to an archive configured as a nested subdirectory.

## Boundary
Treat this as security-sensitive. Do not relax path containment without explicit approval and focused proof.