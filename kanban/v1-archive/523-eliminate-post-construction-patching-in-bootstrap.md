---
id: 523
title: Eliminate post-construction patching in bootstrap
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:31.3955566+01:00
updated: 2026-03-22T19:17:37.0786859+01:00
started: 2026-03-07T00:06:03.5267617+01:00
completed: 2026-03-22T19:17:37.0786859+01:00
tags:
    - audit
    - refactor
    - scope:core
blocked: true
block_reason: Already implemented in commit da621b5 and current source/tests; refresh or close instead of redispatching a builder
class: standard
---

ARC-14: bootstrap creates placeholder for ProjectToolset, patches real agent after construction. agent._deps.agent_registry set after agent construction. Two-phase init creates temporal coupling. Use lazy property or reorder construction. See docs/architecture-audit.md.

## AC

- [ ] No post-construction patching of agent or agent._deps
- [ ] ProjectToolset constructed before Agent, or accessed via lazy property
- [ ] Existing tests pass
- [ ] Ruff clean

[[2026-03-21]] Sat 04:43
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| No post-construction patching of agent or agent._deps | Stale and now over-broad. The ARC-14 seams this task was created for are already removed in current source, but a separate auth-refresh private client assignment still exists by design in bootstrap and daemon and is covered by dedicated cleanup tests. | Do not dispatch implementation from #523; treat the task as stale historical work. |
| ProjectToolset constructed before Agent, or accessed via lazy property | Satisfied. bootstrap/__init__.py creates SessionStore and ContextManager before _add_project_toolset, and bootstrap/toolsets.py constructs ProjectToolset with direct session/context/agent_toolsets injection. | Mark satisfied in current tree. |
| Existing tests pass | Historical implementation evidence already exists: tests/test_bootstrap_patching_elimination.py encodes the contract and the change landed in commit da621b5. | Do not requeue a builder for already-landed work. |
| Ruff clean | Historical gate for the landed refactor, not a reason to move this stale task to todo. | Keep as closure evidence only. |

### Architecture Notes
- Verified in src/owlbear/core/agent.py and src/owlbear/bootstrap/__init__.py that agent_registry is injected at OwlBearAgent(...) construction time; there is no late agent._deps.agent_registry patch anymore.
- Verified in src/owlbear/bootstrap/toolsets.py and src/owlear/projects/toolset.py that ProjectToolset now receives session, context, and agent_toolsets directly; there is no placeholder object or bind_agent() path in the current tree.
- Verified tests/test_bootstrap_patching_elimination.py is already the dedicated contract test suite for #523.
- Verified git history shows commit da621b5 refactor: eliminate post-construction patching in bootstrap (#523, builder) touching the exact source files plus the task-scoped tests.
- Verified a distinct private-attribute lifecycle seam still exists for auth refresh: src/owlbear/bootstrap/__init__.py and src/owlbear/daemon.py set agent._openai_client, and tests/test_client_cleanup.py intentionally asserts that behavior. That is separate from the ARC-14 work already completed and is not safe to absorb into this task's current AC.
- Because the intended implementation already landed, moving #523 to todo would duplicate scope and risk sending a builder after an already-closed refactor.

### Changes Made
- Claimed #523 for architecture review.
- Re-checked the current bootstrap wiring, the task-scoped tests, and git history for #523.
- Marked #523 as stale and moved it out of the active backlog queue instead of creating a duplicate builder handoff.

### Dependencies
- Verified current source: src/owlbear/bootstrap/__init__.py, src/owlbear/bootstrap/toolsets.py, src/owlbear/core/agent.py, src/owlbear/projects/toolset.py
- Verified current tests: tests/test_bootstrap_patching_elimination.py, tests/test_client_cleanup.py
- Verified existing implementation history: commit da621b5
