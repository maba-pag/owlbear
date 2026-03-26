---
id: 524
title: Expand validator role policy denied tools
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:32.0256337+01:00
updated: 2026-03-11T10:44:22.2318607+01:00
started: 2026-03-07T00:06:04.1585264+01:00
completed: 2026-03-11T10:44:22.2318607+01:00
tags:
    - audit
    - security
    - scope:core
class: standard
---

ARC-20: VALIDATOR_POLICY only denies write_file and create_file. Doesnt restrict run_command, git_commit, git_push, browser_click, browser_type. Validator agent could still execute arbitrary shell commands.

Research complete. See docs/research/validator-role-policy.md for details.

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

[[2026-03-11]] Wed 10:44
## Architecture Review
**Verdict:** SPLIT -> #740, #741, #742

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| (no formal AC) | Task body is research summary, not implementation AC | Split into 3 tasks with precise AC |

### Architecture Notes
Research doc (docs/research/validator-role-policy.md) is thorough. Allow-list model is the correct approach per OWASP LLM06:2025. Key observations:

1. **No agent currently declares role: validator**  all 8 agents default to builder. Infrastructure is ready but unused.
2. **run_command must stay in allow-list**  research recommends excluding it, but reviewer/auditor agents need pytest/ruff execution. CommandSafetyGuard is the defense layer. Deviation documented in #741 AC.
3. **kanban_edit/kanban_move needed by validators**  all pipeline agents must append notes and advance status per agent-common protocol. Included in #741 AC.
4. **delegate_to_agent excluded**  validators report findings, orchestrator re-dispatches. Matches research recommendation.
5. **#561 (double-build)**  separate concern at someday priority. #741 works with current pattern.
6. **Auditor special case**  may need kanban_create for follow-up tasks. Deferred to #742 for decision.

### Changes Made
- Created #740: Test allow-list RolePolicy filtering (RED) -> todo
- Created #741: Implement allow-list RolePolicy model (GREEN) -> todo, depends on #740
- Created #742: Assign validator role to read-only agent definitions -> todo, depends on #741
- Original #524 replaced by split

### Dependencies
- #740 -> #741 -> #742 (strict chain)
- #561 (double-build) is independent, not blocked
