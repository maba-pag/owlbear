# PreToolUse Guard Hooks — Test Approach

> **Owning task:** #891 — Tests: PreToolUse guard hooks equivalence (5 hooks)
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #890 (macOS compat) requires porting 7 PowerShell hooks to Python. Task #891 is the RED-phase test file for the 5 PreToolUse guard hooks. The existing codebase has 4 separate PowerShell test files (test_deny_writes_hook_211.py, test_deny_code_writes_hook_591.py, test_deny_src_writes_hook_589.py, test_deny_scratch_only_writes_hook_685.py) plus no tests for allow-stances-only. All invoke PowerShell via subprocess.

**Question:** What is the correct testing approach for a single consolidated parameterized test file that covers all 5 hooks via Python subprocess?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | VS Code Hooks docs — PreToolUse I/O | code.visualstudio.com/docs/copilot/customization/hooks | 1.0 |
| 2 | deny-writes.ps1 | `.owlbear/hooks/deny-writes.ps1` | 1.0 |
| 3 | deny-code-writes.ps1 | `.owlbear/hooks/deny-code-writes.ps1` | 1.0 |
| 4 | deny-src-writes.ps1 | `.owlbear/hooks/deny-src-writes.ps1` | 1.0 |
| 5 | deny-scratch-only-writes.ps1 | `.owlbear/hooks/deny-scratch-only-writes.ps1` | 1.0 |
| 6 | allow-stances-only.ps1 | `.owlbear/hooks/allow-stances-only.ps1` | 1.0 |
| 7 | editFiles schema research #638 | `.owlbear/research/editfiles-schema-verification-638.md` | 0.9 |
| 8 | test_deny_code_writes_hook_591.py | `tests/test_deny_code_writes_hook_591.py` | 0.9 |
| 9 | test_deny_src_writes_hook_589.py | `tests/test_deny_src_writes_hook_589.py` | 0.9 |

## 3. Analysis

### 3.1 Shared I/O Contract (all 5 hooks)

- **stdin:** `{"tool_name": "...", "tool_input": {...}}` (additional VS Code fields like `timestamp`, `cwd`, `sessionId` are ignored by all hooks)
- **stdout allow:** `{}` (empty JSON object)
- **stdout deny:** `{"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "..."}}`
- **exit code:** always 0
- **fail-open:** malformed/empty/binary stdin → `{}` + exit 0

### 3.2 Hook Behavior Summary

| Hook | Guard Type | Write Tools Gated | Path Check | Normalization |
|------|-----------|-------------------|------------|---------------|
| deny-writes | tool-name only | 6 tools | None (no path extraction) | N/A |
| deny-code-writes | deny-list paths | 6 tools (incl. apply_patch, editFiles) | Prefix deny-list (10 dirs + 1 exact) | `\` → `/`, strip `./` |
| deny-src-writes | allow-list paths | 6 tools (incl. apply_patch, editFiles) | `(^|/)tests/` regex | `\` → `/` |
| deny-scratch-only | allow-list paths | 6 tools (incl. apply_patch, editFiles) | `(^|/)\.owlbear/scratch/` regex | `\` → `/` |
| allow-stances-only | allow-list paths | 6 tools (incl. apply_patch, editFiles) | `(/|^)stances/` regex | `\` → `/`, strip `./` |

### 3.3 Path Extraction Fields (4 path-checking hooks share this)

| Field | Tools | Format |
|-------|-------|--------|
| `tool_input.filePath` | create_file, replace_string_in_file, apply_patch | string |
| `tool_input.dirPath` | create_directory | string |
| `tool_input.replacements[*].filePath` | multi_replace_string_in_file | array of objects |
| `tool_input.files[*]` | editFiles | array of strings (or objects with `.filePath`) |

### 3.4 Test Structure Recommendation

| Aspect | Approach | Rationale |
|--------|----------|-----------|
| Invocation | `subprocess.run(["uv", "run", "python", script])` | Matches future agent.md `command:` pattern; tests full I/O contract |
| Parameterization | Data-driven fixtures per hook | Each hook has unique allow/deny rules; shared malformed-input tests |
| RED guarantee | Scripts at `.owlbear/hooks/{name}.py` don't exist | FileNotFoundError or subprocess failure = RED |
| File | `tests/test_pretooluse_hooks.py` | Single consolidated file per AC |
| Markers | `pytest.mark.slow` (subprocess I/O) | Consistent with existing hook tests |

### 3.5 Test Case Matrix

| Category | deny-writes | deny-code-writes | deny-src-writes | deny-scratch-only | allow-stances-only |
|----------|-------------|-------------------|-----------------|-------------------|--------------------|
| Allow input | non-write tool | write to README.md | write to tests/foo.py | write to .owlbear/scratch/x | write to stances/arch.md |
| Deny input | write tool | write to serve/x.py | write to serve/x.py | write to serve/x.py | write to serve/x.py |
| Edge: backslash | N/A | `serve\\foo.py` → denied | `tests\\foo.py` → allowed | `.owlbear\\scratch\\x` → allowed | `stances\\foo.md` → allowed |
| Edge: leading ./ | N/A | `./serve/foo.py` → denied | N/A (no strip in .ps1) | N/A (no strip in .ps1) | `./stances/foo.md` → allowed |
| Edge: no paths | N/A | write tool, empty tool_input → allow | same | same | same |
| Multi-path (mixed) | N/A | replacements with 1 denied → deny all | same | same | same |
| editFiles format | N/A | `files: ["serve/x.py"]` → denied | `files: ["tests/x.py"]` → allowed | `files: [".owlbear/scratch/x"]` → allowed | `files: ["stances/x"]` → allowed |
| Malformed JSON | `{}` exit 0 | `{}` exit 0 | `{}` exit 0 | `{}` exit 0 | `{}` exit 0 |

## 4. Recommendation (confidence: 0.92)

**Follow the established subprocess-based testing pattern** from existing hook tests, adapted for Python invocation. Single file, data-driven parameterization, shared malformed-input tests. No design alternatives to weigh — the AC prescribes the approach, and 4 prior test files validate the pattern.

Challenge: skipped — info-only research confirming a prescribed approach with no alternatives.

Key implementation notes for the test-writer:
1. Helper: `_run_hook(hook_name: str, stdin_data: dict | str) -> tuple[int, dict]` — invokes `uv run python .owlbear/hooks/{hook_name}.py`
2. The helper should raise `FileNotFoundError` when the .py script doesn't exist (makes RED failures explicit)
3. For raw/malformed input tests, accept `str | bytes` as stdin to bypass JSON serialization
4. deny-writes is the only hook that doesn't extract paths — it just checks tool_name
5. The 4 path-checking hooks all share the same path extraction logic and can reuse test infrastructure

## 5. Follow-up Tasks

No new follow-up tasks needed — #894 (GREEN phase: port hooks to Python) already exists as the dependency target.
