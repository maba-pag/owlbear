---
id: 1419
title: Document SAST coverage and run baseline CI scan
status: archived
priority: medium
created: 2026-05-07T23:29:18.911471+00:00
updated: 2026-05-08T19:04:34.987707+00:00
tags:
- scope:infra
- type:docs
parent: 1413
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Create `.owlbear/sast-coverage.md` documenting CI/SAST tooling: tool coverage matrix, suppression rationale, baseline evidence. Content source: `.owlbear/research/1419-sast-coverage.md` sections 3–5.
See `.owlbear/research/1413-ci-sast-baseline.md` gap G5 and follow-up item 6.

## Acceptance Criteria
P2: `.owlbear/sast-coverage.md` contains a tool coverage matrix listing Ruff S-rules, Gitleaks, DevSkim, and Trivy with category, scan scope, and determinism for each (td:0)
P2: Same document contains a table of all production `noqa` S-rule suppressions with rule code, affected file(s), count, and justification (td:0)
P3: Same document records MegaLinter baseline evidence: CI trigger configuration (workflow YAML triggers) and post-enablement activity (commits to `dev` after trigger addition confirm the workflow would fire); execution verification beyond local artifacts is out of scope (td:0)

## Research
- Research doc: .owlbear/research/1419-sast-coverage.md
- Sources: 6 studied (all local — configs, codebase, git history), 5 high-relevance
- Recommendation: T1 autonomous — documentation of existing state (confidence: 0.85)

### Key findings
- 4 security scanning tools active: Ruff S-rules, Gitleaks, DevSkim, Trivy
- 26 inline noqa S-rule suppressions in production code + 1 global (S101) — all justified
- S608 (SQL formatting) accounts for 15/26 — all use parameterized values with trusted table/column names
- MegaLinter baseline exists: 5+ runs triggered via push to origin/dev since trigger addition, 2 merged megalinter-fixes PRs confirm execution
- No follow-up tasks created — documentation is complete, baseline is established
[[2026-05-08]]


## Architecture Review (cycle 3)
**Verdict:** APPROVED → todo

**Context:** Returned from review cycle 2. P2 lines PASS. P3 FAIL — the document's baseline execution confirmation claims more than its cited evidence proves. The reviewer correctly identified that local reflog + workflow wiring proves configuration and commit chronology, not remote CI execution.

**AC Refinement:** P3 rewritten to require only locally verifiable evidence:
- CI trigger configuration from workflow YAML
- Post-enablement activity (commits to `dev` after trigger addition)
- Explicit scope note: execution verification beyond local artifacts is out of scope

**AC Assessment:**
| AC Line | Assessment | Action |
|---------|-----------|--------|
| P2: Tool coverage matrix | PASS (cycle 2 verified) | No change |
| P2: Suppression rationale table | PASS (cycle 2 verified) | No change |
| P3: MegaLinter baseline evidence | FAIL (cycle 2) — overclaimed | Refined: scoped to locally verifiable evidence |

**Builder guidance:**
- Only P3 needs a fix. P2 lines are stable — do not modify them.
- In `.owlbear/sast-coverage.md`, update the "Baseline execution confirmation" subsection:
  - Remove the final sentence "This confirms the baseline CI scan is active and recurring." — it overclaims.
  - Replace with: "This confirms the CI trigger configuration is committed and that pushes to `dev` have occurred post-enablement, meaning the workflow would fire on those events. Verification of actual GitHub Actions run outcomes requires GitHub UI or API access, which is outside the scope of this local evidence document."
- The three bullet points citing reflog commits and workflow wiring are fine — they prove configuration + post-enablement activity. Keep them.

**Architecture Notes:**
- All td:0 — Test-writer: SKIP
- Challenger: skipped (all td:0)
- No dependency changes
- Documentation-only task, no code interfaces
[[2026-05-08]]
Architecture review cycle 3. Refined P3 AC to scope evidence to locally verifiable artifacts only — removes the unachievable "confirmation that baseline runs have executed" bar. P2 lines stable from cycle 2. All td:0, test-writer SKIP. Builder guidance included for surgical P3 fix in `.owlbear/sast-coverage.md`.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- All AC lines annotated (td:0). Architecture Review explicitly marked: "All td:0 — Test-writer: SKIP".
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: Updated `.owlbear/sast-coverage.md` baseline evidence wording to match refined P3 scope (locally verifiable trigger wiring + post-enablement push activity, with explicit out-of-scope note for GitHub UI/API run-outcome verification).
- Files changed: `.owlbear/sast-coverage.md`
- Tests: N/A (td:0 docs task; no test paths)
- Lint: markdownlint clean via quality-runner scoped run (`violations: []`, `exit: 0`)
- Coverage: N/A (documentation-only change)
- Approach: Surgical P3-only edit per Architecture Review cycle 3 guidance, then resolved markdownlint formatting issues (MD032/MD012) to keep gate clean.
- Commit: `c2135160` — `docs: scope megalinter baseline evidence claims (#1419, builder)`
[[2026-05-08]]
## Review Evidence
### Test Results
- Max AC depth is td:0 across all three AC lines; no executable tests or coverage are required for this documentation-only task.
- quality-runner was not dispatched because the deliverable is a markdown document with no task-scoped test artifacts; review used direct artifact verification instead.
- VS Code diagnostics for .owlbear/sast-coverage.md reported no errors.

### Lint Results
- Builder-scoped deliverable is .owlbear/sast-coverage.md only.
- No editor diagnostics were present in .owlbear/sast-coverage.md during review.

### Coverage
- Not applicable for td:0 documentation task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P2: .owlbear/sast-coverage.md contains a tool coverage matrix listing Ruff S-rules, Gitleaks, DevSkim, and Trivy with category, scan scope, and determinism for each | .owlbear/sast-coverage.md:6-13 contains all four tools with category, scope, and determinism. Repo config corroboration: .mega-linter.yml:9,25-27 enables PYTHON_RUFF, REPOSITORY_GITLEAKS, REPOSITORY_DEVSKIM, and REPOSITORY_TRIVY. | PASS |
| P2: Same document contains a table of all production noqa S-rule suppressions with rule code, affected file(s), count, and justification | .owlbear/sast-coverage.md:15-29 contains the suppression table; rows at :21-27 list S101, S105, S311, S506, S603, S607, and S608 with file/count/justification and :29 records total inline production suppressions: 26. Independent codebase scan found 26 inline noqa S-rule suppressions under serve/**/src/**. Global S101 ignore exists at pyproject.toml:59, and production assert call sites exist at serve/kanban/src/owlbear_kanban/engine.py:1909 and serve/knowledge/src/owlbear_knowledge/qdrant.py:191. | PASS |
| P3: Same document records MegaLinter baseline evidence: CI trigger configuration and post-enablement activity, with execution verification beyond local artifacts out of scope | .owlbear/sast-coverage.md:32-51 records CI trigger configuration and the refined out-of-scope sentence; trigger lines are corroborated by .github/workflows/megalinter.yml:5,8,11. The workflow wiring cited in the doc is corroborated by .github/workflows/megalinter.yml:59,68,74,154,156. The cited post-enablement commit chronology is present in local git logs at .git/logs/refs/heads/dev:2055 and :2125, and the doc now ends with the scoped statement at .owlbear/sast-coverage.md:51 rather than claiming actual GitHub run outcomes. | PASS |

### Test Integrity / Security / Process Checks
- No TestFromAC classes apply to this td:0 documentation task.
- No source code, dependency, or runtime interface changes were introduced by the reviewed deliverable.
- No prior Review Evidence section exists in the task file; this is the first review cycle for task 1419.

### Deductions
- 0.03 deducted because this tool surface could not execute git diff name-only or git status; changed-file scope was reconstructed from Builder Notes plus commit-presence evidence in .git/logs/HEAD and .git/logs/refs/heads/dev.
- 0.02 deducted because td:0 documentation review relied on direct artifact verification rather than quality-runner output.

### Verdict
- PASS
- Confidence: 0.95

### Action
- Advance to docs.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task created `.owlbear/sast-coverage.md` (a new doc, not a behavior/API/CLI change). README.md and SECURITY.md contain no references to SAST tooling or MegaLinter — no existing prose docs require update. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | All 6 research sources were local (configs, codebase, git history). No external patterns used. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1419-sast-coverage.md` exists and is linked from task body under `## Research`. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: serve/*/pyproject.toml, share/**, setup/**, .owlbear/**` — `.owlbear/sast-coverage.md` matches `.owlbear/**`. Footer updated to `Last verified: 2026-05-08 (e6feb8ac)`. Committed `e211a61c`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/sast-coverage.md` | OUT (new deliverable doc, not an IN-scope editable doc) | N/A — task created this file; no edits needed |
| `share/diagrams/project-overview.excalidraw` | IN | Footer updated (describes-match trigger) |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer updated to `Last verified: 2026-05-08 (e6feb8ac)`, commit `e211a61c`

### Child Tasks Created
- None

### Scratch Files Cleaned
- No `.owlbear/scratch/1419-*` files found.
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P2: Tool coverage matrix (Ruff S-rules, Gitleaks, DevSkim, Trivy with category, scope, determinism) | .owlbear/sast-coverage.md:6-13 — all four tools listed with required columns | PASS |
| P2: Suppression table (rule code, files, count, justification) | .owlbear/sast-coverage.md:15-29 — 7 rules, 26 inline + 1 global, all justified | PASS |
| P3: MegaLinter baseline evidence (CI triggers, post-enablement activity, out-of-scope note) | .owlbear/sast-coverage.md:32-51 — trigger config, reflog commits, explicit scope limitation | PASS |

### Test Results
- pytest: 2978 passed, 173 failed — no failures in task scope (docs-only, no Python changed)
- vitest: 1127 passed, 19 failed — no failures in task scope
- ruff: 29 violations — none in task deliverables (markdown file)
- eslint: 4 problems — none in task scope

### Architect Quality: 4/5
P3 required 3 architecture cycles to settle (overclaimed → refined to locally verifiable scope). Final AC is precise and realistic. P2 lines were clean from cycle 2.

### Deduction Breakdown
- No deductions applied. All AC lines have specific evidence. No lint violations in deliverables. AC quality > 3. Reviewer evidence present and detailed. No task-scope test failures.

### Confidence: 1.00
### Action: archive