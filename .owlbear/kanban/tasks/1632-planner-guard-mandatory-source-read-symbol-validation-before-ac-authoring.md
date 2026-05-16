---
id: 1632
title: 'Planner guard: mandatory source-read + symbol validation before AC authoring'
status: review
priority: important
created: 2026-05-16T08:36:17.257578+00:00
updated: 2026-05-16T12:11:16.206496+00:00
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
archival_reason:
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
