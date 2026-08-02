---
id: 1358
title: Remove legacy API key branch from mcp-knowledge server.py
status: archived
priority: medium
created: 2026-05-05T08:18:53.248842+00:00
updated: 2026-05-05T10:12:13.673880+00:00
tags:
- knowledge
- cleanup
- security
- scope:mcp-knowledge
parent: 1316
depends_on: []
blocked: false
block_reason:
claimed_at:
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
[[2026-05-05]]
## Review Evidence
### Source Scope
- Builder scope reconstructed from task body and current workspace state: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `serve/mcp-knowledge/README.md`, deletion of `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, deletion of `serve/mcp-knowledge/tests/test_llmextractor_wiring_876.py`.
- Current task file contains no prior `## Review Evidence` section, so this is the first review cycle.
- Direct `git diff` / `git status` evidence was not available in this session, so TestFromAC immutability and dirty-tree contamination checks are lower-confidence than normal.

### Test Results
- quality-runner scoped task-owned regression pass: **145 passed, 0 failed, 0 skipped** across `tests/test_server_1358.py`, `tests/test_server_1317.py`, `tests/test_persistence_source_wiring_1320.py`, `tests/test_content_guard_wiring_1321.py`, `tests/test_browser_fetcher_wiring_1325.py`, `tests/test_browser_fetcher_wiring_1326.py`, `serve/mcp-knowledge/tests/test_server.py`, `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py`, and `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`.
- quality-runner broad package-context pass: **232 passed, 5 failed, 0 skipped**. Failures were limited to `serve/mcp-knowledge/tests/test_outputschema_541.py` (schema contract task lineage) and `serve/mcp-knowledge/tests/test_phase_a_config.py` (legacy skill-path contract); neither failure is traceable to AC1-AC5 or the changed lifecycle lines.

### Lint Results
- quality-runner scoped lint: **clean** (`ruff` exit code 0) for `serve/mcp-knowledge/src/`, `serve/mcp-knowledge/tests/test_server.py`, `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py`, `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`, `tests/test_server_1358.py`, `tests/test_server_1317.py`, `tests/test_persistence_source_wiring_1320.py`, `tests/test_content_guard_wiring_1321.py`, `tests/test_browser_fetcher_wiring_1325.py`, and `tests/test_browser_fetcher_wiring_1326.py`.

### Coverage
- Scoped `owlbear_mcp_knowledge.server` coverage: **52%**.
- Broad package-context `owlbear_mcp_knowledge.server` coverage: **66%**.
- This task is a narrow dead-branch removal in `app_lifespan`; coverage is treated as informational only because the changed lines have direct structural proof at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:530-532` and discriminating AC-mapped tests.

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 remove `if api_key:` branch / extractor always `None` | `tests/test_server_1358.py::test_structured_extractor_none_when_owlbear_key_set`, `::test_structured_extractor_none_when_openai_key_set`, `::test_llmextractor_never_instantiated_when_both_keys_set` | Yes — exact `is None` and `assert_not_called()` checks fail if the branch or constructor returns | COVERED |
| AC2 remove dead imports / env-var wiring | `tests/test_server_1358.py::test_server_source_no_llm_extractor_import`, `::test_server_source_no_owlbear_llm_api_key`, `::test_server_source_no_openai_api_key`; plus `tests/test_server_1317.py::test_copilot_auth_not_imported_when_no_api_key` and `::test_copilot_auth_module_absent_from_sys_modules_after_lifespan` for the conditional `copilot_auth` clause | Yes — exact source-absence checks fail on reintroduced strings; prior no-copilot regression tests fail on renewed auth import | COVERED |
| AC3 README cleanup | `tests/test_server_1358.py::test_readme_no_owlbear_llm_api_key`, `::test_readme_no_openai_api_key` | Yes — exact string-absence checks fail if either env var is documented again | COVERED |
| AC4 dead tests removed | `tests/test_server_1358.py::test_copilot_server_wiring_888_file_deleted`, `::test_llmextractor_wiring_876_file_deleted` | Yes — `Path.exists()` flips immediately if either file remains | COVERED |
| AC5 no regression / downstream constructors still receive `None` | `tests/test_server_1358.py::test_entity_extractor_receives_none_when_api_key_set`, `::test_intra_doc_builder_receives_none_when_api_key_set`; adjacent green regression suites listed above | Yes — constructor kwarg identity checks fail if a non-`None` extractor is passed | COVERED |

### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `tests/test_server_1358.py` TestFromAC inventory from task body (5 classes / 12 tests) | Current file still exposes the same AC classes and 12 mapped tests described by the test-writer note | PRESERVED (lower confidence; commit diff unavailable) |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:530-532` sets `structured_extractor = None` and passes it into `EntityExtractor` / `IntraDocGraphBuilder` | `tests/test_server_1358.py:70`, `:84`, `:99` | PASS |
| AC2 | `grep_search` found **no matches** for `OWLBEAR_LLM_API_KEY`, `OPENAI_API_KEY`, `llm_extractor`, or `copilot_auth` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`; prior no-copilot suite remains green | `tests/test_server_1358.py:124`, `:133`, `:141`; `tests/test_server_1317.py:85`, `:117` | PASS |
| AC3 | `grep_search` found **no matches** for `OWLBEAR_LLM_API_KEY` or `OPENAI_API_KEY` in `serve/mcp-knowledge/README.md` | `tests/test_server_1358.py:159`, `:167` | PASS |
| AC4 | `file_search` returned **no files found** for `**/test_copilot_server_wiring_888.py` and `**/test_llmextractor_wiring_876.py` | `tests/test_server_1358.py:185`, `:193` | PASS |
| AC5 | Exact `None` wiring remains at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:531-532`; scoped lifecycle/wiring regression run is green (145 passed, 0 failed) | `tests/test_server_1358.py:213`, `:234` | PASS |

### Informational
- Residual dead test setup remains in `serve/mcp-knowledge/tests/test_server.py:27-29`, `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py:21-23`, and `serve/mcp-knowledge/tests/test_ingest_graph_tools.py:37-39`: `_bypass_copilot_auth` still sets `OWLBEAR_LLM_API_KEY` with stale comments. This is dead setup after `#1318`/`#1358`, but it does not assert API-key-present behavior and did not block task proof.
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` and `serve/knowledge/src/owlbear_knowledge/copilot_auth.py` remain present but have no active production imports under `serve/**/src/**`. They are dormant library modules, not active MCP wiring.

### Deductions
- `-0.03` direct `git diff` / `git status` evidence unavailable, so changed-file ownership, TestFromAC immutability, and dirty-tree contamination were reconstructed rather than proven from source control.
- `-0.02` broad package-context run is not fully green; the failing suites appear pre-existing and unrelated, but they prevent full-package clean-slate confirmation.

### Verdict
- **PASS**
- **Confidence:** `0.93`
- **Action:** advance to `docs`

### Post-task Reflection
- Broad package sweeps can surface unrelated historical red; a second task-owned scoped run is necessary to separate regression evidence from background debt.
- Narrow dead-code removals need structural absence proof plus adjacent lifecycle regression, not a raw module-coverage gate.
- Missing git-diff access is survivable for review, but it should always cost confidence because immutability and contamination checks become reconstructed instead of direct.
- Dormant library modules (`llm_extractor.py`, `copilot_auth.py`) are not the same as active wiring; this task correctly removed the wiring without needing to delete the library code.
[[2026-05-05]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified | `serve/mcp-knowledge/README.md` updated by builder (AC3): `OWLBEAR_LLM_API_KEY`, `OPENAI_API_KEY`, and related LLM config lines absent. Read confirmed. |
| 2 | Module docstrings | Yes | N/A | `server.py` module docstring ("FastMCP server for owlbear-mcp-knowledge: knowledge ingestion and search tools.") remains accurate after dead-branch removal. No public class or function docstrings changed by this task. |
| 3 | External attribution | No | N/A | No external patterns cited in task body or research. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc produced. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` has `describes: serve/mcp-*/src/**` — matches changed `serve/mcp-knowledge/src/**`. Footer updated: `Last verified: 2026-05-05 (f260e033)`. Committed `76e620fb`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | Yes | N/A | Deleted files (`test_copilot_server_wiring_888.py`, `test_llmextractor_wiring_876.py`) are test files — OUT scope. No IN-scope doc references these test files or the now-removed env vars (README already cleaned by builder). No orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | OUT (source) | Docstrings verified — no changes needed |
| `serve/mcp-knowledge/README.md` | IN (package README) | Verified accurate — builder updated in AC3 |
| `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py` (deleted) | OUT (test file) | No IN-scope doc references detected |
| `serve/mcp-knowledge/tests/test_llmextractor_wiring_876.py` (deleted) | OUT (test file) | No IN-scope doc references detected |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated (describes-match) |

### Files Updated
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-05-05 (f260e033)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for task 1358)
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 remove `if api_key:` branch | server.py:530 `structured_extractor = None` unconditionally; no env reads | PASS |
| AC2 remove dead imports | grep confirms no `llm_extractor`, `OWLBEAR_LLM_API_KEY`, `OPENAI_API_KEY` in server.py | PASS |
| AC3 README cleanup | reviewer grep confirmed absence of both env var strings | PASS |
| AC4 dead tests removed | `test_copilot_server_wiring_888.py` and `test_llmextractor_wiring_876.py` absent from workspace | PASS |
| AC5 no regression | 12/12 task tests pass; EntityExtractor/IntraDocGraphBuilder receive None at L531-532 | PASS |

### Test Results
- pytest (full suite): 746 passed, 6 failed (all in kanban/memory/state-machine scope, none in mcp-knowledge)
- pytest (task-scoped): 12 passed, 0 failed
- ruff (task scope): clean; violations exist only in unrelated packages (copilot_auth.py T201, tools/ ARG002/F401)

### Architect Quality: 5/5
Specific line numbers, clear verifiability, optional suggestion appropriately scoped. Clean implementation path.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 mapped)
- Lint violations in task scope: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence: present, detailed, methodical (no deduction)
- Full-suite failures in task scope: 0
- Background noise: -0.01 (6 unrelated failures prevent absolute clean-slate confirmation)

### Confidence: 0.99
### Action: archive

### Commits Verified
| Commit | Type | Agent |
|--------|------|-------|
| 087a5eeb | test | test-writer |
| 6444bdb7 | fix | builder |
| 76e620fb | docs | doc-writer |