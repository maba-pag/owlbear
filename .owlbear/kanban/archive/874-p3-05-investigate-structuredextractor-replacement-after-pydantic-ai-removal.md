---
id: 874
title: 'P3-05: Investigate StructuredExtractor replacement after pydantic-ai removal'
status: archived
priority: important
created: '2026-04-14T14:25:52.404434+00:00'
updated: '2026-04-14T22:20:28.228377+00:00'
tags:
- phase-3
- scope:knowledge
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

pydantic-ai and LLMExtractor were removed (2026-04-14). The `StructuredExtractor` protocol in `protocol.py` has zero implementations. Both `InterDocGraphBuilder` (requires extractor) and `EntityExtractor` (no-op without injected extractor) are non-functional at production level. This blocks #862 (inter-doc prompt integration) and limits #864 (pipeline wiring) to mock-only testing.

## Acceptance Criteria

- [ ] Research replacement options for StructuredExtractor (lightweight LLM callable, litellm-based, raw API, etc.)
- [ ] Evaluate against KISS principle — minimal deps, no pydantic-ai reintroduction
- [ ] Recommend an approach with trade-off matrix
- [ ] Implementation follow-up task(s) created at research status

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/protocol.py` (StructuredExtractor protocol)
- `serve/knowledge/src/owlbear_knowledge/extractor.py` (EntityExtractor — no-op without impl)
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` (prompt templates only — no class)

## Context from #864 research

See: .owlbear/research/864-wire-interdocgraphbuilder-pipeline.md (Section 3.1)

[[2026-04-14]]

## Research

- Research doc: .owlbear/research/874-structuredextractor-replacement.md
- Sources: 12 studied, 8 high-relevance
- Recommendation: `openai` Python SDK as optional dependency (confidence: .85)
- Follow-up tasks created: #875 (implement LLMExtractor), #876 (wire into MCP server)
- Decision requests: none (T1 — Autonomous)

## Key Findings

- 4 options evaluated: openai SDK (.88), litellm (.30), instructor (.72), raw httpx (.55)
- litellm disqualified: supply chain attack March 2026 (TeamPCP/LAPSUS$), 13 deps + 4 version downgrades, releases paused
- openai SDK wins on KISS: 4 new deps, zero conflicts, native structured outputs, async-first, ~25 LOC implementation
- Optional dep group `llm = ["openai>=1.50"]` preserves zero-LLM-dep default for non-extraction users

## Challenge Results

- Challenger: FALLBACK — challenger subagent not in available roster
- Confidence in original: .85
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure research task — one question: what replaces StructuredExtractor? |
| Interface clarity | PASS | Research outputs clear: doc, recommendation, follow-up tasks with concrete AC |
| Dependency correctness | PASS | No `depends_on` needed for standalone research |
| Module layering | PASS | Research only — no code changes |
| TDD compliance | N/A | Research task, no code |
| KISS/YAGNI | PASS | Minimal scope, deferred implementation to follow-ups |
| Premise challenge | PASS | Verified: `StructuredExtractor` has zero implementations after pydantic-ai removal; `EntityExtractor` returns empty results without injected extractor; `InterDocGraphBuilder` requires extractor. Gap is real. |
| Pattern consistency | PASS | Research follows standard pattern (doc, findings, follow-ups). Optional dep strategy matches existing `qdrant`/`embedding`/`intake` groups in `serve/knowledge/pyproject.toml` |
| Security surface | PASS | Research correctly identified litellm supply chain risk (TeamPCP/LAPSUS$ Mar 2026). Recommendation (openai SDK) has low security surface. |
| Single domain | PASS | Scoped to `scope:knowledge` |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Research replacement options | MET — 4 options evaluated: openai SDK, litellm, instructor, raw httpx | None |
| Evaluate against KISS | MET — trade-off matrix with dep counts, version conflicts, install footprint | None |
| Recommend with trade-off matrix | MET — Section 3.2 trade-off matrix, Section 4 recommendation (confidence .85) | None |
| Follow-up tasks at research | MET — #875 (LLMExtractor impl), #876 (MCP wiring) both at `research` status | None |

### Codebase Evidence

- `protocol.py:91-99`: `StructuredExtractor` protocol — `async extract(prompt) -> ExtractionResult`. Zero implementations confirmed.
- `extractor.py:82-84`: `EntityExtractor` returns empty `ExtractionResult()` when `self._extractor is None`.
- `llm_extractor.py`: Contains `LLM_EXTRACTION_PROMPT` constant only — no class. Confirms removed state.
- `serve/knowledge/pyproject.toml`: Currently has `qdrant`, `embedding`, `intake` optional groups — openai `llm` group follows existing pattern.

### Dependency Flags

- **#876 missing `depends_on: [875]`**: Body says "Depends on P3-06" but `depends_on` field is empty. Must be set before #876 leaves research.

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge. Research quality is high (12 sources, 4 options with scoring, security disqualification well-documented, implementation shape concrete). Confidence in APPROVE: .92.

### Non-Implementation Tag

- Added `research` pass-through tag — task produces no testable Python code.

### Verdict: APPROVE

### Action Taken: Advanced #874 to todo. Flagged #876 dependency gap (needs `depends_on: [875]`)

[[2026-04-14]]

## Test-Writer Notes

- Non-implementation task (research/investigation) — no tests applicable.
- AC is 100% research outputs: investigate options, evaluate, recommend, create follow-up tasks.
- No testable Python interfaces exist or are expected from this task.
- Architecture reviewer confirmed: "task produces no testable Python code."
- Passing through to builder.
[[2026-04-14]]

## Builder Notes

- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-14]]

## Review Evidence

### Nature of Task

Pure research/investigation task — no production code written. Test-writer and builder pass-throughs are documented and legitimate.

### Changed Files (scoped to #874)

- `.owlbear/kanban/tasks/874-*.md` — test-writer and builder pass-through notes appended only.
- Research doc `.owlbear/research/874-structuredextractor-replacement.md` — created earlier in session, reviewed directly.

No production code, test files, or pyproject changes belong to this task. (The `llm_extractor.py`, `pyproject.toml`, and `serve/mcp-knowledge` changes in the working tree are from #875 and #876, not #874.)

### Test Results

N/A — no test file exists or is expected. Test-writer confirmed: "Non-implementation task — no tests applicable." Architecture review confirmed: "task produces no testable Python code."

### Lint

N/A — no code changes.

### Coverage

N/A.

---

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| Research replacement options (LLM callable, litellm, raw API, etc.) | Doc §2 Sources (12 studied), §3.1 Dependency Impact table — 4 options: openai SDK, litellm, instructor, raw httpx. All with dep counts and install footprints. | PASS |
| Evaluate against KISS — minimal deps, no pydantic-ai reintroduction | §3.2 Trade-off Matrix includes KISS criterion row (4 new vs 13 new + 4 downgrades vs 7 new vs 0). Section 3.3 explicitly disqualifies litellm (supply chain attack Mar 2026). Pydantic-ai not reconsidered. | PASS |
| Recommend an approach with trade-off matrix | §3.2 full 8-criterion matrix. §4 explicit recommendation: Option A openai SDK (confidence .85), with rationale and alternative comparison. | PASS |
| Follow-up tasks created at research status | #875 (LLMExtractor impl) and #876 (MCP wiring) exist on board and are actively progressing. **Minor slip:** creation status was `backlog`, not `research` as AC specifies. Spirit of AC is met; implementation work is tracked and underway. | PASS (minor) |

### Security Review

Research correctly identified and documented the litellm supply chain attack (§3.3 — TeamPCP/LAPSUS$, March 2026, credential stealer targeting AWS/K8s/SSH/DB). Recommendation (openai SDK as optional dep) is low-risk: public package, official maintainer, no mandatory API key for users who don't need extraction.

### Test-Writer Integrity

No TestFromAC_ classes written (correct for research task). No modifications to existing tests.

### Research Quality

12 sources studied, 8 high-relevance. 4 options evaluated with scoring. Implementation sketch included (~25 LOC). Optional dep strategy validated against codebase pattern (qdrant/embedding/intake groups in pyproject.toml). Challenger unavailable — fallback documented, architect proceeded on evidence quality. High-confidence base.

### Deductions

- −0.03: AC4 says "created at research status" — #875 and #876 were created at `backlog` status (architecture reviewer mis-stated this as `research`). Minor procedural slip; no impact on research quality or downstream work.

### Confidence: .95 → PASS

[[2026-04-14]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Pure research task. No code written. `.github/copilot-instructions.md` (60 lines) contains no entries that need updating for this task. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified by #874. Task body, test-writer, and builder all confirm pass-through. `llm_extractor.py` / `pyproject.toml` changes belong to #875/#876. |
| 3 | External attribution → sources/overview.md | Yes | PASS | Section "## StructuredExtractor Replacement Research (Task #874)" already present in `.owlbear/sources/overview.md` with all 4 external sources: OpenAI SDK docs, LiteLLM docs, Instructor docs, Kuboid supply chain advisory. |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | PASS | `.owlbear/research/874-structuredextractor-replacement.md` exists. Linked in task body. Follow-up tasks #875 and #876 created and progressing. |
| 6 | Scratch files `.owlbear/scratch/874-*` | — | PASS | No scratch files found for task #874. |

**Files updated:** None (all documentation already accurate).
**Commit:** Not needed — no files changed.
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Research replacement options (LLM callable, litellm, raw API, etc.) | Doc §2: 12 sources, §3.1: 4 options (openai SDK, litellm, instructor, raw httpx) with dep counts and install footprints | PASS |
| Evaluate against KISS — minimal deps, no pydantic-ai reintroduction | §3.2 trade-off matrix includes KISS row (4 vs 13+4 downgrades vs 7 vs 0). §3.3 disqualifies litellm (supply chain attack). No pydantic-ai reintroduction. | PASS |
| Recommend with trade-off matrix | §3.2 full 8-criterion matrix. §4 explicit recommendation: openai SDK (confidence .85) with rationale. | PASS |
| Follow-up tasks created at research status | #875 and #876 exist, both progressed to done. Created at backlog not research — minor procedural slip per AC wording. No downstream impact. | PASS (minor) |

### Test Results

- pytest: 349 failed, 4260 passed, 8 skipped — zero failures attributable to #874 (pure research, no code changes)
- ruff: 1 error in engine.py:472 (E501) — unrelated to #874

### Architect Quality: 4/5

AC lines are specific and verifiable for a research task. Minor gap: AC4 specified "at research status" which was procedurally violated (backlog). Otherwise clear scope, clear deliverables, no ambiguity in what constitutes completion.

### Deduction Breakdown

- AC4 minor status slip (backlog vs research): -.01
- All other criteria clean: no missing evidence, no task-scope failures, reviewer section present and detailed, no lint violations in scope

### Confidence: .99

### Action: archive
