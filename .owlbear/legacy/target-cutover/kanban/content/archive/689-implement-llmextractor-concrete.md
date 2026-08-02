---
id: 689
title: Implement LLMExtractor concrete StructuredExtractor using PydanticAI
status: archived
priority: medium
created: 2026-04-08T21:06:19.8005764+02:00
updated: 2026-04-09T13:07:58.3495833+02:00
started: 2026-04-09T13:07:58.3495833+02:00
completed: 2026-04-09T13:07:58.3495833+02:00
tags:
    - scope:knowledge
    - ' type:feature'
    - ' source:research'
depends_on:
    - 698
class: standard
---

## Context

Research for #676 determined that PydanticAI is the right SDK for structured extraction. v1 used `Agent(model, output_type=ExtractionResult, system_prompt=EXTRACTION_PROMPT)` successfully. A concrete `StructuredExtractor` implementation is the missing piece that activates the knowledge graph.

## Acceptance Criteria

- [ ] AC1: `LLMExtractor` class in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` implementing `async def extract(self, prompt: str) -> ExtractionResult` satisfying the async `StructuredExtractor` protocol (post-#687)
- [ ] AC2: Uses `pydantic-ai` `Agent` with `result_type=ExtractionResult` and a dedicated extraction system prompt; calls `await agent.run(prompt)` in `extract()`
- [ ] AC3: System prompt enumerates all 6 `EntityType` values (file, function, class_, decision, pattern, concept) and all 7 `RelationType` values (defines, imports, depends_on, related_to, implements, documents, governed_by)
- [ ] AC4: `pydantic-ai` added as optional dependency in `serve/knowledge/pyproject.toml` under an `llm` extras group
- [ ] AC5: Graceful degradation — `extract()` catches `Exception` at the `agent.run()` boundary, logs the error, and returns empty `ExtractionResult()` (no exception propagation to callers)
- [ ] AC6: All RED-phase tests from #698 pass; builder may add supplementary tests for implementation details not covered by #698

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` (new)
- `serve/knowledge/pyproject.toml` (edit)
- `tests/test_llm_extractor.py` (created by #698; updated if builder-discovered tests needed)

[[2026-04-09]] Thu 05:08
## Research
- Research doc: .owlbear/research/llmextractor-pydanticai-implementation.md
- Sources: 8 studied, 6 high-relevance (codebase: protocol.py, extractor.py, models.py, pyproject.toml; external: PydanticAI agent docs, testing docs, output docs)
- Recommendation: Thin PydanticAI Agent wrapper (~30 LOC) with complete system prompt (confidence: 0.88)
- Key finding: Existing EXTRACTION_PROMPT missing `governed_by` from RelationType enum — LLMExtractor system prompt must include all 7 relation types for AC3 compliance
- Testing strategy: PydanticAI TestModel + agent.override() pattern with ALLOW_MODEL_REQUESTS=False safety guard
- Dependency chain: #687 (async protocol) + #698 (TDD RED) must complete first; metadata defect (depends_on: [676] → [698, 687]) still unapplied
- Follow-up tasks created: none — ACs are complete and concrete, predecessor tasks exist
- Decision requests: none — T1 autonomous (implements existing AC with proven v1 pattern)

## Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Confidence in original: 0.88
- Key risks: PydanticAI transitive deps (~5) mitigated by optional extras group; protocol must be async first (#687)
- Researcher response: N/A (fallback)

[[2026-04-09]] Thu 05:31
## Architecture Review

### Refinements Applied
- **Dependency fix:** `depends_on` changed from [676] to [698]. Task #698 (TDD RED) depends on #687 (async protocol) which depends on #676 — transitive chain preserved, direct predecessor is now correct.
- **AC1:** Made async requirement explicit — `async def extract(...)` satisfying post-#687 protocol.
- **AC2:** Specified `await agent.run(prompt)` call pattern.
- **AC3:** Enumerated all 6 EntityType + 7 RelationType values for verifiability (research confirmed existing EXTRACTION_PROMPT misses `governed_by`).
- **AC4:** Pinned extras group name to `llm`.
- **AC5:** Specified `Exception` catch at `agent.run()` boundary with logging.
- **AC6:** Clarified this is GREEN phase — #698 writes the RED tests, #689 makes them pass.
- **Affected files:** Corrected test file status (created by #698, not new here).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One class, one protocol implementation |
| Interface clarity | PASS | After refinement: async signature, specific exception handling, explicit enum coverage |
| Dependency correctness | PASS | Fixed: [698] chains through #687 and #676. #698 writes tests, #687 makes protocol async |
| Module layering | PASS | `llm_extractor.py` in `owlbear_knowledge` package, same layer as `extractor.py` |
| TDD compliance | PASS | #698 is the RED phase predecessor |
| KISS/YAGNI | PASS | Thin ~30 LOC wrapper per research recommendation. Optional dep via extras group |
| Premise challenge | PASS | v1 proved the pattern works; no built-in alternative exists |
| Pattern consistency | PASS | Follows EntityExtractor/IntraDocGraphBuilder injection pattern (protocol + optional extractor) |
| Security surface | PASS | LLM boundary — AC5 ensures no unhandled exceptions propagate. Input is internal prompts, not user-facing |
| Single domain | PASS | scope:knowledge only |

### Codebase Evidence
- `protocol.py` L87-94: `StructuredExtractor` protocol (currently sync, #687 will make async)
- `extractor.py` L22-40: Existing `EXTRACTION_PROMPT` missing `governed_by` — confirmed AC3 requirement
- `models.py` L14-36: EntityType (6 values), RelationType (7 values including GOVERNED_BY)
- `extractor.py` L54-100: `EntityExtractor` injection pattern — LLMExtractor follows same structural approach
- `graph_builder.py`, `inter_doc_graph_builder.py`: Both consume StructuredExtractor — no changes needed for #689

### Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Architect confidence: 0.91 — ACs are now fully verifiable, dependency chain is correct, pattern is proven from v1

### Verdict: APPROVE (after inline REFINE)
### Action Taken: Refined AC1/AC2/AC3/AC5/AC6 for precision, fixed depends_on [676] to [698], corrected affected files. Advanced to todo.

[[2026-04-09]] Thu 11:18
## Test-Writer Notes

- Test file: `tests/test_llm_extractor.py` (created by #698)
- Classes: `TestFromAC_LLMExtractor`
- Tests per category: happy 5, edge 2, error 5, boundary 2
- Total: 14 tests — **all PASS** (not RED state)
- ruff: clean (per #698 delivery)

### Situation: Pre-shipped Implementation

Task #698 committed both RED tests and the GREEN implementation in a single commit (`feat(knowledge): add LLMExtractor + RED/GREEN tests (#698)`). By the time the test-writer reached #689:

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — fully implemented
- `serve/knowledge/pyproject.toml` — `pydantic-ai>=0.1` under `[llm]` extras — already present
- All 14 AC tests pass — no failing tests can be written for already-correct behavior

### AC4 Gap

No test exists for AC4 (pyproject.toml `llm` extras group). A config-file test was assessed but would pass immediately — writing a trivially-passing test violates the RED mandate. AC4 can be verified visually by the builder: `pyproject.toml` L14 `llm = ["pydantic-ai>=0.1"]` is present.

### Recommendation for Builder

Confirm all 14 tests pass (`uv run pytest tests/test_llm_extractor.py -v`), verify pyproject.toml AC4, and advance to done. No code changes required.

[[2026-04-09]] Thu 11:46
## Builder Notes

### Files Changed
- No code changes required — implementation shipped by #698 (`feat(knowledge): add LLMExtractor + RED/GREEN tests (#698)`)

### AC Verification
- **AC1** ✓ — `LLMExtractor` in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` with `async def extract(self, prompt: str) -> ExtractionResult`
- **AC2** ✓ — `pydantic_ai.Agent(model, output_type=ExtractionResult, system_prompt=LLM_EXTRACTION_PROMPT)`, calls `await self._agent.run(prompt)`
- **AC3** ✓ — `LLM_EXTRACTION_PROMPT` uses `_ENTITY_VALUES`/`_RELATION_VALUES` built dynamically from enums — all 6 EntityType + 7 RelationType values (including `governed_by`) auto-included
- **AC4** ✓ — `serve/knowledge/pyproject.toml` line 14: `llm = ["pydantic-ai>=0.1"]` under `[project.optional-dependencies]`
- **AC5** ✓ — `except Exception` at `agent.run()` boundary, `logger.warning(...)`, returns `ExtractionResult()`
- **AC6** ✓ — All 14 AC tests pass

### Test Results
- Total: **14 passed**, 0 failed
- Coverage: **100%** (19/19 statements on `llm_extractor.py`)
- Lint: **ruff clean**

### Builder-Discovered Tests
- None needed — pre-shipped implementation already fully covered

### Situation
Test-writer notes confirmed #698 shipped implementation + tests together. Builder role: evidence verification only. No code changes were warranted.

[[2026-04-09]] Thu 12:18
## Review Evidence

### Test Results
pytest: 14 passed, 0 failed (Quality-Runner, independent run)

### Lint
ruff: clean

### Coverage
owlbear_knowledge.llm_extractor: 100% (19/19 statements)

### AC Compliance

| AC | Evidence | Mapped Test(s) | Status |
|----|----------|----------------|--------|
| AC1: LLMExtractor with async extract() satisfying StructuredExtractor | llm_extractor.py L44 class, L63 async def extract; protocol.py @runtime_checkable | test_llm_extractor_satisfies_structured_extractor_isinstance, test_llm_extractor_extract_is_coroutine_function | PASS |
| AC2: Agent with output_type=ExtractionResult, await agent.run(prompt) | llm_extractor.py L50 output_type=ExtractionResult; L64 await self._agent.run(prompt) | test_pydantic_agent_instantiated_with_output_type_extraction_result, test_extract_awaits_agent_run_with_prompt, test_extract_returns_agent_run_output_attribute | PASS |
| AC3: System prompt has all 6 EntityType + 7 RelationType values | llm_extractor.py L16-18 _ENTITY_VALUES/_RELATION_VALUES built dynamically from enums; governed_by confirmed present via RelationType.GOVERNED_BY | test_system_prompt_contains_all_entity_type_values, test_system_prompt_contains_all_relation_type_values, test_system_prompt_contains_governed_by_boundary, test_system_prompt_contains_class_underscore_entity_type | PASS |
| AC4: pydantic-ai>=0.1 in llm extras group | pyproject.toml L14 llm = ["pydantic-ai>=0.1"] — no test (config-only, test-writer documented judgment call) | None (verified by file read) | PASS |
| AC5: except Exception at agent.run(), logs, returns ExtractionResult() | llm_extractor.py L65-68 except Exception; logger.warning; return ExtractionResult() | test_llm_runtime_error_returns_empty_extraction_result, test_llm_failure_does_not_propagate_exception, test_llm_value_error_returns_empty_not_raises | PASS |
| AC6: All RED tests from #698 pass | pytest: 14 passed, 0 failed | All 14 tests | PASS |

### Pass 1 Checks
- 5.0 TestFromAC coverage: All testable ACs covered. AC4 config-only, no test — acceptable (documented by test-writer, verified by file read).
- 5.1 Security: No hardcoded secrets, no injection, no path traversal, no insecure deserialization. pydantic-ai from Pydantic team, no known CVEs. Error log does not leak PII.
- 5.2 TestFromAC integrity: Builder made zero code changes — all TestFromAC tests preserved verbatim.
- 5.3 Test quality: STRONG. Assertions are specific (mock call arg inspection, enum membership, assert_awaited_once_with). 3 error-path tests cover exception branch. Manual mutation would catch all failures.
- 5.4 Data safety: No shared state, no persisted unvalidated output in this module.
- 5.5 Implementation-aware gap: All paths covered — constructor, happy path (result.output), exception path.
- 5.7 Builder process: CLEAN — single builder notes section, no retries.

### Informational (6.1)
AC2 text says result_type=ExtractionResult (v1 API) but implementation correctly uses output_type=ExtractionResult (current PydanticAI API). Tests check output_type. Functional requirement satisfied; AC text has stale parameter name from v1 reference.

### Deductions
0

### Verdict
Confidence: 0.95 → PASS

[[2026-04-09]] Thu 12:20
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | New `LLMExtractor` class. `copilot-instructions.md` contains only project identity + branch topology — no knowledge package table to update. No change required. |
| 2 | Module docstrings | Yes | Verified | `llm_extractor.py`: module docstring (L1-4), class docstring with Args (L45-55), `extract()` with Args + Returns (L58-68). All accurate against implementation. |
| 3 | External attribution | Yes | Already present | `sources/overview.md` has "LLMExtractor PydanticAI Implementation (Task #689)" with 3 PydanticAI sources (agents, structured output, testing docs) — shipped by research phase. |
| 4 | CLI changes | No | N/A | No CLI surface added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/llmextractor-pydanticai-implementation.md` exists. Linked in task body under Research section. Follow-up tasks: none required per research notes. |

### Files Updated
None — all documentation already accurate.

### Scratch Files
No `.owlbear/scratch/689-*` files found.

### Commit
No docs commit required — no files modified.

[[2026-04-09]] Thu 13:07
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: LLMExtractor with async extract() satisfying StructuredExtractor | llm_extractor.py L44 class, L63 `async def extract`; test: `test_llm_extractor_satisfies_structured_extractor_isinstance`, `test_llm_extractor_extract_is_coroutine_function` | PASS |
| AC2: Agent with output_type=ExtractionResult, await agent.run(prompt) | llm_extractor.py L57-62 Agent(model, output_type=ExtractionResult), L72 `await self._agent.run(prompt)`; tests: `test_pydantic_agent_instantiated_with_output_type_extraction_result`, `test_extract_awaits_agent_run_with_prompt`, `test_extract_returns_agent_run_output_attribute` | PASS |
| AC3: System prompt covers all 6 EntityType + 7 RelationType values | llm_extractor.py L16-18 `_ENTITY_VALUES`/`_RELATION_VALUES` built dynamically from enums; governed_by confirmed; tests: `test_system_prompt_contains_all_entity_type_values`, `test_system_prompt_contains_all_relation_type_values`, `test_system_prompt_contains_governed_by_boundary`, `test_system_prompt_contains_class_underscore_entity_type` | PASS |
| AC4: pydantic-ai in llm extras group | pyproject.toml L14: `llm = ["pydantic-ai>=0.1"]` under `[project.optional-dependencies]` — config-only, no test (documented by test-writer) | PASS |
| AC5: Graceful degradation — catch Exception, log, return empty | llm_extractor.py L74-77: `except Exception`, `logger.warning(...)`, `return ExtractionResult()`; tests: `test_llm_runtime_error_returns_empty_extraction_result`, `test_llm_failure_does_not_propagate_exception`, `test_llm_value_error_returns_empty_not_raises` | PASS |
| AC6: All RED-phase tests from #698 pass | 14/14 passed (direct run) | PASS |

### Test Results
- pytest (task-scoped): 14 passed, 0 failed
- pytest (full suite): 3866 passed, 389 failed, 8 errors — 0 failures in task scope; failures are pre-existing (qdrant import, strictyaml dep count, unrelated modules)
- ruff (task-scoped): All checks passed

### Architect Quality: 4/5
ACs are specific, measurable, and concrete. All 6 EntityType + 7 RelationType values enumerated in AC3. Explicit async signature in AC1, exception boundary in AC5. Minor issue: AC2 says `result_type=` (v1 PydanticAI API) but current API is `output_type=` — reviewer caught this as informational. Builder implemented correctly despite stale parameter name.

### Deduction Breakdown
- AC lines without evidence: 0 → -.00
- Lint violations in scope: 0 → -.00
- AC quality ≤ 3: No (4/5) → -.00
- Missing reviewer evidence: No (detailed, PASS at 0.95) → -.00
- Full-suite failures in task scope: 0 → -.00

### Confidence: .98
### Action: archive

### Notes
- Implementation was pre-shipped by #698 (single commit `0bca8f2`). Builder for #689 performed verification only — no code changes required.
- Reviewer evidence is thorough with file:line citations and per-AC test mappings. Trusted code-level findings; spot-checked AC1 (async signature), AC3 (enum coverage via dynamic build), AC5 (exception boundary).
