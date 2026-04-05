# Deny-Code-Writes AC Validation — #637

> **Owning task:** #637 — Revise #591 AC: deny-list script for doc-writer path guard
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #637 holds revised AC (from #591 research) for a deny-list PreToolUse hook
(`deny-code-writes.ps1`) protecting doc-writer from writing to source code dirs.
**Question:** Are the AC correct, complete, and implementable as written?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | deny-src-writes.ps1 (allow-list pattern) | `.owlbear/hooks/deny-src-writes.ps1` | 1.0 |
| 2 | deny-writes.ps1 (blanket deny, includes apply_patch) | `.owlbear/hooks/deny-writes.ps1` | 0.9 |
| 3 | lint-changed.ps1 (apply_patch path extraction) | `.owlbear/hooks/lint-changed.ps1` | 0.9 |
| 4 | #591 research doc | `.owlbear/research/pretooluse-doc-writer-path-guard-591.md` | 1.0 |
| 5 | #546 task + tests (apply_patch schema) | `tests/test_lint_guard_hook_546.py` | 0.8 |
| 6 | Doc-writer agent boundaries | `share/agents/doc-writer.agent.md` | 1.0 |
| 7 | VS Code hooks docs (PreToolUse schema) | `code.visualstudio.com/docs/copilot/customization/hooks` | 1.0 |
| 8 | test-writer hook registration pattern | `share/agents/test-writer.agent.md` | 0.7 |

## 3. Analysis

### 3.1 Deny-List Completeness

| Dir/File | In AC1? | Should deny? | Rationale |
|----------|---------|-------------|-----------|
| `serve/` | Yes | Yes | Main source code |
| `v1/` | Yes | Yes | Legacy source code |
| `tests/` | Yes | Yes | Test files |
| `setup/` | Yes | Yes | Setup scripts |
| `.owlbear/hooks/` | Yes | Yes | Hook scripts |
| `.owlbear/scripts/` | Yes | Yes | Automation scripts |
| `conftest.py` | Yes | Yes | Shared test config |
| **`seed/`** | **No** | **Yes** | Template files — edits corrupt future scaffolds |
| **`store/`** | **No** | **Yes** | MCP-managed data — direct writes bypass APIs |
| **`share/agents/`** | **No** | **Yes** | Self-modification: doc-writer could remove its own hook |
| **`.git/`** | **No** | **Yes** | `.git/hooks/` = privilege escalation vector |
| `pyproject.toml` | No | No | Low risk — instruction-enforced |
| `share/skills/` | No | No | Doc files, not in agent boundaries either — instruction-enforced |

**Gap summary:** 4 entries missing from AC1 deny-list: `seed/`, `store/`, `share/agents/`, `.git/`.

### 3.2 Write-Tool Gate — `editFiles` Gap

VS Code docs (source 7) show `editFiles` as a real `tool_name` in PreToolUse hooks:
```json
{ "tool_name": "editFiles", "tool_input": { "files": ["src/main.ts"] } }
```
Doc-writer's tools list includes `edit/editFiles`. AC2 write-tools array omits it.
Path schema uses `tool_input.files[]` (array), not `tool_input.filePath` (string).

| Tool | In AC2? | tool_input path field |
|------|---------|---------------------|
| `create_file` | Yes | `filePath` (string) |
| `replace_string_in_file` | Yes | `filePath` (string) |
| `multi_replace_string_in_file` | Yes | `replacements[*].filePath` |
| `create_directory` | Yes | `dirPath` (string) |
| `apply_patch` | Yes | `filePath` (string) — confirmed by #546 |
| **`editFiles`** | **No** | **`files[]` (array)** — from VS Code docs |

**Risk:** Without `editFiles` in the gate, doc-writer can bypass the deny-list entirely
via `edit/editFiles` tool calls.

### 3.3 apply_patch Schema — Resolved

#546 tests confirm `apply_patch` uses `tool_input.filePath`. Known Limitation about
unverified schema can be removed. Multi-file patching risk is low — note as advisory.

### 3.4 Dependency Status

#589 is archived (complete). Dependency met.

## 4. Recommendation (confidence: .80)

**AC is fundamentally sound with 5 amendments needed:**

| # | Amendment | Type | Confidence |
|---|-----------|------|-----------|
| R1 | Add `seed/`, `store/`, `share/agents/`, `.git/` to AC1 deny-list | Blocking | .90 |
| R2 | Add `editFiles` to AC2 write-tools array | Blocking | .85 |
| R3 | Add `files[]` array extraction to AC1 path extraction logic | Blocking | .85 |
| R4 | Remove "apply_patch schema unverified" Known Limitation | Advisory | .95 |
| R5 | Add Known Limitation: `editFiles` `files[]` schema based on docs — verify empirically | Advisory | .75 |

Challenge: proceed — confidence in original: .80. Challenger validated B1 (share/agents/
self-modification), B3 (editFiles gap). Researcher accepted both as blocking amendments.
A1 (.git/ escalation) accepted. B2 (share/ scope) deferred — boundary documentation is
a separate concern.

## 5. Follow-up Tasks

| # | Title | Status | Scope |
|---|-------|--------|-------|
| A | Update #637 AC with 5 amendments above | ideation | Edit task body |
| B | Implement deny-code-writes.ps1 + hook registration | follows A | Core deliverable |
