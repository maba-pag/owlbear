# Role System Complexity Evaluation — Keep vs Simplify

> **Owning task:** #565 — Evaluate role system complexity for 2 roles
> **Date:** 2026-03-07  **Status:** Complete

## 1. Context and Question

The software-design-audit (YAGNI-03) flagged `roles.py` as potentially over-engineered: an `AgentRole` enum, `RolePolicy` dataclass, `apply_role_policy()` function, and two policy constants exist to express "validators cannot use `write_file` and `create_file`." Is this justified, or should it be simplified?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PydanticAI Toolsets — FilteredToolset | <https://ai.pydantic.dev/toolsets/#filtering-tools> | .95 — framework's native tool-filtering API |
| 2 | PydanticAI Agents docs | <https://ai.pydantic.dev/agents/> | .70 — agent construction, no built-in role concept |
| 3 | CrewAI Agents docs | <https://docs.crewai.com/concepts/agents> | .75 — `tools` per-agent, no role-based restriction layer |
| 4 | OwlBear `roles.py` | `src/owlbear/core/roles.py` | 1.0 — the code under evaluation |
| 5 | OwlBear `agent_registry.py` | `src/owlbear/core/agent_registry.py` L186-200 | 1.0 — sole consumer of role system |

## 3. Current State — LOC Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `src/owlbear/core/roles.py` | 70 | Enum, dataclass, function, 2 constants |
| `tests/test_roles.py` | 195 | 10+ test cases for role policies |
| `agent_registry.py` (role lines) | ~12 | Import, dict, if-block in `_build_agent` |
| **Total** | **~277** | Entire role subsystem |

Agents using `role: validator`: architect, closer, reviewer (3 of 8).
Agents using `role: builder`: builder, kanban-planner, orchestrator, researcher, writer (5 of 8).

## 4. Analysis — How Peers Handle This

| Criterion | PydanticAI (native) | CrewAI | OwlBear (current) |
|-----------|--------------------|---------|--------------------|
| Role concept | None — no built-in role | `role` is a prompt string, not an access-control concept | `AgentRole` enum (builder/validator) |
| Tool restriction | `toolset.filtered(fn)` inline | Pass different `tools=[]` per agent | `RolePolicy` + `apply_role_policy` |
| Infrastructure LOC | 0 (caller writes 1-line lambda) | 0 (tools list is per-agent) | 70 + 195 test = 265 |
| Extensibility | Add another `.filtered()` call | Add/remove tools from list | Add enum member + policy constant |

**Key finding:** Neither PydanticAI nor CrewAI have a "role" abstraction for tool access. Both use direct per-agent tool lists. PydanticAI's `toolset.filtered()` is a 1-line call that replaces the entire `apply_role_policy` function.

## 5. Trade-off Matrix — Keep vs Simplify

| Criterion | Keep (.45) | Simplify (.80) |
|-----------|-----------|----------------|
| **KISS** | Low — 277 LOC for a 2-element deny-set | High — inline `filtered()` in `_build_agent` |
| **YAGNI** | Violates — no 3rd role planned | Aligns — build infra when needed |
| **Readability** | Clear but over-abstracted | Obvious at call site |
| **Extensibility** | Easy to add roles | Easy to add — just add another `.filtered()` |
| **Framework alignment** | Custom layer over PydanticAI | Uses PydanticAI's native `FilteredToolset` |
| **Risk** | None — works correctly | Low — 1-line behavioral equivalent |
| **Test burden** | 195 LOC of tests for trivial logic | Tests become simpler or unnecessary |
| **Migration effort** | None | Small — delete file, update registry, simplify tests |

## 6. Recommendation (.80 confidence) — Simplify

**Replace the role subsystem with inline `toolset.filtered()` calls in `_build_agent`.**

Rationale:

- The current system is correct but disproportionate (277 LOC for a 2-tool deny-list).
- PydanticAI's `toolset.filtered()` is the idiomatic way to restrict tools. OwlBear wraps it in 70 LOC of its own abstractions without adding value.
- No 3rd role is planned or on the roadmap. Per YAGNI, build the infra when you need it.
- The `role` field in `AgentDefinition` stays — it's a useful metadata label for prompts. Only the policy infrastructure is removed.
- Task #561 (apply policy before agent construction) becomes simpler with inline filtering — the double-construction bug goes away naturally.

**Simplified approach** — in `_build_agent`:

```python
# Deny write tools for non-builder roles (3 lines replaces entire roles.py)
_VALIDATOR_DENIED = frozenset({"write_file", "create_file"})

if defn.role.lower() != "builder":
    toolsets = [ts.filtered(lambda _ctx, td: td.name not in _VALIDATOR_DENIED) for ts in toolsets]
```

**Risk:** If a 3rd role with different restrictions is needed later, you'd extract the abstraction then. Until then, inline is simpler.

## 7. Follow-up Tasks

```bash
kanban\kanban-md.exe create "Simplify role system: replace roles.py with inline filtered() in _build_agent" --priority nice-to-have --status backlog --tags "refactor,yagni,scope:core" --body "Replace AgentRole enum, RolePolicy, apply_role_policy, BUILDER_POLICY, VALIDATOR_POLICY with inline toolset.filtered() call. See docs/role-system-complexity-research.md. AC: (1) roles.py deleted, (2) _build_agent uses inline filtered() for non-builder roles, (3) test_roles.py replaced with simpler test in test_agent_registry.py, (4) all existing tests pass, (5) __init__.py exports cleaned up. Depends on: #561 (apply role policy before construction)."

kanban\kanban-md.exe create "Keep role field in AgentDefinition as metadata-only label" --priority nice-to-have --status backlog --tags "refactor,scope:core" --body "After role infrastructure removal, ensure role field in AgentDefinition still works as a prompt/metadata label. No behavioral change needed. AC: (1) role field present in AgentDefinition, (2) agent .md files still declare role:, (3) no policy infrastructure references remain."
```
