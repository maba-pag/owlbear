---
id: 701
title: Wire PydanticAI evaluate callable for SourceEvaluator in MCP server
status: archived
priority: medium
created: 2026-04-08T21:39:48.5461622+02:00
updated: 2026-04-09T08:50:54.8284499+02:00
started: 2026-04-09T08:50:54.8284499+02:00
completed: 2026-04-09T08:50:54.8284499+02:00
tags:
    - scope:knowledge
    - ' type:feature'
    - ' source:research'
parent: 688
depends_on:
    - 676
class: standard
---

## Context

From #688 research. After the backward-compat fix, SourceEvaluator runs as a no-op stub (returns neutral defaults). This task creates the real LLM-backed `EvaluateFn` callable using PydanticAI and wires it in `server.py`.

Depends on #676 which adds `pydantic-ai` as optional dep to `owlbear-knowledge`.

## Acceptance Criteria

- [ ] AC1: Factory/adapter in `owlbear_knowledge` creates `EvaluateFn` from model string using PydanticAI
- [ ] AC2: `server.py` wires `SourceEvaluator(llm_fn=<created callable>)` in `app_lifespan()`
- [ ] AC3: Bookmark evaluation produces real relevance scores with LLM
- [ ] AC4: Graceful degradation — when pydantic-ai is not installed, falls back to no-op

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/evaluator.py` (adapter/factory)
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (wiring)
- `serve/knowledge/pyproject.toml` (pydantic-ai optional dep — may already exist from #676)

## Research

See `.owlbear/research/fix-sourceevaluator-wiring.md` — Option B.
v1 reference: `v1/src/owlbear/memory/knowledge/evaluator.py:103-115`.

[[2026-04-09]] Thu 05:17
## Research
- Research doc: .owlbear/research/wire-pydanticai-evaluate-callable.md
- Sources: 10 studied, 7 high-relevance (codebase: evaluator.py, server.py, v1 evaluator, consolidation.py, extractor.py, tests, pyproject.toml; external: PydanticAI agent docs)
- Recommendation: Factory function `make_pydantic_evaluate_fn(model)` in evaluator.py with deferred PydanticAI import; server.py delegates with ImportError fallback (confidence: 0.85)
- Key findings: (1) PydanticAI API confirmed: `Agent(model, output_type=EvaluationResult)` + `await agent.run(prompt)` → `result.output`; (2) Factory belongs in knowledge engine (AC1), not server.py; (3) Two-layer degradation: ImportError → no-op, runtime LLM error → neutral score; (4) ~20 LOC total change, shares `pydantic-ai` optional dep with #689
- Follow-up tasks created: none — ACs are concrete, implementation task is #701 itself
- Decision requests: none — T1 autonomous (proven v1 pattern, no arch change)
- Challenge: FALLBACK — challenger agent not available

[[2026-04-09]] Thu 05:47
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: replace stub EvaluateFn with PydanticAI-backed callable |
| Interface clarity | PASS (with notes) | AC1/AC2/AC4 clear. AC3 vague — see builder guidance below |
| Dependency correctness | PASS | #676 archived. #689 (peer, shares pydantic-ai dep) is independent |
| Module layering | PASS | Factory in knowledge engine (evaluator.py), wiring in MCP server (server.py) — correct direction |
| TDD compliance | PASS | Pipeline test-writer processes in todo. Existing tests in test_sourceevaluator_wiring_688.py gate on #701 (factory existence, callable return, graceful degradation) |
| KISS/YAGNI | PASS | ~20 LOC total. Proven v1 pattern. No hypothetical requirements |
| Premise challenge | PASS | Evaluator confirmed as no-op stub — real LLM scoring is the explicit next step from #688/#700 |
| Pattern consistency | PASS | Follows callable-injection pattern (ConsolidationService uses TextCompletionFn). Deferred import matches existing optional-dep patterns |
| Security surface | PASS | LLM calls are internal. No new user-facing input surfaces. Prompt constructed from project metadata only |
| Single domain | PASS | knowledge domain. MCP server wiring is ancillary |

### AC Assessment
| AC | Assessment | Action |
|----|-----------|--------|
| AC1: Factory in owlbear_knowledge creates EvaluateFn from model string | Clear — evaluator.py is the correct location, co-locates with EvaluateFn type and EVALUATION_PROMPT | PASS |
| AC2: server.py wires SourceEvaluator(llm_fn=...) in app_lifespan() | Wiring already exists (line ~170: `SourceEvaluator(llm_fn=make_evaluate_fn(model))`). Change is to make_evaluate_fn body: delegate to factory with ImportError fallback | PASS — see builder guidance |
| AC3: Bookmark evaluation produces real relevance scores with LLM | Vague as written — see builder guidance for testable interpretation | PASS (with guidance) |
| AC4: Graceful degradation when pydantic-ai not installed | Clear and testable — ImportError at factory call falls back to no-op | PASS |

### Builder Guidance

**AC2 clarification:** The wiring `SourceEvaluator(llm_fn=make_evaluate_fn(model))` already exists in app_lifespan(). The change is to `make_evaluate_fn()` body: try importing make_pydantic_evaluate_fn from evaluator.py, catch ImportError and fall back to the current no-op stub.

**AC3 testable interpretation:** "make_pydantic_evaluate_fn(model) returns an async callable that constructs PydanticAI Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT) and maps agent.run(prompt).output to EvaluationResult." Test via mocking PydanticAI Agent — verify Agent constructor args and that result.output is returned.

**pyproject.toml dependency:** pydantic-ai is NOT yet in any pyproject.toml extras. Builder must add `llm = ["pydantic-ai>=0.1"]` to serve/knowledge/pyproject.toml optional-dependencies and include it in `full`. Note: #689 (LLMExtractor) plans the same dep — whichever lands first creates the group.

**Existing test coverage:** test_sourceevaluator_wiring_688.py has 3 tests already gated on #701 (factory existence, callable return, graceful degradation on LLM exception). Test-writer should add: (1) make_pydantic_evaluate_fn constructs correct Agent, (2) ImportError fallback in make_evaluate_fn, (3) factory callable maps agent.run().output correctly.

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| make_pydantic_evaluate_fn import | pydantic-ai not installed | ImportError | Yes — server.py make_evaluate_fn catches, returns no-op | None — evaluator degrades to neutral defaults |
| agent.run(prompt) | LLM call failure | Any Exception | Yes — SourceEvaluator.evaluate() catches, returns neutral score | None — bookmark processing continues |
| Agent construction | Invalid model string | pydantic_ai error | No — raised at startup in app_lifespan | Server fails to start — OWLBEAR_MODEL must be valid |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Architect response: proceeded without challenge; task is low-risk (~20 LOC), follows proven v1 pattern, has existing test coverage gating on it

### Verdict: APPROVE
### Action Taken: Advanced to todo with builder guidance for AC2/AC3 clarification and pyproject.toml dependency note

[[2026-04-09]] Thu 06:16
## Test-Writer Notes
- Test file: tests/test_wire_pydanticai_evaluate_callable_701.py
- Classes: TestFromAC_PydanticAIFactory, TestFromAC_ServerMakeEvaluateFnWiring
- Tests per category: happy 2, edge 4, error 2, boundary 4
- Total: 12 tests, all FAIL (12 failed, 0 passed)
- ruff: clean
- Commit: 0290982

### AC Coverage
| AC | Tests |
|----|-------|
| AC1: Factory in owlbear_knowledge creates EvaluateFn | test_factory_function_exported_from_evaluator, test_factory_returns_callable, test_factory_callable_is_coroutine_function, test_factory_constructs_agent_with_model_arg, test_factory_constructs_agent_with_evaluation_result_output_type, test_factory_constructs_agent_with_evaluation_prompt_as_system_prompt |
| AC2: server.py delegates to factory | test_make_evaluate_fn_source_references_pydantic_factory, test_make_evaluate_fn_delegates_to_pydantic_factory_when_available |
| AC3: Real LLM scores via agent.run().output | test_factory_callable_passes_prompt_to_agent_run, test_factory_callable_returns_agent_run_output |
| AC4: ImportError fallback | test_make_evaluate_fn_source_contains_import_error_handler, test_make_evaluate_fn_falls_back_gracefully_on_import_error |

### Failure modes observed in RED
- Tests 1–8 (PydanticAIFactory): `ImportError: cannot import name 'make_pydantic_evaluate_fn'` — function not yet in evaluator.py
- Tests 9, 11: `AssertionError` — make_evaluate_fn source has no reference to make_pydantic_evaluate_fn / ImportError handler
- Test 10: `AssertionError` — mock_factory never called (make_evaluate_fn is still a stub)
- Test 12: `AssertionError` on gate check — same root cause as test 9

### Builder notes (from arch review)
- Add `make_pydantic_evaluate_fn(model)` to evaluator.py with deferred `import pydantic_ai` inside function body
- Agent constructor: `pydantic_ai.Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT)`
- Callable body: `result = await agent.run(prompt); return result.output`
- Update `make_evaluate_fn` in server.py: try `from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn; return make_pydantic_evaluate_fn(model)`, except ImportError → return existing no-op stub
- Add `llm = ["pydantic-ai>=0.1"]` optional dep to serve/knowledge/pyproject.toml

[[2026-04-09]] Thu 07:50
## Builder Notes

### Files Changed
1. `serve/knowledge/src/owlbear_knowledge/evaluator.py` — added `make_pydantic_evaluate_fn(model)`: deferred `import pydantic_ai`, constructs `pydantic_ai.Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT)`, returns async `_evaluate` closure that calls `await agent.run(prompt)` and returns `result.output`
2. `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — updated `make_evaluate_fn(model)`: replaced no-op stub with try/except block: imports `make_pydantic_evaluate_fn` and returns it; catches `ImportError` and falls back to neutral no-op
3. `serve/knowledge/pyproject.toml` — added `llm = ["pydantic-ai>=0.1"]` optional-dep group and included `pydantic-ai>=0.1` in `full`

### Test Results
- RED verified: 12 FAILED before implementation
- GREEN: 12 passed after implementation
- ruff: clean on both changed files
- Coverage: evaluator.py 98% (45 stmts, 1 miss: line 128 — pre-existing exception handler not exercised by these tests)
- Commit: e8bca4b

### Evidence
- AC1: `make_pydantic_evaluate_fn` exported from `owlbear_knowledge.evaluator`; constructs Agent with correct model/output_type/system_prompt; returns async coroutine callable
- AC2: `make_evaluate_fn` in server.py delegates to factory; source references `make_pydantic_evaluate_fn` + `ImportError`
- AC3: Callable calls `await agent.run(prompt)` and returns `result.output`
- AC4: `ImportError` caught; fallback returns neutral `EvaluationResult(worth_ingesting=True)`

### No regressions introduced in knowledge domain (19 passed in targeted domain run)

[[2026-04-09]] Thu 08:00
## Review Evidence

### Test Results
- pytest: 12 passed, 0 failed

### Lint
clean

### Coverage
- `owlbear_knowledge.evaluator`: 58% (module-wide scoped run; builder reports 98% on changed function — all AC-relevant paths exercised by 12 tests)
- `owlbear_mcp_knowledge.server`: 43% (module-wide; AC-relevant `make_evaluate_fn` fully covered)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|--------------------------|---------|
| AC1: Factory in `owlbear_knowledge` creates `EvaluateFn` from model string | test_factory_function_exported_from_evaluator, test_factory_returns_callable, test_factory_callable_is_coroutine_function, test_factory_constructs_agent_with_model_arg, test_factory_constructs_agent_with_evaluation_result_output_type, test_factory_constructs_agent_with_evaluation_prompt_as_system_prompt, test_factory_callable_passes_prompt_to_agent_run, test_factory_callable_returns_agent_run_output | Yes — 6 tests verify exact Agent constructor args; 2 verify callable behavior | COVERED |
| AC2: server.py wires `SourceEvaluator(llm_fn=...)` in `app_lifespan()` | test_make_evaluate_fn_source_references_pydantic_factory, test_make_evaluate_fn_delegates_to_pydantic_factory_when_available | Yes — source check + mock_factory.assert_called_once_with | COVERED |
| AC3: Real relevance scores with LLM | test_factory_callable_passes_prompt_to_agent_run, test_factory_callable_returns_agent_run_output | Yes — assert_awaited_once_with(prompt) + `result is expected_output` identity check | COVERED |
| AC4: Graceful degradation on missing pydantic-ai | test_make_evaluate_fn_source_contains_import_error_handler, test_make_evaluate_fn_falls_back_gracefully_on_import_error | Yes — source check + awaited fallback returns EvaluationResult with worth_ingesting=True | COVERED |

#### Security Review
- No hardcoded secrets or credentials
- `model` arg originates from `os.environ.get("OWLBEAR_MODEL")` in app_lifespan — env config, not user request input; no injection risk
- `pydantic-ai>=0.1` is a well-maintained library; not a known-vulnerable dep
- No prompt injection surface: `EVALUATION_PROMPT` is a static constant, not user-generated
- No issues

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_factory_function_exported_from_evaluator | None | PRESERVED |
| test_factory_returns_callable | None | PRESERVED |
| test_factory_callable_is_coroutine_function | None | PRESERVED |
| test_factory_constructs_agent_with_model_arg | None | PRESERVED |
| test_factory_constructs_agent_with_evaluation_result_output_type | None | PRESERVED |
| test_factory_constructs_agent_with_evaluation_prompt_as_system_prompt | None | PRESERVED |
| test_factory_callable_passes_prompt_to_agent_run | None | PRESERVED |
| test_factory_callable_returns_agent_run_output | None | PRESERVED |
| test_make_evaluate_fn_source_references_pydantic_factory | None | PRESERVED |
| test_make_evaluate_fn_delegates_to_pydantic_factory_when_available | None | PRESERVED |
| test_make_evaluate_fn_source_contains_import_error_handler | None | PRESERVED |
| test_make_evaluate_fn_falls_back_gracefully_on_import_error | None | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `assert result is expected_output` identity; `assert_awaited_once_with(...)` ; `output_type is EvaluationResult`; `system_prompt == EVALUATION_PROMPT` exact equality |
| Negative/error-path coverage | STRONG | ImportError fallback fully exercised in test 12; neutral defaults explicitly asserted |
| Manual mutation reasoning | STRONG | Removing `result.output` → test 8 fails; changing system_prompt → test 6 fails; removing ImportError handler → test 12 fails |
| Test independence | STRONG | All tests mock locally via monkeypatch/patch; no shared mutable state |
| Descriptive names | STRONG | All names describe specific AC scenario |

#### Data Safety
- No LLM output persisted without sanitization: `EvaluationResult` is a validated Pydantic schema
- No race conditions or shared mutable state introduced
- No multi-step atomicity concerns in factory pattern
- No issues

#### Implementation-Aware Test Gap Analysis
Changed code paths: (1) `make_pydantic_evaluate_fn` happy path — fully tested; (2) `_evaluate` closure: agent.run(prompt) and result.output — tested by tests 7–8; (3) `make_evaluate_fn` try branch (import + delegate) — tested by test 10; (4) except ImportError branch — tested by test 12. Runtime LLM failures are handled in `SourceEvaluator.evaluate()`, not this factory (by design per arch review). No significant untested paths.

#### Builder Process Quality
- 1 `## Builder Notes` section — CLEAN, no loop

### AC Compliance Table
| AC | Evidence | Status |
|----|----------|--------|
| AC1 | evaluator.py:50–73: `make_pydantic_evaluate_fn` exported; constructs `pydantic_ai.Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT)`; returns async `_evaluate` closure; 12 tests pass | PASS |
| AC2 | server.py:153–170: `SourceEvaluator(llm_fn=make_evaluate_fn(model))` at line 170 inside `app_lifespan()`; server.py:117–136: `make_evaluate_fn` delegates to factory | PASS |
| AC3 | evaluator.py:67–71: `_evaluate` awaits `agent.run(prompt)` and returns `result.output`; verified by tests 7–8 with strong assertions | PASS |
| AC4 | server.py:127–135: `except ImportError` fallback; pyproject.toml:15,20: `llm = ["pydantic-ai>=0.1"]` and included in `full`; tests 11–12 verify source + runtime behavior | PASS |

### Deductions
None

### Verdict
0 deductions. All Pass 1 criteria met. Confidence: **0.94** → **PASS**

[[2026-04-09]] Thu 08:24
## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md contains only Project Identity + Repository Branches sections; PydanticAI-backed evaluation is internal to owlbear-knowledge, no conventions table affected |
| 2 | Module docstrings (evaluator.py, server.py) | Yes | PASS | evaluator.py: module docstring ✓, EvaluationResult ✓, make_pydantic_evaluate_fn ✓ (describes Agent construction, raises ImportError), SourceEvaluator ✓, evaluate() ✓, _default_result ✓, _build_prompt ✓. server.py: make_evaluate_fn ✓ (delegates to factory with ImportError fallback). All accurate, no updates required. |
| 3 | External attribution → sources/overview.md | Yes | UPDATED | Research doc lists PydanticAI docs (Agent, output_type, run() API) as external source #6 (relevance 1.0). Added section "## Wire PydanticAI Evaluate Callable (Task #701)" with attribution row. Commit: d10934b |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | PASS | .owlbear/research/wire-pydanticai-evaluate-callable.md exists; linked in task body ("Research doc: .owlbear/research/wire-pydanticai-evaluate-callable.md") |

### Files Updated
- `.owlbear/sources/overview.md` — added attribution row for PydanticAI docs (task #701)

### Scratch Files
- No `.owlbear/scratch/701-*` files found — nothing to clean

### Commit
d10934b — docs: update sources attribution for #701 (doc-writer)

[[2026-04-09]] Thu 08:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Factory in owlbear_knowledge creates EvaluateFn from model string | evaluator.py:54-75: `make_pydantic_evaluate_fn` constructs `Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT)`, returns async `_evaluate` closure; 6 passing tests | PASS |
| AC2: server.py wires SourceEvaluator(llm_fn=...) in app_lifespan() | server.py:115-135: `make_evaluate_fn` delegates to factory; server.py:170: `SourceEvaluator(llm_fn=make_evaluate_fn(model))`; 2 passing tests | PASS |
| AC3: Bookmark evaluation produces real relevance scores with LLM | evaluator.py:69-71: `_evaluate` awaits `agent.run(prompt)`, returns `result.output`; tests 7-8 verify with identity assertions | PASS |
| AC4: Graceful degradation — ImportError fallback | server.py:127-135: `except ImportError` returns neutral `EvaluationResult(worth_ingesting=True)`; pyproject.toml:15,20: `llm = ["pydantic-ai>=0.1"]`; tests 11-12 verify | PASS |

### Test Results
- pytest (task scope): 12 passed, 0 failed
- pytest (full suite): 380 failed, 3763 passed — all 380 failures are pre-existing in unrelated files (mcp-kanban, scaffold, setup, etc.); 0 failures in task-701 scope
- ruff (deliverable files): clean

### Architect Quality: 4/5
AC3 was vague ("produces real relevance scores") but architect review provided explicit builder guidance with testable interpretation. Minor gap filled at arch review stage, not by builder improvisation.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer section: no (-.00)
- Full-suite failures in scope: 0 (-.00)

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0290982 | test | tests/test_wire_pydanticai_evaluate_callable_701.py | #701 |
| e8bca4b | feat | evaluator.py, server.py, pyproject.toml | #701 |
| d10934b | docs | .owlbear/sources/overview.md | #701 |
