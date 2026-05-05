---
id: 1358
title: Remove legacy API key branch from mcp-knowledge server.py
status: review
priority: needed
created: 2026-05-05T08:18:53.248842+00:00
updated: 2026-05-05T09:18:36.594878+00:00
tags:
- knowledge
- cleanup
- security
- scope:mcp-knowledge
parent: 1316
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-05T09:18:36.594878+00:00
archival_reason:
archival_refs: []
---

## Objective

Remove the legacy API key branch from `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (L531-542). This code was the rejected "Option B" from brief D4 (`.owlbear/briefs/draft-knowledge-activation/decisions.md`): corporate policy prohibits API keys.

The agent-driven enrichment approach (Option A) replaces this path entirely.

## Acceptance Criteria

1. **Remove the `if api_key:` branch** at server.py L531-542 and all related env var reads (`OWLBEAR_LLM_API_KEY`, `OPENAI_API_KEY`). `structured_extractor` always resolves to `None`.
2. **Remove dead imports** — `LLMExtractor`, `copilot_auth` (if still imported), and any env-var-gated wiring.
3. **Update README** — remove documentation of `OWLBEAR_LLM_API_KEY`/`OPENAI_API_KEY` env vars from `serve/mcp-knowledge/README.md`.
4. **Clean dead tests** — remove or update tests that assert API-key-present behavior (e.g. `test_copilot_server_wiring_888.py`, `test_llmextractor_wiring_876.py`).
5. **No regression** — existing tests pass; `EntityExtractor` and `IntraDocGraphBuilder` receive `structured_extractor=None` always (current behavior without keys set).

## Context

- Brief decision D4: "B rejected because corporate policy prohibits API keys. Hard constraint."
- Task #1326 was blocked for 3 reviewer cycles disputing proof quality on this dead code
- `copilot_auth.py` OAuth flow already removed in #1318; this removes the remaining plain API key path
- Consider also removing `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` if no other consumers exist
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_server_1358.py
- Classes: TestFromAC_ApiKeyBranchRemoved, TestFromAC_DeadImportsRemoved, TestFromAC_ReadmeCleanup, TestFromAC_DeadTestsRemoved, TestFromAC_NoRegression
- Tests per category: happy 0, edge 0, error 0, boundary 0 — all tests are contract/removal assertions
  - AC1 (branch removal): 3 tests — structured_extractor=None when key set (OWLBEAR), when fallback (OPENAI), LLMExtractor never instantiated
  - AC2 (dead imports): 3 tests — server.py source has no llm_extractor, OWLBEAR_LLM_API_KEY, OPENAI_API_KEY strings
  - AC3 (README cleanup): 2 tests — README has neither OWLBEAR_LLM_API_KEY nor OPENAI_API_KEY
  - AC4 (dead files): 2 tests — test_copilot_server_wiring_888.py and test_llmextractor_wiring_876.py do not exist
  - AC5 (regression guard): 2 tests — EntityExtractor and IntraDocGraphBuilder receive extractor=None even with key set
- Total: 12 tests, all FAIL
- ruff: clean
[[2026-05-05]]
## Builder Notes
- Implementation: Removed legacy API-key-gated structured extractor wiring from [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py), so `structured_extractor` is always `None` in `app_lifespan`.
- Cleanup: Removed API-key configuration docs from [serve/mcp-knowledge/README.md](serve/mcp-knowledge/README.md) (`OWLBEAR_LLM_API_KEY`, `OPENAI_API_KEY`, and related LLM key/base-url/model lines tied to that branch).
- Dead tests removed: Deleted [serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py](serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py) and [serve/mcp-knowledge/tests/test_llmextractor_wiring_876.py](serve/mcp-knowledge/tests/test_llmextractor_wiring_876.py).
- Test evidence (quality-runner scoped): 81 passed, 0 failed across [tests/test_server_1358.py](tests/test_server_1358.py), [serve/mcp-knowledge/tests/test_server.py](serve/mcp-knowledge/tests/test_server.py), [serve/mcp-knowledge/tests/test_ingest_graph_wiring.py](serve/mcp-knowledge/tests/test_ingest_graph_wiring.py), [serve/mcp-knowledge/tests/test_ingest_graph_tools.py](serve/mcp-knowledge/tests/test_ingest_graph_tools.py).
- Lint evidence (quality-runner scoped): clean (`ruff` exit code 0) for `serve/mcp-knowledge/src/`, `tests/test_server_1358.py`, and `serve/mcp-knowledge/tests/`.
- Coverage evidence (quality-runner scoped): `owlbear_mcp_knowledge.server` reported 49% in this scoped run.
- Commit: `6444bdb7` — "fix: remove legacy API-key extractor path (#1358, builder)".

### Post-task Reflection
- apply_patch deletion reported success but did not remove files from disk; verifying filesystem state prevented a false-green result.
- Direct `rm` plus immediate existence check is the reliable fallback when delete directives silently no-op.
- Keeping the server diff branch-local (single conditional removal) minimized risk to unrelated MCP tool wiring.
- Scoped regression tests around mcp-knowledge server lifecycle/tool wiring gave stronger confidence than task-file-only execution.