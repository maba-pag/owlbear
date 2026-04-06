---
id: 662
title: Add type:user-action to NON_IMPL_TAGS (gates.py + server.py)
status: research
priority: nice-to-have
created: 2026-04-06T16:39:07.1761895+02:00
updated: 2026-04-06T16:39:07.1761895+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:config
depends_on:
    - 665
parent: 661
class: standard
---

## Objective\nAdd `type:user-action` to the NON_IMPL_TAGS set in both Python gate locations for TDD gate exemption.\n\n## Context\nFrom #661 research: `type:user-action` tag convention for manual user-action tasks needs TDD gate exemption so the test-writer passes through cleanly after user completes the action.\nSkill doc updates split to #666.\n\n## Acceptance Criteria\n- [ ] Add `type:user-action` to `_NON_IMPL_TAGS` in serve/orchestrator/src/owlbear/planner/gates.py\n- [ ] Add `type:user-action` to `_PICK_NON_IMPL_TAGS` in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py\n- [ ] Existing tests pass (no regressions)\n\n## Files Affected\n- serve/orchestrator/src/owlbear/planner/gates.py\n- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
