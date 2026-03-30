---
id: 198
title: Expand validate_agents.py to check all tool names against canonical registry
status: todo
priority: nice-to-have
created: 2026-03-29T23:08:48.2138586+02:00
updated: 2026-03-30T06:17:57.1400882+02:00
tags:
    - phase-1
    - tooling
    - agent
    - config
blocked: true
block_reason: 'Test-writer must resolve contradictions: (1) test_tools_todos_passes vs test_todos_with_other_tools_still_errors, (2) test_todo_prefix_substring_does_not_trigger vs _check_unknown_tools requirement. See Builder Notes for details.'
class: standard
---

## Objective

Expand validate_agents.py to validate ALL tool names in agent frontmatter against a registry of known VS Code built-in toolsets and standalone tool names. Catches typos, hallucinated tools, and future stale references automatically.

## Acceptance Criteria

- [ ] `KNOWN_TOOLSETS` frozenset constant with the canonical VS Code tool set prefixes: `agent`, `browser`, `edit`, `execute`, `read`, `search`, `web`, `vscode`
- [ ] `KNOWN_STANDALONE_TOOLS` frozenset constant with standalone tool names not under any toolset prefix: `newWorkspace`, `selection`
- [ ] Both constants have a comment citing the source (VS Code Copilot cheat sheet 2026-03-25 + docs/research/stale-tool-names.md) and a note to update when VS Code adds new toolsets
- [ ] New `_check_unknown_tools()` helper called from `validate_agent()`: parses each tool name from `_tools_text()` output, validates against the registry
- [ ] Tool name validation rules — a name is valid if ANY of: (a) exact match in KNOWN_TOOLSETS (toolset shorthand like `search`), (b) prefix before first `/` is in KNOWN_TOOLSETS (e.g. `execute/runInTerminal`), (c) exact match in KNOWN_STANDALONE_TOOLS, (d) ends with `/*` (MCP server wildcard pattern)
- [ ] Unknown tool produces error message: `"{file}: tools: unknown tool '{name}' — not a recognized VS Code built-in or MCP server pattern"`
- [ ] Existing ban checks (from #193: todos, manage_todo_list; original: resolveMemoryFileUri, bare todo) remain unchanged — banned tools are NOT also reported as unknown (no double errors)
- [ ] Validator exits 0 on all 11 current agents/*.agent.md files

## Architecture Notes

Use **toolset-prefix matching** rather than enumerating every individual tool. This avoids the "stale list on day 1" problem identified in the research doc — the VS Code cheat sheet omits several confirmed-active tools (execute/awaitTerminal, execute/killTerminal, execute/runTests, read/viewImage, edit/rename, vscode/memory). Prefix matching under known toolsets (`execute/*`, `read/*`, etc.) passes all of them without listing each one.

The MCP wildcard pattern (ends with `/*`) handles all current MCP server references: 'owlbear-kanban/*', 'microsoft/markitdown/*'.

## Patterns to follow

- Existing `_tools_text()` already extracts the tools: block from frontmatter — reuse it
- YAML list parsing: split on `,` within `[]`, strip quotes and whitespace — same trivial parsing already implicit in the regex checks
- Follow the existing check structure: helper function returns list of error strings, called from `validate_agent()`
- Run order: ban checks first (specific deny), then unknown-tool check (general allow-list) — so a banned tool never shows as "unknown"

## Files to touch

- `scripts/validate_agents.py` (~30 LOC: add constants, add `_check_unknown_tools()`, call from `validate_agent()`)
- `tests/test_validate_agents.py` (~40 LOC: new test class)

## Context

See docs/research/stale-tool-names.md for the canonical tool list analysis.
Depends on: #193 (Ban manage_todo_list/todos) should land first to avoid merge conflicts — but not a hard dependency since both add to the same function.

[[2026-03-30]] Mon 05:01
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| KNOWN_TOOLSETS frozenset | Precise: 8 named prefixes, matches VS Code cheat sheet toolset structure | Keep |
| KNOWN_STANDALONE_TOOLS frozenset | Precise: 2 named tools, matches cheat sheet standalones | Keep |
| Source comment on constants | Verifiable: builder can check comment exists | Keep |
| _check_unknown_tools() helper | Clear interface, follows existing pattern | Keep |
| Validation rules (a)-(d) | Covers all current agent tool formats: shorthands, prefixed, MCP wildcards | Keep |
| Error message format | Template-literal, verifiable by test | Keep |
| Ban checks remain separate | Prevents double-reporting, verifiable | Keep |
| Validator exits 0 on current agents | Already covered by test_script_exits_zero_on_current_agents | Keep |

### Architecture Notes
Toolset-prefix matching is the key design decision. The VS Code cheat sheet is explicitly non-exhaustive (6+ active tools missing). Enumerating every individual tool would require constant maintenance. Prefix matching (agent, browser, edit, execute, read, search, web, vscode) covers all current and future tools within known toolsets.

Codebase verified: scripts/validate_agents.py (93 LOC), tests/test_validate_agents.py (400+ LOC). Existing _tools_text() extracts the tools: block. Existing ban checks pattern (resolveMemoryFileUri, bare todo) provides the template.

#193 (Ban manage_todo_list/todos) is in-progress and modifies the same files. Soft dependency -- #198 should land after #193 to avoid merge conflicts on validate_agent() function body.

### Changes Made
- Rewrote AC from 6 vague lines to 8 precise, testable lines
- Added Architecture Notes, Patterns to follow, Files to touch sections
- Approved to todo

### Dependencies
- Verified: docs/research/stale-tool-names.md exists (source doc)
- Soft: #193 (in-progress) modifies same files -- no hard dep but sequencing recommended

[[2026-03-30]] Mon 05:37
## Test-Writer Notes\n- Test file: tests/test_validate_agents.py\n- Classes: TestFromAC_KnownToolsConstants, TestFromAC_CheckUnknownToolsHelper, TestFromAC_UnknownToolErrors, TestFromAC_UnknownToolErrorMessage, TestFromAC_NoBannedToolDoubleError\n- Tests per category: happy 0, edge 4, error 9, boundary 7\n- Total: 20 tests, all FAIL\n- ruff: clean\n- AC8 (exits 0 on current agents): covered by existing TestFromAC_ValidateAgentsIntegration

[[2026-03-30]] Mon 06:17
## Builder Notes
BLOCK - interface mismatch: two pairs of irreconcilable TestFromAC constraints.

Contradiction 1 - todos ban:
- TestFromAC_ValidateAgentsTodoCheck::test_tools_todos_passes (task #134, PASSING): expects tools: [todos, read/readFile] returns no errors.
- TestFromAC_BanTodosToolCheck::test_todos_with_other_tools_still_errors (#193): expects same input to produce errors. Mutually exclusive.

Contradiction 2 - unknown-tool check vs old boundary test:
- TestFromAC_ValidateAgentsTodoCheck::test_todo_prefix_substring_does_not_trigger (PASSING): expects [todos, todo_extra] returns no errors.
- TestFromAC_UnknownToolErrors::test_hallucinated_tool_name_produces_error (#198): requires fly_to_moon to produce unknown-tool error.
- _check_unknown_tools flags both fly_to_moon AND todo_extra as unknown (same class: not in KNOWN_TOOLSETS, no slash, not in KNOWN_STANDALONE_TOOLS). No principled exclusion differentiates them.

Resolution required (test-writer):
1. Update test_tools_todos_passes and test_multiline_tools_todos_passes: todos now banned by #193.
2. Update test_todo_prefix_substring_does_not_trigger: todo_extra is unknown tool; assert the unknown error IS present, or scope test to only verify bare-todo check does not fire.
3. Implement and complete #193 before re-dispatching #198.
