---
id: 16
title: 'P3-01: Research VS Code hooks format and best patterns'
status: ideation
priority: high
created: 2026-02-24T15:08:55.4967412+01:00
updated: 2026-02-26T18:52:56.8050472+01:00
started: 2026-02-24T15:17:04.9349684+01:00
tags:
    - phase-3
    - research
    - hooks
class: standard
---

AC: Clone disler/claude-code-hooks-mastery into docs/research/. Read VS Code Copilot customization docs. Analyze hook format: JSON config in .github/hooks/, events (SessionStart, PreToolUse, PostToolUse, SubagentStop, Stop), exit codes (0=success, 2=block), OS-specific overrides. Document in docs/hooks-research.md with: supported events summary, recommended 5 hook implementations, JSON config examples, backing script requirements, known limitations. End with Follow-up Tasks per research-docs guardrails. Delete cloned repo after. Log sources in docs/sources.md.
