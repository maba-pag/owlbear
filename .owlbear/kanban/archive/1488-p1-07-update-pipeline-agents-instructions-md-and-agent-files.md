---
id: 1488
title: 'P1-07: Update pipeline-agents.instructions.md and agent files'
status: archived
priority: needed
created: 2026-05-11T09:00:01.154177+00:00
updated: 2026-05-11T17:12:06.839907+00:00
tags:
- pipeline
- convention
- scope:instructions
- agent
parent: 1481
depends_on:
- 1483
- 1484
- 1485
- 1486
- 1487
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. `builder.agent.md` `<critical_rules>` quality-runner verification bullet references `Proof bundle: skip` (replaces "no executable proof") and `Proof bundle: existing` (replaces "Existing proof required: ...")
2. `builder.agent.md` `<pipeline_position>` "Pass-through" condition references `Proof bundle: skip` / `Proof bundle: existing` levels
3. `pipeline-agents.instructions.md`: verify no td:N terminology; no changes expected (file has no routing logic)
4. `reviewer.agent.md`: verify no td:N or pre-proof-bundle terminology; no changes expected (routing is in w-code-review via required_reading)
5. No td:N terminology remains in any `share/instructions/*.instructions.md` or `share/agents/*.agent.md` file (grep verification)

## Scope

- In: `share/agents/builder.agent.md` (primary), `share/instructions/pipeline-agents.instructions.md` and `share/agents/reviewer.agent.md` (verification only)
- Out: skill files (covered by earlier tasks)

## Builder Guidance

The builder.agent.md edits are in `<critical_rules>` and `<pipeline_position>` markdown sections — not Python code. The `Existing proof required:` field name is still valid within the `Proof bundle: existing` flow (w-tdd-green Step 0a references it), so the field name stays; only the summary phrasing in the agent persona needs updating to use proof-bundle vocabulary.

Proof bundle: skip
Brief: see parent #1481
[[2026-05-11]]
## Architecture Review

### Verdict: REFINE → APPROVE

AC rewritten from stale assumptions (td:N never existed in these files) to precise, verifiable conditions targeting the actual pre-proof-bundle phrasing in `builder.agent.md`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: proof-bundle terminology alignment in agent/instruction files |
| Interface clarity | PASS (after refine) | Original AC assumed td:N existed in target files — refined to target actual pre-proof-bundle phrasing |
| Dependency correctness | PASS | All deps (1483–1487) archived/done; parent 1481 archived |
| Module layering | N/A | Markdown files only |
| TDD compliance | N/A | Proof bundle: skip — no testable code |
| KISS/YAGNI | PASS | Minimal scope — two edits in one file plus grep verification |
| Premise challenge | PASS | builder.agent.md critical_rules and pipeline_position use pre-proof-bundle phrasing ("no executable proof", "Existing proof required:") that should align with proof-bundle vocabulary now defined in r-pipeline-protocol |
| Pattern consistency | PASS | Follows proof-bundle migration pattern from sibling tasks |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Agent ecosystem domain only |

### Proof-Bundle Validation

- Planner assignment: `Proof bundle: skip` — **confirmed**. Convention/docs changes only, no testable Python code.
- Test-writer: SKIP
- Challenger: skipped (bundle is `skip`)

### Codebase Evidence

- `pipeline-agents.instructions.md` (99 lines): No td:N, no proof-bundle, no routing logic. Verification-only AC line.
- `builder.agent.md`: `<critical_rules>` line ~61 references "no executable proof" and "Existing proof required: ..." — pre-proof-bundle phrasing. `<pipeline_position>` "Pass-through" row uses same phrasing. Both need proof-bundle vocabulary.
- `reviewer.agent.md`: No td:N or pre-proof-bundle phrasing. Routing handled by w-code-review via `<required_reading>`. No changes needed.
- Non-impl tag `agent` already present — pass-through tagging correct.
[[2026-05-11]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`, `Proof bundle: skip`) — no tests applicable.
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Non-implementation task (`Proof bundle: skip`) confirmed from task body and test-writer handoff.
- No code changes required.
- Passing through to review.
[[2026-05-11]]
## Review Evidence
### Test Results
- Proof bundle: skip. No task tests applicable.
- quality-runner scoped lint-only verification succeeded: 0 tests run; markdownlint clean for [share/agents/builder.agent.md](share/agents/builder.agent.md), [share/agents/reviewer.agent.md](share/agents/reviewer.agent.md), and [share/instructions/pipeline-agents.instructions.md](share/instructions/pipeline-agents.instructions.md).

### Scope Reconstruction
- No builder commit hash was recorded in the task body.
- Review scope reconstructed from the AC and task scope: [share/agents/builder.agent.md](share/agents/builder.agent.md), [share/agents/reviewer.agent.md](share/agents/reviewer.agent.md), [share/instructions/pipeline-agents.instructions.md](share/instructions/pipeline-agents.instructions.md).
- Task body contained no prior `## Review Evidence` section, so this is the first review cycle.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. `builder.agent.md` `<critical_rules>` uses proof-bundle wording | [share/agents/builder.agent.md](share/agents/builder.agent.md#L50) still says "Pass-through tasks with no executable proof" and refers to `Existing proof required: ...` instead of `Proof bundle: skip` / `Proof bundle: existing`. | FAIL |
| 2. `builder.agent.md` `<pipeline_position>` pass-through row uses proof-bundle wording | [share/agents/builder.agent.md](share/agents/builder.agent.md#L60) still says "no executable proof exists" / "named existing proof passed" instead of `Proof bundle: skip` / `Proof bundle: existing`. | FAIL |
| 3. `pipeline-agents.instructions.md` has no td:N terminology; no changes expected | Scoped grep for `td:` in `share/instructions/**` returned no matches. File inspection of [share/instructions/pipeline-agents.instructions.md](share/instructions/pipeline-agents.instructions.md) shows Channel B / section-mapping guidance only. | PASS |
| 4. `reviewer.agent.md` has no td:N or pre-proof-bundle terminology; no changes expected | Scoped grep for `no executable proof|Existing proof required` in [share/agents/reviewer.agent.md](share/agents/reviewer.agent.md) returned no matches; scoped grep for `td:` in `share/agents/**` returned no matches. | PASS |
| 5. No td:N terminology remains in any `share/instructions/*.instructions.md` or `share/agents/*.agent.md` file | Scoped grep for `td:` across `share/agents/**` and `share/instructions/**` returned no matches. | PASS |

### Blocking Findings
| # | Type | Evidence | Impact |
|---|---|---|---|
| 1 | Implementation miss | [share/agents/builder.agent.md](share/agents/builder.agent.md#L50) | Required `<critical_rules>` terminology update was not made. |
| 2 | Implementation miss | [share/agents/builder.agent.md](share/agents/builder.agent.md#L60) | Required `<pipeline_position>` terminology update was not made. |

### Deductions
- `-0.35` AC 1 unmet.
- `-0.25` AC 2 unmet.
- `-0.03` No builder commit hash in task body; scope reconstructed from task AC and live files.

### Verdict
- FAIL -> in-progress
- Confidence: `0.37`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update the `<critical_rules>` quality-runner verification bullet to use `Proof bundle: skip` and `Proof bundle: existing` terminology. | `share/agents/builder.agent.md` | [share/agents/builder.agent.md](share/agents/builder.agent.md#L50) |
| 2 | builder | Update the `<pipeline_position>` `Pass-through` row to reference `Proof bundle: skip` / `Proof bundle: existing` rather than the old phrasing. | `share/agents/builder.agent.md` | [share/agents/builder.agent.md](share/agents/builder.agent.md#L60) |

## Observations
- Non-blocking: [share/agents/reviewer.agent.md](share/agents/reviewer.agent.md) and [share/instructions/pipeline-agents.instructions.md](share/instructions/pipeline-agents.instructions.md) already satisfy the refined AC.
- Non-blocking: markdownlint is clean on all three scoped files.
[[2026-05-11]]
## Builder Notes
- Implementation: updated proof-bundle terminology in `share/agents/builder.agent.md` at `<critical_rules>` and `<pipeline_position>` pass-through condition.
- Files changed: `share/agents/builder.agent.md`
- Tests: 0 run (non-implementation docs/instructions scope)
- Coverage: N/A (no code execution paths touched)
- Lint: quality-runner scoped lint-only pass, markdownlint clean for:
  - `share/agents/builder.agent.md`
  - `share/agents/reviewer.agent.md`
  - `share/instructions/pipeline-agents.instructions.md`
- Verification evidence:
  - `td:` grep check across `share/agents/**` and `share/instructions/**`: no matches.
  - Reviewer-only verification target `share/agents/reviewer.agent.md`: no pre-proof-bundle phrasing found.
- Commit: `223a624dfc5b9d8f1c7bec3d14d939ea8df6f45b`
- Approach: surgical wording-only alignment to AC; no behavioral or structural changes.
[[2026-05-11]]
## Review Evidence
### Test Results
- Proof bundle: skip. No task tests or coverage are applicable for this markdown-only task.
- Independent verification via quality-runner: markdownlint clean on `share/agents/builder.agent.md`, `share/agents/reviewer.agent.md`, and `share/instructions/pipeline-agents.instructions.md`.
- Coverage: not applicable.

### Scope Reconstruction
- Current review cycle is anchored to the retry commit recorded by the builder: `223a624dfc5b9d8f1c7bec3d14d939ea8df6f45b`.
- Commit presence confirmed in [.git/logs/HEAD](.git/logs/HEAD#L2721) and [.git/logs/refs/heads/dev](.git/logs/refs/heads/dev#L2521).
- The available tool surface did not permit direct `git show` or `git status`, so changed-file ownership and dirty-tree cleanliness could not be independently proven beyond builder notes and live file inspection. Confidence reduced accordingly.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. `builder.agent.md` `<critical_rules>` quality-runner verification bullet references `Proof bundle: skip` and `Proof bundle: existing` | [share/agents/builder.agent.md](share/agents/builder.agent.md#L50) now uses `Proof bundle: skip` and `Proof bundle: existing` framing; `Existing proof required: ...` remains only as the named field inside the existing-proof flow, which matches the task's Builder Guidance. | PASS |
| 2. `builder.agent.md` `<pipeline_position>` pass-through condition references `Proof bundle: skip` / `Proof bundle: existing` levels | [share/agents/builder.agent.md](share/agents/builder.agent.md#L60) now states the pass-through condition in proof-bundle terms. | PASS |
| 3. `pipeline-agents.instructions.md`: verify no td:N terminology; no changes expected | No `td:` matches were found in [share/instructions/pipeline-agents.instructions.md](share/instructions/pipeline-agents.instructions.md) or in the broader `share/instructions/**` scan; the file content is Channel B and section-mapping guidance only. | PASS |
| 4. `reviewer.agent.md`: verify no td:N or pre-proof-bundle terminology; no changes expected | No `td:`, `no executable proof`, or `Existing proof required` matches were found in [share/agents/reviewer.agent.md](share/agents/reviewer.agent.md) after scoped inspection and grep. | PASS |
| 5. No td:N terminology remains in any `share/instructions/*.instructions.md` or `share/agents/*.agent.md` file | Repo-wide grep over `share/agents/**` and `share/instructions/**` returned no `td:` matches. | PASS |

### Blocking Findings
- None.

### Deductions
- `-0.02` Direct `git show` unavailable; changed-file scope beyond builder notes could not be independently diffed.
- `-0.02` Direct dirty-tree contamination check unavailable from the current tool surface.

### Verdict
- PASS.
- Confidence: `0.94`.
- Advance to docs.

## Observations
- This is the second review cycle; the prior review's two blockers in [share/agents/builder.agent.md](share/agents/builder.agent.md#L50) and [share/agents/builder.agent.md](share/agents/builder.agent.md#L60) are resolved in the live file.
- Builder-reported scope of one changed file is consistent with the live AC surface. The main residual limitation is the lack of direct git-diff and git-status visibility from this tool surface.
[[2026-05-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are OUT-scope agent-executables; no IN-scope prose docs reference them |
| 2 | Module docstrings | No | N/A | No `.py` files touched |
| 3 | External attribution | No | N/A | No external patterns used (markdown wording alignment only) |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | No IN-scope files; no describes-match possible |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/agents/builder.agent.md | OUT | N/A — agent-executable |
| share/agents/reviewer.agent.md | OUT | N/A — agent-executable (verification-only, no changes made) |
| share/instructions/pipeline-agents.instructions.md | OUT | N/A — agent-executable (verification-only, no changes made) |

No docs impact — all changed files are OUT-of-scope agent-executables. Stale agent-executable content drift, if any, routes to architect; none was flagged by reviewer.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1488-* scratch files existed)
[[2026-05-11]]
## Audit
### Regression Detection
- quality-runner mode full: 684 passed, 29 failed, 4 skipped. All 29 failures are pre-existing baseline (engine/cockpit/server test modules — `TypeError: NoneType not callable` in `engine.agent_view().move_task()`). Task #1488 changed only `share/agents/builder.agent.md` (markdown); cannot cause Python test regressions.
- Ruff: 271 pre-existing violations (E402, F811); none in changed file. Markdown lint clean on `builder.agent.md`.
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS — commit `223a624d` touches exactly 1 file (`share/agents/builder.agent.md`), 2 insertions / 2 deletions. Stays within agent ecosystem domain.
- Purpose match: PASS — diff replaces "no executable proof" / "named existing proof" phrasing with `Proof bundle: skip` / `Proof bundle: existing` in both `<critical_rules>` and `<pipeline_position>`, exactly as AC specifies.
- Extraneous scope: none
- AC5 grep verification: `grep -rn 'td:' share/agents/*.agent.md share/instructions/*.instructions.md` returns no matches.
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC was refined during architecture review (original assumed td:N existed in target files — corrected to target actual pre-proof-bundle phrasing). Refined AC was specific and verifiable with exact line references and terminology. First builder cycle failed because builder passed through without editing, not due to AC ambiguity. Builder Guidance section correctly noted the `Existing proof required:` field name should remain within the existing-proof flow.

### Commit Integrity
- Upstream commit presence: PASS — `223a624dfc5b9d8f1c7bec3d14d939ea8df6f45b` confirmed via `git log` and `git show --stat`. Message follows format: `chore: align builder proof-bundle wording (#1488, builder)`.
- Kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
- No deductions applied. All 4 pillars PASS. Pre-existing failures (29 test, 271 lint) are baseline — not caused by this markdown-only change.

### Confidence: 1.00
### Action: archive