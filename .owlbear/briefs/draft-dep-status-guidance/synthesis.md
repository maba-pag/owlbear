# Synthesis — Dep-Status Guidance in start_work

## Panel Convergence

Architecture and user-experience reviews (both 0.82 confidence) fully converged on a single design with no tensions.

| Decision Point | Architecture | User Experience |
|----------------|-------------|-----------------|
| Helper vs. inline | Inline — 2 consumers below threshold | — |
| Placement | After claim — skip I/O on failure paths | — |
| Guidance wording | Format is wire contract — pin in tests | Keep proposed text; advisory tone matches channel |
| Emoji | — | Use ⚠️ (U+26A0 + U+FE0F) for consistency |

## Critic Validation (O15)

Critical review at high pressure (0.38 confidence in its own challenges). All 6 findings classified as **minor**:

1. "Confirm with the user" undefined for depth ≥2 agents → primary trigger (manual assignment) has user present; advisory nature handles rare case gracefully
2. Claim before warning → explicit design intent (D4)
3. No machine-readable dep_status → explicitly out of scope (D3)
4. Same message for different blocked conditions → addressed by generic "unresolved" label + dep IDs as escape hatch
5. Hot-path performance → negligible for disk-bound kanban ops with ≤3 deps
6. Other guidance producers exist → factual correction noted; pattern unchanged

## Factual Corrections

- Research notes incorrectly stated `_skip_transition_guidance()` is the "only existing guidance producer." `create_task`, `edit_task`, and `end_work` also produce guidance.
- Design is unaffected — same pattern regardless of producer count.
