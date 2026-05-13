---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Adopt boundary test + validation hardening (T1 items only)"
notes: ""
# >> Agent metadata (do not edit)
task_id: 429
agent: researcher
created: 2026-04-01
urgency: blocking
decision_type: approach-selection
impact_tier: 3
---

# Decision: Which deer-flow patterns should OwlBear adopt?

## Context

Task #429 surveyed deer-flow's architecture, context engineering, guardrails, and tooling patterns (excluding memory/subagent delegation per #428). Of 12 areas evaluated, 5 patterns have adoption potential. This decision request asks which patterns to pursue.

Full analysis: `docs/research/deer-flow-broad-survey.md`
Prior rapid survey: `docs/research/deer-flow-adoptable-patterns.md` (#386)

Already adopted from prior research: loop detection (#432), tool error handling (#433), dispatch trace ID (#434).

## Options

### A: Adopt boundary test + validation hardening only ← (rec:) recommended

Adopt only the two T1 patterns with highest confidence and lowest risk:

1. **Package boundary enforcement test** (.80 confidence, ~1 day) — AST-based test that prevents cross-package imports. Proven in deer-flow CI. Prevents silent architectural coupling between OwlBear packages.
2. **Skill validation hardening** (.75 confidence, ~0.5 day) — Enhance `validate_skills.py` with hyphen-case naming, max length, description safety checks per deer-flow patterns.

- Effort: ~1.5 days, 2 tasks
- Trade-off: conservative scope; defers context summarization and guardrail work
- Risk: minimal — pure tooling additions, no behavioral changes

### B: Adopt A + investigate context summarization — (bp:) best practice

Includes everything in A, plus:

3. **Research VS Code context management** (.65 confidence, ~1 day research) — Determine what VS Code does natively for context window management before building custom summarization.
4. **If gap found, implement orchestrator summarization** (~2 days extra) — Configurable triggers for context reduction in long dispatch sessions.

- Effort: ~3.5-5.5 days, 3-4 tasks
- Trade-off: addresses long-session context bloat but may duplicate VS Code's built-in handling
- Risk: research may reveal VS Code already handles this adequately → wasted effort

### C: Full adoption (A + B + guardrail protocol prototype)

Includes everything in B, plus:

5. **Prototype GuardrailProvider pattern** (.55 confidence, ~3 days) — Implement Request/Decision dataclass protocol for future tool-call authorization.

- Effort: ~6.5-8.5 days, 5-6 tasks
- Trade-off: builds infrastructure for a need that doesn't exist yet (YAGNI risk)
- Risk: premature abstraction; OwlBear doesn't execute arbitrary code

### D: Defer / do nothing

- Effort: 0
- Trade-off: existing validation gaps persist; no boundary enforcement
- Risk: cross-package coupling accumulates silently; skill naming drifts

## Recommendation

.80 confidence — **Option A**. The two T1 patterns are high-value, low-risk, KISS-aligned improvements to existing infrastructure. Context summarization (Option B) is interesting but requires research to determine if VS Code already handles it. The guardrail protocol (Option C) is premature per YAGNI.

## Impact of Deferral

Task #429 is blocked. T3 impact tier — no auto-resolve. If Option A is approved, 2 follow-up tasks will be created at `ideation`. If B or C, additional research/implementation tasks created accordingly.
