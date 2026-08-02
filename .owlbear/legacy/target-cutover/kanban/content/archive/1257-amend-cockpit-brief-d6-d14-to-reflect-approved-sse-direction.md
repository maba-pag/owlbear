---
id: 1257
title: Amend cockpit brief D6/D14 to reflect approved SSE direction
status: archived
priority: medium
created: 2026-05-01T05:33:27.534058+00:00
updated: 2026-05-01T12:53:37.356114+00:00
tags:
- docs
- cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Amend `.owlbear/briefs/draft-cockpit/decisions.md` D6 and D14 to reflect the approved T3 decision (Option A: SSE replaces polling).

## Context
- T3 DR approved: `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md` (Option A)
- D6 currently reads: "no SSE/WebSocket in v1" — must be updated to reflect SSE approval
- D14 currently reads: "Poll @ 3 s" under polling — must be updated to reflect SSE as primary with polling fallback
- Also update relevant sections in `.owlbear/briefs/draft-cockpit/brief.md` that reference polling as the only mechanism

## Acceptance Criteria
- [ ] D6 in decisions.md updated to reflect SSE approval, removing "no SSE/WebSocket in v1" (td:0)
- [ ] D14 polling references updated to note SSE as primary transport with polling as fallback (td:0)
- [ ] brief.md sections referencing polling-only updated for consistency (td:0)
- [ ] All changes reference the resolved DR as authority
[[2026-05-01]]
## Research

Amended cockpit brief D6/D14 to reflect approved T3 decision (Option A: SSE replaces polling).

**Changes made:**
- `decisions.md` D6: replaced "no SSE/WebSocket in v1" → SSE primary + polling @ 3s fallback; added DR attribution
- `decisions.md` D14: renamed "Polling" to "Change detection"; SSE as primary push transport with polling fallback
- `brief.md`: updated Phase 1 HTTP routes (added `GET /api/events` SSE endpoint), Phase 1 backend row, Phase 2 frontend row, Out of Scope entry, outcomes O3/O7, risks R3/R8, condensed D6 summary
- All amendments reference `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`

**No follow-up tasks needed** — implementation tasks #1234/#1235/#1236 already exist from the original DR approval.
[[2026-05-01]]

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: amend brief docs to reflect approved DR |
| Interface clarity | PASS | Clear targets (D6, D14, brief.md sections) and clear outputs |
| Dependency correctness | PASS | No deps; resolved DR verified in `.owlbear/decisions/resolved/` |
| Module layering | N/A | Docs-only task |
| TDD compliance | N/A | All td:0 |
| KISS/YAGNI | PASS | Minimal scope — brief amendments only |
| Premise challenge | PASS | DR approved (Option A); brief must reflect current authority |
| Pattern consistency | PASS | DR attribution follows existing brief amendment conventions |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Docs domain only |

### Challenge Results
- Challenger: SKIPPED — all td:0

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Annotated AC line 4 with (td:0). Advanced to todo.
[[2026-05-01]]
Architecture review complete. Docs-only task, all AC td:0. Verified D6, D14, and brief.md amendments are in place with DR attribution. Test-writer: SKIP.
[[2026-05-01]]
## Test-Writer Notes

Non-implementation pass-through. All AC lines are `td:0` (docs-only amendments to brief D6/D14). No testable Python interfaces exist. Architecture review explicitly marked Test-writer: SKIP.

**AC Coverage:** N/A — no testable contracts.
**Tests written:** 0
**Outcome:** Pass-through advance to in-progress.
[[2026-05-01]]
## Builder Notes
- Non-implementation task (td:0) confirmed from `## Test-Writer Notes`; no code changes required.
- AC verification completed directly in brief artifacts:
  - D6 updated to SSE primary with polling fallback and DR authority reference.
  - D14 change-detection text updated to SSE primary with polling fallback and DR authority reference.
  - brief sections using polling-only language updated for SSE-primary consistency.
- Files inspected:
  - `.owlbear/briefs/draft-cockpit/decisions.md`
  - `.owlbear/briefs/draft-cockpit/brief.md`
- Quality evidence (quality-runner, scoped/minimal viable):
  - pytest: not executed (docs-only, no implementation surface)
  - ruff: existing workspace lint debt only (4 violations outside task scope), no regressions for task #1257.
- Commits: none (no file modifications during builder pass-through).
- Evidence summary: acceptance criteria are already satisfied in source docs and align with resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`.
[[2026-05-01]]
## Review Evidence
### Test Results
- pytest: not applicable for this td:0 docs-only task; no implementation surface or task-owned tests.

### Lint
- quality-runner: no applicable lint target exists for these markdown brief artifacts in the local workspace.
- Ambient Python lint debt was reported as out of scope and is not used as gating evidence for task #1257.

### Coverage
- Not applicable for this td:0 docs-only task.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Not applicable. All AC lines are td:0 and no TestFromAC_* classes were expected or produced.

#### Security Review
- No runtime or boundary changes in scope. No security findings.

#### Test Integrity
- Not applicable. No task-owned tests.

#### Test Quality
- Not applicable. No task-owned tests.

#### Data Safety
- Not applicable. Documentation-only task.

#### Implementation-Aware Gap Analysis
- The live docs satisfy the SSE-direction content changes, but AC 4 is not fully met as written.
- decisions.md carries explicit resolved-DR attribution in both required decision rows:
  - .owlbear/briefs/draft-cockpit/decisions.md:19
  - .owlbear/briefs/draft-cockpit/decisions.md:65
- brief.md reflects the SSE-primary / polling-fallback amendments in multiple sections:
  - .owlbear/briefs/draft-cockpit/brief.md:31
  - .owlbear/briefs/draft-cockpit/brief.md:55
  - .owlbear/briefs/draft-cockpit/brief.md:57
  - .owlbear/briefs/draft-cockpit/brief.md:71
  - .owlbear/briefs/draft-cockpit/brief.md:74
  - .owlbear/briefs/draft-cockpit/brief.md:103
  - .owlbear/briefs/draft-cockpit/brief.md:108
- However, explicit resolved-DR attribution inside brief.md appears only at:
  - .owlbear/briefs/draft-cockpit/brief.md:92
  - .owlbear/briefs/draft-cockpit/brief.md:119
- Under the current acceptance criterion text, "All changes reference the resolved DR as authority," the amended brief.md sections above do not all carry the required authority reference.

#### Necessity Check
- Not applicable. No new dependency, integration, or tool addition.

#### Builder Process Quality
- CLEAN. Single builder pass-through note, no retry loop, no prior Review Evidence section detected.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| D6 in decisions.md updated to reflect SSE approval, removing "no SSE/WebSocket in v1" | .owlbear/briefs/draft-cockpit/decisions.md:19 now states SSE primary with polling fallback; exact old phrase is absent from decisions.md | PASS |
| D14 polling references updated to note SSE as primary transport with polling as fallback | .owlbear/briefs/draft-cockpit/decisions.md:65 states SSE primary push transport with polling fallback | PASS |
| brief.md sections referencing polling-only updated for consistency | .owlbear/briefs/draft-cockpit/brief.md:31, :55, :57, :71, :74, :92, :103, :108, :119 all reflect SSE-primary / polling-fallback wording | PASS |
| All changes reference the resolved DR as authority | decisions.md:19 and :65 cite the resolved DR, but amended brief.md sections at :31, :55, :57, :71, :74, :103, and :108 do not; only brief.md:92 and :119 cite the DR | FAIL |

### Deductions
- -0.14: AC 4 violated in the live brief artifact. The content is updated, but authority attribution is incomplete across the amended brief.md sections.

### Verdict
- FAIL
- Confidence: 0.86

### Required Follow-up
- Amend the updated brief.md sections introduced by this task so they explicitly reference the resolved authority `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`, or add a clearly governing nearby attribution that unambiguously covers those amended sections.
- Preserve the already-correct D6 and D14 decisions.md wording.
- Re-submit for review once the live brief artifact, not just the notes, satisfies AC 4 as written.

### Action
- Reject to in-progress. This is an implementation issue in the documentation artifact, not a test-gap issue.
[[2026-05-01]]
## Builder Notes
- Files changed: `.owlbear/briefs/draft-cockpit/brief.md`
- Fix applied: added explicit resolved-DR authority references to all SSE/polling statements that were amended under this task, including outcomes, backend/frontend phase rows, risk rows, out-of-scope note, and condensed D6.
- Test results (quality-runner scoped): 0 passed, 0 failed, pytest exit 5 (`test_paths=[]`, no tests collected; expected for td:0 docs-only task).
- Coverage: N/A (docs-only scope; no executable modules touched).
- Lint status (quality-runner scoped): clean with 0 violations (no lint targets provided for markdown docs; ruff exit 0).
- Evidence summary: AC1-AC3 remained satisfied; AC4 now satisfied because brief amendments now carry explicit authority to resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md` alongside already-correct decisions.md references.
- Commit: `23e18214` (`docs: align SSE authority refs in cockpit brief (#1257, builder)`).

Post-task reflection:
- Problem faced: prior brief updates were semantically correct but lacked explicit authority attribution on every amended SSE/polling mention required by AC text.
- Workaround applied: standardized inline authority references directly on each affected row/statement rather than relying on nearby implicit references.
- Pattern discovered: for docs AC phrased as "all changes reference authority," reviewers enforce per-change explicit citation, not just section-level intent.
- Quality gap avoided: removed shorthand DR mentions and normalized to the full resolved decision path to prevent another ambiguity-based reject.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner: no execution for this td:0 docs-only review (`test_paths=[]`, `lint_paths=[]`, `coverage_modules=[]`); no task-owned tests or executable modules were in scope.

### Lint
- quality-runner: clean with 0 violations; no applicable Python lint targets existed for the markdown-only artifact set.

### Coverage
- Not applicable for this td:0 docs-only scope.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Not applicable. All AC lines are td:0 and no `TestFromAC_*` classes were expected or produced.

#### Security Review
- No runtime, boundary, or dependency changes were in scope. No security findings.

#### Test Integrity
- Not applicable. No task-owned tests.

#### Test Quality
- Not applicable. No task-owned tests.

#### Data Safety
- Not applicable. Documentation-only task.

#### Implementation-Aware Gaps
- No critical gaps found after direct artifact inspection.
- `.owlbear/briefs/draft-cockpit/decisions.md:19` now states SSE primary with polling fallback and cites the resolved DR.
- `.owlbear/briefs/draft-cockpit/decisions.md:65` now states SSE primary push transport with polling fallback and cites the resolved DR.
- `.owlbear/briefs/draft-cockpit/brief.md:31`, `:55`, `:57`, `:71`, `:74`, `:92`, `:103`, `:108`, and `:119` all reflect the SSE-primary / polling-fallback direction and each carries explicit resolved-DR attribution.
- Workspace search found no remaining `"no SSE/WebSocket in v1"` text under `.owlbear/briefs/draft-cockpit/`.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Verified retry commit `23e18214` exists in `.git/logs/HEAD:1341` and `.git/logs/refs/heads/dev:1216`.
- quality-runner could not execute tooling because this td:0 docs-only retry had no test or lint artifacts; verdict is grounded in direct file inspection instead.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| D6 in decisions.md updated to reflect SSE approval, removing "no SSE/WebSocket in v1" | `.owlbear/briefs/draft-cockpit/decisions.md:19` states SSE primary with polling fallback, and the old phrase is absent from `.owlbear/briefs/draft-cockpit/` | N/A (td:0) | PASS |
| D14 polling references updated to note SSE as primary transport with polling as fallback | `.owlbear/briefs/draft-cockpit/decisions.md:65` states SSE primary push transport with polling fallback | N/A (td:0) | PASS |
| brief.md sections referencing polling-only updated for consistency | `.owlbear/briefs/draft-cockpit/brief.md:31`, `:55`, `:57`, `:71`, `:74`, `:92`, `:103`, `:108`, and `:119` all reflect SSE-primary / polling-fallback wording | N/A (td:0) | PASS |
| All changes reference the resolved DR as authority | `.owlbear/briefs/draft-cockpit/decisions.md:19`, `:65` and `.owlbear/briefs/draft-cockpit/brief.md:31`, `:55`, `:57`, `:71`, `:74`, `:92`, `:103`, `:108`, `:119` all cite `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md` | N/A (td:0) | PASS |

### Deductions
- None.

### Confidence: 0.98
### Verdict: PASS
### Action
- Advance to docs.
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are `.owlbear/briefs/` artifacts — OUT of scope; no IN-scope prose doc references them |
| 2 | Module docstrings | No | N/A | No Python files touched |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No `.owlbear/research/*.md` produced; resolved DR is in `.owlbear/decisions/resolved/` (not a research doc) |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index has no `describes` glob matching `.owlbear/briefs/draft-cockpit/` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/briefs/draft-cockpit/decisions.md` | OUT | N/A — `.owlbear/briefs/` not in IN-scope list |
| `.owlbear/briefs/draft-cockpit/brief.md` | OUT | N/A — `.owlbear/briefs/` not in IN-scope list |

**No docs impact.** Both changed files are brief artifacts outside the doc-writer IN-scope boundary. All checklist items resolve to N/A.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| D6 in decisions.md updated to reflect SSE approval, removing "no SSE/WebSocket in v1" | `.owlbear/briefs/draft-cockpit/decisions.md` D6 now reads "SSE (server-sent events) as primary transport; mtime-scan polling @ 3 s as fallback"; grep confirms old phrase absent from `.owlbear/briefs/draft-cockpit/` | PASS |
| D14 polling references updated to note SSE as primary transport with polling as fallback | `.owlbear/briefs/draft-cockpit/decisions.md` D14 reads "SSE as primary push transport… polling @ 3 s as automatic fallback" with DR attribution | PASS |
| brief.md sections referencing polling-only updated for consistency | brief.md lines :31, :55, :57, :71, :74, :92, :103, :108, :119 all reflect SSE-primary / polling-fallback wording | PASS |
| All changes reference the resolved DR as authority | decisions.md:19, :65 and brief.md:31, :55, :57, :71, :74, :92, :103, :108, :119 all cite `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md` | PASS |

### Test Results
- pytest: 3483 passed, ~104 failed, 4 skipped — all failures pre-existing and outside task scope (engine storage, corruption, React compiler, migration tests). No regressions from #1257.
- ruff: 4 violations, all pre-existing and outside task scope (knowledge, mcp-knowledge, mcp-memory, orchestrator packages).

### Architect Quality: 4/5
AC was specific and verifiable. Minor ambiguity in AC4 about per-section vs per-file attribution granularity (caused one reviewer reject cycle), but reasonable for a docs-only task.

### Deduction Breakdown
- AC lines: 4/4 PASS, no deduction
- Lint: out of scope, no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence: present, detailed, two-pass (FAIL→PASS at 0.98): no deduction
- Full-suite failures in task scope: none, no deduction

### Confidence: 1.00
### Action: archive

### Commits (upstream)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 46dd244f | docs | decisions.md, brief.md | #1257 |
| 23e18214 | docs | brief.md | #1257 |