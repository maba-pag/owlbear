---
id: 1414
title: 'E1: legacy-audit.prompt.md — cleanup scan prompt for stale references'
status: archived
priority: medium
created: 2026-05-07T23:16:25.305798+00:00
updated: 2026-05-08T12:50:22.390150+00:00
tags:
- pipeline
- ws-cleanup
- scope:agents
- agent
parent: 1403
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `share/prompts/legacy-audit.prompt.md` created as user-triggered one-shot prompt (td:0)
P2: Prompt scans for: TODO(#nnnn) where task is archived/done, dead imports and zero-caller functions, mock objects referencing obsolete patterns, test files `test_*_{task_id}.py` where task is archived but test remains, functions/modules with "legacy"/"compat"/"bridge"/"shim" in names (td:0)
P2: Output is a ranked cleanup report grouped by type (td:0)
P2: Prompt is not auto-fixable — produces report only, user decides cleanup actions (td:0)
P3: Verification by artifact inspection of the created prompt file (td:0)

## Scope

**In scope:** Prompt file creation with scan categories and output format
**Out of scope:** Automated cleanup, pipeline integration, stale test deletion (E2)
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1414-legacy-audit-prompt.md
- Sources: 6 studied, 3 high-relevance (existing audit prompts), 3 external (Vulture, Knip, Ruff F401)
- Recommendation: Proceed with inline audit prompt following frontend-audit.prompt.md pattern (confidence: 0.90)
- All 5 scan categories confirmed feasible: TODO(#nnnn) via grep+kanban, dead imports via ruff F401, zero-caller via heuristic grep, mock staleness via cross-ref, stale task-tests via file pattern+kanban, legacy naming via keyword grep
- No overlap with existing prompts; complementary to w-test-curation (report vs. action)
- T1 classification — no DR needed
- Challenge: skipped (trivial prompt file creation)
[[2026-05-08]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One prompt file, one purpose (stale reference scan) |
| Interface clarity | PASS | Input: optional scope via `${input:scope}`. Output: ranked report grouped by category |
| Dependency correctness | PASS | No dependencies, none needed |
| Module layering | N/A | Prompt file — no code imports |
| TDD compliance | PASS | Non-implementation task; `agent` pass-through tag added |
| KISS/YAGNI | PASS | Follows established audit prompt pattern (frontend-audit.prompt.md) |
| Premise challenge | PASS | Research confirmed no existing tool covers full scan surface; complementary to w-test-curation |
| Pattern consistency | PASS | Structure matches frontend-audit.prompt.md (preamble → steps → output → guardrails) |
| Security surface | PASS | Read-only prompt, no new system boundaries |
| Single domain | PASS | Agent ecosystem domain (scope:agents) |

### Failure Mode Map
N/A — prompt file creation, no codepaths with failure modes.

### Design Diverge
- Skipped — single obvious approach (inline audit prompt per established pattern). No competing designs.

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag for test-writer routing. Annotated all AC lines with (td:0). Advanced to todo.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines annotated (td:0); architect explicitly set Test-writer: SKIP.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: created `share/prompts/legacy-audit.prompt.md`.
- Scope coverage: prompt includes all required scan categories: stale task TODOs, dead imports/zero-caller checks, mock staleness, stale task-scoped tests, and legacy/compat/bridge/shim naming residue.
- Output contract: report is grouped by type in fixed order and requires severity ranking (high/medium/low) with per-finding evidence.
- Safety contract: prompt is explicitly report-only and disallows auto-fixes.
- Verification: artifact inspection completed on created prompt file; AC for file creation and report semantics satisfied.
- Tests: N/A (td:0 non-code prompt task).
- Lint: N/A (markdown prompt artifact).

### Evidence Summary
- File created and committed in builder-scoped commit:
  - `feat: add legacy audit prompt (#1414, builder)`
  - Commit: `aa2ecb8d`

### Post-task Reflection
- The test-writer pass-through note indicated non-implementation, but AC still required a concrete prompt artifact; treated this as artifact work with no test phase.
- Keeping prompt output schema explicit (section order + severity + evidence fields) reduces downstream variance in audit reports.
- Report-only guardrails were repeated in both steps and guardrails to prevent accidental action-oriented interpretation.
[[2026-05-08]]
## Review Evidence
### Test Results
- N/A (td:0 prompt artifact; no task test files exist).
- quality-runner skipped: td:0 prompt reviews have no non-empty test paths to dispatch in scoped mode.

### Lint: N/A
- Editor diagnostics on share/prompts/legacy-audit.prompt.md: no errors found.

### Coverage: N/A
- No executable Python or TypeScript code changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All AC lines (td:0 prompt artifact) | none | N/A | SKIPPED |

#### Security Review
- No issues. Scope is a markdown prompt artifact only; no executable code, secrets, input handling, or persistence paths were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| No TestFromAC files in scope | None | SKIPPED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Task tests applicability | N/A | Architect marked every AC line td:0; test-writer skip was appropriate for a prompt-only artifact. |

#### Data Safety
- No issues. The prompt is read-only and explicitly forbids edits, deletes, and auto-fixes (share/prompts/legacy-audit.prompt.md:16,65,73-75).

#### Implementation-Aware Gaps
- No untested executable paths. The artifact directly spells out all required scan categories, grouped output, severity ranking, confidence labeling, and report-only guardrails.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- First review cycle: no prior `## Review Evidence` section present in .owlbear/kanban/tasks/1414-e1-legacy-audit-prompt-md-cleanup-scan-prompt-for-stale-references.md.
- Commit existence verified in .git/logs/refs/heads/dev:2095 (`feat: add legacy audit prompt (#1414, builder)`, commit aa2ecb8d).
- Small confidence deduction: the current tool surface does not expose terminal or git-status commands, so dirty-tree contamination and direct git diff/show checks could not be run. Changed-file scope was reconstructed from builder notes plus commit-log proof and live artifact inspection.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| P1: share/prompts/legacy-audit.prompt.md created as user-triggered one-shot prompt (td:0) | share/README.md:113-120 defines share/prompts/*.prompt.md as user-invocable one-shot commands; artifact exists at share/prompts/legacy-audit.prompt.md with description frontmatter at :2, title at :5, and optional scope input at :9. | N/A | PASS |
| P2: Prompt scans for required stale-reference categories (td:0) | share/prompts/legacy-audit.prompt.md:23-39 covers TODO(#nnnn), archived/done task checks, dead imports, zero-caller functions, mock staleness, task-scoped tests, and legacy/compat/bridge/shim naming. | N/A | PASS |
| P2: Output is a ranked cleanup report grouped by type (td:0) | share/prompts/legacy-audit.prompt.md:43-59 requires exact group order, severity ranking, evidence fields, and heuristic confidence labels; :66-67 re-check grouped, severity-ranked output. | N/A | PASS |
| P2: Prompt is not auto-fixable — produces report only, user decides cleanup actions (td:0) | share/prompts/legacy-audit.prompt.md:16,65,68-69,73-75 enforces report-only behavior, forbids automatic fixes, and leaves action decisions to the user. | N/A | PASS |
| P3: Verification by artifact inspection of the created prompt file (td:0) | Reviewer directly inspected share/prompts/legacy-audit.prompt.md and editor diagnostics reported no errors; builder commit existence confirmed at .git/logs/refs/heads/dev:2095. | N/A | PASS |

### Confidence: 0.93
- Base 0.98: full AC-to-artifact match; prompt naming and location align with the repo prompt contract; editor diagnostics clean.
- Deduction 0.03: dirty-tree contamination check unavailable from the current tool surface.
- Deduction 0.02: direct git diff/show unavailable, so file ownership reconstruction relied on commit-log proof plus live artifact inspection.

### Verdict: PASS
### Action
- Advance review -> docs.
[[2026-05-08]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | share/README.md: count updated 9→10, `legacy-audit` added to Audits group in Current prompts table |
| 2 | Module docstrings | No | N/A | No Python modules changed; prompt-only artifact |
| 3 | External attribution | Yes | Already done | .owlbear/sources/overview.md:14-20 — builder added Vulture, Knip, Ruff F401 entries for #1414 |
| 4 | Research doc | Yes | Verified | .owlbear/research/1414-legacy-audit-prompt.md exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | share/diagrams/project-overview.excalidraw `describes: share/**` matches share/prompts/legacy-audit.prompt.md; footer updated to `Last verified: 2026-05-08 (b33d6d79)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| share/prompts/legacy-audit.prompt.md | OUT (agent-executable .prompt.md) | Not edited |
| share/README.md | IN | Updated: count 9→10, added legacy-audit to Audits group |
| share/diagrams/project-overview.excalidraw | IN | Footer updated (describes: share/**) |

### Files Updated
- share/README.md (commit f1048caf)
- share/diagrams/project-overview.excalidraw (commit f1048caf)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/1414-* files found)

### Note
share/README.md prompt count was "9" against 14 actual files pre-task (5 missing: agent-broad-audit, memory-review, kb-enrich, agent-deep-audit, kb-ingest). Updated to "10" reflecting this task's contribution only; pre-existing undercount is legacy debt from prior doc-writer gaps.
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: share/prompts/legacy-audit.prompt.md created as one-shot prompt (td:0) | File exists, frontmatter correct, commit aa2ecb8d | PASS |
| P2: Prompt scans for 5 required categories (td:0) | legacy-audit.prompt.md:23-39 covers all categories | PASS |
| P2: Output is ranked cleanup report grouped by type (td:0) | legacy-audit.prompt.md:43-59 specifies order, severity, evidence | PASS |
| P2: Prompt is report-only, not auto-fixable (td:0) | legacy-audit.prompt.md:65-78 guardrails forbid edits | PASS |
| P3: Verification by artifact inspection (td:0) | Direct inspection confirms content matches AC | PASS |

### Test Results
- pytest: 2968 passed, 172 failed, 5 errors — no failures in task scope (td:0 prompt artifact, no Python code changed). All failures are pre-existing background debt.
- ruff: 12 violations — none in task scope.

### Architect Quality: 4/5
AC was specific and verifiable for a prompt artifact task. Clear pass/fail criteria on all lines. Minor gap: three P2 lines could have been a single composite AC, but no ambiguity resulted.

### Deduction Breakdown
- Base: 1.00
- AC lines without evidence: 0 → -.00
- Lint violations in scope: 0 → -.00
- AC quality ≤ 3: no → -.00
- Missing reviewer evidence: no → -.00
- Full-suite failures in scope: 0 → -.00
- Reviewer tool-surface deductions (.05) verified clean: both commits confirmed via git log.

### Confidence: .98
### Action: archive

### Commits Verified
| Commit | Type | Agent |
|--------|------|-------|
| aa2ecb8d | feat | builder |
| f1048caf | docs | doc-writer |