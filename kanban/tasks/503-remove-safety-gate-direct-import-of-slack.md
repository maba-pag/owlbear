---
id: 503
title: Remove safety gate direct import of slack_templates
status: archived
priority: important
created: 2026-03-04T07:38:16.0494432+01:00
updated: 2026-03-07T18:07:57.8987143+01:00
started: 2026-03-06T20:32:52.5591455+01:00
completed: 2026-03-07T18:07:57.8987143+01:00
tags:
    - audit
    - architecture
    - safety
class: standard
---

INT-08: safety/gate.py has top-level import from channels.slack_templates. Creates coupling between safety and Slack. Move behind hasattr check with lazy import. See docs/integration-audit.md.

## Research Findings (2026-03-06)

See task history for full research. Architect verified all claims against codebase.

## Acceptance Criteria

- [ ] Top-level `from owlbear.channels.slack_templates import format_approval_blocks` removed from `src/owlbear/safety/gate.py` line 33
- [ ] `format_approval_blocks` imported inline inside the `if hasattr(self.channel, "send_blocks")` branch (~line 108)
- [ ] No other imports from `owlbear.channels` remain at module level in gate.py (TYPE_CHECKING imports are fine)
- [ ] `uv run ruff check src/owlbear/safety/` clean
- [ ] `uv run pytest tests/test_approval_gate.py -q --tb=short` passes
- [ ] `python -c "import sys; import owlbear.safety.gate; assert 'owlbear.channels.slack_templates' not in sys.modules"` succeeds — proves no module-level channel import at runtime

## Architecture Notes

- Pattern to follow: move import inside the `hasattr` branch. No try/except needed (slack_templates is part of owlbear, no optional deps).
- Do NOT introduce a callback parameter, factory, or any new abstraction. Single line move, nothing else.
- Existing `ChannelPlugin` import is already behind `TYPE_CHECKING` (line 37-41) — that pattern is correct and stays.
- The `hasattr(self.channel, "send_blocks")` guard is the natural lazy-import boundary.

## Out of Scope

- Do not refactor the hasattr check itself
- Do not touch slack_templates.py
- Do not add new test cases (existing test_approval_gate.py coverage is sufficient)
