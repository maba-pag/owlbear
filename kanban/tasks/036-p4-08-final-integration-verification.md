---
id: 36
title: 'P4-08: Final integration verification'
status: ideation
priority: critical
created: 2026-02-24T15:16:35.3534616+01:00
updated: 2026-02-26T18:59:02.4210106+01:00
tags:
    - phase-4
    - test
    - tooling
depends_on:
    - 11
    - 33
    - 34
    - 35
    - 15
class: standard
---

## Research required (gate: ideation to backlog)

1. **Theoretical validity** - N/A, verification task
2. **Prior art** - N/A, verification task
3. **Technical feasibility** - N/A, verification task
4. **Architecture fit** - Define scope: this verifies P4 (auth/provider) only, not P3 hooks/agents
5. **Implementation approach** - Checklist-based verification

## AC (P4-scoped only)
Full end-to-end verification of Copilot OAuth and provider integration:
1. uv sync -- no errors
2. uv run pytest tests/ -m 'not api' --tb=short -q -- all tests pass
3. uv run ruff check src/ tests/ -- zero lint errors
4. uv run bearclaw auth status -- prints 'not found' or token status
5. uv run python -c 'from owlbear.auth.copilot import request_device_code' -- importable
6. uv run python -c 'from owlbear.providers.copilot import CopilotProvider' -- importable
7. Coverage >= 90%
If anything fails, create follow-up fix tasks.
