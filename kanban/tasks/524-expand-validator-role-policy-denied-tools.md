---
id: 524
title: Expand validator role policy denied tools
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:32.0256337+01:00
updated: 2026-03-07T00:14:57.0652372+01:00
started: 2026-03-07T00:06:04.1585264+01:00
tags:
    - audit
    - security
    - scope:core
class: standard
---

ARC-20: VALIDATOR_POLICY only denies write_file and create_file. Doesnt restrict run_command, git_commit, git_push, browser_click, browser_type. Validator agent could still execute arbitrary shell commands.

Research complete. See docs/validator-role-policy-research.md for details.

Key findings:
- No agent currently uses role: validator (all default to builder)
- Allow-list model recommended over deny-list (.90 confidence)
- OWASP LLM06:2025 Excessive Agency mandates minimize extensions
- Proposed allow-list: 22 read-only tools for validators
- delegate_to_agent excluded from validator allow-list
- 3 follow-up implementation tasks identified

Research checklist:
- [x] Theoretical validity - allow-list is standard least-privilege practice
- [x] Prior art - OWASP LLM06:2025, NVIDIA NeMo-Guardrails
- [x] Technical feasibility - minimal change to RolePolicy + apply_role_policy
- [x] Architecture fit - extends existing roles.py, used by agent_registry.py
- [x] Implementation approach - add allowed_tools field, update filter logic
