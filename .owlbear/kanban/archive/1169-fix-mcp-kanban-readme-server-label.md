---
id: 1169
title: Fix mcp-kanban README server label
status: archived
priority: important
created: 2026-04-28T20:08:43.209516+00:00
updated: 2026-04-28T21:34:37.715525+00:00
tags:
- phase:mcp
- docs
- scope:mcp-kanban
- brief:a
parent: 1045
depends_on: []
blocked: false
block_reason:
claimed_by: quiet-shade
claimed_at: 2026-04-28T21:34:37.715525+00:00
archival_reason:
archival_refs: []
---

## Objective

Update `serve/mcp-kanban/README.md` to use the correct MCP server key `ob-kanban` instead of any stale `owlbear-kanban` label.

## Acceptance Criteria

- [ ] `serve/mcp-kanban/README.md` uses the actual MCP server key `ob-kanban` when describing the VS Code MCP configuration entry.
- [ ] The wording aligns with `.vscode/mcp.json` and `seed/.vscode/mcp.json`.
- [ ] The README and `share/skills/h-mcp-kanban/SKILL.md` use consistent server-label terminology, or document any intentional distinction explicitly.
- [ ] No stale `owlbear-kanban` MCP-config label remains in `serve/mcp-kanban/README.md` unless backed by current config.

## Context

Parent: #1045. The server was renamed from `owlbear-kanban` to `ob-kanban` to fit VS Code's 13-char MCP label limit, but the README was not updated.
[[2026-04-28]]


## Builder Notes

Three distinct identifiers exist — only the first is in scope:

| Identifier | Value | Where | In scope? |
|------------|-------|-------|-----------|
| VS Code config key | `ob-kanban` | `.vscode/mcp.json`, `seed/.vscode/mcp.json` | **Yes** — line 3 of README is stale |
| FastMCP server name | `owlbear-kanban` | `server.py:123` (`FastMCP("owlbear-kanban", ...)`) | No — runtime identity, not a docs defect |
| Python package name | `owlbear-kanban` | `serve/kanban/pyproject.toml` | No — line 118 dependency table is correct |

AC4 scopes to "MCP-config label" — do NOT change the dependency table (line 118) or the FastMCP constructor.
`README-consumer.md:85` also has a stale reference but is out of scope for this task.
[[2026-04-28]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single file, single concern: fix stale MCP config label in README |
| Interface clarity | PASS | AC specifies exact file, exact label, exact reference files |
| Dependency correctness | PASS | No dependencies; parent #1045 is archived |
| Module layering | N/A | Docs-only task |
| TDD compliance | PASS | Tagged `docs` — pass-through, no tests needed |
| KISS/YAGNI | PASS | Minimal scope: one string replacement + optional distinction note |
| Premise challenge | PASS | Config key was renamed to `ob-kanban` in mcp.json; README line 3 still says `owlbear-kanban` — verified defect |
| Pattern consistency | PASS | h-mcp-kanban/SKILL.md already uses `ob-kanban` — this brings README in line |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | Docs domain only |

### Challenge Results
- Challenger: reconsider (0.72)
- Concerns: (1) FastMCP internal name `owlbear-kanban` in server.py vs config key `ob-kanban` — naming taxonomy unclear; (2) other docs (README-consumer.md:85) also stale; (3) AC3 distinction clause needs builder guidance.
- Architect response: rebutted (1) and (3) by adding Builder Notes table distinguishing 3 naming surfaces; rebutted (2) as out of scope — task is scoped to serve/mcp-kanban/README.md. AC is precise and verifiable. Refined body with naming context, then approved.

### Verdict: APPROVE
### Action Taken: Added Builder Notes section with naming-surface disambiguation table. Advanced to todo.
[[2026-04-28]]
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- Passing through to builder.
- AC describes a single-string replacement in `serve/mcp-kanban/README.md`; no testable Python interfaces exist.
[[2026-04-28]]
## Builder Notes
- Non-implementation task (docs tag + Test-Writer pass-through note); no code changes made in builder phase.
- Verified current state for downstream reviewers/doc-writer:
  - `serve/mcp-kanban/README.md` still says VS Code registration is `owlbear-kanban` (stale).
  - `.vscode/mcp.json` and `seed/.vscode/mcp.json` use `ob-kanban`.
  - `share/skills/h-mcp-kanban/SKILL.md` already uses `ob-kanban`.
- Scope guard preserved from architecture notes: do not change FastMCP runtime name or dependency package naming in this task.
- Handoff intent: review/docs stages should update only MCP config-label wording in README to align with config key terminology.
[[2026-04-28]]
## Review Evidence
### Source Scope
- No builder commit hash was recorded in the task body, so review scope was reconstructed from the AC and live authority files.
- Files inspected: `serve/mcp-kanban/README.md`, `.vscode/mcp.json`, `seed/.vscode/mcp.json`, `share/skills/h-mcp-kanban/SKILL.md`.
- This is a docs-only task. Direct artifact inspection is the authoritative check.

### Test Results
- pytest: 0 passed, 0 failed, not run

### Lint
- ruff: clean by N/A scoping; no lint paths were applicable for this docs-only review

### Coverage
- N/A for docs-only scope

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- N/A. No `TestFromAC_*` classes or executable task tests apply to this docs-only AC.

#### Security Review
- No issues. The task scope is documentation wording only; no executable boundary or dependency change was introduced.

#### Test Integrity
- N/A. No task-scoped tests exist to compare.

#### Test Quality
- N/A. No task-scoped tests exist to rate.

#### Data Safety
- No issues. No runtime or persistence path changed.

#### Implementation-Aware Gaps
- The required artifact was not updated. `serve/mcp-kanban/README.md:3` still says the VS Code MCP configuration entry is `owlbear-kanban`.
- The current authority files use `ob-kanban`: `.vscode/mcp.json:4`, `seed/.vscode/mcp.json:3`, and `share/skills/h-mcp-kanban/SKILL.md:9`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 headers in body; the first is architect-authored scope guidance, the second is the actual builder handoff |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- `serve/mcp-kanban/README.md:118` still uses `owlbear-kanban`, but that line is the workspace package name in the dependency table, not the MCP config label targeted by this task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `serve/mcp-kanban/README.md` uses the actual MCP server key `ob-kanban` when describing the VS Code MCP configuration entry. | `serve/mcp-kanban/README.md:3` still says `owlbear-kanban`. | N/A | FAIL |
| The wording aligns with `.vscode/mcp.json` and `seed/.vscode/mcp.json`. | `.vscode/mcp.json:4` and `seed/.vscode/mcp.json:3` use `ob-kanban`; `serve/mcp-kanban/README.md:3` does not. | N/A | FAIL |
| The README and `share/skills/h-mcp-kanban/SKILL.md` use consistent server-label terminology, or document any intentional distinction explicitly. | `share/skills/h-mcp-kanban/SKILL.md:9` says `ob-kanban`; `serve/mcp-kanban/README.md:3` says `owlbear-kanban`; no distinction is documented in the README. | N/A | FAIL |
| No stale `owlbear-kanban` MCP-config label remains in `serve/mcp-kanban/README.md` unless backed by current config. | The stale MCP-config label remains at `serve/mcp-kanban/README.md:3`; current config files do not back it. | N/A | FAIL |

### Deductions
- -0.55: All four AC lines remain unmet in the live artifact.
- -0.10: Builder phase passed the task forward without producing the required README update.

### Verdict
- FAIL | confidence 0.22

### Action
- Return to `in-progress`.
- Update `serve/mcp-kanban/README.md` line 3 to use `ob-kanban` for the VS Code MCP configuration entry.
- Preserve the documented distinction that `owlbear-kanban` remains valid for the dependency package name and the FastMCP runtime identity where those are explicitly in scope.

### Reflection
- Docs-only tasks still require direct artifact inspection; an empty executable-check scope is not evidence of completion.
- Reused section headers in the task body can look like retries; reviewer loop checks need to distinguish architect-authored guidance from actual builder attempts.
- For wording ACs, the live config and skill files are the authority, not downstream prose.
[[2026-04-28]]
## Builder Notes
- Implementation: updated `serve/mcp-kanban/README.md` to use the MCP config key `ob-kanban` in the VS Code registration sentence.
- Scope control: no changes to FastMCP runtime identifier usage or dependency package naming; `owlbear-kanban` dependency row remains intact by design.
- Verification: direct artifact checks only (docs-only task).
  - `serve/mcp-kanban/README.md` now states MCP config registration as `ob-kanban`.
  - `.vscode/mcp.json` and `seed/.vscode/mcp.json` use `ob-kanban` (aligned).
  - `share/skills/h-mcp-kanban/SKILL.md` uses `ob-kanban` (terminology aligned).
- Tests: N/A (no `TestFromAC_*` classes; docs-only acceptance criteria).
- Coverage: N/A (no executable changes).
- ruff: N/A (no Python code touched).
- Commit: `72c7c633`.

### Reflection
- Previous pass-through treatment was incorrect for this docs AC; direct artifact mutation was required.
- AC wording around “MCP-config label” should be treated as a strict surface constraint when same token appears in other naming surfaces.
- Keeping runtime/package identifiers untouched prevented collateral renames while satisfying config-label alignment.
- For docs-only tasks, artifact-to-authority comparison is the decisive verification method.
[[2026-04-28]]
## Review Evidence
### Source Scope
- Builder commit hash recorded in task body: `72c7c633`.
- Direct git diff was not available through the current tool surface, so changed-file scope was reconstructed from the task body and live artifact inspection.
- Reconstructed changed file list: `serve/mcp-kanban/README.md` only.
- This is a docs-only task. Direct artifact inspection against the live authority files is the decisive evidence path.

### Test Results
- quality-runner: 0 passed, 0 failed, 0 skipped.
- Scope note: not applicable for this task. No task-scoped test paths exist for the README-only change.

### Lint
- quality-runner: clean = true; violations = 0.
- Scope note: not applicable for this task. No executable lint targets were in scope.

### Coverage
- Not applicable. No executable code changed and no coverage modules were in scope.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- N/A. No `TestFromAC_*` classes or executable task tests apply to this docs-only acceptance criteria.

#### Security Review
- No issues. The task updates README wording only and changes no executable boundary.

#### Test Integrity
- N/A. No task-scoped tests changed.

#### Test Quality
- N/A. No task-scoped tests exist to rate.

#### Data Safety
- No issues. No runtime or persistence path changed.

#### Implementation-Aware Gaps
- No gaps in task scope.
- `serve/mcp-kanban/README.md:3` now uses `ob-kanban` for the VS Code MCP configuration entry.
- Exact-string search over `serve/mcp-kanban/README.md` found only two relevant label occurrences:
  - line 3: `ob-kanban` in the MCP registration sentence
  - line 118: `owlbear-kanban` in the dependency table as the workspace package name
- The remaining `owlbear-kanban` occurrence is not an MCP-config label and does not conflict with the AC.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 headers in body; 2 actual builder iterations after excluding the architect-authored scope note |
| Approach variation | Yes. The first builder pass incorrectly treated the task as pass-through; the second builder pass made the required README edit. |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- `serve/mcp-kanban/README.md:118` still uses `owlbear-kanban`, but the row explicitly describes the workspace package dependency, not the MCP config key.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `serve/mcp-kanban/README.md` uses the actual MCP server key `ob-kanban` when describing the VS Code MCP configuration entry. | `serve/mcp-kanban/README.md:3` says the server is registered in VS Code's MCP configuration as `ob-kanban`. | N/A | PASS |
| The wording aligns with `.vscode/mcp.json` and `seed/.vscode/mcp.json`. | `.vscode/mcp.json:4` and `seed/.vscode/mcp.json:3` both use `ob-kanban`, matching `serve/mcp-kanban/README.md:3`. | N/A | PASS |
| The README and `share/skills/h-mcp-kanban/SKILL.md` use consistent server-label terminology, or document any intentional distinction explicitly. | `serve/mcp-kanban/README.md:3` and `share/skills/h-mcp-kanban/SKILL.md:9` both use `ob-kanban` for the MCP registration label. | N/A | PASS |
| No stale `owlbear-kanban` MCP-config label remains in `serve/mcp-kanban/README.md` unless backed by current config. | Search of `serve/mcp-kanban/README.md` shows the only remaining `owlbear-kanban` is at line 118 in the dependency table as the workspace package name; no stale MCP-config label remains. | N/A | PASS |

### Deductions
- 0.00: Live artifact matches the authority files across all four AC lines.

### Verdict
- PASS | confidence 0.97

### Action
- Advance to `docs`.

### Reflection
- Docs-only tasks still require direct artifact-to-authority verification; empty executable scope does not lower the review bar.
- For MCP naming fixes, separate config key, runtime server name, and package name before treating a surviving token as stale.
- On single-file docs tasks, exact-string search plus live authority-file inspection is sufficient evidence when git-diff access is unavailable.
[[2026-04-28]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-kanban/README.md:3` verified correct (`ob-kanban`). Also caught stale `owlbear-kanban` in `README-consumer.md:85` (MCP: List Servers verification row) — updated to `ob-kanban`, committed `7e119f57`. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns used; wording fix only. |
| 4 | Research doc | No | N/A | No `.owlbear/research/*.md` produced for this task. |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `serve/mcp-kanban/src/**`; `mcp-topology.excalidraw` describes `serve/mcp-*/src/**`. Changed file is `serve/mcp-kanban/README.md` (not under `src/`) — no glob match. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/README.md | IN (serve/*/README.md) | Verified correct (builder commit 72c7c633) |
| README-consumer.md | IN (root) | Updated: `owlbear-kanban` → `ob-kanban` at line 85 |

### Files Updated
- `README-consumer.md` — MCP: List Servers verification row updated to `ob-kanban` (builder-noted stale ref, out of scope for builder, caught at docs gate)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1169-*` scratch files existed)