---
id: 1154
title: Implement static tests for M3.5 proposal-round contracts
status: todo
priority: important
created: 2026-04-28T01:02:59.048361+00:00
updated: 2026-04-28T01:33:06.215625+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\n\nAdd a `TestFromAC_ProposalRoundContracts` class to `tests/test_ideation_overhaul_static.py` covering M3.5 proposal-round contract surfaces.\n\nSee `.owlbear/research/1153-m3-5-static-coverage.md` for full analysis.\n\n## Acceptance Criteria\n\n1. New `TestFromAC_ProposalRoundContracts` class in `tests/test_ideation_overhaul_static.py`\n2. Tests verify: panel handbook Propose Mode section, proposal sections, Critic skip, Pragmatist mode=compare, mediation Step 1.5, M3.5/Step 2 mutual exclusivity, panelist agent PROPOSE mode (parametrized x4), pragmatist agent mode=compare, blackboard proposal artifacts\n3. All tests pass\n4. No existing tests broken\n\n## Affected Files\n\n- `tests/test_ideation_overhaul_static.py` (edit only)
[[2026-04-28]]
## Research\n- Research doc: .owlbear/research/1153-m3-5-static-coverage.md (validation pass — all 7 contract surfaces confirmed current)\n- Sources: 8 studied (from parent #1153), 5 high-relevance (.90+)\n- Recommendation: Add TestFromAC_ProposalRoundContracts class to existing test file with parametrized panelist checks (confidence: .88)\n- Follow-up tasks created: none needed — this IS the implementation task, ready for architect\n- Decision requests: none (T1 autonomous — test coverage for existing contracts)\n- Tier: T1\n\n## Validation Results\nAll 15 contract needles verified present in source files (2026-04-28). No drift from research doc #1153.\n\n## Challenge Results\n- Challenger: SKIPPED — trivial/info-only research (test placement recommendation, no architectural choice)\n- Confidence in original: .88
[[2026-04-28]]
## Architecture Review\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | One class in one file covering M3.5 proposal-round contracts |\n| Interface clarity | PASS | AC enumerates all 10 contract surfaces; research doc maps to specific test methods and needle strings |\n| Dependency correctness | PASS | Depends on #1148 contracts being in place — verified all 7 source-file surfaces present via grep |\n| Module layering | PASS | Test file only; no src imports, uses _read() helper pattern from existing file |\n| TDD compliance | PASS | Task IS test code; test-writer writes the test class directly |\n| KISS/YAGNI | PASS | Straightforward string-presence assertions matching established pattern |\n| Premise challenge | PASS | Zero existing M3.5 coverage confirmed; existing file covers Phase 1 only |\n| Pattern consistency | PASS | Follows TestFromAC_* naming, _read() helper, parametrize for 4-agent check |\n| Security surface | N/A | No system boundaries |\n| Single domain | PASS | Ideation test coverage only |\n\n### Challenge Results\n- Challenger: reconsider (confidence 0.42)\n- Challenges: (1) pass-through tag incorrect for Python test code, (2) \"7 surfaces\" vs AC enumeration, (3) \"15 needles\" traceability\n- Architect response: Accepted (1) — no pass-through tag added; test-writer writes the test class, assertions pass immediately since contracts exist. Rebutted (2)(3) — both reference the research body section, not the AC; AC line 2 explicitly enumerates all surfaces including blackboard artifacts.\n\n### Verdict: APPROVE\n### Action Taken: Advanced to todo. No tags added — task produces executable Python test code, standard TDD flow applies.