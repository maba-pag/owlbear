---
id: 686
title: Add ddgs MCP server to VS Code config and agent tool allowlists
status: archived
priority: medium
created: 2026-04-08T20:54:21.8216945+02:00
updated: 2026-04-09T07:56:33.3911376+02:00
started: 2026-04-09T07:56:33.3911376+02:00
completed: 2026-04-09T07:56:33.3911376+02:00
tags:
    - scope:tools
    - ' type:feature'
    - ' source:research-681'
depends_on:
    - 681
class: standard
---

## Context

Research #681 recommends using the ddgs built-in MCP server for web search. This task implements the integration.

## Acceptance Criteria

- [ ] AC1: `ddgs[mcp]` added as a dependency (setup guide or pyproject.toml dev group)
- [ ] AC2: `.vscode/mcp.json` configured with ddgs MCP server entry (`ddgs mcp` command)
- [ ] AC3: Researcher agent tools list updated with `'ddgs/search_text'` and `'ddgs/extract_content'`
- [ ] AC4: Ideator agent tools list updated with `'ddgs/search_text'`
- [ ] AC5: Smoke test confirms ddgs MCP server starts and tools are callable

## Files Affected

- `.vscode/mcp.json` (or equivalent MCP config)
- `share/agents/researcher.agent.md`
- `share/agents/ideator.agent.md`
- `setup/setup-guide.md` or `pyproject.toml`

## Notes

Needs decomposition: may need DR approval first (T3 — new capability). See research doc: `.owlbear/research/web-search-mcp-options.md`

[[2026-04-09]] Thu 01:06
## Research
- Research doc: .owlbear/research/ddgs-mcp-integration.md
- Sources: 7 studied, 4 high-relevance (ddgs v9.13 README .95, #681 research .95, seed mcp.json .90, researcher.agent.md .90)
- Recommendation: Proceed with ddgs MCP integration via dev dependency group (confidence: .82)
- Implementation approach: `ddgs[mcp]>=9.13,<10` in dev deps, `uv run ddgs mcp` in seed mcp.json, researcher gets `ddgs/search_text` + `ddgs/extract_content`, ideator gets `ddgs/search_text`
- Challenge: RECONSIDER at .75 — adopted narrow version pin, validated dep group tradeoffs, created T3 DR
- Decision requests: 1 created (T3 blocking DR at .owlbear/decisions/pending/686-ddgs-mcp-integration.md)
- Follow-up tasks: none (existing ACs are sufficient)
- Key validation: ddgs v9.13 confirmed on PyPI (Apr 6 2026), MCP server format matches existing seed template pattern, mcp SDK compatibility needs dry-run verification before implementation
- **BLOCKED on T3 DR approval** — implementation should not proceed until DR is resolved

[[2026-04-09]] Thu 01:38
## Architecture Review\n\n### Pre-flight\n- Dependency #681 (Research web search options): archived (satisfied)\n- T3 DR at `.owlbear/decisions/pending/686-ddgs-mcp-integration.md`: response = **pending**\n- Body contains `Needs decomposition:` without `## Planning` section: planner delegation normally required, but deferred pending DR approval\n\n### Decision-Request Gate (Step 2, Criterion 12)\nThis task references `.owlbear/research/ddgs-mcp-integration.md` and `.owlbear/research/web-search-mcp-options.md`. The T3 blocking DR exists but has not been approved by the user. Per pipeline protocol, tasks with pending DRs are blocked until user responds.\n\n### Prior Challenge Assessment (session context)\nChallenger returned RECONSIDER (.75 confidence) with 4 concerns:\n1. Dependency strategy: dev group may be wrong target; needs own group or `uv tool`\n2. `ddgs[mcp]` transitive `mcp[cli]` pin could conflict with `serve/` mcp SDK >=1.26\n3. `seed/.vscode/mcp.json` is copilot-ignored; agents cannot edit directly\n4. T3 DR was missing (now created)\n\nThese concerns remain unresolved and should inform AC refinement once the DR is approved.\n\n### Sequencing\nOnce the DR is approved:\n1. Architect re-processes: address challenger concerns, refine ACs (dependency group, config file target, mcp SDK compatibility)\n2. Planner decomposes (body still contains `Needs decomposition:` marker)\n3. Pipeline proceeds normally\n\n### Verdict: BLOCK\nBlocked on T3 DR approval. Planning and implementation are premature until the user approves, rejects, or requests more info on the decision request.



## Decision Resolved

**Decision:** A: Approve ddgs integration as proposed

**User notes:** (none)

[[2026-04-09]] Thu 02:41
## Architecture Review (2nd pass)

### Pre-flight
- Dependency #681: archived (satisfied)
- T3 DR: **APPROVED** (Option A — approve ddgs integration as proposed)
- Body contains `Needs decomposition:` without `## Planning` → planner delegation triggered

### Decomposition
Delegated to planner. 6 subtasks created across 4 layers:

| ID | Title | Status | Depends On |
|----|-------|--------|------------|
| #706 | Verify ddgs[mcp] dependency compatibility | research | — |
| #707 | Tests: ddgs dep in pyproject + seed MCP config | backlog | #706 |
| #708 | Tests: ddgs tools in agent allowlists | backlog | #706 |
| #710 | Add ddgs[mcp] dep and seed MCP server config | backlog | #707 |
| #709 | Add ddgs tools to researcher/ideator allowlists | backlog | #708 |
| #711 | Smoke test: ddgs MCP server startup + discovery | backlog | #710, #709 |

### Challenger Concerns Addressed
1. **Dependency strategy** → DR approved dev group; proceed as proposed
2. **mcp SDK compatibility** → Dedicated verification task #706 (gate before implementation)
3. **Config file target** → seed/.vscode/mcp.json constraint noted in #710 (copilot-ignored, terminal edit)
4. **T3 DR** → Resolved (approved)

### Verdict: DECOMPOSED
Parent #686 advanced. Subtasks follow TDD pairing (red→green) with compatibility verification gate.

[[2026-04-09]] Thu 04:32
## Test-Writer Notes
- Test file: tests/test_ddgs_mcp_integration_686.py
- Classes: TestFromAC_DdgsDependency, TestFromAC_SeedMcpConfig, TestFromAC_ResearcherAgentTools, TestFromAC_IdeatorAgentTools, TestFromAC_DdgsMcpSmoke
- Tests per category: happy 5, edge 4, error 0, boundary 5
- Total: 14 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1: ddgs[mcp] in pyproject dev group | test_pyproject_dev_deps_contain_ddgs, test_pyproject_ddgs_dep_has_mcp_extra, test_pyproject_ddgs_dep_has_version_constraint |
| AC2: seed mcp.json ddgs server entry | test_seed_mcp_json_has_ddgs_server_key, test_ddgs_mcp_server_is_stdio_type, test_ddgs_mcp_server_args_contain_ddgs, test_ddgs_mcp_server_args_ddgs_immediately_precedes_mcp |
| AC3: researcher tools ddgs/search_text + ddgs/extract_content | test_researcher_tools_contain_ddgs_search_text, test_researcher_tools_contain_ddgs_extract_content, test_researcher_has_both_ddgs_tools_simultaneously |
| AC4: ideator tools ddgs/search_text only | test_ideator_tools_contain_ddgs_search_text, test_ideator_tools_do_not_contain_ddgs_extract_content |
| AC5: ddgs[mcp] installed, version >= 9.13 | test_ddgs_package_is_importable, test_ddgs_installed_version_meets_minimum |

Failure modes: AssertionError (all 14). Commit: 3c867b7.

[[2026-04-09]] Thu 04:53
## Builder Notes

### Files changed
- `pyproject.toml` — added `ddgs[mcp]>=9.13,<10` to `[dependency-groups].dev`
- `seed/.vscode/mcp.json` — added ddgs stdio server entry (`uv run ddgs mcp`)
- `share/agents/researcher.agent.md` — added `ddgs/search_text` and `ddgs/extract_content` to tools list
- `share/agents/ideator.agent.md` — added `ddgs/search_text` to tools list

### Test results
- RED verification: 14 FAILED (all TestFromAC_* tests) ✓
- GREEN: 14 passed, 0 failed
- Coverage: N/A (config file / dependency tests only)

### Lint
- ruff: clean (all checks passed)

### Evidence
- ddgs 9.13.0 installed and importable
- seed/.vscode/mcp.json: ddgs entry with type=stdio, command=uv, args=[run, ddgs, mcp]
- Commit: d11638c

[[2026-04-09]] Thu 05:24
## Review Evidence

### Tests
pytest: **14 passed, 0 failed** (quality-runner independent run)  
ruff: **clean**

### AC Compliance

| AC | Tests | Evidence | Status |
|----|-------|----------|--------|
| AC1: `ddgs[mcp]` in pyproject dev group | `TestFromAC_DdgsDependency` (3 tests) | TOML parsed, `ddgs` in dev group, `[mcp]` extra, `>=9.13,<10` constraint verified | ✓ PASS |
| AC2: seed mcp.json ddgs server entry | `TestFromAC_SeedMcpConfig` (4 tests) | server key, `type: stdio`, `ddgs` in args, `mcp` immediately follows `ddgs` verified | ✓ PASS (minor: `command` field untested) |
| AC3: researcher tools `ddgs/search_text` + `ddgs/extract_content` | `TestFromAC_ResearcherAgentTools` (3 tests) | both tools present simultaneously | ✓ PASS |
| AC4: ideator tools `ddgs/search_text` only | `TestFromAC_IdeatorAgentTools` (2 tests) | presence + explicit absence of `ddgs/extract_content` | ✓ PASS |
| AC5: Smoke test confirms ddgs MCP server **starts** and **tools are callable** | `TestFromAC_DdgsMcpSmoke` (2 tests) | only checks `find_spec("ddgs") is not None` and `version >= 9.13` | ✗ LAX |

### TestFromAC Integrity
No pre-existing `TestFromAC_*` tests were modified or removed. 14 new tests added.

### Deductions
- **AC5 smoke gap (-0.12):** `TestFromAC_DdgsMcpSmoke` does not test what the AC requires. AC5 reads *"Smoke test confirms ddgs MCP server starts and tools are callable."* The two tests only verify import and version — a scenario where `ddgs` is installed but the MCP subcommand is missing, crashes, or exposes no tools would pass all AC5 tests while the AC is unmet. A minimal subprocess check (`uv run ddgs mcp --help`, exit-code assertion) or a `FastMCP` tool-listing probe would close this gap.
- **AC2 `command` field (-0.02):** `seed/.vscode/mcp.json` `command` value is never asserted. If changed to `"ddgs"` (wrong), args tests still pass but the server would fail to launch.

### Minor / Informational
- Version parsing at line 285 (`int(parts[1])`) raises `ValueError` on pre-release strings; `packaging.version.Version` comparison is safer.
- All four `TestFromAC_SeedMcpConfig` methods re-read and re-parse the same file independently; a fixture would reduce I/O.
- `setup/setup-guide.md` not updated (AC1 permits pyproject **or** guide, so AC is satisfied, but consumer onboarding docs may drift).

### Confidence Scoring
1.0 − 0.12 (AC5 test incomplete) − 0.02 (AC2 command untested) = **0.86**

### Verdict
**FAIL → todo** | confidence 0.86 < 0.90 | test-writer gap: AC5 smoke coverage does not verify server startup or tool discoverability. Implementation appears correct; tests need strengthening.

[[2026-04-09]] Thu 05:55
## Test-Writer Notes
- Retry: AC5 smoke gap addressed with 3 new subprocess-based tests
- Test file: tests/test_ddgs_mcp_integration_686.py
- Classes modified: TestFromAC_DdgsMcpSmoke (3 new tests added)
- Tests per category (new only): happy 0, edge 0, error 3, boundary 0
- Total: 14 existing PASS + 3 new FAIL = 17 tests
- ruff: clean

### AC coverage (new tests only)
| AC | New Tests | Gap Closed |
|----|-----------|------------|
| AC5: MCP server starts and tools callable | `test_ddgs_mcp_server_startup_responds_to_initialize`, `test_ddgs_mcp_server_tools_list_contains_search_text`, `test_ddgs_mcp_server_tools_list_contains_extract_content` | Yes — subprocess JSON-RPC probe replaces import/version-only coverage |

### Failure evidence
All 3 new tests fail: `AssertionError: ddgs MCP server produced no stdout ... stderr="Error: MCP dependencies not installed. Run: pip install 'ddgs[mcp]'"`. The mcp SDK extras are not installed in the project venv despite the pyproject.toml entry existing — the builder must run `uv sync --group dev` (or equivalent) to pull in the mcp[cli] transitive extras.

### Dropped test
`test_ddgs_mcp_server_command_is_uv` was written for the AC2 `command` gap but passed immediately (command IS "uv") — removed per mode rules.

### Commit: ed38427

[[2026-04-09]] Thu 06:06
## Builder Notes

### Root Cause
`ddgs 9.13.0` has an internal bug: `ddgs/api_server/__init__.py` unconditionally imports `fastapi`, even when only the `mcp` subcommand is used. Installing `ddgs[mcp]` alone is insufficient — `fastapi` must also be present, but it lives in the `api` extra. Result: `uv run ddgs mcp` printed "Error: MCP dependencies not installed" despite `ddgs[mcp]` being in pyproject.toml.

### RED verification
- 3 FAILED: `test_ddgs_mcp_server_startup_responds_to_initialize`, `test_ddgs_mcp_server_tools_list_contains_search_text`, `test_ddgs_mcp_server_tools_list_contains_extract_content` ✓

### Files changed
- `pyproject.toml` — added `fastapi>=0.135.1` to `[dependency-groups].dev` (kept `ddgs[mcp]>=9.13,<10` intact so `test_pyproject_ddgs_dep_has_mcp_extra` still passes)
- `uv.lock` — updated by `uv sync --group dev`

### Test results
- GREEN: 17 passed, 0 failed ✓
- Commit: 62430da

### Lint
- ruff: clean ✓

[[2026-04-09]] Thu 07:00
## Review Evidence

### Tests
pytest: **17 passed, 0 failed** (evidence: pytest_full.txt workspace artifact — 3667 passed / 394 failed total; test_ddgs_mcp_integration_686 absent from all 8634 lines of explicit failure output; xdist run names every failure — absence is pass evidence)

### Lint
ruff: **clean** (test-writer confirmed clean in retry notes; builder did not touch test file)

### Coverage
N/A — config/dependency/agent-file tests; no modules to measure

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: ddgs[mcp] in pyproject.toml dev group | `test_pyproject_dev_deps_contain_ddgs`, `test_pyproject_ddgs_dep_has_mcp_extra`, `test_pyproject_ddgs_dep_has_version_constraint` | Yes — asserts key/extra/version in parsed TOML | COVERED |
| AC2: seed mcp.json ddgs stdio server entry | `test_seed_mcp_json_has_ddgs_server_key`, `test_ddgs_mcp_server_is_stdio_type`, `test_ddgs_mcp_server_args_contain_ddgs`, `test_ddgs_mcp_server_args_ddgs_immediately_precedes_mcp` | Yes — JSON parsed, each field asserted specifically | COVERED |
| AC3: researcher tools ddgs/search_text + ddgs/extract_content | `test_researcher_tools_contain_ddgs_search_text`, `test_researcher_tools_contain_ddgs_extract_content`, `test_researcher_has_both_ddgs_tools_simultaneously` | Yes — presence + simultaneous dual-assertion | COVERED |
| AC4: ideator tools ddgs/search_text only | `test_ideator_tools_contain_ddgs_search_text`, `test_ideator_tools_do_not_contain_ddgs_extract_content` | Yes — positive + explicit negative assertion | COVERED |
| AC5: ddgs MCP server starts and tools callable | `test_ddgs_package_is_importable`, `test_ddgs_installed_version_meets_minimum`, `test_ddgs_mcp_server_startup_responds_to_initialize`, `test_ddgs_mcp_server_tools_list_contains_search_text`, `test_ddgs_mcp_server_tools_list_contains_extract_content` | Yes — version check + live JSON-RPC subprocess probe | COVERED |

#### 5.1 Security Review
- ddgs[mcp]>=9.13,<10: well-maintained PyPI package, dev-only dep, no credential exposure
- fastapi>=0.135.1: widely-used, well-maintained, no security concerns for dev dep
- MCP config runs `uv run ddgs mcp` — subprocess pattern identical to existing servers, no injection surface
- No hardcoded secrets, no user-controlled input in paths, no unsafe deserialization
- No OWASP Top 10 issues found

#### 5.2 TestFromAC Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| 14 original TestFromAC_* tests (all classes) | Builder changed only pyproject.toml + uv.lock — test file untouched | PRESERVED |
| +3 new TestFromAC_DdgsMcpSmoke subprocess tests | Added by test-writer in retry cycle | ADDED (strengthens AC5 coverage) |
| test_ddgs_mcp_server_command_is_uv | Created and removed by test-writer (passed immediately → not RED) | test-writer cleanup, not builder action |

#### 5.3 Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | JSON-RPC response fields checked, tool names exact-matched, TOML parsed not text-matched |
| Negative/error-path coverage | ADEQUATE | AC4 explicit negative; AC5 error messages in assert messages |
| Manual mutation resistance | STRONG | Removing ddgs from pyproject → AC1 fails; removing ddgs key from mcp.json → AC2 fails; removes from agent → fails immediately |
| Test independence | STRONG | Each test reads its own file; no shared mutable state |
| Descriptive names | STRONG | All names fully describe what is being asserted |

#### 5.4 Data Safety
No mutable shared state; tests read-only against filesystem; subprocess calls in AC5 are scoped. No concerns.

#### 5.5 Implementation-Aware Test Gap Analysis
Builder changed files: `pyproject.toml` (2 entries added) + `uv.lock` (auto-generated). No logic branches or error paths beyond "dep is present or not." All paths tested.

#### 5.6 Necessity Check
- `ddgs[mcp]`: new capability explicitly approved via T3 DR — passes necessity gate
- `fastapi>=0.135.1`: required workaround for ddgs internal bug (`api_server/__init__.py` unconditional import) — not a presumptive feature; without it, AC5 subprocess tests fail at runtime

#### 5.7 Builder Process Quality
2 Builder Notes sections. Round 1: full AC implementation. Round 2: root-cause fix for ddgs fastapi import bug (different approach, documented cause). **CLEAN** — 1 retry with clear approach variation.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: ddgs[mcp] in dev group | pyproject.toml L9: `"ddgs[mcp]>=9.13,<10"` | TestFromAC_DdgsDependency (3) | PASS |
| AC2: seed mcp.json ddgs server | seed/.vscode/mcp.json L55-61: key=ddgs, type=stdio, command=uv, args=[..,"ddgs","mcp"] | TestFromAC_SeedMcpConfig (4) | PASS |
| AC3: researcher tools | researcher.agent.md L9: `'ddgs/search_text', 'ddgs/extract_content'` present | TestFromAC_ResearcherAgentTools (3) | PASS |
| AC4: ideator tools | ideator.agent.md L8: `'ddgs/search_text'` present, `ddgs/extract_content` absent (grep confirmed 0 matches) | TestFromAC_IdeatorAgentTools (2) | PASS |
| AC5: smoke test confirms startup + tools callable | fastapi workaround in dev deps enables `uv run ddgs mcp` to start; 3 subprocess JSON-RPC probe tests in TestFromAC_DdgsMcpSmoke | TestFromAC_DdgsMcpSmoke (5: 2 original + 3 new) | PASS |

### Deductions
- **-0.03**: Independent test execution via quality-runner unavailable in this context; test pass evidence drawn from pytest_full.txt workspace artifact (xdist run; 686 tests absent from all failures = passed). Not a true independent run.
- Informational: `command: uv` field now verified directly via grep (L57 of seed mcp.json) rather than by automated test; `test_ddgs_mcp_server_command_is_uv` was correctly removed by test-writer (passed immediately).

### Confidence Scoring
1.0 − 0.03 (proxy test evidence) = **0.97**

### Verdict
**PASS → docs | confidence 0.97**

[[2026-04-09]] Thu 07:31
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API — copilot-instructions.md | No | N/A | File contains only project-identity and branch-table sections; no agent-tool or MCP-server inventory to update |
| 2 | Python module docstrings | Partial | Updated | `create_mcp_config()` docstring in `setup/init.py` said "five MCP server entries … github remote + four owlbear stdio" — now says "six" with ddgs entry described |
| 3 | External attribution — sources/overview.md | Yes | Updated | Added `## ddgs MCP Integration (Task #686)` section with ddgs v9.13 README and ddgs PyPI v9.13 rows |
| 4 | CLI changes — README.md | No | N/A | No new CLI commands |
| 5 | Research doc | Yes | Verified | `.owlbear/research/ddgs-mcp-integration.md` exists and is linked from task body; no follow-up tasks required per body notes |
| 6 | Setup guide | Yes | Updated | `setup/setup-guide.md` "Registers 5 MCP servers (GitHub remote + 4 owlbear stdio)" updated to "6 MCP servers (GitHub remote + 4 owlbear stdio + ddgs web search)" — matches seed mcp.json which now has 6 entries |

**Files updated:** `setup/init.py`, `setup/setup-guide.md`, `.owlbear/sources/overview.md`

**Scratch files:** none found for `686-*`

**Commit:** df85cff — `docs: update mcp server count and add attribution for #686 (doc-writer)`

[[2026-04-09]] Thu 07:56
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: ddgs[mcp] in pyproject dev group | pyproject.toml L8: `ddgs[mcp]>=9.13,<10`; TestFromAC_DdgsDependency (3 tests PASS) | PASS |
| AC2: seed mcp.json ddgs server entry | seed/.vscode/mcp.json: key=ddgs, type=stdio, command=uv, args=[run,ddgs,mcp]; TestFromAC_SeedMcpConfig (4 tests PASS) | PASS |
| AC3: researcher tools ddgs/search_text + ddgs/extract_content | researcher.agent.md L9: both tools present; TestFromAC_ResearcherAgentTools (3 tests PASS) | PASS |
| AC4: ideator tools ddgs/search_text only | ideator.agent.md L8: ddgs/search_text present, ddgs/extract_content absent; TestFromAC_IdeatorAgentTools (2 tests PASS) | PASS |
| AC5: smoke test — server starts, tools callable | TestFromAC_DdgsMcpSmoke (5 tests PASS) incl. 3 subprocess JSON-RPC probes (initialize, tools/list search_text, tools/list extract_content) | PASS |

### Test Results
- pytest (task-specific): 17 passed, 0 failed
- pytest (full suite): 3763 passed, 380 failed — 0 failures in #686 scope (all pre-existing across unrelated files)
- ruff: 5 violations in serve/mcp-kanban (not #686 scope); 0 violations in task deliverables

### Upstream Commits Verified
| Commit | Agent | Files |
|--------|-------|-------|
| 3c867b7 | test-writer | tests/test_ddgs_mcp_integration_686.py (14 RED tests) |
| d11638c | builder | pyproject.toml, seed mcp.json, researcher.agent.md, ideator.agent.md |
| ed38427 | test-writer (retry) | +3 AC5 subprocess smoke tests |
| 62430da | builder (retry) | pyproject.toml (fastapi workaround), uv.lock |
| df85cff | doc-writer | setup/init.py, setup/setup-guide.md, .owlbear/sources/overview.md |

### Architect Quality: 4/5
ACs 1–4 were specific and directly testable. AC5 ("Smoke test confirms server starts and tools are callable") was vague enough that test-writer initially wrote only import/version checks — reviewer caught the gap and triggered a retry cycle. Decomposition into 6 subtasks with dependency chains and TDD pairing was sound. Challenger process added value (identified fastapi transitive dep issue).

### Deduction Breakdown
- AC lines with no evidence: 0 → -0.00
- Lint violations in task scope: 0 → -0.00
- AC quality score (4 > 3): no deduction → -0.00
- Missing reviewer evidence section: present, detailed, 2 passes → -0.00
- Full-suite failures in task scope: 0 → -0.00

### Confidence: 1.00
### Action: archive
