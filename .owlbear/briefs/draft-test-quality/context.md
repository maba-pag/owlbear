# Test Quality — Context

## Problem Statement

The TDD RED/GREEN pipeline generates task-scoped test files (one per kanban task, e.g. `test_bookmark_pipeline_553.py`). These tests verify the narrow implementation detail of a single change, not the business behavior of the module. Over time, hundreds accumulate.

**Three layers of harm:**

1. **Time waste.** Running hundreds of low-value tests takes multiple minutes per suite run, blocking agent dispatch cycles.
2. **Signal destruction.** When a module is improved, stale task-scoped tests break — not because anything is wrong, but because the tests were coupled to old implementation details. Agents see a wall of failures and can't distinguish "pre-existing noise" from "real regression I just caused."
3. **Behavioral corruption.** Agents develop a "probably not my fault" heuristic and learn to dismiss test failures as noise. This erodes the TDD feedback loop entirely — the test suite becomes worse than having no tests, because it creates false confidence while reducing actual bug detection.

**Root cause:** A multi-layered feedback-loop design problem:

1. **Convention drift.** The pipeline already has conventions (w-tdd-red, h-python-conventions, r-project-standards) prescribing module-level, contract-focused tests. But agents don't follow them consistently, and the user wasn't even aware they existed. The conventions are ineffective.
2. **Scoped execution.** RED/GREEN agents run only task-scoped tests during development. Full-suite runs happen only at the auditor stage (end of pipeline). Cross-task breakage is detected late.
3. **No test lifecycle.** Tests are born during task execution and never curated, promoted, pruned, or evaluated for lasting value. No human or automated process decides "this stays, this goes." Tests accumulate until the pile is unbearable and the human deletes hundreds manually.
4. **Test immutability during review.** Code review treats test-writer assertions as immutable, preventing reviewers from consolidating or pruning during the review stage.

The core insight: this is a **test lifecycle problem**, not just a test-quality-at-birth problem.

**Current state:** ~180 test files remain (hundreds already manually deleted). All tests are fully agent-authored. The human never writes or curates tests. Test files are named with task numbers, making it hard to identify which tests have lasting value.

## Project Type

Feature change to existing project (OwlBear pipeline tooling).

## Outcomes

1. **Green suite = trust.** When all tests pass, it's a reliable signal. When a test fails, agents investigate rather than dismiss. *Verified by:* absence of "pre-existing, skipping" patterns in agent behavior over time.
2. **Fast suite.** Full suite completes in under 60 seconds. No blocking dispatch cycles. *Verified by:* timed pytest runs.
3. **Automated lifecycle.** Tests are born, evaluated, and pruned without human intervention. Task-scoped tests are transient scaffolding; only module-level tests persist. *Verified by:* `tests/` contains module-level test files, not task-numbered files, without manual cleanup.
4. **Right-sized suite.** Test files map to modules, not tasks. The suite stays proportional to codebase size. *Verified by:* test file count stays bounded relative to module count.
5. **Coverage floor.** Test coverage stays above 90% (target 95%). The lifecycle can prune noisy tests but must not sacrifice actual behavioral coverage. *Verified by:* coverage reports on every suite run.

## Landscape Summary

**Current state:** 229 test files in `tests/`. ~190 (83%) are task-numbered, ~39 (17%) are module-level. Zero cleanup mechanisms exist.

**Convention gap:** `w-tdd-red` prescribes `tests/test_{module}.py` but in practice each task creates a new file with a task-number suffix. The convention exists on paper but the pipeline produces task-level files.

**Test immutability blocks curation:** Code review rules make `TestFromAC_*` classes immortal — any weakening or removal is an automatic FAIL. Reviewers cannot consolidate or remove even obviously redundant tests.

**Late detection:** Only the auditor runs the full suite. Builders and reviewers run only the task-scoped file. Cross-task breakage isn't visible until the final pipeline stage.

**Existing markers:** `api`, `slow`, `integration`, `e2e`. No lifecycle or permanence markers.

**What works:** `TestFromAC_*` naming for traceability. Scoped-run pattern (fast for builders, full for auditor). Coverage target 90%+ per-module.

## User Constraint

**Task-scoped tests are correct behavior for the test-writer.** The test-writer's job is to validate the AC — they should write task-bound tests. "Good" tests in the test-writer context means tests that verify AC scope, not broader module tests. The problem is not test *creation* quality — it's what happens *after* the task is done: no consolidation, pruning, promotion, or expiration. Solutions must not try to change test-writer behavior. The lifecycle fix belongs downstream: reviewer, auditor, or a new lifecycle agent.
