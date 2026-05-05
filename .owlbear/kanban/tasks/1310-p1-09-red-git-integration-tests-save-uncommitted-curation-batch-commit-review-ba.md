---
id: 1310
title: 'P1-09+10: Git integration — batch commit with scoped staging fix'
status: in-progress
priority: needed
created: 2026-05-04T01:32:27.314281+00:00
updated: 2026-05-05T21:44:12.080727+00:00
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
[[2026-05-05]]
## Builder Notes
- Implementation: added [serve/mcp-memory/src/owlbear_mcp_memory/git.py](serve/mcp-memory/src/owlbear_mcp_memory/git.py) with `commit_batch(memory_dir, *, session_type)` plus small internal helpers (`_git`, `_state_from_file`).
- Behavior: stages only non-pending memory markdown files, creates a single batch commit when staged diff exists, returns `\"\"` when nothing is staged, and uses exact commit messages:
  - `chore: memory curation batch (mcp-memory, curator)`
  - `chore: memory review batch (mcp-memory, reviewer)`
- Tests: 10 `TestFromAC_*` passed in [tests/test_memory_git_integration_1310.py](tests/test_memory_git_integration_1310.py).
- Coverage: 100% on target module `owlbear_mcp_memory.git` (quality-runner scoped report).
- ruff: clean for changed source + task test file.
- Module-level durable test file: none present for this module (`tests/test_memory_git*.py` only contains task-scoped file).
- Commit: `f260e033493e0e81cc1d28c19cfd06b170715d67` (`feat: implement memory git batch commit (#1310, builder)`).

### Reflection
- Kept change surgical to one new source file to avoid touching existing tool handlers.
- Used defensive parsing for malformed frontmatter while keeping staging logic simple and deterministic.
- Quality gate required small lint/coverage polish (`PLR2004`, trailing newline, defensive branch coverage).

[[2026-05-05]]
## Builder Notes
- Verified existing implementation for task scope in serve/mcp-memory/src/owlbear_mcp_memory/git.py; no additional code changes were required in this pass.
- Quality-runner scoped verification:
  - Tests: 10 passed, 0 failed in tests/test_memory_git_integration_1310.py
  - Lint: clean for serve/mcp-memory/src/owlbear_mcp_memory/git.py and tests/test_memory_git_integration_1310.py
  - Coverage: 100% for owlbear_mcp_memory.git (overall run reported 39% due to scoped module target)
- Git evidence:
  - Builder commit exists: f260e033 (`feat: implement memory git batch commit (#1310, builder)`)
  - Test-writer commit exists: cc347390 (`test: add failing tests for memory git batch integration (#1310, test-writer)`)
  - Relevant files are clean in working tree.
- Evidence summary:
  - AC behavior remains satisfied: no commit on save-only, single batch commit semantics for curation/review, pending hard-delete exclusions, soft-delete inclusion, and exact commit message format.
[[2026-05-05]]
## Review Evidence
### Source Control
- First review cycle: no prior Review Evidence section in .owlbear/kanban/tasks/1310-p1-09-red-git-integration-tests-save-uncommitted-curation-batch-commit-review-ba.md.
- Commit presence confirmed via grep hits in .git/logs/HEAD:1953 for test-writer commit cc347390 and .git/logs/HEAD:1957 for builder commit f260e033.
- Direct commit diff and working-tree cleanliness checks were not available in this tool surface, so changed-file scope was reconstructed from live files and task notes. Small confidence deduction applied to immutability and dirty-tree proof.

### Test Results
- quality-runner scoped pass: 10 passed, 0 failed, 0 skipped in tests/test_memory_git_integration_1310.py.

### Lint Results
- Ruff clean for serve/mcp-memory/src/owlbear_mcp_memory/git.py and tests/test_memory_git_integration_1310.py.

### Coverage
- Scoped coverage: 100% on owlbear_mcp_memory.git.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Tests assert save_memory does NOT create a git commit (file exists uncommitted) | tests/test_memory_git_integration_1310.py:145 and :159 only prove commit count stays at 1. No assertion proves the file was written and left uncommitted after MemoryEngine.write. | test_save_does_not_commit | FAIL |
| Tests assert curation batch: multiple curate/delete operations produce single batch commit | tests/test_memory_git_integration_1310.py:170 proves multiple curated entries batch into one commit, and tests/test_memory_git_integration_1310.py:315 proves a deleted entry can trigger a commit, but no test exercises one curation batch containing both curated and deleted entries as the AC states. | test_multiple_curated_produce_single_commit; test_soft_deleted_entry_included_in_commit | FAIL |
| Tests assert review batch: multiple approve/curate/delete operations produce single batch commit | tests/test_memory_git_integration_1310.py:211 and :235 cover approved plus curated entries only. No review-batch test includes a deleted entry. | test_mixed_review_operations_produce_single_commit; test_review_batch_leaves_clean_working_tree | FAIL |
| Tests assert hard-deleted (pending) files never appear in git history | tests/test_memory_git_integration_1310.py:269 and :290 cover both hard-delete before commit and pending file left on disk. | test_hard_deleted_pending_absent_from_git_log; test_pending_file_on_disk_not_staged_by_commit_batch | PASS |
| Tests assert soft-deleted entries are included in batch commit | tests/test_memory_git_integration_1310.py:315, :331, and :333 prove deleted state is committed in the curation path. | test_soft_deleted_entry_included_in_commit | PASS |
| Tests assert batch commit message matches chore: memory {curation|review} batch (mcp-memory, {actor}) | tests/test_memory_git_integration_1310.py:352 and :368 assert exact subject equality for curation and review. | test_curation_batch_commit_message; test_review_batch_commit_message | PASS |
| All tests fail (RED state) | .owlbear/kanban/tasks/1310-p1-09-red-git-integration-tests-save-uncommitted-curation-batch-commit-review-ba.md:34 still requires RED, and :83 records all tests failing from missing module import. But the same task now records source implementation added at :98, while sibling GREEN task 1311 still owns implementation and file staging logic at .owlbear/kanban/tasks/1311-p1-10-green-git-integration-batch-commit-for-curation-runs-and-review-sessions.md:34 and :38. Current snapshot diverges from task authority. | none | FAIL |

### Critical Findings
1. Split-task contract violation: task 1310 still declares RED-phase authority and explicitly says GREEN task 1311 already exists for the implementation path, but builder work under 1310 added serve/mcp-memory/src/owlbear_mcp_memory/git.py. Evidence: task 1310 lines 34, 49, and 98 versus task 1311 lines 34 and 38. This task cannot PASS as written on the live snapshot.
2. Implementation defect: commit_batch stages selected memory files, then checks the repository-wide cached diff and performs an unscoped commit. Any unrelated pre-staged file in the repo would be swept into the memory batch commit. Evidence: serve/mcp-memory/src/owlbear_mcp_memory/git.py:57, :63, :73, and :74. No current test pre-stages a non-memory file before calling commit_batch.
3. Test quality is below gate. AC1, AC2, AC3, and AC7 are not proven by discriminating assertions even though the scoped suite is green. Evidence: tests/test_memory_git_integration_1310.py:145, :170, :211, :235, :315 and the AC table above.

### Deductions
- 0.30 split RED/GREEN task authority mismatch on the live snapshot
- 0.20 real implementation defect around unrelated staged files entering the batch commit
- 0.05 AC proof gaps in AC1, AC2, AC3, and AC7
- 0.04 lower-confidence immutability and dirty-tree evidence without direct git diff/status access

### Verdict
- FAIL
- Confidence: 0.41

### Action
- Rejected to backlog. This is not a clean builder-only retry. The architect needs to reconcile the RED and GREEN split first, then re-dispatch corrected proof and implementation work against the right task boundary.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Rewrite the task split so 1310 is a test-only RED task or move the implementation ownership and live acceptance criteria fully to 1311 before another review cycle | .owlbear/kanban/tasks/1310-p1-09-red-git-integration-tests-save-uncommitted-curation-batch-commit-review-ba.md; .owlbear/kanban/tasks/1311-p1-10-green-git-integration-batch-commit-for-curation-runs-and-review-sessions.md | 1310:34, 1310:49, 1310:98, 1311:34, 1311:38 |
| 2 | architect | Tighten the RED-proof contract so the suite explicitly covers file-exists-uncommitted, mixed curated plus deleted curation batches, and deleted-entry review batches, or narrow the AC text if those branches are not truly required | tests/test_memory_git_integration_1310.py; .owlbear/kanban/tasks/1310-p1-09-red-git-integration-tests-save-uncommitted-curation-batch-commit-review-ba.md | AC table rows 1, 2, 3, and 7 |
| 3 | architect | Re-dispatch GREEN implementation work with an explicit regression for unrelated staged files so memory batch commits cannot sweep non-memory repo changes into the commit | serve/mcp-memory/src/owlbear_mcp_memory/git.py; tests/test_memory_git_integration_1310.py or successor GREEN test file | git.py:57, git.py:63, git.py:73, git.py:74 |
[[2026-05-05]]

## Revised Acceptance Criteria (supersedes original AC above)

- [ ] `commit_batch` tracks which paths it staged; skips commit when no memory paths were staged (eliminates repo-wide `git diff --cached --quiet` gate); commits only tracked paths via `git commit -m <msg> -- <paths>` (td:2)
- [ ] Test: `save_memory` writes file to disk without git add; assert file exists AND shows untracked in `git status --porcelain` (td:1)
- [ ] Test: curation batch containing both curated AND soft-deleted entries → single commit (td:2)
- [ ] Test: review batch containing approved, curated, AND soft-deleted entries → single commit (td:2)
- [ ] Hard-deleted (pending) files never appear in git history (existing tests cover this) (td:2)
- [ ] Soft-deleted entries included in batch commit; test asserts committed file content contains `state: deleted` frontmatter — not just filename presence in history (td:1)
- [ ] Commit message matches `chore: memory {curation|review} batch (mcp-memory, {actor})` (existing tests cover this) (td:1)
- [ ] New regression test: pre-stage an unrelated file, call `commit_batch`, assert unrelated file remains staged but is NOT included in the memory batch commit (td:2)
- [ ] All 10 existing passing tests in tests/test_memory_git_integration_1310.py continue to pass (td:0)

## Architecture Review (Cycle 2)
### Context
Reviewer rejected cycle 1 with three findings: (1) RED/GREEN split violated — implementation added under RED task; (2) `commit_batch` sweeps pre-staged unrelated files into memory commit; (3) AC1/AC2/AC3 test discriminators insufficient. Task #1311 (GREEN) merged into this task since implementation already exists here.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Git batch commit behavior + its test coverage (merged scope) |
| Interface clarity | PASS | `commit_batch(memory_dir, *, session_type) -> str` (SHA or "") |
| Dependency correctness | PASS | #1307 done (archived); no other deps needed |
| Module layering | PASS | Leaf module `owlbear_mcp_memory.git`; no upward imports |
| TDD compliance | PASS | Existing tests + new failing tests for the scoped-staging fix |
| KISS/YAGNI | PASS | Single function, subprocess git, tracked-paths list replaces repo-wide gate |
| Premise challenge | PASS | No existing solution; wiring tasks downstream under #1301 |
| Pattern consistency | PASS | Matches kanban engine subprocess+git pattern |
| Security surface | PASS | No user input reaches git commands; memory_dir from config |
| Single domain | PASS | scope:mcp-memory only |

### Challenge Results
- Challenger: block (0.32 confidence)
- Architect response: PARTIALLY ACCEPTED — retained AC4/5/6 as explicit lines (contract erosion fixed), specified root-cause fix covers both diff-gate and commit scope, strengthened soft-delete discriminator. REBUTTED on "no production caller" — wiring is explicitly out of scope for this phase.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED (new tests for scoped-staging regression + discriminator upgrades to existing tests)

### Verdict: APPROVE (after REFINE)
### Action Taken: Merged #1311 scope into #1310. Rewrote AC to address all three reviewer findings. Challenger concerns incorporated. Advanced to todo.

[[2026-05-05]]
Architecture review cycle 2 complete. Merged #1311 (GREEN) into this task since implementation already exists here. Refined AC to address three reviewer findings: (1) scoped staging — tracked-paths replaces repo-wide git diff gate; (2) test discriminator gaps in AC1/2/3 strengthened; (3) soft-delete proof requires content assertion. Challenger partially accepted (retained explicit AC lines, specified root-cause fix). 9 AC lines, max td:2, test-writer proceeds.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_memory_git_integration_1310.py
- Retry cycle: 5 new tests added addressing all reviewer gaps
- Classes added: TestFromAC_SaveNoCommit_FilesystemProof, TestFromAC_CurationBatch_MixedTypes, TestFromAC_ReviewBatch_MixedTypes, TestFromAC_SoftDeletedContent, TestFromAC_ScopedStagingRegression
- Tests per category: happy 3, edge 1, boundary 0, regression 1
- Total new: 5 tests; 10 original pass, 4 new pass (impl already satisfies), 1 new FAIL
- Failing test: TestFromAC_ScopedStagingRegression::test_commit_batch_does_not_sweep_unrelated_staged_file (AC8 regression — current git.py uses `git commit -m msg` without `-- <paths>`, sweeping unrelated staged file into batch commit)
- ruff: clean

AC coverage (retry additions):
| Revised AC | Test(s) |
|---|---|
| Revised AC2 (td:1) file exists AND untracked | test_save_writes_file_as_untracked |
| Revised AC3 (td:2) curation batch curated+deleted | test_curation_batch_with_curated_and_deleted |
| Revised AC4 (td:2) review batch approved+curated+deleted | test_review_batch_with_approved_curated_and_deleted |
| Revised AC6 (td:1) soft-delete content assertion | test_soft_deleted_content_has_deleted_state_in_commit |
| Revised AC8 (td:2) unrelated staged file excluded | test_commit_batch_does_not_sweep_unrelated_staged_file — FAILS |
| Revised AC9 (td:0) existing 10 pass | all 10 pass |

Builder must implement scoped staging: track staged paths, commit via `git commit -m <msg> -- <paths>` so pre-staged unrelated files are never swept into the memory batch commit.