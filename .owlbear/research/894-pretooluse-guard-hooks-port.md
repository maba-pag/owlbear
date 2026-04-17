# PreToolUse Guard Hooks — Python Port Validation

> **Owning task:** #894 — Port PreToolUse guard hooks to Python (5 hooks)
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #894 requires porting 5 PowerShell PreToolUse guard hooks to Python. Dependency #891 (equivalence tests, 109 test cases) is archived/done. The brief (D5, D7, D8) mandates Python via `uv run python`, bug-for-bug fidelity, and fail-open behavior.

**Question:** What implementation approach is needed, and is there existing work?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | deny-writes.ps1 (original) | `.owlbear/hooks/deny-writes.ps1` | 1.0 |
| 2 | deny-code-writes.ps1 | `.owlbear/hooks/deny-code-writes.ps1` | 1.0 |
| 3 | deny-src-writes.ps1 | `.owlbear/hooks/deny-src-writes.ps1` | 1.0 |
| 4 | deny-scratch-only-writes.ps1 | `.owlbear/hooks/deny-scratch-only-writes.ps1` | 1.0 |
| 5 | allow-stances-only.ps1 | `.owlbear/hooks/allow-stances-only.ps1` | 1.0 |
| 6 | Python ports (all 5) | `.owlbear/hooks/{name}.py` | 1.0 |
| 7 | Equivalence tests (#891) | `tests/test_pretooluse_hooks.py` | 1.0 |
| 8 | #891 research doc | `.owlbear/research/891-pretooluse-hooks-test-approach.md` | 0.9 |
| 9 | macOS compat brief | `.owlbear/briefs/draft-macos-compat/brief.md` | 0.8 |

## 3. Analysis — PS1 ↔ PY Behavioral Parity

| Hook | Guard Type | PS1 Pattern | PY Pattern | Parity |
|------|-----------|-------------|------------|--------|
| deny-writes | tool-name | `-contains` (case-insens.) | `in` set (case-sens.) | ✓ Equiv¹ |
| deny-code-writes | deny-list | 10 prefixes + `conftest.py` exact, strip `./` | Same prefixes/exact/strip | ✓ Exact |
| deny-src-writes | allow-list | `(^|/)tests/` regex | Same regex | ✓ Exact |
| deny-scratch-only | allow-list | `(^|/)\.owlbear/scratch/` regex | Same regex | ✓ Exact |
| allow-stances-only | allow-list | `(/|^)stances/` regex, strip `./` | Same regex/strip | ✓ Exact |

¹ PS1 `-contains` is case-insensitive; PY `in` is case-sensitive. VS Code tool names are always lowercase — no functional difference.

### Shared behaviors verified

- **Write tools gated:** 6 tools in all hooks (create_file, replace_string_in_file, multi_replace_string_in_file, apply_patch, create_directory, editFiles)
- **Path extraction:** filePath, dirPath, replacements[].filePath, files[] (string or object)
- **Normalization:** `\` → `/` in all path-checking hooks; `./` strip in deny-code-writes and allow-stances-only
- **Fail-open:** JSON parse error → `{}` exit 0 (all 5)
- **Deny response:** `{"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "..."}}` with identical reason strings
- **Test coverage:** 109/109 tests pass (subprocess invocation, full I/O contract)

### Minor PS1 inconsistency ported (D7)

PS1 originals mix `-contains` (case-insensitive) and `-cnotcontains` (case-sensitive) for tool name matching. PY versions are all case-sensitive. No functional impact — tool names are always lowercase.

## 4. Recommendation

**Implementation pre-exists and is complete.** Confidence: **0.95**.

All 5 Python scripts exist at `.owlbear/hooks/{name}.py`, match PS1 originals bug-for-bug (D7), preserve fail-open (D8), and pass all 109 equivalence tests from #891. No additional implementation work required.

Challenge: SKIP — validation finding, no recommendation with alternatives.

## 5. Follow-up Tasks

No follow-up tasks needed. All AC items are satisfied by existing code:
- 5 scripts exist ✓, stdin JSON / stdout JSON ✓, deny-list/allow-list logic ✓
- hookSpecificOutput structure ✓, fail-open ✓, bug-for-bug fidelity ✓, 109 tests GREEN ✓

Tier: **T1 — Autonomous.** Port is mechanical and already complete.
