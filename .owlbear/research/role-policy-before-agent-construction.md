# Apply Role Policy Before Agent Construction

> **Owning task:** #561 — Apply role policy before Agent construction to avoid double-build
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Code-quality audit finding F-20 identified that `AgentRegistry._build_agent()` constructs **two** `Agent` instances when `role != BUILDER`. The first Agent is built with unfiltered toolsets, then immediately discarded when a second Agent is built with filtered toolsets. The question: can we safely apply `apply_role_policy` to toolsets *before* the first Agent construction, eliminating the wasteful double-build?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PydanticAI Agent constructor docs | <https://ai.pydantic.dev/agents/> | .90 |
| 2 | PydanticAI Toolsets → FilteredToolset | <https://ai.pydantic.dev/toolsets/#filtering-tools> | .95 |
| 3 | OwlBear `agent_registry.py` L170-199 | `src/owlbear/core/agent_registry.py` | 1.0 |
| 4 | OwlBear `roles.py` — `apply_role_policy` | `src/owlbear/core/roles.py` | 1.0 |
| 5 | OwlBear `code-quality-audit.md` F-20 | `docs/code-quality-audit.md` L254-265 | 1.0 |
| 6 | OwlBear `validator-role-policy.md` | `docs/research/validator-role-policy.md` | .80 |

## 3. Current Code Analysis

The problematic method in `agent_registry.py` L170-199:

```python
def _build_agent(self, defn):
    model = defn.model or self._default_model
    toolsets = [self._resolve_tool(t) for t in defn.tools]  # resolve
    if self._skill_registry and defn.skills:
        toolsets.append(self._skill_registry)
    agent = Agent(model, instructions=..., toolsets=toolsets)  # BUILD 1
    role_str = defn.role.lower()
    if role_str != AgentRole.BUILDER:
        policy = _ROLE_POLICIES.get(AgentRole(role_str), BUILDER_POLICY)
        if policy.denied_tools:
            filtered = [apply_role_policy(ts, policy) for ts in toolsets]
            agent = Agent(model, instructions=..., toolsets=filtered)  # BUILD 2
    return agent
```

**BUILD 1** is always executed. **BUILD 2** replaces it for all non-builder roles. Three agents currently declare `role: validator` (architect, closer, reviewer) — each gets double-built on first `registry.get()`.

## 4. Analysis

| Criterion | Keep double-build | Filter before construction (.90) |
|-----------|-------------------|----------------------------------|
| Correctness | Both produce same Agent | Same — toolsets identical either way |
| Performance | 2x Agent `__init__` overhead | 1x construction per agent |
| Code clarity | Confusing — reader expects first Agent to be used | Clear linear flow |
| Side effects | Agent `__init__` is pure (no I/O) — wasted but harmless | Eliminates waste |
| Risk | None (status quo) | Very low — reorder only, no new logic |
| Test impact | Existing test passes but doesn't verify single-build | Can add assertion |
| KISS/YAGNI | Violates KISS — unnecessary complexity | Aligns with KISS |

### Why the double-build is NOT intentional

1. The first Agent is never used — the variable `agent` is immediately reassigned.
2. The `roles.py` module docstring itself shows the intended pattern: filter first, then construct.
3. PydanticAI's `FilteredToolset` (via `toolset.filtered()`) is designed to be composed *before* Agent construction, not as a post-hoc patch.

### Why this is safe to change

1. **Agent `__init__` is stateless** — no I/O, no side effects, no registration. Constructing one fewer Agent is purely a performance/clarity improvement.
2. **`apply_role_policy` is a pure function** — it returns a `FilteredToolset` wrapping the original. It doesn't mutate the input toolset.
3. **Toolset resolution order is unchanged** — tools are resolved first, then filtered. The filtering just moves up 3 lines.
4. **BUILDER_POLICY has empty `denied_tools`** — for builder role, `apply_role_policy` returns the toolset unchanged. So applying it unconditionally for all roles is a no-op for builders.

## 5. Recommendation (.95 confidence)

**Move `apply_role_policy` before `Agent()` construction.** The fix is a ~10-line rewrite of `_build_agent`:

```python
def _build_agent(self, defn):
    model = defn.model or self._default_model
    toolsets = [self._resolve_tool(t) for t in defn.tools]
    if self._skill_registry and defn.skills:
        toolsets.append(self._skill_registry)
    # Apply role-based filtering before construction.
    role_str = defn.role.lower()
    policy = _ROLE_POLICIES.get(AgentRole(role_str), BUILDER_POLICY)
    if policy.denied_tools:
        toolsets = [apply_role_policy(ts, policy) for ts in toolsets]
    return Agent(model, instructions=defn.system_prompt or None, toolsets=toolsets)
```

**Alternative considered:** Apply `apply_role_policy` unconditionally (drop the `if policy.denied_tools` guard). This is cleaner but wraps builder toolsets in a trivial `FilteredToolset`. The guard is cheap and idiomatic — keep it.

## 6. Testing Strategy

- Modify existing `test_get_applies_role_policy_for_non_builder` to assert only one `Agent()` call (mock `Agent` constructor, verify call count = 1).
- Add a test verifying builder agents also produce exactly one `Agent()` call.
- Existing integration tests (`test_bootstrap_integration.py`) cover end-to-end.

## 7. Follow-up Tasks

See commands below — NOT executed, presented for review.
