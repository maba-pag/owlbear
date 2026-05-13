---
id: 1533
title: 'P1-02: Implement body newline normalization at MCP kanban ingress'
status: archived
priority: critical
created: 2026-05-13T12:29:21.909969+00:00
updated: 2026-05-13T16:06:11.851308+00:00
tags:
  - phase-1
  - scope:mcp-kanban
  - type:feature
parent: 1531
depends_on:
  - 1532
blocked: false
block_reason:
claimed_at:
archival_reason: duplicate
archival_refs:
  - 1531
---
## Summary

GREEN phase: implement the normalization helper and wire it into all 5 MCP kanban tool call sites.

Brief: see parent #1531

## Scope

**In scope:**
- `_normalize_escaped_newlines()` helper function (alongside `_coerce_to_str()`)
- Call-site wiring in create_task, edit_task (body + append_body), end_work (note), create_dr (body)
- Guidance append after existing guidance block in each tool
- `create_dr` response dict: optional `guidance` key
- Tool description/docstring updates documenting normalization + escape convention

**Out of scope:**
- Engine changes, storage changes, archive remediation
- New dependencies
- `\r\n` handling, non-body parameters

## Implementation Reference

See `.owlbear/briefs/draft-body-newline-normalization/brief.md` for the exact helper code, guidance message text, and positional ordering constraints.
2026-05-13T15:46:56+00:00
## Research\n- Research doc: N/A — trivial finding (task fully superseded)\n- Sources: 1 studied (codebase), 1 high-relevance\n- Recommendation: Archive as superseded by parent #1531 (confidence: 0.98)\n- Follow-up tasks created: none (zero remaining work)\n- Decision requests: none\n\n### Finding: Task Fully Superseded\n\nAll scope items already implemented and reviewed under parent #1531 (commit ec29dd79, builder):\n- `_normalize_escaped_newlines()` helper at server.py:87\n- 5 call-site wirings at server.py:375, 411, 508, 511, 600\n- `_NORM_PARAM_DESC` on all 5 parameters at server.py:700-801\n- `create_dr` guidance key at server.py:411\n- Tests written and archived in sibling #1532\n\nTier: T1 (autonomous). Recommend immediate archival with reason `superseded` and archival_refs [1531].\n\n## Challenge Results\n- Challenger: SKIPPED — trivial supersession finding, no recommendation to challenge\n- Confidence in original: 0.98
2026-05-13T15:52:48+00:00
## Architecture Review\n\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Premise challenge | SUPERSEDED | All scope items verified implemented under parent #1531 (commit ec29dd79) |\n\n### Supersession Evidence\n- `_normalize_escaped_newlines()` at server.py:87 — matches scope item 1\n- 5 call-site wirings at server.py:375, 411, 508, 511, 600 — matches scope items 2-4\n- `_NORM_PARAM_DESC` at server.py:700-801 — matches scope item 5\n- `create_dr` guidance key at server.py:411 — matches scope item 4\n- Sibling test task #1532 done; parent #1531 full pipeline (reviewer PASS, docs gate)\n\n### Challenge Results\n- Challenger: SKIPPED — supersession mechanically verified (grep confirms all scope items present)\n\n### Proof-Bundle Validation\n- Planner assignment: behavioral\n- Final bundle: skip (superseded — zero remaining work)\n- Test-writer: SKIP\n\n### Verdict: APPROVE (immediate archival — fully superseded by parent #1531)\n### Action Taken: All scope items implemented under parent #1531. Advanced to done for immediate archival with reason=superseded, archival_refs=[1531].
2026-05-13T16:06:01+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4598 passed, ~210 failed, 14 skipped\n- All failures in unrelated domains (cockpit_view, ideation_diagram, engine_accessor_migration, server StatusNamesDictFormBug). Zero failures in mcp-kanban normalization scope.\n- Lint: clean\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (superseded — all 5 scope items implemented under parent #1531 commit ec29dd79)\n- purpose match: PASS (parent #1531 archived as completed, covering this task's entire scope)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer (parent audit)\n\n### Architect Quality: 3/5\nAC was specific with 5 enumerated scope items and clear in/out boundaries. However, the decomposition created an unnecessary subtask — all work landed in the parent task, making this subtask pure overhead. Decomposition accuracy gap, not an AC clarity issue.\n\n### Commit Integrity\n- upstream commit presence: N/A (superseded — zero work under this task; parent commits ec29dd79 and 118f8e1e verified during parent audit)\n- kanban commit packaging: pending (will commit after archival)\n\n### Deduction Breakdown\n- AC quality 3/5: -.03\n- All other criteria: 0\n\n### Confidence: 0.97\n### Action: archive (reason=superseded, archival_refs=[1531])