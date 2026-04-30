---
id: 1186
title: 'P2-01: Test DR skill replacement structure'
status: backlog
priority: needed
created: 2026-04-30T00:51:55.701005+00:00
updated: 2026-04-30T00:55:46.016907+00:00
tags:
- phase-2
- scope:agents
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Static test: `share/skills/h-decision-requests/SKILL.md` exists with valid YAML frontmatter (name, description fields)
- Static test: `share/agents/scribe.agent.md` does NOT exist
- Static test: `share/skills/w-decision-routing/SKILL.md` does NOT exist
- Static test: no remaining "scribe" references in any `share/agents/*.agent.md` file (agents: list or body)
- Static test: `share/skills/r-pipeline-protocol/SKILL.md` contains "create_dr" and does NOT contain "scribe"
- Static test: `share/skills/w-orchestration/SKILL.md` does NOT contain "dispatch scribe" or "scribe" dispatch pattern

## Scope

- IN: structural/static assertions validating P2 outcomes
- OUT: runtime behavior, content quality review

Brief: see parent #1179
[[2026-04-30]]
## Research

**Feasibility:** Confirmed. All 6 AC lines are testable with pathlib + yaml + glob. Tests will be RED initially (TDD pattern) — current codebase has scribe.agent.md, w-decision-routing skill, and 20+ "scribe" references across agent/skill files.

**Prior art:** `tests/test_ideation_overhaul_static.py` — identical structural-validation pattern (existence checks, content assertions, glob scans over share/ files).

**Implementation approach:** Single file `tests/test_dr_skill_replacement_1186.py`:
- `_REPO_ROOT = Path(__file__).parent.parent`
- 6 test functions mapping 1:1 to AC lines
- `yaml.safe_load()` for frontmatter validation
- `glob("share/agents/*.agent.md")` for scribe-reference scan

**No blockers, no follow-up tasks needed** — this is a leaf test task with clear AC and established patterns.
