---
id: 13
title: 'P2-01: Create docs/sources.md attribution table'
status: done
priority: high
created: 2026-02-24T15:06:14.3499844+01:00
updated: 2026-02-26T18:55:09.5639663+01:00
started: 2026-02-24T15:17:04.8235974+01:00
completed: 2026-02-26T18:55:06.4391219+01:00
tags:
    - phase-2
    - docs
depends_on:
    - 4
class: standard
---

## Acceptance Criteria
- Create docs/sources.md with:
  - # Attribution & Sources heading
  - Brief intro paragraph explaining: every pattern, code snippet, or architecture decision inspired by or copied from an external source is logged here for transparency and credit
  - A Markdown table with columns: | Source | URL | What Was Taken | How/Where Used in OwlBear | Date |
  - Initial entries (at minimum):
    1. HKUDS/nanobot | https://github.com/HKUDS/nanobot | Architecture patterns: agent loop, skills system, config management, provider abstraction | src/owlbear/ package structure, agent loop design | 2026-02-24
    2. Graphicator (tool.graphicator) | Local project | Copilot OAuth device-flow implementation, provider factory pattern | src/owlbear/auth/copilot.py, src/owlbear/providers/copilot.py | 2026-02-24
    3. openclaw/openclaw | https://github.com/openclaw/openclaw | Conceptual inspiration: gateway pattern, skills platform, workspace injection | Architecture decisions | 2026-02-24
    4. disler/claude-code-hooks-mastery | https://github.com/disler/claude-code-hooks-mastery | VS Code hook patterns: PostToolUse lint, PreToolUse safety, SessionStart context injection, builder/validator pattern | .github/hooks/, agent design | 2026-02-24
    5. coleam00/context-engineering-intro | https://github.com/coleam00/context-engineering-intro | Context engineering patterns: PRP workflow, examples folder concept, validation gates | .github/prompts/ design, project conventions | 2026-02-24
    6. coleam00/link-in-bio-page-builder | https://github.com/coleam00/link-in-bio-page-builder | Agent/skill file structure, command patterns | .github/agents/ and .github/skills/ structure | 2026-02-24
    7. coleam00/second-brain-research-dashboard | https://github.com/coleam00/second-brain-research-dashboard | PydanticAI + research pipeline patterns | Agent research workflow design | 2026-02-24
    8. VS Code Copilot docs | https://code.visualstudio.com/docs/copilot/copilot-customization | Hook event types, hook config JSON format | .github/hooks/ implementation | 2026-02-24
- Table should be clean, aligned, and easy to maintain

## Files to Create
- docs/sources.md

## Verification
- docs/sources.md exists with all 8 initial entries
- Table renders correctly in Markdown preview
- markdownlint passes
