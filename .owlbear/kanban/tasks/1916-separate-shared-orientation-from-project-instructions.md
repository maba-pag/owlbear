---
id: 1916
title: Separate shared orientation from project instructions
status: collect
priority: medium
created: 2026-07-12T04:09:21.262709+02:00
updated: 2026-07-12T04:17:25.572315+02:00
tags:
  - scope:agent-config
  - docs
parent:
depends_on: []
ac:
  - The owlbear-dev Copilot instruction contains only repository-specific 
    identity, topology, stack, branch, Cockpit, and test-domain information.
  - Portable index/test-root orientation and project-context discovery live in 
    `h-project-orientation`; shared OwlBear artifact placement lives in 
    `r-project-standards`.
  - Shared skills no longer treat local Copilot instructions as an authority for
    universal principles, and live references remain consistent.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Keep `.github/copilot-instructions.md` project-specific by moving portable OwlBear tool, artifact-placement, and orientation behavior into shared skills.

## Scope
In: `.github/copilot-instructions.md`, `h-project-orientation`, `r-project-standards`, `w-research`, WIRING/docs/index regeneration as needed.
Out: retiring ideation skills and unrelated project-specific Cockpit/branch/test-domain facts.

Proof guidance: exact-reference scans, agent validation, focused documentation/cross-reference checks.

[[2026-07-12T04:17:25+02:00]]
Builder Notes
- Removed portable OwlBear tool, placement, and duplicate layout guidance from `.github/copilot-instructions.md`; retained only owlbear-dev identity, branch topology, concrete directory map, Cockpit stack, and project test-domain mapping.
- Consolidated project discovery and portable `indexes`/`test-root`/Semble behavior in `h-project-orientation`; consolidated OwlBear-managed artifact placement in `r-project-standards`.
- Replaced the percentage-based Copilot-instructions doctrine in `h-agent-structure` and `agent-broad-audit.prompt.md` with a categorical project-facts/shared-behavior boundary; aligned `share/README.md` and `w-research`.
- Replaced stale extraction assertions in `tests/test_skill_extraction.py` with authority-boundary regressions.
- Regenerated committed indexes.

Evidence
- `uv run python .owlbear/scripts/validate_agents.py`: PASS, all 23 agent files.
- Focused authority/extraction tests: 47 passed.
- Authority and consumer-scaffold regressions: 23 passed.
- Ruff check and format check for updated Python test: PASS.
- VS Code diagnostics on changed authority surfaces: none.
- Exact scan for old `h-code-orientation`, `80% Rule`, and extraction doctrine: no matches.
- `git diff --check`: PASS.
- builder-challenger: PASS, no blocking findings.

Unrelated existing failures observed but not changed: one config-schema fixture uses statuses incompatible with the default entry status; four cross-reference assertions require removed WIRING rows from a concurrent ecosystem rewrite.
