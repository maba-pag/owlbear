---
id: 600
title: Move .github/ customizations to share/
status: todo
priority: needed
created: 2026-04-04T20:30:21.323724+02:00
updated: 2026-04-04T22:15:11.0814615+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - type:config
parent: 598
class: standard
---

## Summary

Move .github/agents/, .github/skills/, .github/instructions/, .github/prompts/ to share/agents/, share/skills/, share/instructions/, share/prompts/ using git mv.

## Acceptance Criteria

- [ ] AC1: share/agents/ contains all 16 agent files + README
- [ ] AC2: share/skills/ contains all 30 skill directories + README
- [ ] AC3: share/instructions/ contains all 4 instruction files + README
- [ ] AC4: share/prompts/ contains all 6 prompt files
- [ ] AC5: .github/ retains only copilot-instructions.md and dependabot.yml
- [ ] AC6: .vscode/settings.json updated with chat.agentFilesLocations, chat.agentSkillsLocations, chat.instructionsFilesLocations pointing to share/ paths
- [ ] AC7: VS Code discovers agents, skills, instructions, and prompts from share/ (manual verification). If prompt discovery fails (no chat.promptFilesLocations equivalent exists), revert prompts to .github/prompts/ and adjust AC4/AC5 accordingly.

## Notes

Reference updates (copilot-instructions.md directory table, skill file path references, instruction applyTo patterns, pre-commit hook regex) are NOT in scope for this task — they belong to #607 (live references) and #609 (config cleanup). This task is limited to the physical git mv + VS Code settings update.

Historical docs (archived tasks, old research) must NOT be updated.

## Known Temporal Gaps

Between this task and #607/#609, the following will be stale (by design):
- copilot-instructions.md directory structure table
- Instruction applyTo patterns (e.g., agents-and-skills.instructions.md)
- Pre-commit validate-agents files: regex (.pre-commit-config.yaml)
- scripts/setup.py path generation (replaced by #604)
- r-project-standards file placement table
- README counts (already stale: say 14 agents/29 skills, actually 16/30)

[[2026-04-04]] Sat 22:14
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Physical file move + VS Code settings. Reference updates deferred to #607/#609. |
| Interface clarity | PASS (fixed) | AC1 corrected from 14 to 16 agents. AC7 expanded to gate prompt discovery. Note clarified to remove scope ambiguity. |
| Dependency correctness | PASS | No depends_on. Leaf starter task. Parent: #598 (approved). |
| Module layering | N/A | File moves only, no new code modules. |
| TDD compliance | PASS | Tagged type:config (pass-through). Test updates in sibling #608. |
| KISS/YAGNI | PASS | Minimal scope: git mv + settings JSON edit. |
| Premise challenge | PASS | .github/ namespace conflict with target projects is established in parent #598. No simpler alternative. |
| Pattern consistency | PASS | Uses git mv for history preservation. Settings follow existing chat.*Locations convention. |
| Security surface | PASS | File moves only. No new system boundaries. |
| Single domain | PASS | scope:infra. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| VS Code discovery from share/ | Default .github/ auto-discovery lost | None (silent) | Yes — AC6 settings + AC7 manual verification | Agents/skills invisible if settings wrong |
| Prompt discovery from share/prompts/ | No chat.promptFilesLocations setting | None (silent) | Yes — AC7 gates; fallback to .github/prompts/ | Prompts invisible until reverted |
| Pre-commit validate-agents regex | Regex no longer matches share/ paths | Hook silently skips | Acknowledged — #609 AC5 fixes | Agent validation disabled in gap |

### Refinements Applied

1. AC1: 14 agent files corrected to 16 (actual count: architect, auditor, builder, challenger, code-reader, curator, dispatcher, doc-writer, fix-attempt, orchestrator, planner, quality-runner, researcher, reviewer, scribe, test-writer)
2. AC7: Expanded to include prompt discovery verification with fallback plan
3. Note: Clarified scope boundary — reference updates explicitly excluded, belonging to #607/#609
4. Added Known Temporal Gaps section documenting expected stale state between subtasks
5. Added type:config pass-through tag

### Challenge Results

- Challenger: reconsider (confidence: 0.55)
- Concerns: (1) pre-commit regex breaks silently, (2) applyTo patterns break, (3) prompt discovery unverified, (4) Note/AC scope ambiguity, (5) README count staleness
- Architect response: Override with targeted refinements
  - C1: Pre-commit regex deferred to #609 AC5, acknowledged in Known Temporal Gaps
  - C2: applyTo patterns deferred to #607, acknowledged in Known Temporal Gaps
  - C3: AC7 now explicitly gates prompt discovery with revert fallback
  - C4: Note rewritten to remove ambiguity — explicit scope boundary stated
  - C5: README count staleness documented in Known Temporal Gaps

### Verdict: APPROVE
### Action Taken: Refined AC1 (16 agents), expanded AC7 (prompt fallback), clarified Notes (scope boundary), documented temporal gaps, added type:config tag. Advanced to todo.

[[2026-04-04]] Sat 22:15
APPROVED #600 -> todo | Move .github/ customizations to share/. Refined AC1 (14→16 agents), expanded AC7 (prompt discovery fallback), clarified scope boundary in Notes, documented known temporal gaps. Challenger overridden (0.55) — all 5 concerns addressed via AC refinements and temporal gap documentation.
