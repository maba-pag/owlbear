---
id: 763
title: Add soft-fail exit classification for terminal commands
status: backlog
priority: nice-to-have
created: 2026-03-12T21:40:09.2923504+01:00
updated: 2026-03-12T21:40:09.2923504+01:00
tags:
    - scope:core
    - tooling
class: standard
---

Treat shell exit code 1 with non-empty stdout as soft failure (not error). Commands like grep, diff, find exit 1 for no-matches -- not real errors. Pattern from context-mode exit-classify.ts.

See docs/research/claude-context-mode-research.md S3d.3.

AC:
- [ ] Add soft_fail: bool field to TerminalResult dataclass
- [ ] classify_exit(exit_code: int, stdout: str) -> bool function in terminal.py
- [ ] Returns True when exit_code == 1 and stdout is non-empty
- [ ] _run_command_wrapper annotates output with (soft-fail) when soft_fail is True
- [ ] run_command() populates soft_fail field via classify_exit()
- [ ] Tests cover: grep-no-match (exit 1, no stdout), diff-differences (exit 1, stdout), real failures (exit 2+)
