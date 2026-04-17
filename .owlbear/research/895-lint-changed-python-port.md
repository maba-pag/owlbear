# lint-changed.py Port — Validation Research

> **Owning task:** #895 — Port lint-changed PostToolUse hook to Python
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #895 (GREEN phase) ports `.owlbear/hooks/lint-changed.ps1` to Python. The .py file already exists (likely from an earlier builder pass). Tests from #892 exist at `tests/test_lint_changed_hook.py` (30+ test cases). This research validates the existing implementation against the AC and .ps1 for bug-for-bug fidelity (D7) before advancing to backlog for GREEN verification.

**Question:** Does the existing `lint-changed.py` satisfy all AC items and maintain fidelity with the .ps1 original?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | VS Code Hooks docs — PostToolUse I/O | code.visualstudio.com/docs/copilot/customization/hooks | 1.0 |
| 2 | lint-changed.ps1 (dev) | `.owlbear/hooks/lint-changed.ps1` | 1.0 |
| 3 | lint-changed.py (dev) | `.owlbear/hooks/lint-changed.py` | 1.0 |
| 4 | #892 test file | `tests/test_lint_changed_hook.py` | 1.0 |
| 5 | #892 research | `.owlbear/research/892-lint-changed-hook-test-approach.md` | 0.9 |
| 6 | macOS compat brief | `.owlbear/briefs/draft-macos-compat/brief.md` | 0.9 |
| 7 | Brief decisions | `.owlbear/briefs/draft-macos-compat/decisions.md` | 0.9 |
| 8 | #547 additionalContext research | `.owlbear/research/posttooluse-additionalcontext-lint-feedback.md` | 0.8 |

## 3. Analysis

### 3.1 Bug-for-Bug Fidelity (.ps1 → .py)

| Aspect | .ps1 | .py | Match |
|--------|------|-----|-------|
| Edit tools | 4 (create_file, replace_string, multi_replace, apply_patch) | 5 (same + editFiles) | Superset — intentional per AC |
| Path extraction | filePath, replacements[].filePath | filePath, replacements[].filePath, files[] | Superset — intentional per AC |
| File filter | None (all files to ruff) | .py only | Enhanced — intentional per AC |
| Dedup | Case-insensitive HashSet | Case-insensitive set (`.lower()`) | Equivalent |
| Ruff args | `ruff check --ignore INP001 @paths` | `["ruff", "check", "--ignore", "INP001", *paths]` | Equivalent |
| Exit code check | `$LASTEXITCODE -eq 1` → report | `returncode == 1` → report | Equivalent |
| Output JSON | systemMessage + hookSpecificOutput | systemMessage + hookSpecificOutput | Equivalent |
| Fail-open | try/catch → `{}` exit 0 | except Exception → `{}` return | Equivalent |
| BOM handling | Implicit (ConvertFrom-Json) | Explicit strip | Enhanced — safe |
| Stdin | `[Console]::In.ReadToEnd()` | `sys.stdin.buffer.read()` | Equivalent |
| Exit code | Always 0 | Always 0 (implicit from `main()` return) | Equivalent |

All .ps1 behaviors preserved. Three intentional expansions match AC requirements.

### 3.2 AC Coverage

| AC | Requirement | .py Status |
|----|-------------|------------|
| 1 | `.owlbear/hooks/lint-changed.py` created | ✅ 110 lines |
| 2 | Reads JSON, extracts paths (filePath, dirPath, replacements[], editFiles[]) | ✅ dirPath implicit — not an edit tool, filtered by .py ext |
| 3 | Filters to existing .py files, deduplicates | ✅ `.endswith(".py")` + `Path.is_file()` + case-insensitive |
| 4 | Runs `ruff check --ignore INP001` via subprocess | ✅ |
| 5 | Returns JSON with systemMessage + hookSpecificOutput | ✅ matches docs |
| 6 | Non-zero ruff exit captured, no crash | ✅ `check=False` |
| 7 | Fail-open: exception → `{}` exit 0 | ✅ broad except handlers |
| 8 | Bug-for-bug fidelity (D7) | ✅ see §3.1 |
| 9 | All #892 tests pass | ❓ builder must verify |

### 3.3 PostToolUse Output Validation (VS Code docs, April 2026)

The .py uses `systemMessage` (user-facing warning) + `hookSpecificOutput.additionalContext` (model-facing context). This is non-blocking — no `decision: "block"`. Confirmed correct by #547 research: `additionalContext` reaches subagent models via `<PostToolUse-context>` XML wrapping.

## 4. Recommendation (confidence: 0.92)

**The existing implementation is correct and ready for GREEN verification.** No code changes needed — the builder's GREEN task is to run the #892 tests and confirm all pass.

One minor observation: `dirPath` in the AC is handled implicitly (not an edit tool → `{}`, or not `.py` → filtered). This is correct behavior and the #892 test `test_dirpath_returns_empty_dict` confirms it. No explicit extraction needed.

Challenge: skipped — validation research on existing implementation with no design alternatives.

## 5. Follow-up Tasks

No new follow-up tasks needed. The GREEN phase (#895 itself) is the actionable next step.
