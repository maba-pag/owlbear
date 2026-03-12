---
id: 762
title: Improve terminal output truncation with line-boundary snapping
status: backlog
priority: nice-to-have
created: 2026-03-12T21:39:58.9199581+01:00
updated: 2026-03-12T21:39:58.9199581+01:00
tags:
    - scope:core
    - tooling
class: standard
---

Upgrade _truncate() in src/owlbear/tools/terminal.py to snap to line boundaries instead of splitting mid-line. Adopt 60/40 head/tail split ratio. Pattern from context-mode truncate.ts.

See docs/research/claude-context-mode-research.md S3d.1.

AC:
- [ ] _truncate() snaps to newline boundaries (never cuts mid-line)
- [ ] Head gets 60%% of budget, tail gets 40%%
- [ ] Truncation marker shows line/KB counts: [N lines / X.YKB truncated -- showing first A + last B lines]
- [ ] Existing tests updated
- [ ] No behavior change for output under max_bytes
