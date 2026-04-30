---
id: 1176
title: 'P3-02: Migrate support modules, cleanup compat layer, and live config'
status: in-progress
priority: nice-to-have
created: 2026-04-29T07:36:12.009209+00:00
updated: 2026-04-30T00:54:48.060522+00:00
tags:
- scope:kanban
- phase-3
- type:build
parent: 1155
depends_on:
- 1175
blocked: false
block_reason:
claimed_by: dim-stream
claimed_at: 2026-04-30T00:54:48.060522+00:00
archival_reason:
archival_refs: []
---

## Context

Parent: #1155 — config.yml schema grouping (nested sub-models)
Phase 3 of 3: Support Modules + Cleanup — implementation task
Depends on: #1175 (support module tests written first per TDD)

## Acceptance Criteria

- [ ] 8 corruption.py access sites use sub-model paths
- [ ] 9 storage.py access sites (non-save_config) use sub-model paths
- [ ] Remaining test fixtures across ~50 files updated to grouped config format
- [ ] Live .owlbear/kanban/config.yml migrated to grouped format
- [ ] terminal_status added to live config.yml
- [ ] Forwarding properties removed from BoardConfig (all consumers now use sub-model access)
- [ ] extra='allow' strategy documented (inline code comment or dedicated note)
- [ ] All tests pass

## Scope

- In: corruption.py, storage.py (non-save_config), remaining test fixtures, live config, BoardConfig compat removal, documentation
- Out: engine.py (done in Phase 2), models.py sub-model definitions (done in Phase 1), save_config (done in Phase 1)
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_support_module_migration_1176.py
- Classes:
  - TestFromAC_CorruptionSubmodelMigration (AC1)
  - TestFromAC_StorageSubmodelPaths (AC2 — regression guards, pass now)
  - TestFromAC_LiveConfigFlatKeyCleanup (AC4)
  - TestFromAC_ForwardingPropertiesRemoved (AC6)
- Tests per category: happy 2 (storage regression guards), error 4 (source inspection negative), boundary 4 (source inspection positive + behavioral split-config), edge 12 (live config flat keys + forwarding props)
- Total: 22 tests — 20 FAIL, 2 PASS (storage sub-model regression guards, already correct)
- ruff: clean

## AC Coverage Table

| AC | Description | Test count | Status |
|----|-------------|------------|--------|
| AC1 | 8 corruption.py access sites use sub-model paths | 8 | All FAIL ✓ |
| AC2 | 9 storage.py non-save_config sites use sub-model paths | 2 | PASS (regression guards — already correct) |
| AC4 | Live config.yml migrated to grouped format (no flat duplicates) | 9 | All FAIL ✓ |
| AC6 | Forwarding properties removed from BoardConfig | 3 | All FAIL ✓ |
| AC3 | Fixture updates (~50 files) | — | Covered by regression of full suite in AC "all tests pass" |
| AC5 | terminal_status in live config pipeline | — | Already present, regression guard omitted (would pass) |
| AC7 | extra='allow' documented | — | Non-testable (inline comment) |

## Key Behavioral Tests (AC1)

Split-config technique (model_construct bypasses validation):
- root.statuses=['root-status'] vs pipeline.statuses=['pipeline-status']
- Task with status='pipeline-status' is invalid per root but valid per pipeline
- detect_corruption should return None (valid) after migration → currently FAILS ✓
- attempt_repair mode9/mode3: priority should come from pipeline.priorities[0] → currently FAILS ✓

## Key Source Inspection Tests (AC1, AC4, AC6)

- corruption.py must contain 'pipeline.statuses' and 'pipeline.priorities' patterns
- corruption.py code (comments+strings stripped) must NOT contain 'config.statuses'/'config.priorities'
- Live config.yml YAML must not have 11 forbidden flat duplicate keys at root
- Loaded live config model_extra must be free of forbidden flat keys after cleanup