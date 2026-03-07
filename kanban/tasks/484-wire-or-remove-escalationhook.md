---
id: 484
title: Wire or remove EscalationHook
status: archived
priority: important
created: 2026-03-04T07:38:01.1970371+01:00
updated: 2026-03-07T18:07:53.8074603+01:00
started: 2026-03-06T19:26:41.4864849+01:00
completed: 2026-03-07T18:07:53.8074603+01:00
tags:
    - audit
    - yagni
    - hooks
    - scope:core
class: standard
---

YAGNI-02/INT-03: EscalationHook is fully implemented and tested but never imported or registered in bootstrap.py. Orphan code. Decision: DELETE (.85 confidence). See docs/escalation-hook-research.md.

## Acceptance Criteria

Delete all EscalationHook code, tests, and documentation references. No functional behavior changes (code was never wired).

### Files to delete

- [ ] `src/owlbear/core/escalation.py` — entire module (EscalationHook, EscalationAction, ~131 LOC)
- [ ] `tests/test_escalation.py` — dedicated test file

### Files to edit

- [ ] `tests/test_error_recovery.py`:
  - Remove `from owlbear.core.escalation import EscalationAction, EscalationHook` (line 25)
  - Remove module docstring reference to `owlbear.core.escalation` (line 6)
  - Remove helper `_make_channel` (lines 46-51) — only used by EscalationHook tests
  - Remove `class TestOnErrorEdgeCases` (lines ~148-207) — 6 tests exercising `_on_error`
  - Remove `class TestParseResponseEdgeCases` (lines ~212-237) — 7 tests exercising `_parse_response`
- [ ] `.github/copilot-instructions.md`:
  - Safety row: remove `` `EscalationHook` wires ON_ERROR to user prompt (retry/skip/abort) when retries exhausted; `` from the Safety cell
- [ ] `docs/architecture.md`:
  - Remove directory listing line: `escalation.py  # EscalationHook (ON_ERROR -> user prompt)` (line 101)

### Verification

- [ ] `uv run ruff check src/ tests/` — clean (no F811/F401 from removed imports)
- [ ] `uv run pytest -q --tb=short` — all remaining tests pass
- [ ] `grep -r "EscalationHook" src/` — zero matches
- [ ] `grep -r "from owlbear.core.escalation" src/ tests/` — zero matches

### Out of scope

- Do NOT edit audit/research docs (`docs/escalation-hook-research.md`, `docs/architecture-audit.md`, `docs/software-design-audit.md`, `docs/integration-audit.md`, `docs/executive-audit-report.md`, `docs/error-message-sanitization-research.md`). These are historical records and remain accurate as-is.
- Do NOT delete `docs/escalation-hook-research.md` — it documents the decision rationale.

### Patterns to follow

- When removing test classes from `test_error_recovery.py`, preserve the section comment structure (numbered `# ===` blocks). Renumber remaining section headers if needed.
- `_make_channel` helper is ONLY used by the EscalationHook test classes. Delete it (lines 46-51).

See `docs/escalation-hook-research.md` for full analysis.
