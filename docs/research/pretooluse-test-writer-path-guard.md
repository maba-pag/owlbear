# PreToolUse Path Guard — Test-Writer Agent (Phase 3)

> **Owning task:** #589 — Add PreToolUse path guard hook to test-writer agent (Phase 3)
> **Date:** 2026-04-04 **Status:** Complete
> **Parent research:** `docs/research/agent-scoped-hooks.md` §3.3

## 1. Context and Question

Validation pass on #589 AC. Parent research (#37) recommends a PreToolUse path guard
for the test-writer at .80 confidence. This doc validates feasibility against current
codebase state and identifies AC gaps found during challenger review.

## 2. Sources Studied

| # | Source | Location/URL | Relevance |
|---|--------|-------------|-----------|
| 1 | VS Code hooks docs (4/1/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — PreToolUse input schema, `tool_input` field naming, `$TOOL_INPUT_FILE_PATH` env var |
| 2 | Parent research (#37) | `docs/research/agent-scoped-hooks.md` §3.1–3.5 | 1.0 — per-agent guard catalog, boundary map, hook mechanism |
| 3 | `scripts/hooks/deny-writes.ps1` | In-repo: established Phase 2 pattern | 1.0 — tool-name matching, JSON I/O, deny response format |
| 4 | `tests/test_deny_writes_hook_211.py` | In-repo: 26-test contract suite for Phase 2 | 1.0 — test pattern for hook scripts |
| 5 | `test-writer.agent.md` frontmatter | In-repo: current tools list, no hooks yet | 1.0 — baseline for hook addition |

## 3. Analysis

### 3.1 Codebase Validation

| Prerequisite | Status | Evidence |
|-------------|--------|----------|
| `chat.useCustomAgentHooks: true` | Enabled | `.vscode/settings.json` line 60 |
| Phase 2 pattern deployed | Working | `deny-writes.ps1` + `reviewer.agent.md` hooks frontmatter |
| Test-writer has no hooks | Confirmed | `test-writer.agent.md` frontmatter — no `hooks:` key |
| Test pattern exists | 26 tests | `test_deny_writes_hook_211.py` — subprocess + JSON + YAML |

**Verdict:** Parent findings hold. Approach is feasible and follows established pattern.

### 3.2 AC Gap Analysis (Challenger Findings)

| ID | Gap | Severity | Impact |
|----|-----|----------|--------|
| G1 | `rename` tool in tools list but not in hook deny list | High | Rename can move files into `packages/`, bypassing guard |
| G2 | `multi_replace_string_in_file` uses `tool_input.replacements[].filePath` (nested) | High | Flat `tool_input.filePath` check misses nested paths |
| G3 | `create_directory` uses `tool_input.dirPath`, not `filePath` | Medium | AC edge-case rule ("missing filePath → {}") would allow through |
| G4 | `apply_patch` `tool_input` structure unverified | Low | May embed paths in diff headers only, not a top-level field |
| G5 | Deny-list (`packages/`) vs allow-list (`tests/`) not justified | Medium | Allow-list is more restrictive and simpler |

### 3.3 Deny-List vs Allow-List

| Approach | Blocked | Allowed | Complexity | Security |
|----------|---------|---------|-----------|----------|
| **Deny-list** (`packages/`) | `packages/*` only | Everything else (`.github/`, `scripts/`, root) | Low — one prefix check | Moderate — unknown paths pass |
| **Allow-list** (`tests/`) | Everything except `tests/` | `tests/*` only | Low — one prefix check | High — unknown paths blocked |

Test-writer's legitimate write scope per `w-tdd-red`: only `tests/test_*.py` files.
MCP tool calls (kanban, memory) bypass hooks — so `kanban/` write access isn't needed in the hook.

**Recommendation: allow-list.** Check path starts with `tests/` (or absolute equivalent).
Deny everything else. Simpler and more secure than enumerating deny prefixes.

### 3.4 `rename` Tool Mitigation

Two options:

| Option | Description | Effort | Confidence |
|--------|-------------|--------|------------|
| A — Remove from tools list | Drop `edit/rename` from test-writer tools | 0 LOC | .90 — test-writer never needs rename |
| B — Add to hook with path checks | Check `oldPath`/`newPath` fields | ~10 LOC | .60 — field names unverified |

**Recommendation: Option A.** The test-writer creates new test files; it does not rename
existing files. Removing `edit/rename` from the tools list eliminates the bypass at the
primary enforcement layer with zero implementation cost.

### 3.5 Path Extraction Strategy

The script must extract file paths from heterogeneous `tool_input` schemas:

| Tool | Path field | Extraction |
|------|-----------|------------|
| `create_file` | `filePath` | Direct |
| `replace_string_in_file` | `filePath` | Direct |
| `multi_replace_string_in_file` | `replacements[].filePath` | Iterate array |
| `create_directory` | `dirPath` | Direct (different key) |
| `apply_patch` | Unknown | Skip — return `{}` (safe default, low risk) |

Script pseudocode: extract all paths from `filePath`, `dirPath`, and `replacements[*].filePath`.
If ANY path does not start with `tests/` (or `tests\`), deny. If no paths found, return `{}`.

## 4. Recommendation (.75 confidence)

**Challenge:** `block` — confidence in original: 0.35.
**Researcher response:** Accepted G1 (rename), G2 (nested paths), G3 (dirPath), G5 (allow-list).
Revised AC. Rebutted T2 classification — these are AC refinements within the established
pattern, not new capabilities or architecture changes. Still T1.

**Revised AC (proposed):**

1. Create `scripts/hooks/deny-src-writes.ps1` — PreToolUse hook that extracts file paths
   from `tool_input.filePath`, `tool_input.dirPath`, and `tool_input.replacements[*].filePath`,
   denies when ANY path does not start with `tests/` (allow-list approach)
2. Add PreToolUse hook to `test-writer.agent.md` frontmatter
3. Remove `edit/rename` from test-writer's tools list (bypass prevention)
4. Script returns `{}` for non-write tools, missing paths, empty tool_name
5. Agent file parses as valid YAML frontmatter
6. `chat.useCustomAgentHooks` already enabled (prerequisite from #209)

**Known limitation:** `run_in_terminal` bypasses PreToolUse hooks entirely (terminal
writes are opaque). Documented in parent research §3.4. Not addressable at the hook layer.

## 5. Follow-up Tasks

No new follow-up tasks required. #589 AC should be revised per §4. Existing follow-ups
#590 (SessionStart) and #591 (doc-writer path guard) remain valid at `someday` priority.

**Tier classification:** T1 — Autonomous. AC refinements within established hook pattern.
No new capabilities, no architecture changes, no security policy modifications.
