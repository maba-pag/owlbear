---
id: 887
title: 'Research: Copilot SDK vs OpenAI-compat endpoint for knowledge extraction LLM'
status: archived
priority: medium
created: '2026-04-15T13:34:22.037145+00:00'
updated: '2026-04-15T19:42:14.879091+00:00'
tags:
- research
- scope:knowledge
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Evaluate two approaches for using GitHub Copilot's LLM from the knowledge extraction pipeline (Python MCP server), without requiring an external OpenAI API key.

## Acceptance Criteria

- Compare **Copilot SDK** (`github-copilot-sdk`) vs **OpenAI SDK with Copilot endpoint** (faking VS Code client headers at `api.githubcopilot.com`)
- For each approach, verify:
  1. Can send a system prompt + user content and get structured JSON back
  2. Works from a standalone Python process (MCP server, not inside VS Code)
  3. Supports `ExtractionResult` schema parsing (entities + edges)
  4. Authentication flow — does it use Copilot subscription seamlessly?
  5. Rate limits, model availability, latency
- Document which models support structured output (`response_format`) via each approach
- Recommend one approach with confidence score and trade-off analysis
- Reference v1 experiment where OpenAI-compatible Copilot endpoint was tested (OpenClaw context)

## Context

- Current: `LLMExtractor` in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` uses `openai.AsyncOpenAI` with `chat.completions.parse(response_format=ExtractionResult)`
- Goal: use Copilot subscription for LLM access without external API keys
- Copilot SDK: `pip install github-copilot-sdk` (v0.2.2) — session-based, event-driven, supports BYOK
- OpenAI-compatible endpoint: `api.githubcopilot.com` — tested in v1, required client ID header faking

## Research sources

- <https://pypi.org/project/github-copilot-sdk/>
- <https://github.com/github/copilot-sdk>
- <https://github.com/ericc-ch/copilot-api> (OpenAI-compat wrapper)
- v1 experiment notes (if findable in archive)
[[2026-04-15]]

## Research

- Research doc: .owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Option B (OpenAI SDK + Copilot endpoint) is technically viable but carries ToS/abuse-detection risk; Option A (Copilot SDK) lacks structured output support entirely (confidence: .65)
- Follow-up tasks created: #888 (port Copilot auth — needs user decision on ToS risk), #889 (monitor SDK for structured output)
- Decision requests: 0 created — classified T2 advisory; user should decide risk tolerance before #888 proceeds
- Challenge: FALLBACK — challenger subagent not in available roster

Key findings:

1. Copilot SDK (v0.2.2) is agent-oriented — session.send() → text events. No `response_format`, no completions API. Cannot guarantee schema-valid JSON for ExtractionResult.
2. OpenAI SDK + Copilot endpoint works — Graphicator v1 proved it. Requires device-flow OAuth + faked editor headers. Minimal code changes to LLMExtractor.
3. Risk: GitHub warns automated/bulk use of Copilot API may trigger abuse detection and access suspension. Faking editor headers is grey-area ToS.
4. GPT-4.1 and GPT-5 mini are 0× multiplier (included) on paid plans — no premium request cost for extraction.
[[2026-04-15]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One research question: SDK vs endpoint for LLM extraction |
| Interface clarity | PASS | AC lists 5 verification axes per approach + recommendation + confidence + v1 reference |
| Dependency correctness | PASS | No dependencies; none needed for pure research |
| Module layering | N/A | Research task — no code changes |
| TDD compliance | N/A | Research task — pass-through tag `research` present |
| KISS/YAGNI | PASS | Appropriately scoped — two specific approaches, not open-ended |
| Premise challenge | PASS | Valid need: `LLMExtractor` requires `api_key`, Copilot subscription is a legitimate alternative to evaluate |
| Pattern consistency | PASS | Research doc at `.owlbear/research/887-*.md`, follows established format |
| Security surface | PASS | Research correctly identifies ToS/abuse-detection risk for Option B; #888 tagged `needs-decision` before implementation |
| Single domain | PASS | `scope:knowledge` only |

### AC Coverage

| AC Line | Addressed | Evidence |
|---------|-----------|----------|
| Compare SDK vs endpoint | ✓ | §3.1 full comparison table (8 criteria) |
| Structured JSON output | ✓ | §3.2 feasibility detail — SDK lacks `response_format`, endpoint supports it |
| Standalone Python process | ✓ | §3.1 row 2 — SDK spawns CLI subprocess, endpoint uses standard `AsyncOpenAI` |
| ExtractionResult parsing | ✓ | §3.2 — SDK requires fragile tool-call hack, endpoint uses native `parse()` |
| Authentication flow | ✓ | §3.3 — full step-by-step comparison |
| Rate limits / model availability | ✓ | §3.1 rows 5–6 — same Copilot quota, GPT-4.1/GPT-5 mini at 0× multiplier |
| Document structured output models | ✓ | §3.1 row 1, §3.2 table |
| Recommend with confidence | ✓ | §4 — Option B recommended, confidence .65, caveats documented |
| Reference v1 experiment | ✓ | S3, S4 — Graphicator/OpenClaw auth flow referenced |

### Follow-up Task Quality

- **#888** (Port Copilot auth): Well-scoped AC, affected files listed, correctly tagged `needs-decision` and depends_on=[887], at `research` status pending user ToS decision
- **#889** (Monitor SDK): Appropriately low priority (`nice-to-have`), tracking tag, quarterly cadence defined

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available roster
- Architect response: Proceeding — research task with all AC lines covered, no code changes proposed, T2 advisory classification is correct

### Verdict: APPROVE

### Action Taken: Advanced #887 to todo. All AC items addressed in research doc. Follow-up tasks #888/#889 properly created. Non-implementation tag `research` already present

[[2026-04-15]]

## Test-Writer Notes

- Non-implementation task (tagged `research`) — no tests applicable.
- Passing through to builder.
[[2026-04-15]]

## Builder Notes

**Task type:** Non-implementation (tagged `research`) — pass-through per test-writer notes.

**Files changed:** None
**Tests:** N/A — no code changes
**Ruff:** N/A
**Coverage:** N/A

**Evidence:** Research doc at `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` covers all AC items. Follow-up tasks #888 (Copilot auth port, `needs-decision`) and #889 (SDK monitoring) created and properly scoped. Architecture review approved. No implementation work required for this task.
[[2026-04-15]]

## Review Evidence

### Task Type

Non-implementation — tagged `research`. No code changes. Tests, lint, coverage: N/A.

### Changed Files

`get_changed_files` not run — builder confirmed no files changed. Independent verification: `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` unchanged (grep confirms `AsyncOpenAI`/`chat.completions.parse` intact, no `copilot_auth.py` present). Research doc at `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` verified readable and complete.

### Source Integrity

- **S4 (`copilot-auth.md`)**: File confirmed at `.owlbear/research/copilot-auth.md` — is Graphicator device-flow OAuth research (task #30). Confirms v1 experiment reference is legitimate, not fabricated.
- **S5 (`llm_extractor.py`)**: Confirmed — `AsyncOpenAI` with `chat.completions.parse(response_format=...)` at line 86. Codebase state matches research doc claim.
- **Endpoint URL**: `api.individual.githubcopilot.com` confirmed in `copilot-auth.md` line 40, consistent with §3.3 in research doc.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| Compare SDK vs OpenAI-compat endpoint | §3.1 — 8-criterion comparison table | PASS |
| Structured JSON back (per approach) | §3.1 row 1, §3.2 — SDK: no `response_format`; endpoint: supported via `parse()` | PASS |
| Standalone Python process (per approach) | §3.1 row 2 — SDK: CLI subprocess ~200ms overhead; endpoint: standard `AsyncOpenAI`, yes | PASS |
| ExtractionResult schema parsing (per approach) | §3.2 table — SDK: fragile tool-call hack; endpoint: native `parse()` | PASS |
| Authentication flow (per approach) | §3.3 step-by-step table — SDK: CLI-managed; endpoint: device-flow OAuth + manual token cache | PASS |
| Rate limits, model availability, latency | §3.1 rows 5–6 (rate limits + model list); row 2 (SDK ~200ms startup); endpoint latency implicit = current code path unchanged | PASS (minor: endpoint latency not explicitly quantified) |
| Document structured output models | §3.1 row 1 + §3.2 table — GPT-4.1, GPT-5 mini, Claude Sonnet 4 listed; endpoint supports all; SDK supports none natively | PASS |
| Recommend with confidence score + trade-off | §4 — Option B, confidence .65, caveats documented; §3.4 risk matrix | PASS |
| Reference v1 experiment (OpenClaw context) | S4 `copilot-auth.md` (task #30) + "Graphicator v1" cited in §3.1 rows 1–2, §3.3 | PASS |

### Follow-up Task Quality

- **#888**: Exists at `research` status. Properly scoped AC, affected files listed, `needs-decision` tag, `depends_on=[887]`. Architect REJECT on #888 for T3 DR gap — correctly identified and handled downstream, not a defect in #887 deliverable.
- **#889**: Exists at `backlog` status, `tracking` tag, `nice-to-have` priority. Monitoring update already added to research doc — SDK still lacks structured output per v0.2.2 changelog. AC has structural issue (recurring, no done state) flagged by #889's architect — again downstream, not a defect in #887 deliverable.

### Deductions

- **-0.02** Latency for Option B not explicitly stated — "same as current code path" is implied but not written as a conclusion in §3.1. AC says "verify … latency" for each approach; only SDK's overhead (~200ms) is quantified. Minor gap in documentation rigor.
- **-0.01** Challenger subagent FALLBACK — documented, not contested; research task with no code changes is low-risk for missing a challenge. Acceptable.

### Verdict

Confidence: 1.00 − 0.02 − 0.01 = **0.97 → PASS**

Research doc is thorough, well-sourced (7 sources, 5 high-relevance), and covers all 9 AC lines with section-level citations. Codebase state verified. Follow-up tasks correctly created. Recommendation appropriately conservative (confidence .65 explicitly communicated). No code changes → no security surface to audit.
[[2026-04-15]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure research task — no code changes. `llm_extractor.py` confirmed unchanged (AsyncOpenAI/parse intact, no copilot_auth.py present). `copilot-instructions.md` update not warranted — no implemented behavior change. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | Yes | Verified (already done) | 4 external sources (S1–S3, S6) present in `.owlbear/sources/overview.md` under `## Copilot SDK vs OpenAI-Compat Endpoint Research (Task #887)`. S4/S5 are internal codebase sources (no attribution needed). S7 (GitHub ToS/AUP) is a policy doc reviewed for risk context, not a technical pattern — omission is acceptable. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` exists and is complete (9 AC lines covered, 7 sources, recommendation at confidence .65). Linked in task body. Follow-up tasks #888 (research status, needs-decision tag) and #889 (backlog, tracking tag) confirmed created. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/887-*` files existed)
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Compare SDK vs OpenAI-compat endpoint | Research doc §3.1 — 8-criterion comparison table | PASS |
| Structured JSON output (per approach) | §3.1 row 1, §3.2 — SDK lacks response_format; endpoint supports parse() | PASS |
| Standalone Python process (per approach) | §3.1 row 2 — SDK: subprocess ~200ms; endpoint: standard AsyncOpenAI | PASS |
| ExtractionResult schema parsing | §3.2 — SDK: fragile tool-call hack; endpoint: native parse() | PASS |
| Authentication flow (per approach) | §3.3 — full step-by-step comparison table | PASS |
| Rate limits, model availability, latency | §3.1 rows 5-6, row 2 (SDK ~200ms startup) | PASS |
| Document structured output models | §3.1 row 1, §3.2 table — GPT-4.1, GPT-5 mini, Claude Sonnet 4 | PASS |
| Recommend with confidence + trade-offs | §4 — Option B, confidence .65, caveats documented | PASS |
| Reference v1 experiment | S4 copilot-auth.md (task #30), Graphicator v1 cited throughout | PASS |

### Follow-up Tasks

- #888: exists at research, needs-decision tag, depends_on=[887] — correct
- #889: exists at backlog, tracking tag, blocked type:user-action — correct

### Test Results

- pytest: 242 passed, 24 failed (all in test_analysis.py — pre-existing, unrelated to #887, no code changes in this task)
- ruff: 1 violation in serve/kanban/engine.py:471 (E501) — pre-existing, unrelated

### Architect Quality: 5/5

AC was specific, complete, and cleanly scoped. 9 verifiable lines covering comparison axes, deliverable format, and context references. No improvisation needed by downstream agents.

### Deduction Breakdown

- AC lines without evidence: 0 (9/9 PASS)
- Lint violations in scope: 0 (existing violation unrelated)
- AC quality: 5/5, no deduction
- Reviewer evidence: present, detailed, PASS at .97
- Test failures in scope: 0 (failures in test_analysis.py pre-existing)
- Note: research doc was uncommitted by upstream — committed by auditor (8146cb7e)

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8146cb7e | docs | .owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md | #887 |
