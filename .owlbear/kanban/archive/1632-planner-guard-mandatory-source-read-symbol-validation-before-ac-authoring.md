---
id: 1632
title: 'Planner guard: mandatory source-read + symbol validation before AC authoring'
status: archived
priority: medium
created: 2026-05-16T08:36:17.257578+00:00
updated: 2026-05-16T13:08:10.668299+00:00
tags:
  - process
  - quality
  - pipeline
parent:
depends_on: []
ac:
  - 'w-task-decomposition SKILL.md contains a new step between Step 1a and Step 2,
    requiring the planner to: (a) identify target source files from the parent task/brief/caller
    context, (b) read those files, (c) extract and record referenced symbols (function
    signatures, enum/union values, component names, token names) before drafting ACs.
    Step 1a shortcut skip/continue lists updated to include this step. Verified by
    reading the skill file.'
  - 'The new step specifies a trigger condition: applies when the input plan, parent
    task, or brief references existing codebase modules or symbols that will appear
    in ACs. Explicitly states the step may be skipped for greenfield tasks with no
    existing code references. Verified by reading the skill file.'
  - The new step includes a verification sub-step requiring the planner to 
    cross-check each drafted AC against the recorded symbols — any AC 
    referencing a function return type, enum value, or component name must match
    the actual source. Verified by reading the skill file.
  - The skill includes at least one example (good_example or bad_example in 
    markdown format) illustrating the source-read guard — e.g., a bad_example 
    showing ACs with incorrect symbol references, or a good_example showing 
    symbol extraction before AC drafting. Verified by reading the skill file.
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Update the `w-task-decomposition` skill so the planner must read target source files and verify referenced function signatures, enums, tokens, and component names before writing ACs for refactor/extension tasks.

## Context

Audit #1631 found that planner-authored ACs for the PDS decomposition batch (#1590) contained factually incorrect references — e.g., `computeSignal` described as returning an object instead of a `CardSignal` string union, and state names listed as "green/yellow/red/gray/stale" instead of the actual `dr-pending | blocked | claimed | deps-unmet | ready | unknown`. Root cause: the planner did not read the actual source code before authoring ACs.

This task adds a mandatory source-read step to the decomposition workflow to prevent this class of error.

## Audit reference

Follow-up from AC-accuracy audit #1631.

[[2026-05-16T11:05:53+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One step addition to one skill file |
| Interface clarity | PASS | AC specifies step content, trigger, verification, and example requirements |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | N/A | Skill markdown file, no code layering |
| TDD compliance | PASS | Non-impl task with `quality` pass-through tag |
| KISS/YAGNI | PASS | Minimal addition addressing a verified failure mode (#1631 audit) |
| Premise challenge | PASS | No existing source-read guard in the skill; audit #1631 confirmed the gap |
| Pattern consistency | PASS | Follows existing skill step structure |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Pipeline/process domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Findings: (1) shortcut-path ambiguity — ACCEPTED, refined AC-1 to explicitly require Step 1a skip/continue list updates; (2) examples-section format — NOTED, builder follows skill conventions; (3) trigger taxonomy — PARTIALLY ACCEPTED, catch-all condition sufficient; (4) P1 gap — minor, addressed in AC tightening; (5) durability collision — REBUTTED, source accuracy and behavior-first AC are complementary
- Architect response: ACCEPTED critical finding, REFINED AC-1 and AC-2 to resolve shortcut-mode ambiguity

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC-1 to address shortcut-mode interaction (Step 1a skip/continue lists). Refined AC-2 for trigger clarity. Set proof_bundle=skip. Advanced backlog → todo.

[[2026-05-16T11:06:37+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — no tests applicable.
- Proof bundle: skip — no new test writing required.
- Task updates `share/skills/w-task-decomposition/SKILL.md` (a markdown skill file). No testable Python interfaces exist.
- Passing through to builder.

[[2026-05-16T14:11:16+02:00]]
## Builder Notes
- Implementation: updated [share/skills/w-task-decomposition/SKILL.md](share/skills/w-task-decomposition/SKILL.md) to add a mandatory source-read/symbol-capture guard before decomposition for existing-code references.
- AC mapping:
  - AC1: Added new `Step 1b — Source-Read & Symbol Capture Guard` between Step 1a and Step 2, with explicit requirements to identify target files, read them, and record symbol types (function signatures, enum/union values, component names, token names). Updated Step 1a shortcut skip list to include Step 1b.
  - AC2: Step 1b now includes trigger condition (references to existing modules/symbols) and explicit greenfield skip condition.
  - AC3: Step 1b includes explicit cross-check verification during AC drafting; symbol/type/value references must exactly match source.
  - AC4: Added `good_example` and `bad_example` sections demonstrating correct source-read guard usage vs incorrect memory-based AC authoring.
- Tests: 0 task-scoped tests executed (`proof_bundle=skip`, non-implementation quality/process task).
- Coverage: N/A (no executable code changes).
- Lint: commit hooks passed after whitespace correction (markdown/editorconfig gate).
- Evidence summary: final commit `abe2e5b43100d8ced3af4c31d74ab5a3e55ff6d6` contains only the target skill-file change.
- Fixes applied: inserted Step 1b guard, adjusted Step 1a shortcut skip list, added example block; no other functional/task files changed.

[[2026-05-16T14:31:26+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1632 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- AC evidence map:

| AC | Code Evidence | Status |
|---|---|---|
| 1 | share/skills/w-task-decomposition/SKILL.md:58 updates the Step 1a shortcut skip list to include Step 1b; share/skills/w-task-decomposition/SKILL.md:68-83 adds Step 1b between Step 1a and Step 2 with target-file identification, source-read, and symbol-capture requirements; share/skills/w-task-decomposition/SKILL.md:77-80 enumerates function signatures/return types, enum or union values, component names, and token names. | PASS |
| 2 | share/skills/w-task-decomposition/SKILL.md:70-72 applies the guard when existing modules or symbols will appear in AC text and explicitly allows skipping only for greenfield requests with no existing code references. | PASS |
| 3 | share/skills/w-task-decomposition/SKILL.md:81-82 requires cross-checking each drafted AC against recorded symbols and exact matching for function return types, enum values, and component/token names. | PASS |
| 4 | share/skills/w-task-decomposition/SKILL.md:86-95 includes both good_example and bad_example blocks illustrating the guard. | PASS |

- Proof sufficiency: proof_bundle=skip. This task changes a markdown skill file only; the AC requires file inspection, not executable behavior proof. Builder Notes include scoped lint status, and no task section requires existing executable proof.
- Builder evidence consistency: the Builder Notes' AC mapping matches the current file content. Commit reference abe2e5b43100d8ced3af4c31d74ab5a3e55ff6d6 is corroborated in .git/logs/HEAD:3338 and .git/logs/refs/heads/dev:3098.

## Observations
- I could not independently inspect the commit diff stat or path-scoped dirty-tree status through the current tool surface. Current on-disk content and recovered git-log evidence showed no contradiction with the builder's single-file-change summary, so this remained non-blocking for a proof_bundle=skip review.

[[2026-05-16T14:45:47+02:00]]
## Docs Gate

**Verdict: PASS — no docs impact**

### Convention Mapping
- Changed file: `share/skills/w-task-decomposition/SKILL.md`
- Mapped targets: `share/README.md`, `share/WIRING.md`

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | `share/README.md` has no entry for this skill by name; skill count (35) unchanged. `share/WIRING.md` lines 93 and 165 reference the skill by name only (wiring connections) — internal step structure is not documented at that level. No structural drift from adding Step 1b internally. Layer 1 grep: no removed symbols. Layer 2 editorial: WIRING and README remain coherent. |
| 2. External Attribution | N/A | No external sources used; task is a follow-up from internal audit #1631. |
| 3. Research Doc | N/A | No research file exists for this task. |
| 4. Deletion Detection | N/A | No source files deleted. |

### AC Content Verification
Read `share/skills/w-task-decomposition/SKILL.md` lines 50–95. All four ACs confirmed in file:
- Step 1a shortcut skip list includes \"Skip Step 1b\" ✓
- Step 1b present between Step 1a and Step 2 with trigger, file-read, and symbol-capture requirements ✓
- Greenfield skip condition explicit ✓
- Cross-check sub-step with exact-match requirement ✓
- good_example and bad_example blocks present ✓

### Scratch Cleanup
No `.owlbear/scratch/1632-*` files found.

### Files Modified
None (no docs changes required).

[[2026-05-16T15:08:10+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4646 passed, 236 failed, 14 skipped, lint clean, vitest clean
- All failures are pre-existing (test_cockpit_view.py, test_server.py, test_engine_accessor_migration.py, test_ideation_diagram.py) — none related to the changed markdown skill file. Confirmed by prior audit cycle (#1595) which also showed exit code 1 on the same test domains.
- regression verdict: PASS (no task-attributable regressions)

### Intent Verification
- scope alignment: PASS (single file changed: share/skills/w-task-decomposition/SKILL.md — pipeline/process domain matches tags process, quality, pipeline)
- purpose match: PASS (Step 1b source-read guard added between Step 1a and Step 2 with symbol capture, trigger condition, cross-check, and examples — directly addresses audit #1631 finding)
- extraneous scope: none (git diff stat: 1 file, 31 insertions, 1 deletion)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
All 4 ACs are specific, verifiable, and complete. Each AC precisely states what to verify and how (read the skill file). Challenger cycle was properly conducted with findings accepted/rebutted. Shortcut-mode interaction was refined based on challenger feedback. Clean implementation path with no builder improvisation needed.

### Commit Integrity
- upstream commit presence: PASS (abe2e5b4 confirmed via git log; single-file diff matches builder claim)
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
No deductions. Pre-existing test failures are not task-attributable (markdown-only change cannot cause Python test regressions). Lint clean. Reviewer evidence present and detailed. AC quality exemplary.

### Confidence: 1.00
### Action: archive
