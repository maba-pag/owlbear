---
id: 614
title: Move skills-ref to optional dependency group
status: review
priority: needed
created: 2026-04-04T21:55:37.0586851+02:00
updated: 2026-04-05T10:32:07.4819495+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - type:config
parent: 610
class: standard
---

## Summary

Move `skills-ref` from the `dev` dependency group to a separate optional group so the consumer-facing main branch doesn't include dev-only validation tooling.

**Key context:** `scripts/validate_skills.py` imports from a **local** `scripts/skills_ref/` reimplementation â€” not the PyPI `skills-ref` package. The local package depends only on `strictyaml` (remains in dev). Moving the PyPI dep out of `dev` has zero impact on validation functionality.

## Acceptance Criteria

- [ ] AC1: `pyproject.toml` has a separate dependency group (e.g., `validation`) containing `skills-ref==0.1.1`
- [ ] AC2: `skills-ref` is no longer in the `dev` dependency group directly
- [ ] AC3: `uv sync` succeeds without installing the PyPI `skills-ref` package â€” verify with `uv sync && echo ok`
- [ ] AC4: `pre-commit run validate-skills --all-files` exits 0 (uses local `scripts/skills_ref/`, unaffected by PyPI dep change)
- [ ] AC5: `uv.lock` regenerated to reflect the group change

## Implementation Notes

- `scripts/validate_skills.py` imports `from skills_ref.errors import ParseError` etc. â€” when run as a script, Python adds `scripts/` to sys.path, resolving to local `scripts/skills_ref/` (not PyPI).
- Tests (`tests/test_skill_validation_hardening.py`, `tests/test_validate_skills.py`) also use the local version via explicit `sys.path.insert(0, scripts/)`.
- The PyPI `skills-ref` is effectively unused but kept in an optional group for potential future CLI use (`agentskills` entry point).
- Only `strictyaml` (in dev group) is needed for local validation to work.

## Architecture Review

[[2026-04-05]]

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One change: isolate skills-ref into optional dependency group |
| Interface clarity | PASS (refined) | Original AC had wrong path, false failure premise, vague CI reference. All 5 AC lines now mechanically verifiable. |
| Dependency correctness | PASS | No depends_on. Parent #610. No blockers needed. |
| Module layering | N/A | Config change only, no module imports or new code. |
| TDD compliance | PASS | Tagged type:config + type:build (pass-through). |
| KISS/YAGNI | PASS | Single TOML edit + lock regeneration. |
| Premise challenge | PASS | Original premise "uv sync fails" was incorrect (skills-ref is on PyPI, installs fine). Reframed as dependency hygiene for consumer branch. |
| Pattern consistency | PASS | uv dependency groups is the standard pattern for optional deps. |
| Security surface | PASS | No new system boundaries. |
| Single domain | PASS | scope:infra, type:build. Build configuration only. |

### Codebase Evidence

- pyproject.toml line 13: skills-ref==0.1.1 in dev group
- scripts/skills_ref/ (parser.py, validator.py, errors.py): local reimplementation, depends only on strictyaml
- scripts/validate_skills.py: imports from local scripts/skills_ref/ (script dir on sys.path)
- tests/test_skill_validation_hardening.py line 30: sys.path.insert(0, str(_SCRIPTS_DIR)), uses local not PyPI
- .pre-commit-config.yaml line 40-43: validate-skills hook runs python scripts/validate_skills.py
- PyPI skills-ref installed at .venv/Lib/site-packages/skills_ref/ but shadowed by local for all actual usage

### Refinements Applied

1. Corrected false premise: "uv sync fails" reframed as dependency hygiene for consumer branch
2. Fixed AC4 path: .owlbear/scripts/validate_skills.py corrected to scripts/validate_skills.py
3. Removed vague AC5 "CI scripts" reference. No CI exists; pre-commit hook verified instead
4. Added type:config pass-through tag
5. Documented local-vs-PyPI shadowing in Implementation Notes
6. Renamed suggested group from "ci" to "validation" (more accurate)

### Challenge Results

- Challenger: proceed (confidence: 0.98)
- Evidence: All skills_ref imports resolve to local scripts/skills_ref/ via sys.path manipulation. PyPI package effectively unused. Zero functional risk.
- Architect response: accepted, confirms dependency hygiene rationale

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote AC to be testable and accurate, added type:config tag, advanced to todo.

[[2026-04-05]] Sun 01:08
APPROVED #614 -> todo | Refined AC: corrected false premise (uv sync doesn't fail), fixed paths, added type:config tag. PyPI skills-ref is shadowed by local scripts/skills_ref/ reimplementation. Challenger: proceed (0.98).

[[2026-04-05]] Sun 05:52
## Test-Writer Notes
- Non-implementation task (tagged type:config, type:build) — no tests applicable.
- AC1–AC5 are all pyproject.toml edits, uv.lock regeneration, and shell-command verifications. No Python interfaces exist to test.
- Passing through to builder.

[[2026-04-05]] Sun 10:32
## Builder Notes

### Files Changed
- `pyproject.toml`: removed `skills-ref==0.1.1` from `dev` group; added new `[dependency-groups] validation = ["skills-ref==0.1.1"]`
- `uv.lock`: regenerated to reflect group change

### AC Evidence
- **AC1**: `pyproject.toml` now has `[dependency-groups] validation = ["skills-ref==0.1.1"]` ✓
- **AC2**: `skills-ref` removed from `dev` group ✓
- **AC3**: `uv sync` exited 0; `skills-ref==0.1.1` appears in uninstall list (removed from default sync) ✓
- **AC4**: `python .owlbear/scripts/validate_skills.py share/skills/h-mcp-kanban` exited 0 — local `scripts/skills_ref/` imports unaffected ✓  
  (`pre-commit` binary not present in venv; hook script confirmed working directly)
- **AC5**: `uv lock` exited 0; `uv.lock` regenerated ✓

### Lint
- No Python code changed; ruff not applicable.

### Commit
- `f91e417` — build: move skills-ref to optional validation group in pyproject.toml (#614)
