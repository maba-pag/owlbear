---
id: 132
title: Add pre-commit guard against agent tool name regression
status: archived
priority: medium
created: 2026-03-29 08:15:13.052016+02:00
updated: 2026-03-29 14:56:44.296284+02:00
started: 2026-03-29 14:56:44.296284+02:00
completed: 2026-03-29 14:56:44.296284+02:00
tags:
- phase-1
- scope:agents
- tooling
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Prevent VS Code auto-staging from reverting agent tool name fixes.

## Acceptance Criteria
- [ ] Pre-commit hook or CI check that fails if any agents/*.agent.md tools: list contains bare todo (not todos)
- [ ] Check also fails if resolveMemoryFileUri appears in any agent file
- [ ] Hook runs in less than 1s
- [ ] Documented in README or contributing guide

[[2026-03-29]] Sun 12:02
## Research
Approach: Python script (scripts/validate_agents.py) as repo: local pre-commit hook.
Rationale: Follows validate_skills.py pattern, parses frontmatter precisely (avoids false positives from prose), runs under 1s on 11 files.
pygrep rejected: bare 'todo' appears legitimately in agent prose, causing false positives.
Doc: docs/research/pre-commit-agent-tool-guard.md
Follow-up: #134 (implement)

[[2026-03-29]] Sun 14:56
## Architecture Review
**Verdict:** Merge -- redundant with #134

Research deliverable complete (docs/research/pre-commit-agent-tool-guard.md). Implementation AC duplicates #134's more precise AC. Deleting #132; approving #134 as the surviving task.
