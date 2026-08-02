---
id: 1353
title: Agent & Skill SNR Compression Tooling
status: archived
priority: medium
created: 2026-05-04T21:20:12.818826+00:00
updated: 2026-05-05T19:31:26.994057+00:00
tags:
- prompt
- refactor
- snr
parent:
depends_on:
- 1354
- 1355
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Summary

Two complementary audit prompts (`agent-broad-audit.prompt.md` + `agent-deep-audit.prompt.md`) to reduce signal-to-noise ratio across 80 instruction files in `share/`. Broad audit: ecosystem-level coherence with SNR indicator and ranked report. Deep-dive: extreme-depth per-agent/skill cluster audit with interactive compression proposals.

## Brief

`.owlbear/briefs/draft-skill-snr/brief.md`

## AC Summary

- AC1: Broad audit prompt replaces agent-audit with strengthened D6 + ranked report
- AC2: Deep-dive prompt with agent/skill cluster scope, section-by-section approval
- AC3: Shared 6-category noise taxonomy in both prompts
- AC4: Evaluation task (blocked, user-action, last) — run on reviewer agent
[[2026-05-04]]
## Planning
### Decomposition: Agent & Skill SNR Compression Tooling
- Tasks created: 3
- Dependency layers: 2
- Phase: 1

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1354 | P1-01: Write agent-broad-audit.prompt.md | needed | — | phase-1, scope:prompts, prompt, snr |
| #1355 | P1-02: Write agent-deep-audit.prompt.md | needed | — | phase-1, scope:prompts, prompt, snr |
| #1356 | P1-03: Evaluate SNR prompts on reviewer agent | important | #1354, #1355 | phase-1, scope:prompts, user-action, snr |

### Dependency Graph
```mermaid
graph LR
  1354[\"#1354 Broad Audit\"] --> 1356[\"#1356 Evaluation\"]
  1355[\"#1355 Deep-Dive\"] --> 1356
```

### Notes
- TDD pairing N/A: deliverables are `.prompt.md` files (no automated test harness). AC4 (#1356) serves as the verification gate.
- #1356 is blocked from the start per Brief constraint (user-action, last task).
- #1354 and #1355 are independent — taxonomy is fully specified in Brief, both inline it.
- Status skip to `todo` intentional: Brief provides full spec, no research phase needed.
[[2026-05-05]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `.prompt.md` files — no Python testable interface.
- Step 2a heuristic: AC1 targets `agent-broad-audit.prompt.md`, AC2 targets `agent-deep-audit.prompt.md`, AC3 verifies shared taxonomy. No `implement`, `function`, `class`, `src/`, or `.py` keywords in any AC line.
- Planning notes confirmed: "TDD pairing N/A: deliverables are `.prompt.md` files (no automated test harness)."
- Both files already exist and satisfy AC1–AC3 (created by tasks #1354 and #1355). AC4 is a blocked user-action task (#1356) — not in scope.
- Passing through to builder.
[[2026-05-05]]
## Builder Notes
- Non-implementation task — no code changes needed.
- AC scope is prompt-only (`.prompt.md`) and already satisfied by upstream tasks #1354 and #1355.
- Passing through to review.
[[2026-05-05]]
## Review Evidence
### Test Results
- `quality-runner` skipped. This is a td:0-style artifact review: the parent task scope is prompt files plus kanban state only, and the task body explicitly says there is no automated test harness (`.prompt.md` deliverables; AC4 is the verification gate).

### Lint Results
- Not applicable. No source or task-local test files were changed in this parent pass-through task.

### Coverage
- Not applicable. No runtime module or task-local executable test target exists for the parent task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | `share/prompts/agent-broad-audit.prompt.md` preserves D1-D7 at lines 49, 53, 72, 86, 98, 113, 143, and 173; keeps the finding loop at lines 20, 199, and 203; emits attention flags at line 159; flags universal files at line 160; and produces the ranked report at line 257. `file_search("share/prompts/*audit*.prompt.md")` returned `agent-broad-audit.prompt.md`, `agent-deep-audit.prompt.md`, `frontend-audit.prompt.md`, and `memory-audit.prompt.md`; `agent-audit.prompt.md` is absent. | PASS |
| AC2 | `share/prompts/agent-deep-audit.prompt.md` accepts `agent`/`skill` input at lines 9, 10, 56, 58, and 59; defines agent and skill cluster loading at lines 18, 19, 63, 76, 96, and 99; and requires a single structured proposal plus approval loop at lines 150, 154, 156, 158, 172, 182, 184, and 187. | PASS |
| AC3 | Both prompts inline the same six taxonomy labels: `share/prompts/agent-broad-audit.prompt.md` lines 149-154 and `share/prompts/agent-deep-audit.prompt.md` lines 33, 36, 39, 42, 45, and 48. The definitions are semantically aligned enough to satisfy the shared-taxonomy requirement. | PASS |
| AC4 | The brief requires the evaluation task to be run on reviewer, rated, and regression-checked at `.owlbear/briefs/draft-skill-snr/brief.md` lines 117, 119, 120, 121, and 122. The parent task says `AC4 (#1356) serves as the verification gate` at `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 59. Child task `#1356` is still `status: review` at `.owlbear/kanban/tasks/1356-p1-03-evaluate-snr-prompts-on-reviewer-agent.md` line 4 and still lists pending user-action evaluation steps at lines 27, 28, 29, and 38. | FAIL |

### Findings
1. Parent task `#1353` advanced to review before its own verification gate completed.
2. The prompt artifacts materially satisfy AC1-AC3 in the current repository state. The blocking defect is AC4 only.

### Deductions
- `-0.20` AC4 verification gate is incomplete.
- `-0.03` Upstream child task records for `#1354` and `#1355` were not present in active kanban task files, so artifact presence had to stand in for task-history inspection.

### Verdict
- FAIL. Confidence: `0.77`.
- Route: `backlog`.
- Reason: parent AC set includes an unfinished child evaluation gate (`#1356`), so the parent cannot pass review yet.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile the parent completion gate with child task `#1356`: either keep `#1353` out of review until the evaluation task is completed and recorded, or narrow `#1353` AC so AC4 is explicitly delegated out of parent scope. | `.owlbear/briefs/draft-skill-snr/brief.md`, `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md`, `.owlbear/kanban/tasks/1356-p1-03-evaluate-snr-prompts-on-reviewer-agent.md` | Brief AC4 lines 117, 119, 120, 121, 122; parent gate note line 59; child status line 4; child evaluation scope lines 27, 28, 29, 38 |
[[2026-05-05]]

## Architecture Review (re-review after reviewer rejection)
### AC Refinement
AC4 ("Evaluation task — run on reviewer agent") is **removed from parent scope**. It was decomposed into child task #1356 which already captures the full evaluation AC independently. The parent's completion condition is: both prompt files exist with shared taxonomy (AC1–AC3).

Rationale: Parent tasks that decompose into subtasks should not re-gate child deliverables. #1356 has its own pipeline flow (currently blocked on user-action AR). Including AC4 in #1353 creates an unresolvable circular gate — the parent can't complete before its child, but the child's `parent` field points back here.

**Revised AC Summary:**
- AC1: Broad audit prompt replaces agent-audit with strengthened D6 + ranked report (td:0)
- AC2: Deep-dive prompt with agent/skill cluster scope, section-by-section approval (td:0)
- AC3: Shared 6-category noise taxonomy in both prompts (td:0)
- ~~AC4~~: Delegated to #1356 (not in parent scope)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent tracks artifact creation (prompts); evaluation is separate child |
| Interface clarity | PASS | AC1-AC3 have clear pass/fail conditions verified by reviewer |
| Dependency correctness | PASS | depends_on [1354, 1355] correct — both archived/done |
| Module layering | N/A | No Python modules |
| TDD compliance | PASS | Non-impl (prompt tag); test-writer pass-through |
| KISS/YAGNI | PASS | Minimal scope after AC4 delegation |
| Premise challenge | PASS | Prompt files exist and are useful |
| Pattern consistency | PASS | Follows prompt file conventions |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Prompt domain only |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE (REFINE + immediate approve)
### Action Taken: Narrowed AC to AC1-AC3, delegating AC4 to child #1356. Advancing to todo.

[[2026-05-05]]
Architecture re-review after reviewer rejection. Root cause: AC4 referenced child #1356's completion as a parent gate — structurally unresolvable. Fix: narrowed parent AC to AC1-AC3 (artifact deliverables), delegated AC4 entirely to #1356. All td:0, test-writer SKIP. Reviewer already verified AC1-AC3 PASS on prior cycle.
[[2026-05-05]]
## Test-Writer Notes
- Retry cycle: reviewer FAILed on AC4 gate; architect re-reviewed and narrowed AC to AC1–AC3 only.
- All revised AC lines are (td:0): AC1 (td:0), AC2 (td:0), AC3 (td:0); AC4 delegated to child #1356.
- Architecture Review verdict: "Test-writer: SKIP" — depth-zero pass-through confirmed.
- No tests applicable — passing through to builder.
[[2026-05-05]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Revised AC scope is td:0 artifact-only (AC1-AC3), with AC4 delegated to child task #1356.
- Confirmed pass-through condition from `## Test-Writer Notes` and architecture re-review notes.
- Tests: not applicable (no executable interface changes).
- Lint: not applicable (no code changes).
- Coverage: not applicable (no touched runtime modules).
[[2026-05-05]]
## Review Evidence
### Test Results
- `quality-runner` skipped. The binding scope is the later td:0 architecture refinement in `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 115 and lines 120-122, which removes AC4 from the parent and leaves only artifact verification for AC1-AC3. No executable interface or task-local test target exists for this parent pass-through task.

### Lint Results
- Not applicable. No source files or task-local test files are owned by this parent pass-through task.

### Coverage
- Not applicable. No runtime module or task-local executable suite belongs to this parent task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | Binding scope: `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 120. `share/prompts/agent-broad-audit.prompt.md` exists, advertises broad SNR triage and ranked priorities at line 2, defines the audit dimensions at line 49, inlines the 6-category taxonomy at lines 147 and 149-154, defines the `SNR-FLAG` format at lines 163 and 167, and emits the ranked report at line 257. `share/prompts/agent-audit.prompt.md` is absent. Grep found no remaining `agent-audit` references under `share/agents/**`, `share/skills/**`, `share/instructions/**`, `share/prompts/**`, or `.github/**`; remaining hits are documentation-only in `share/WIRING.md`. | N/A (td:0) | PASS |
| AC2 | Binding scope: `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 121. `share/prompts/agent-deep-audit.prompt.md` exists, accepts `agent` or `skill` input at lines 9-10, defines both audit modes at lines 18-19, 63, and 76, requires dependency-cluster loading at line 96, defines a single structured proposal at line 150, and requires section-by-section approval plus a batch-approve escape hatch at lines 172, 182, and 184. | N/A (td:0) | PASS |
| AC3 | Binding scope: `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 122. The same six taxonomy labels appear in `share/prompts/agent-broad-audit.prompt.md` lines 149-154 and `share/prompts/agent-deep-audit.prompt.md` lines 33, 36, 39, 42, 45, and 48. | N/A (td:0) | PASS |

### Findings
- No blocking findings remain in the refined parent scope.
- The prior AC4 blocker is resolved by the later architecture refinement in `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 115 and lines 148 and 151, which delegate evaluation entirely to child task `#1356`.
- `share/WIRING.md` still contains stale `agent-audit` documentation references at lines 144, 181, 194, 195, 202, and 207. This is documentation drift only; no executable surfaces still reference the retired prompt name.
- Earlier parent-task text still mentions AC4 as a verification gate at `.owlbear/kanban/tasks/1353-agent-skill-snr-compression-tooling.md` line 59, but the later Architecture Review is the binding scope for this retry cycle.

### Deductions
- `-0.03` Stale top-of-body AC/planning text remains in the parent task file, so the review relies on the later Architecture Review refinement as the authoritative scope.
- `-0.02` `share/WIRING.md` still documents the retired prompt name, leaving minor documentation drift outside the task-owned artifact surface.

### Verdict
- PASS. Confidence: `0.95`.
- Action: advance to `docs`.

### Post-task Reflection
- Latest Architecture Review refinements are binding even when older task-header text remains stale; review should anchor to the newest explicit scope statement.
- For td:0 prompt-only parent tasks, direct artifact reads are the right evidence path; `quality-runner` adds no value and may fail on empty test scopes.
- Replacement checks should distinguish executable surfaces from documentation residue; stale docs alone are not an AC failure unless the task explicitly owns them.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are `share/prompts/*.prompt.md` (OUT scope). No IN-scope doc (`share/README.md`, root READMEs, setup guides) references `agent-audit` or the two new prompt files. Grep confirmed. |
| 2 | Module docstrings | No | N/A | No Python modules changed. |
| 3 | External attribution | No | N/A | No external patterns used; brief is fully internal. |
| 4 | Research doc | No | N/A | Research phase skipped (status jumped direct to todo per planning notes). No `.owlbear/research/{slug}.md` produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` describes `share/**` — matches the changed prompt files. Footer updated: `Last verified: 2026-05-05 (f7592274)`. Committed. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | Yes | N/A | `share/prompts/agent-audit.prompt.md` was deleted (OUT-scope file). Only IN-scope doc with `agent-audit` references is `.owlbear/research/gate4-tw-missing-tag-exemptions.md` (historical context doc, lines 28/53/68 reference `.github/prompts/agent-audit.prompt.md` — a descriptive reference to state at research time, not a stale instruction). `share/WIRING.md` has stale references (lines 144, 181, 194, 195, 202, 207) but is not in the IN-scope list — no deletion proposal generated. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `share/prompts/agent-broad-audit.prompt.md` | OUT (agent-executable) | N/A |
| `share/prompts/agent-deep-audit.prompt.md` | OUT (agent-executable) | N/A |
| `share/prompts/agent-audit.prompt.md` (deleted) | OUT (agent-executable) | N/A |
| `share/diagrams/project-overview.excalidraw` | IN (diagram describes-match) | Footer updated |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer timestamp/hash updated (commit 3177a8b9)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for task #1353)
[[2026-05-05]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Broad audit prompt replaces agent-audit | `share/prompts/agent-broad-audit.prompt.md` exists; `agent-audit.prompt.md` confirmed deleted; commit `df29ef9a` | PASS |
| AC2: Deep-dive prompt with cluster scope | `share/prompts/agent-deep-audit.prompt.md` exists; commit `5a12dddf` | PASS |
| AC3: Shared 6-category noise taxonomy | Both files contain identical 6 labels (lines 149-154 broad, lines 33-48 deep) | PASS |

### Test Results
- pytest: 4625 passed, 202 failed (pre-existing; prior run had 213 failures, all in unrelated modules: kanban engine, mcp-memory, accessor migration). No regressions from prompt-file changes.
- ruff: 29 violations, none in task-owned files (prompt/diagram only).

### Architect Quality: 4/5
Initial AC4 inclusion created a circular parent-child gate (reviewer correctly rejected). Architect re-review caught and fixed the structural issue by delegating AC4 to child #1356. Revised AC1-AC3 are clear, specific, and verifiable.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (all 3 verified)
- Lint in task scope: 0 (no code files)
- AC quality deduction: 0 (score 4, above threshold)
- Reviewer evidence: present, detailed, specific line citations
- Full-suite regressions in task scope: 0
- Minor: stale WIRING.md references to retired prompt name (doc drift, not AC failure): -0.01

### Confidence: 0.99
### Action: archive