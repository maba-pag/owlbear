---
id: 505
title: Sync copilot-instructions.md agent inventory with actual files
status: done
priority: important
created: 2026-03-04T07:38:17.6612106+01:00
updated: 2026-03-08T02:01:31.8161122+01:00
started: 2026-03-06T23:40:07.8549374+01:00
completed: 2026-03-08T02:01:31.8161122+01:00
tags:
    - audit
    - docs
class: standard
---

DOC-F-09: Agent inventory table mismatches with files on disk.
Research found: src/owlbear/agents/closer.md uses name 'closer' but .github/agents/ and the table use 'auditor' for the same role. Also: curator.md missing from src/owlbear/agents/.
See task research findings.

## Acceptance Criteria

- [ ] src/owlbear/agents/closer.md renamed to src/owlbear/agents/auditor.md
- [ ] name: field inside auditor.md changed from 'closer' to 'auditor'
- [ ] src/owlbear/agents/curator.md created matching .github/agents/curator.agent.md role definition
- [ ] Agent inventory table in copilot-instructions.md matches all files in both directories:
  - src/owlbear/agents/: orchestrator, kanban-planner, researcher, architect, builder, reviewer, writer, auditor, curator (9 files)
  - .github/agents/: same 9 names with .agent.md suffix
- [ ] Any test that references 'closer' agent name updated to 'auditor'
- [ ] AgentRegistry.scan() finds 'auditor' (not 'closer') after rename
- [ ] ruff clean, all tests pass
