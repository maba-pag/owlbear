---
id: 1217
title: Document orchestrator CLI status (possibly deprecated)
status: archived
priority: medium
created: 2026-04-30T15:29:15.278460+00:00
updated: 2026-04-30T17:20:22.834700+00:00
tags:
- audit-kanban
- docs
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Clarify whether serve/orchestrator/planner still uses kanban-md CLI.

## Files
- Documentation only (+ serve/orchestrator/ for inspection)

## Change
Verify whether serve/orchestrator/planner uses kanban-md CLI and whether it's deprecated/unused. Document the status.

## AC
- [ ] Status of orchestrator CLI usage documented in serve/orchestrator/README.md (td:0)
- [ ] If deprecated: add deprecation notice to serve/orchestrator/README.md and relevant module docstrings (td:0)
- [ ] If active: note current usage pattern in audit summary or README (td:0)

## Finding: 2.4

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: document status of CLI dependency |
| Interface clarity | PASS | Output is a doc update with clear location |
| Dependency correctness | PASS | No deps needed |
| Module layering | PASS | Docs only — no code changes |
| TDD compliance | PASS | Non-impl task; docs tag present |
| KISS/YAGNI | PASS | Minimal documentation scope |
| Premise challenge | PASS | Audit found real CLI usage — documenting it is valid |
| Pattern consistency | PASS | Follows existing README pattern in serve/orchestrator/ |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Orchestrator documentation domain only |

### Codebase Evidence
- `serve/orchestrator/src/owlbear/planner/board.py` — wraps `kanban-md list --json` via asyncio subprocess
- `serve/orchestrator/src/owlbear/cli.py` — defines `_KANBAN_BIN = Path("kanban/kanban-md")`
- `serve/orchestrator/README.md` — already documents the kanban binary path
- Orchestrator is ACTIVE (not deprecated): wired into workspace pyproject.toml, has live code paths

### Challenge Results
- Challenger: SKIPPED — all td:0

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC with specific output locations; all td:0 — docs-only task. Orchestrator actively uses kanban-md CLI (confirmed via codebase scan). Approved to todo.

[[2026-04-30]]
Architecture review complete. Orchestrator actively uses kanban-md CLI (board.py wraps `kanban-md list --json`, cli.py references the binary). Not deprecated. AC refined with specific output locations. All td:0 — docs-only, test-writer SKIP.
[[2026-04-30]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-04-30]]
## Builder Notes
- Implementation: updated serve/orchestrator/README.md with an explicit Kanban CLI status section.
- Status decision: orchestrator usage of kanban-md is active (not deprecated); documented current call paths and binary resolution.
- Tests: quality-runner scoped run passed (20 passed, 0 failed, 0 skipped) for tests/test_deny_non_doc_writes.py.
- Coverage: N/A for this docs-only change (no source module exercised in scoped run).
- ruff: clean on serve/orchestrator/src/.
- Evidence summary: board reader and CLI status path both invoke kanban-md list --json; README now reflects active usage pattern clearly.
- Fixes applied: added a dedicated "Kanban CLI Status" section under configuration to satisfy AC visibility requirements.
[[2026-04-30]]
## Review Evidence
### Scope
- Changed-file scope reconstructed from builder notes and direct inspection: [serve/orchestrator/README.md](serve/orchestrator/README.md#L36-L42)
- No builder commit hash was recorded in the task body, so diff-scoped review was not possible. No changed signatures were identified in reviewed scope.

### Test Results
- td:0 docs-only task. Reviewer followed the lint-only path.
- quality-runner tests: not run; report returned pytest exit `N/A` with 0 passed, 0 failed, 0 skipped.

### Lint
- quality-runner ruff: clean on [serve/orchestrator/src/](serve/orchestrator/src/)
- Ruff exit code: 0

### Coverage
- N/A for td:0 docs-only task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped correctly. All AC lines are td:0 and the task body records test-writer pass-through.

#### Security Review
- No issues in reviewed scope. This task documents existing behavior and adds no code, dependency, or boundary changes.

#### Test Integrity
- Not applicable. No task-scoped `TestFromAC_*` coverage exists for this td:0 task.

#### Test Quality
- Not applicable. td:0 docs-only task.

#### Data Safety
- No issues in reviewed scope. No persistence, concurrency, or input-handling changes were introduced.

#### Implementation-Aware Test Gap Analysis
- Not applicable to the verdict. AC is documentation-only; review depends on direct comparison between the README and live code paths.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section, no retry-loop evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Status of orchestrator CLI usage documented in serve/orchestrator/README.md (td:0) | [serve/orchestrator/README.md](serve/orchestrator/README.md#L36-L42) adds a dedicated `Kanban CLI Status` section documenting current state. | N/A (td:0) | PASS |
| If deprecated: add deprecation notice to serve/orchestrator/README.md and relevant module docstrings (td:0) | Active-path evidence makes the deprecated branch inapplicable: [serve/orchestrator/README.md](serve/orchestrator/README.md#L38), [serve/orchestrator/src/owlbear/planner/board.py](serve/orchestrator/src/owlbear/planner/board.py#L1), [serve/orchestrator/src/owlbear/cli.py](serve/orchestrator/src/owlbear/cli.py#L24-L25), [serve/orchestrator/pyproject.toml](serve/orchestrator/pyproject.toml#L13). | N/A (td:0) | PASS |
| If active: note current usage pattern in audit summary or README (td:0) | README usage notes at [serve/orchestrator/README.md](serve/orchestrator/README.md#L40-L42) match live call sites and wiring at [serve/orchestrator/src/owlbear/planner/board.py](serve/orchestrator/src/owlbear/planner/board.py#L43-L45), [serve/orchestrator/src/owlbear/cli.py](serve/orchestrator/src/owlbear/cli.py#L126-L127), and [serve/orchestrator/src/owlbear/orchestrator/loop.py](serve/orchestrator/src/owlbear/orchestrator/loop.py#L408). | N/A (td:0) | PASS |

### Informational
- Package README structure remains compliant with package-readme requirements: purpose, launch/usage, configuration, and dependencies are all present in [serve/orchestrator/README.md](serve/orchestrator/README.md#L1-L47).
- Accuracy check passed: the README's new status text is grounded in live orchestrator code, not stale audit prose.

### Deductions
- `-0.02` No builder commit hash in task body; changed-file scope had to be reconstructed from task scope and direct artifact inspection.
- Total deductions: `0.02`

### Verdict
- PASS -> docs
- Confidence: `0.96`

### Action
- Advanced to docs. No follow-up required.

### Post-task Reflection
- Docs-only td:0 tasks still need direct artifact-to-authority verification; green lint alone would be false confidence.
- Missing builder commit hashes reduce review traceability, even when the changed artifact is easy to identify.
- README accuracy was proven from live call sites and script wiring, not from upstream summaries.
[[2026-04-30]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified | serve/orchestrator/README.md was the changed artifact. Read full file — new `## Kanban CLI Status` section is accurate to live call sites (`board.py:43-45`, `cli.py:126-127`, `loop.py:408`). Root README `## Orchestrator CLI` section describes CLI commands, not internal binaries — no update needed. |
| 2 | Module docstrings | No | N/A | Docs-only task; no Python modules modified. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | Research doc | No | N/A | No research doc produced or referenced. |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index checked — no `describes` glob matches `serve/orchestrator/**`. Nearest match (`serve/mcp-*/src/**`) does not cover orchestrator package. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted by this task. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/orchestrator/README.md | IN | Verified — prose accurate to live code |
| .owlbear/doc-index.md | IN | Updated — regenerated to include new `## Kanban CLI Status` section |

### Files Updated
- `.owlbear/doc-index.md` — regenerated via `uv run doc-index` (e8263cc7); section `## Kanban CLI Status` now indexed under `serve/orchestrator/README.md`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1217-*` scratch files found)
[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Status of orchestrator CLI usage documented in serve/orchestrator/README.md (td:0) | README.md L36-42: dedicated "Kanban CLI Status" section. Spot-checked against live code (board.py:L1, cli.py:L24,L127). | PASS |
| If deprecated: add deprecation notice (td:0) | N/A branch. Active-path evidence (board.py, cli.py, loop.py all reference kanban-md) makes deprecation inapplicable. | PASS |
| If active: note current usage pattern in README (td:0) | README L40-42 documents read_board(), cli.status(), and binary resolution. Matches live call sites. | PASS |

### Test Results
- pytest: 3339 passed, 67 failed (all pre-existing, none in task scope), 4 skipped
- ruff: 4 violations (none in changed files)

### Architect Quality: 4/5
Clear conditional AC structure (deprecated vs active paths) with specific output location. Minor gap: no template for documentation content, but builder interpreted reasonably.

### Deduction Breakdown
- No missing AC evidence: 0
- Lint not in task scope: 0
- AC quality 4/5: 0
- Reviewer evidence present and detailed: 0
- Full-suite failures not in task scope: 0
- Total deductions: 0.00

### Confidence: 0.98
### Action: archive

### Commits Verified
- 0cb407bd docs: document orchestrator kanban CLI status (#1217, builder)
- e8263cc7 docs: update doc-index for orchestrator Kanban CLI Status section (#1217, doc-writer)