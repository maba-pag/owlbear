---
id: 1965
title: Clarify ecosystem validator ownership and eliminate inventory drift
status: archived
priority: medium
created: 2026-07-20T00:33:28.481880+02:00
updated: 2026-07-20T01:18:28.243547+02:00
tags:
  - scope:agent-ecosystem
  - documentation
  - validation
parent:
depends_on: []
ac:
  - 'AC1: `share/README.md` contains no manually maintained exact ecosystem counts
    that can diverge from directory contents.'
  - 'AC2: `h-agent-structure` identifies the existing pre-commit validator as the
    alignment enforcer without claiming a separate CI workflow.'
  - 'AC3: `README.md` tells repository developers to install the Git hook with `uv
    run pre-commit install` and explains that Git invokes the validators during commits.'
  - 'AC4: Both exact validator commands and relevant integrity checks pass locally.'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Give agent/skill structural validation an explicit runner and eliminate manually drifting ecosystem inventory counts.

## Scope
- `.pre-commit-config.yaml` validator ownership
- `.owlbear/scripts/validate_agents.py`
- `.owlbear/scripts/validate_skills.py`
- `README.md` development setup
- `share/README.md` inventory wording

## Boundaries
Do not add a broader CI mechanism without evidence that local commit enforcement is insufficient. Do not claim prompts or instructions are validated by scripts that inspect only agents and skills.

## Implementation Notes

Removed manually maintained ecosystem counts from `share/README.md` while preserving the concurrent ideation cleanup's reduced inventory.

A GitHub Actions workflow was initially added, then removed during the information-flow audit. Both validators already have pre-commit ownership; the workflow duplicated them, triggered on surfaces it did not validate, and had no demonstrated server-side enforcement requirement. Updated `h-agent-structure` to name the `validate-agents` pre-commit hook and updated `README.md` with the required one-time `uv run pre-commit install` command.

Runner: after installation, Git invokes pre-commit during a repository author or agent's commit. There is no dedicated validation agent. Authors can also run `uv run --frozen python .owlbear/scripts/validate_agents.py` and `validate_skills.py` directly.

Evidence: exact pre-commit validator commands pass; agent validator reports 12 conforming agents; skill validator and diff integrity pass.