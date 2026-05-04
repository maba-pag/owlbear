---
id: 1353
title: Agent & Skill SNR Compression Tooling
status: todo
priority: important
created: 2026-05-04T21:20:12.818826+00:00
updated: 2026-05-04T21:23:36.552914+00:00
tags:
- prompt
- refactor
- snr
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Summary\n\nTwo complementary audit prompts (`agent-broad-audit.prompt.md` + `agent-deep-audit.prompt.md`) to reduce signal-to-noise ratio across 80 instruction files in `share/`. Broad audit: ecosystem-level coherence with SNR indicator and ranked report. Deep-dive: extreme-depth per-agent/skill cluster audit with interactive compression proposals.\n\n## Brief\n\n`.owlbear/briefs/draft-skill-snr/brief.md`\n\n## AC Summary\n\n- AC1: Broad audit prompt replaces agent-audit with strengthened D6 + ranked report\n- AC2: Deep-dive prompt with agent/skill cluster scope, section-by-section approval\n- AC3: Shared 6-category noise taxonomy in both prompts\n- AC4: Evaluation task (blocked, user-action, last) — run on reviewer agent
[[2026-05-04]]
## Planning\n### Decomposition: Agent & Skill SNR Compression Tooling\n- Tasks created: 3\n- Dependency layers: 2\n- Phase: 1\n\n### Task List\n| ID | Title | Priority | Depends On | Tags |\n|----|-------|----------|------------|------|\n| #1354 | P1-01: Write agent-broad-audit.prompt.md | needed | — | phase-1, scope:prompts, prompt, snr |\n| #1355 | P1-02: Write agent-deep-audit.prompt.md | needed | — | phase-1, scope:prompts, prompt, snr |\n| #1356 | P1-03: Evaluate SNR prompts on reviewer agent | important | #1354, #1355 | phase-1, scope:prompts, user-action, snr |\n\n### Dependency Graph\n```mermaid\ngraph LR\n  1354[\"#1354 Broad Audit\"] --> 1356[\"#1356 Evaluation\"]\n  1355[\"#1355 Deep-Dive\"] --> 1356\n```\n\n### Notes\n- TDD pairing N/A: deliverables are `.prompt.md` files (no automated test harness). AC4 (#1356) serves as the verification gate.\n- #1356 is blocked from the start per Brief constraint (user-action, last task).\n- #1354 and #1355 are independent — taxonomy is fully specified in Brief, both inline it.\n- Status skip to `todo` intentional: Brief provides full spec, no research phase needed.