---
id: 1294
title: 'Investigate dead code: serve/orchestrator/ module and owlbear-project.json
  usage'
status: archived
priority: medium
created: 2026-05-02T16:08:21.865625+00:00
updated: 2026-05-02T21:53:10.111851+00:00
tags:
- deferred
- cleanup
- research
parent: 1296
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

From neutral-shared-layer ideation (D4, research-notes.md follow-up #2). User flagged serve/orchestrator/ and owlbear-project.json as potential dead code. Needs investigation before removal.


Superseded by parent #1296 which has the full removal Brief. This task's investigation is complete — findings captured in `.owlbear/briefs/draft-dead-code-sweep/research-notes.md`.


### AC
1. Investigation findings captured in `.owlbear/briefs/draft-dead-code-sweep/research-notes.md` (td:0)
2. Parent #1296 Brief covers all removal scope identified by this investigation (td:0)
[[2026-05-02]]
## Architecture Review

**Verdict:** APPROVE — investigation-complete pass-through

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| 1. Findings captured in research-notes.md | Verified: task body references the file; parent #1296 Brief cites findings | None — td:0 |
| 2. Parent #1296 covers removal scope | Verified: #1296 Brief lists 5 deletions + 14 edits + regeneration; decomposed into #1297–#1299 | None — td:0 |

### Architecture Notes

Pure investigation task — no implementation surface. The investigation identified `serve/orchestrator/` and `owlbear-project.json` as dead code from abandoned Copilot CLI/ACP orchestration. Findings were rolled into parent #1296's Brief, which has already been decomposed into 3 implementation tasks (#1297 core removal, #1298 doc cleanup, #1299 diagram cleanup).

### Dependency Analysis

- No `depends_on` — correct, investigation has no upstream deps.
- Parent #1296 owns all downstream implementation via #1297–#1299.

### Challenger

Skipped — all AC lines are td:0.

### Test-writer routing

Test-writer: SKIP (all td:0, tagged `research` — pass-through)
[[2026-05-02]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-02]]
## Builder Notes
- Non-implementation task (all AC lines are td:0) with no implementation surface.
- Files changed: none.
- Tests: not applicable for builder on td:0 pass-through.
- Lint: not applicable (no code changes).
- Evidence summary: task body already records architecture approval and test-writer skip/pass-through; builder confirms no further action required.
[[2026-05-02]]
## Review Evidence

### Tests
- Quality-runner scoped td:0 pass-through report: passed 0, failed [], skipped 0.
- No task-scoped tests apply because both AC lines are td:0 and the task file already records test-writer skip at .owlbear/kanban/tasks/1294-investigate-dead-code-serve-orchestrator-module-and-owlbear-project-json-usage.md:61.

### Lint
- Quality-runner lint-only report: clean true, violations [], reason: "No lintable files for task 1294 (research/pass-through, td:0 investigation)".
- Builder notes independently state there was no implementation surface and no file changes at .owlbear/kanban/tasks/1294-investigate-dead-code-serve-orchestrator-module-and-owlbear-project-json-usage.md:65 and .owlbear/kanban/tasks/1294-investigate-dead-code-serve-orchestrator-module-and-owlbear-project-json-usage.md:66.

### Coverage
- Skipped by td:0 review policy. No changed modules and no executable surface.

### AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| 1. Investigation findings captured in .owlbear/briefs/draft-dead-code-sweep/research-notes.md (td:0) | The research artifact contains the investigation itself: serve/orchestrator dead-code finding at .owlbear/briefs/draft-dead-code-sweep/research-notes.md:5, owlbear-project.json finding at .owlbear/briefs/draft-dead-code-sweep/research-notes.md:14, live scope_transfer consumer at .owlbear/briefs/draft-dead-code-sweep/research-notes.md:18, and Copilot CLI / ACP live-reference inventory at .owlbear/briefs/draft-dead-code-sweep/research-notes.md:25. | PASS |
| 2. Parent #1296 Brief covers all removal scope identified by this investigation (td:0) | The parent brief explicitly scopes complete removal of serve/orchestrator at .owlbear/briefs/draft-dead-code-sweep/brief.md:12, owlbear-project.json infrastructure at .owlbear/briefs/draft-dead-code-sweep/brief.md:13, scope_transfer follow-up at .owlbear/briefs/draft-dead-code-sweep/brief.md:14, and stale Copilot CLI / ACP refs at .owlbear/briefs/draft-dead-code-sweep/brief.md:15. The parent task links that brief at .owlbear/kanban/tasks/1296-dead-code-sweep-remove-copilot-cli-acp-orchestrator-and-owlbear-project-json-inf.md:74 and decomposes the resulting implementation into #1297 to #1299 at .owlbear/kanban/tasks/1296-dead-code-sweep-remove-copilot-cli-acp-orchestrator-and-owlbear-project-json-inf.md:82, .owlbear/kanban/tasks/1296-dead-code-sweep-remove-copilot-cli-acp-orchestrator-and-owlbear-project-json-inf.md:83, and .owlbear/kanban/tasks/1296-dead-code-sweep-remove-copilot-cli-acp-orchestrator-and-owlbear-project-json-inf.md:84. | PASS |

### Critical Check Summary
- Test-Writer Audit: skipped. No TestFromAC classes apply and both AC lines are td:0.
- Test Integrity: skipped. No task test file and no builder test edits.
- Test Quality, Data Safety, Implementation-aware Gap Analysis, and Necessity Check: no implementation surface to assess.
- Process quality: CLEAN. One Builder Notes section begins at .owlbear/kanban/tasks/1294-investigate-dead-code-serve-orchestrator-module-and-owlbear-project-json-usage.md:64, and grep for an existing Review Evidence section in this task file returned no matches.

### Deductions
- 0.02 confidence deduction because quality-runner evidence is necessarily a no-op for this td:0 pass-through task, so confidence rests primarily on direct artifact inspection rather than executable verification.

### Verdict
- PASS with confidence 0.98.

### Action
- Advance to docs. Investigation is complete and no further builder or test-writer work is required.
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavior, API, CLI, config, or package structure changed — pure investigation task |
| 2 | Module docstrings | No | N/A | No Python modules created or modified; Builder Notes confirm "Files changed: none" |
| 3 | External attribution | No | N/A | Research notes reference only internal file/grep analysis; no external repos or articles used |
| 4 | Research doc | No | N/A | Findings captured in `.owlbear/briefs/draft-dead-code-sweep/research-notes.md` (brief file, not `.owlbear/research/`); linked in task body; follow-up tasks exist (#1297–#1299) |
| 5 | Diagram maintenance (describes match) | No | N/A | No changed files — no describes-match applicable |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files — investigation task only |

### Scope Classification

Changed-files set: **none** (Builder Notes explicit: "Files changed: none"; both AC lines td:0).
All files OUT-of-scope or absent — no IN-scope docs affected.

**Result: no docs impact.** Zero files modified. No scratch files found for task 1294. Advancing to done.
[[2026-05-02]]
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Findings captured in research-notes.md (td:0) | File exists at .owlbear/briefs/draft-dead-code-sweep/research-notes.md with 4 detailed findings sections (orchestrator dead-code, owlbear-project.json partial-dead, Copilot CLI/ACP refs, opportunistic observations). Committed in 18d29c10. | PASS |
| 2. Parent #1296 Brief covers removal scope (td:0) | Brief at .owlbear/briefs/draft-dead-code-sweep/brief.md lists 5 deletions + reference cleanup. Parent #1296 decomposed into #1297-#1299. Committed in 18d29c10. | PASS |

### Test Results

- pytest: 3699 passed, 129 failed (all pre-existing; task changed 0 files, no regressions)
- vitest: 876 passed, 80 failed (all pre-existing; no frontend changes)
- ruff: 2 violations (pre-existing, not in task scope)
- eslint: 1 config violation (pre-existing)

### Architect Quality: 4/5

AC lines are specific and verifiable for an investigation task. Clear deliverable references. Minor note: research placement at .owlbear/briefs/ vs .owlbear/research/ is appropriate for brief-integrated research but deviates from Step 1a convention.

### Deduction Breakdown

- 0.02: td:0 no-op quality-runner (confidence rests on artifact inspection rather than executable verification)

### Confidence: 0.98

### Action: archive