---
id: 1310
title: 'P1-09: RED — Git integration tests (save uncommitted, curation batch commit,
  review batch commit)'
status: in-progress
priority: needed
created: 2026-05-04T01:32:27.314281+00:00
updated: 2026-05-05T09:17:49.784992+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1307
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Tests assert save_memory does NOT create a git commit (file exists uncommitted) (td:1)
- [ ] Tests assert curation batch: multiple curate/delete operations produce single batch commit (td:2)
- [ ] Tests assert review batch: multiple approve/curate/delete operations produce single batch commit (td:2)
- [ ] Tests assert hard-deleted (pending) files never appear in git history (td:2)
- [ ] Tests assert soft-deleted entries are included in batch commit (td:1)
- [ ] Tests assert batch commit message matches `chore: memory {curation|review} batch (mcp-memory, {actor})` (td:1)
- [ ] All tests fail (RED state) (td:0)

## Scope

- In: git commit behavior per operation type, batch semantics
- Out: tool handler logic (done in #1307/#1309), consumer wiring
[[2026-05-05]]
## Research
- Research doc: .owlbear/research/memory-git-integration-tests.md
- Sources: 6 studied, 4 high-relevance (all internal)
- Recommendation: Single `commit_batch(memory_dir, *, session_type)` function in `owlbear_mcp_memory.git` module (confidence: .92)
- Key design: commit_batch stages only non-pending files (curated/approved/deleted); pending files never staged → hard-delete safety guaranteed
- Commit message format: `chore: memory {type} batch (mcp-memory, {actor})`
- Test infra: real git repos via subprocess in tmp_path; deferred import guarantees RED
- 7 tests map 1:1 to 7 AC lines
- No new follow-up tasks — #1311 (GREEN) already exists

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests git commit behavior only |
| Interface clarity | PASS | `commit_batch(memory_dir, *, session_type)` → str (SHA or "") |
| Dependency correctness | PASS | #1307 done (archived); uses MemoryEngine for setup which exists |
| Module layering | PASS | New leaf module `owlbear_mcp_memory.git`; no upward imports |
| TDD compliance | PASS | This IS the RED test phase |
| KISS/YAGNI | PASS | Single function, subprocess git, no abstractions |
| Premise challenge | PASS | No existing git-commit solution in mcp-memory |
| Pattern consistency | PASS | Matches kanban engine subprocess+git pattern (engine.py L315) and deferred-import RED pattern (test_recall_memory_1308.py) |
| Security surface | PASS | No user input reaches git commands; memory_dir from config |
| Single domain | PASS | scope:mcp-memory only |

### Challenge Results
- Challenger: reconsider (0.24 confidence)
- Architect response: REBUTTED — challenger confused pipeline stage (backlog review ≠ done verification). No test file expected yet. Accepted minor AC6 refinement: specified exact commit message format to eliminate ambiguity.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Tightened AC6 with exact commit message format. Annotated test depths. Advanced to todo.
[[2026-05-05]]
Architecture review complete. All 10 criteria PASS. Tightened AC6 to specify exact commit message format (`chore: memory {curation|review} batch (mcp-memory, {actor})`). Test depths annotated: max td:2, test-writer proceeds normally. Challenger rebutted (confused pipeline stage with done-verification). Design is sound — single function, subprocess git, follows existing kanban pattern.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_memory_git_integration_1310.py
- Classes: TestFromAC_SaveNoCommit, TestFromAC_CurationBatch, TestFromAC_ReviewBatch, TestFromAC_HardDeletedNeverInHistory, TestFromAC_SoftDeletedInBatch, TestFromAC_CommitMessageFormat
- Tests per category: happy 6, edge 2, boundary 2, error 0
- Total: 10 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_mcp_memory.git')
- ruff: clean

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 (td:1) save_memory no commit | test_save_does_not_commit |
| AC2 (td:2) curation batch single commit | test_multiple_curated_produce_single_commit, test_curation_batch_no_extra_commit_when_nothing_changed |
| AC3 (td:2) review batch single commit | test_mixed_review_operations_produce_single_commit, test_review_batch_leaves_clean_working_tree |
| AC4 (td:2) hard-deleted never in history | test_hard_deleted_pending_absent_from_git_log, test_pending_file_on_disk_not_staged_by_commit_batch |
| AC5 (td:1) soft-deleted in batch | test_soft_deleted_entry_included_in_commit |
| AC6 (td:1) commit message format | test_curation_batch_commit_message, test_review_batch_commit_message |
| AC7 (td:0) all fail | guaranteed by ImportError — no test written |