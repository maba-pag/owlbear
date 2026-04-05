---
id: 565
title: Evaluate role system complexity for 2 roles
status: backlog
priority: someday
created: 2026-03-04T07:39:07.9665052+01:00
updated: 2026-03-21T13:51:31.244503+01:00
started: 2026-03-07T04:28:05.1725947+01:00
tags:
    - audit
    - yagni
    - scope:core
blocked: true
block_reason: 'Split into #897, #898 - work tracked there'
class: standard
---

YAGNI-03: Full infrastructure (AgentRole enum, RolePolicy, apply_role_policy, 2 policies) to express: validators cant use write_file and create_file. 277 LOC for a 2-element frozenset. Research complete: recommend SIMPLIFY (.80 confidence). Replace with inline toolset.filtered() per PydanticAI idiom. See docs/research/role-system-complexity.md.

## AC

- [x] Decision documented: SIMPLIFY recommended

## Architecture Review
**Verdict:** SPLIT -> #897, #898

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Decision documented: SIMPLIFY recommended | Research-only conclusion; the premise is stale because the live code now uses a validator allow-list and active validator roles. | Split into #897 and #898 with RED coverage and preserved allow-list behavior. |

### Architecture Notes
- Runtime consumer is src/owlbear/core/agent_registry.py; src/owlbear/core/roles.py is otherwise test-only.
- Keep AgentDefinition.role as string metadata from src/owlbear/core/agent_def.py and src/owlbear/agents/*.md.
- Preserve #561's single-Agent invariant and the current validator allow-list behavior while removing the extra abstraction layer.

### Changes Made
- Created #897: RED tests for direct filtering without core.roles.
- Created #898: GREEN simplification task, depends on #897.
- Blocked #565 as the umbrella so delivery work is tracked on the child tasks.

### Dependencies
- Verified: #561 archived.
- Added: #897 -> #898
