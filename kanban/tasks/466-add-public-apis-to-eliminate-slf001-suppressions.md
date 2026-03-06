---
id: 466
title: Add public APIs to eliminate SLF001 suppressions
status: archived
priority: needed
created: 2026-03-04T07:37:46.2112012+01:00
updated: 2026-03-06T19:28:09.9022352+01:00
started: 2026-03-06T10:11:03.3885684+01:00
completed: 2026-03-06T19:28:09.9022352+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-05/INT-16: 10 SLF001 suppressions across 4 files. Research complete  see docs/slf001-public-api-research.md.

Implementation plan (4 fix groups, all in one task  unified goal, each is 3-15 LOC):

### 1. Rename _delegation_depth  delegation_depth (1 suppression)
- In src/owlbear/core/deps.py: rename field `_delegation_depth`  `delegation_depth` on OwlBearDeps dataclass.
- Update src/owlbear/core/delegation.py:97  `ctx.deps.delegation_depth` (remove noqa).
- Update src/owlbear/core/delegation.py:126  `dataclasses.replace(deps, delegation_depth=depth + 1)`.
- Update tests/test_agent.py: all `_delegation_depth` references  `delegation_depth`.

### 2. Add OwlBearAgent.set_agent_registry() + ProjectToolset.bind_agent() (2 suppressions)
- In src/owlbear/core/agent.py: add `set_agent_registry(self, registry: AgentRegistry) -> None` that sets `self._deps.agent_registry = registry`.
- In src/owlbear/projects/toolset.py: add `bind_agent(self, agent: object) -> None` that sets `self._agent = agent`.
- Update src/owlbear/bootstrap.py:938 to call `agent.set_agent_registry(agent_registry)` instead of `agent._deps.agent_registry = ...`.
- Update src/owlbear/bootstrap.py:814 (_patch_project_toolset_agent) to call `inner.bind_agent(agent)` instead of `inner._agent = agent`.

### 3. Define WorkspaceAware protocol + update_workspace() (2 suppressions)
- Define `WorkspaceAware` Protocol in src/owlbear/tools/protocols.py (new file) with `update_workspace(self, workspace: Path) -> None`.
- Implement `update_workspace()` on: TerminalToolset (sets _workspace_root), GitLocalToolset (sets _workspace_root), FileToolset (sets _root to workspace.resolve()), KnowledgeToolset (sets _root to workspace.resolve()), KnowledgeSourceToolset (sets _workspace_root), RefreshOrchestrator (sets _workspace_root).
- Update _update_toolset_roots() in src/owlbear/projects/toolset.py to use `isinstance(inner, WorkspaceAware)` + `inner.update_workspace(workspace)` instead of hasattr checks for _workspace_root/_root. Remove both noqa: SLF001 lines.
- Subsumes #522 (closed as duplicate).

### 4. Add GraphStore.merge_entities() (5 suppressions)
- In src/owlbear/memory/knowledge/graph.py: add `merge_entities(self, canonical_id: str, duplicate_ids: Sequence[str], merged_metadata: dict[str, object]) -> int` that encapsulates: update canonical metadata, redirect edges (source_id + target_id) from each duplicate to canonical, delete duplicates, commit. Return count merged.
- Update src/owlbear/memory/knowledge/dedup.py: replace raw SQL block (lines 124-147) with `graph.merge_entities(canonical.id, [d.id for d in duplicates], merged_meta)`. Remove all 5 noqa: SLF001 lines.

### Verification AC
- [ ] `uv run ruff check src/ --select SLF001` returns 0 violations
- [ ] `uv run ruff check tests/ --select SLF001` returns 0 violations (update test references)
- [ ] All existing tests pass (`uv run pytest -q --tb=short`)
- [ ] No new noqa suppressions added anywhere
- [ ] WorkspaceAware protocol is runtime-checkable (`@runtime_checkable`)

TDD note: This is a pure refactoring  no new behavior. Existing test suite is the verification harness. Builder must run tests before and after to confirm no regressions.
