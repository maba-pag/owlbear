---
id: 1426
title: 'P1-05: Add sync-to-main TODO marker warning step'
status: archived
priority: medium
created: 2026-05-08T00:41:08.358257+00:00
updated: 2026-05-09T10:05:36.743434+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
- type:config
parent: 1421
depends_on:
- 1423
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Acceptance Criteria

Add a pre-sync warning step to the sync-to-main GitHub Actions workflow (`.github/workflows/sync-to-main.yml`):

1. Before syncing, grep all `serve/*/README.md`, `README.md`, `README-consumer.md` for `> **TODO:**` markers (td:0)
2. If markers found: print a summary (count + file list) as a workflow warning annotation (td:0)
3. Do NOT fail the workflow — warning only, not a hard gate (td:0)
4. Summary format: "⚠️ {n} unresolved TODO markers in {m} files: {list}" (td:0)

**In scope:** CI workflow step only.
**Out of scope:** Resolving the markers (doc-audit), marker format definition (#1423).

Brief: see parent #1421
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/sync-todo-marker-warning.md
- Sources: 4 studied, 2 high-relevance (GitHub Actions docs, existing workflow)
- Recommendation: single inline bash step using `grep -rn '> \*\*TODO:\*\*'` + `::warning::` annotation (confidence: 0.95)
- Tier: T1 — trivial CI config change, no architecture impact
- Implementation: ~15-line bash step after checkout, before sync. Uses `::warning title=Unresolved TODO markers::` format. Never fails workflow.
- Placement: after "Capture dev metadata" step, before "Validate selected paths"
- No follow-up tasks needed — #1426 is the implementation task itself
[[2026-05-09]]
## Architecture Review

**Verdict:** APPROVED — T1 CI config change, well-scoped AC, follows existing workflow patterns.

### AC Assessment

| AC Line | Assessment | Depth |
|---------|-----------|-------|
| 1. Grep target files for markers | Specific pattern + file list, verifiable | td:0 |
| 2. Print warning annotation | Clear output spec | td:0 |
| 3. Warning only, no failure | Constraint verifiable by inspection | td:0 |
| 4. Summary format | Exact format string | td:0 |

All AC lines td:0 → Test-writer: SKIP

### Architecture Notes

- **Pattern consistency:** Existing workflow uses inline bash steps throughout — this follows the same style.
- **Placement:** After "Capture dev metadata" (line ~134), before "Validate selected paths" (line ~142). Correct — files are checked out by that point.
- **Shell glob:** `serve/*/README.md` is shell-expanded in GHA `run:` — works correctly. Non-matching glob is safe with `2>/dev/null`.
- **Exit code:** grep returns 1 on no-match; research doc correctly notes `|| true` mitigation.
- **No security surface**, no Python code, no test surface.

### Dependency Check

- #1423 (marker format definition): archived/done ✅
- #1421 (parent brief): archived/done ✅

### Challenger

Skipped — all AC lines td:0 per Step 2.1/2.5 rule.

### Tag Added

- `type:config` — enables test-writer pass-through.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- All AC lines annotated `td:0`; architect explicitly flagged SKIP.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Implementation: Added pre-sync workflow step in .github/workflows/sync-to-main.yml to scan README files for `> **TODO:**` markers and emit a warning annotation.
- Files changed: .github/workflows/sync-to-main.yml
- Tests: Not applicable (all AC lines are td:0; config-only workflow change)
- Coverage: N/A (no Python/TS runtime code changed)
- ruff/eslint: N/A (workflow YAML only)
- Approach: Inserted the warning step immediately after "Capture dev metadata" and before path validation to satisfy pre-sync placement while ensuring non-blocking behavior.
- Evidence:
  - Pattern insertion verified with ripgrep matches at workflow step and warning annotation lines.
  - YAML parse validation passed via `uv run python` + `yaml.safe_load`.
  - Summary format implemented as: "⚠️ {n} unresolved TODO markers in {m} files: {list}".
  - Workflow behavior remains warning-only; no failure path introduced for marker presence.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner: skipped
- Reason: every AC line is td:0 and the task scope is a single GitHub Actions YAML step; there are no task-local tests, runtime modules, or coverage surfaces to execute.

### Lint: N/A
- No workflow-file diagnostics were reported for .github/workflows/sync-to-main.yml by editor error checking.

### Coverage: N/A
- No Python or frontend runtime code changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. Grep target files for markers | None (td:0) | N/A | SKIP |
| 2. Print warning annotation summary | None (td:0) | N/A | SKIP |
| 3. Warning only; do not fail workflow | None (td:0) | N/A | SKIP |
| 4. Exact summary format | None (td:0) | N/A | SKIP |

#### Security Review
- No issues. The step reads fixed repository-local README paths and emits a GitHub Actions warning annotation only at .github/workflows/sync-to-main.yml:143-151. No secrets, user-controlled inputs, or external command interpolation were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| None (test-writer SKIP for td:0 task) | No task test files in scope | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Task test surface | N/A | td:0 workflow-only task; no tests were required by the AC or architecture review |

#### Data Safety
- No issues. The step computes counts and file names from grep output and does not persist data or mutate shared state.

#### Implementation-Aware Gaps
- No blocking gaps. The warning branch is explicit and self-contained at .github/workflows/sync-to-main.yml:145-151.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Placement is correct: the new step sits after "Capture dev metadata" (.github/workflows/sync-to-main.yml:133) and before "Validate selected paths exist on dev" (.github/workflows/sync-to-main.yml:154), satisfying the pre-sync requirement.
- Commit provenance is present in reflog history: .git/logs/refs/heads/dev:2232 and .git/logs/HEAD:2417 record builder commit 59fd2299107eff286d729c4705828034188da1c3 with subject "feat: add sync TODO marker warning step (#1426, builder)".
- I could not run git status from this tool surface, so dirty-tree contamination on .github/workflows/sync-to-main.yml is not independently proven. Small confidence deduction.
- Current workspace search found no live `> **TODO:**` markers in README.md, README-consumer.md, or serve/*/README.md, so the warning path is reviewed by code inspection rather than an exercised in-tree positive case. Small confidence deduction.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Before syncing, grep all target README files for `> **TODO:**` markers | .github/workflows/sync-to-main.yml:141-143 defines a dedicated pre-sync step and runs `grep -Hn '> \*\*TODO:\*\*' README.md README-consumer.md serve/*/README.md` | None (td:0) | PASS |
| 2. If markers found, print count + file list as a warning annotation | .github/workflows/sync-to-main.yml:145-151 gates on non-empty hits, computes `todo_count`, unique `todo_files`, `file_count`, `file_list`, and emits `::warning title=Unresolved TODO markers::...` | None (td:0) | PASS |
| 3. Do not fail the workflow | .github/workflows/sync-to-main.yml:143 uses `|| true` on grep no-match, the warning path is inside `if [[ -n "$todo_hits" ]]`, and there is no failure/exit path in .github/workflows/sync-to-main.yml:141-151 | None (td:0) | PASS |
| 4. Summary format is `⚠️ {n} unresolved TODO markers in {m} files: {list}` | .github/workflows/sync-to-main.yml:150 sets `summary="⚠️ ${todo_count} unresolved TODO markers in ${file_count} files: ${file_list}"` | None (td:0) | PASS |

### Confidence: 0.95
### Verdict: PASS
[[2026-05-09]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | grep of all IN-scope READMEs finds no references to sync-to-main or TODO markers |
| 2 | Module docstrings | No | N/A | No Python files modified |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` line 4472 already contains #1426 entry (GitHub Actions Workflow Commands) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/sync-todo-marker-warning.md` exists; linked in task body |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram `describes` glob covers `.github/workflows/**` |
| 6 | Explicit diagram creation | No | N/A | AC contains no diagram request |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.github/workflows/sync-to-main.yml` | OUT | N/A (CI config, not a doc file) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1426-*` scratch files existed)
[[2026-05-09]]
## Audit
### Regression Detection
- quality-runner mode full: 4871 Python passed / 572 failed, 1215 frontend passed / 9 failed
- All failures are pre-existing cockpit cache/API/error envelope and frontend archival/detail-tab tests — none relate to CI workflow YAML
- Task changed only `.github/workflows/sync-to-main.yml` — zero runtime code surface
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single file `.github/workflows/sync-to-main.yml`, matches `scope:shared` + `type:config` tags)
- purpose match: PASS (adds pre-sync TODO marker warning step exactly as specified in AC)
- extraneous scope: none (builder commit `59fd2299` shows 1 file, 13 insertions)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
- AC lines are precise: exact grep pattern, exact summary format string, explicit no-fail constraint, placement guidance
- All td:0 annotated correctly — no test surface needed for CI config
- Edge case (grep no-match exit code) addressed in research and implementation

### Commit Integrity
- upstream commit presence: PASS (`59fd2299 feat: add sync TODO marker warning step (#1426, builder)` — verified via `git show --stat`)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
- No deductions applied

### Confidence: 1.00
### Action: archive