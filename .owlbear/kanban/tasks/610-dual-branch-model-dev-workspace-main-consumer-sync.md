---
id: 610
title: 'Dual-branch model: dev (workspace) + main (consumer sync)'
status: in-progress
priority: nice-to-have
created: 2026-04-04T21:54:46.295562+02:00
updated: 2026-04-05T21:37:02.7429168+02:00
tags:
    - scope:infra
    - type:restructure
    - phase-2
    - type:config
depends_on:
    - 598
class: standard
---

## Summary

Umbrella task for the dual-branch model: dev (full workspace, daily driver) and main (clean consumer-facing, auto-synced product subset). All implementation is delivered through subtasks (#611 through #615). This task verifies the integrated result.

## Context

OwlBear serves two roles: service provider for target projects and self-improving dev project. The dev branch holds everything (research, kanban, tests, v1 archive). The main branch holds only the product subset that consumers need.

A GitHub Actions workflow syncs product files from dev to main on manual dispatch. Consumers clone main; contributors work on dev.

## Architecture

```
dev (default working branch):
  share/ serve/ seed/ setup/          (product files)
  .owlbear/ store/ tests/ v1/ ...    (dev-only files)

main (consumer branch, auto-generated):
  share/ serve/ seed/ setup/          (synced from dev)
  pyproject.toml uv.lock README.md    (synced from dev)
  .python-version .gitignore SECURITY.md
```

## Acceptance Criteria (verification)

- [ ] AC1: #611 archived -- dev branch exists on origin, GitHub default branch is main
- [ ] AC2: #612 archived -- README-consumer.md exists at repo root on dev
- [ ] AC3: #613 archived -- .github/workflows/sync-to-main.yml exists on dev, workflow_dispatch trigger only
- [ ] AC4: #614 archived -- skills-ref in optional dependency group, not in dev group
- [ ] AC5: #615 archived -- first sync validated: clean main branch, consumer clone + uv sync + setup/init.py all exit 0

## Subtask Map

| Subtask | Title | Status |
|---------|-------|--------|
| #611 | Create dev branch and push to remote | in-progress |
| #612 | Write consumer-focused README for main branch | archived |
| #613 | Create GitHub Actions sync workflow (dev to main) | backlog |
| #614 | Move skills-ref to optional dependency group | archived |
| #615 | First sync: validate clean main branch | in-progress (blocked on #613) |

## TDD Exemption

Umbrella/tracker task. All AC items map 1:1 to subtask deliverables with their own pipeline cycles. No additional test task needed.

## Dependencies

Depends on #598 (five-tier folder restructure). The sync workflow copies product files from dev to main; the folder structure must be finalized on dev before the first sync produces a valid main branch.

## Risks

- GitHub default branch must be main (consumer-facing), but dev is the working branch
- pyproject.toml skills-ref dep must be handled for main (uv sync must not fail)
- First sync creates a diverged main that cannot be merged back to dev (by design)

[[2026-04-05]] Sun 20:26
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS (fixed) | Converted from mixed implementation/tracking to pure umbrella/verification task. Original AC duplicated subtask ACs. |
| Interface clarity | PASS (refined) | Original 5 AC lines were vague or redundant. Rewrote as 5 verification ACs, each referencing a specific subtask and its key deliverable. |
| Dependency correctness | PASS (fixed) | Removed #615 from depends_on (child task, redundant with AC5). Kept #598 (external prereq for folder structure). |
| Module layering | N/A | Umbrella task, no code modules. |
| TDD compliance | PASS (fixed) | Added type:config pass-through tag. Added TDD Exemption section (umbrella pattern from #19, #20). |
| KISS/YAGNI | PASS | Parent tracking with verification AC, no over-engineering. |
| Premise challenge | PASS | Dual-branch model is necessary: dev workspace contains research, kanban, tests, v1 archive inappropriate for consumers. README-consumer.md (done), setup/init.py (exists), and sync workflow (#613) are the mechanism. |
| Pattern consistency | PASS (fixed) | Now follows established umbrella pattern from #19 (ACP client) and #20 (dispatch planner): verification AC, subtask map, TDD exemption. |
| Security surface | PASS | No new system boundaries. Sync workflow (#613) handles branch permissions. |
| Single domain | PASS | scope:infra only. |

### Codebase Evidence

- setup/init.py: 206 LOC. Creates .vscode/mcp.json, .vscode/settings.json, owlbear-project.json from seed/ templates. Consumer setup mechanism confirmed working.
- README-consumer.md: exists (107 lines, #612 archived). Consumer-facing README ready for sync.
- .github/workflows/: no sync-to-main.yml yet (#613 in backlog, awaiting arch review).
- pyproject.toml: skills-ref already moved to optional validation group (#614 archived, commit f91e417).
- Prior umbrella tasks: #19 (ACP client, 7 subtasks, archived), #20 (dispatch planner, 3 subtasks, archived) followed same verification-AC pattern.

### Refinements Applied

1. Converted from implementation task to umbrella/tracker pattern (matching #19, #20)
2. Rewrote 5 vague AC lines as 5 verification ACs, each tied to a specific subtask
3. Removed #615 from depends_on (child task, tracked via AC5)
4. Added type:config pass-through tag
5. Added TDD Exemption section
6. Added Subtask Map with current status
7. Eliminated duplicate AC lines that restated subtask ACs verbatim (AC1/AC2 were #611, AC4/AC5 were #615)

### Challenge Results

- Challenger: SKIPPED (REFINE verdict, challenger optional per w-arch-review Step 2.5)
- Architect rationale: straightforward umbrella-pattern application with clear precedent (#19, #20). No novel design decisions to challenge.

### Verdict: REFINE (then APPROVE)
### Action Taken: Converted to umbrella/verification pattern, rewrote all AC, removed redundant dep, added pass-through tag and TDD exemption. Advancing to todo.

[[2026-04-05]] Sun 21:37
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Umbrella/tracker task with explicit TDD Exemption: all AC lines verify subtask deliverables (#611–#615), not Python interfaces.
- Passing through to builder.
