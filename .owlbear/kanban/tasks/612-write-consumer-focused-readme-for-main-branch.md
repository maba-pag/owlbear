---
id: 612
title: Write consumer-focused README for main branch
status: todo
priority: needed
created: 2026-04-04T21:55:11.0661506+02:00
updated: 2026-04-05T01:04:17.9747753+02:00
tags:
    - scope:infra
    - type:docs
    - phase-2
parent: 610
depends_on:
    - 604
class: standard
---

## Summary

Write a consumer-focused README (README-consumer.md) on the dev branch. The sync workflow (#613) renames it to README.md on main. The existing README.md on dev remains the dev project README.

## Acceptance Criteria

- [ ] AC1: README-consumer.md exists at repository root on dev branch
- [ ] AC2: README contains these sections: **Overview** (1-2 paragraphs: what OwlBear is, what it does for consumers), **Prerequisites** (Python 3.12+, uv, VS Code, Copilot extension, Git -- table format matching setup-guide.md), **Quick Start** (clone + `python setup/init.py` with example shell commands), **Directory Layout** (describe share/, serve/, seed/, setup/ only -- table format), **Verification** (post-install check: open VS Code, confirm agents/skills load)
- [ ] AC3: Does NOT reference dev-only content (tests/, kanban/, docs/research/, orchestrator CLI, knowledge loader, .owlbear/, store/, v1/)
- [ ] AC4: Contains an Updates section explaining `git pull` to get latest
- [ ] AC5: Links to setup/setup-guide.md and setup/sharing-guide.md (paths valid after #604 completes)

## Notes

- Dev README.md stays as-is (describes the full dev workspace, orchestrator, knowledge, etc.).
- Sync workflow rename (README-consumer.md to README.md on main) is owned by #613 AC5.
- AC5 paths depend on #604 AC10/AC11 (git mv of docs to setup/). Verify links against actual files.
- Quick Start CLI invocation must match #604 AC8 init.py interface: `python ../owlbear/setup/init.py [--name NAME] [--type TYPE]`


## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS (fixed) | Removed AC6 (sync workflow config) -- belongs to #613. Task now covers only README content. |
| Interface clarity | PASS (refined) | AC2 rewritten: specifies 5 sections with content scope (paragraph counts, table format, example commands). |
| Dependency correctness | PASS (fixed) | Added depends_on: [604]. AC5 links to setup/setup-guide.md and setup/sharing-guide.md which don't exist until #604 AC10/AC11 complete. |
| Module layering | N/A | Docs-only task, no code modules. |
| TDD compliance | PASS | type:docs tag -- pass-through, no tests needed. |
| KISS/YAGNI | PASS | Single markdown file with defined sections. No over-engineering. |
| Premise challenge | PASS | Consumer README needed for dual-branch model (#610). Dev README has dev-only content inappropriate for consumers. |
| Pattern consistency | PASS | Prerequisites table format matches existing setup-guide.md. Directory layout table follows dev README pattern. |
| Security surface | PASS | No system boundaries. Static markdown file. |
| Single domain | PASS | scope:infra, type:docs. Documentation infrastructure. |

### Refinements Applied

1. Removed AC6 (sync workflow config) -- single-responsibility violation. Workflow rename is #613 AC5.
2. Added depends_on: [604] -- AC5 link targets don't exist until #604 moves docs to setup/.
3. Rewrote AC2 with explicit section names and content scope.
4. Added cross-task notes: CLI invocation must match #604 AC8;  rename owned by #613.
5. AC4 promoted from embedded in AC2 to standalone (Updates section).

### Challenge Results

- Challenger: proceed (confidence: 0.88-0.92)
- All three proposed issues confirmed: AC6 duplication, missing #604 dependency, AC2 vagueness.
- Additional concern noted: Quick Start CLI must coordinate with #604 AC8 final interface.
- Architect response: accepted all -- refinements applied.

### Verdict: REFINE (then APPROVE)
### Action Taken: Removed AC6, added depends_on [604], rewrote AC2 with section specs, added cross-task notes. Advanced to todo.

[[2026-04-05]] Sun 01:04
APPROVED #612 -> todo | Refined: removed AC6 (sync workflow owned by #613), added depends_on [604] (setup/ paths), rewrote AC2 with 5 named sections + content scope. Challenger confirmed all 3 issues (0.88-0.92). type:docs pass-through tag present.
