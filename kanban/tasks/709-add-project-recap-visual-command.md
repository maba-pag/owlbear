---
id: 709
title: Add project-recap visual command
status: backlog
priority: nice-to-have
created: 2026-03-09T15:25:19.3510256+01:00
updated: 2026-03-10T03:40:12.8370493+01:00
started: 2026-03-10T03:30:25.9408276+01:00
tags:
    - scope:copilot
    - agent
depends_on:
    - 706
class: standard
---

Adapt visual-explainer's project-recap pattern as an OwlBear agent command. Reads git log + kanban board + codebase structure -> generates HTML mental model snapshot. Uses visual-output skill for output. Requires #707 (visual-output skill) first.
See docs/research/visual-explainer-research.md S3b.

AC:
- [ ] Agent command (instructions or prompt file) for project-recap
- [ ] Reads git log (recent commits), kanban board state, codebase top-level structure
- [ ] Generates self-contained HTML overview using visual-output skill patterns
- [ ] Output saved to .owlbear/diagrams/ directory
- [ ] Delivered via VisualFeedbackToolset (screenshot capture)

[[2026-03-10]] Tue 03:39
## Research
**Doc:** docs/research/project-recap-command-research.md

**Key findings:**
- .prompt.md file is the right format (.85 confidence) - KISS, VS Code native, matches existing pattern
- All 8 visual-explainer sections map to OwlBear data sources (git log, kanban, file tree)
- Zero runtime code needed - pure prompt engineering (~40 lines)
- Soft dependency on #706 (visual-output skill) for polish, but works standalone
- aider RepoMap validates the concept; our approach is simpler (prompt vs 867-line Python)

Full follow-up task commands in docs/research/project-recap-command-research.md S5.

[[2026-03-10]] Tue 03:39
## Research
**Doc:** docs/research/project-recap-command-research.md

**Key findings:**
- .prompt.md file is the right format (.85 confidence) - KISS, VS Code native, matches existing pattern
- All 8 visual-explainer sections map to OwlBear data sources (git log, kanban, file tree)
- Zero runtime code needed - pure prompt engineering (~40 lines)
- Soft dependency on #706 (visual-output skill) for polish, but works standalone
- aider RepoMap validates the concept; our approach is simpler (prompt vs 867-line Python)

Full follow-up task commands in docs/research/project-recap-command-research.md S5.
