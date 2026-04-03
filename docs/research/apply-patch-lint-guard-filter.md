# apply_patch Lint Guard Filter Extension

> **Owning task:** #546 — Add apply_patch to #210 lint guard tool_name filter
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

Task #210 implements a PostToolUse lint guard hook (`scripts/hooks/lint-changed.ps1`)
that runs ruff after file edits. Its AC filters on three tool_names:
`create_file`, `replace_string_in_file`, `multi_replace_string_in_file`. Empirical
verification (#532, s3.6) discovered the builder also uses `tool_name: "apply_patch"`
for file edits. This task investigates the gap and how to close it.

**Question:** What changes are needed to include `apply_patch` in the lint guard filter,
and what is the `apply_patch` tool_input structure for file path extraction?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| #532 empirical verification | docs/research/posttooluse-subagent-output-routing.md s3.6 | 1.0 — confirmed `tool_name: "apply_patch"` in hook log |
| VS Code Hooks docs (4/2/2026) | code.visualstudio.com/docs/copilot/customization/hooks | .95 — PostToolUse I/O schema, `$TOOL_INPUT_FILE_PATH` env var |
| VS Code Hooks FAQ | (same page, FAQ section) | .85 — VS Code uses camelCase `tool_input.filePath` |
| #210 test file | tests/test_lint_guard_hook_210.py | 1.0 — current tool_input conventions |

## 3. Analysis

### 3.1 Regex Addition — Trivial

The PowerShell script matches tool_name via regex. Adding `|apply_patch` to the
existing `create_file|replace_string_in_file|multi_replace_string_in_file` pattern
is a one-token change.

### 3.2 Path Extraction — Unknown tool_input Format

The existing tools use these tool_input structures (per test file conventions):

| tool_name | Path location |
|-----------|--------------|
| `create_file` | `tool_input.filePath` |
| `replace_string_in_file` | `tool_input.filePath` |
| `multi_replace_string_in_file` | `tool_input.replacements[*].filePath` |
| `apply_patch` | **Unknown** — not captured in #532 |

Two likely structures for `apply_patch`:

| Possibility | Format | Path extraction |
|-------------|--------|----------------|
| A: filePath field | `{"filePath": "...", "patch": "..."}` | Same as create_file |
| B: patch-only | `{"patch": "--- a/file.py\n+++ b/file.py\n..."}` | Parse `+++ b/` headers |

### 3.3 Alternative: $TOOL_INPUT_FILE_PATH

VS Code docs Quick Start shows `$TOOL_INPUT_FILE_PATH` env var for PostToolUse hooks.
If VS Code populates this for `apply_patch`, path extraction is trivial (read env var).
However, the #210 design reads stdin JSON — switching to env vars would change the
approach. Not recommended for #546 scope; could be a future simplification.

### 3.4 Dependency

#546 modifies deliverables from #210 (the script and test file). #210 is currently
`in-progress`. #546 must wait for #210 to complete. `depends_on: [210]` required.

## 4. Recommendation (.85 confidence)

**T1 — Autonomous.** No T3 triggers (no new capability, no arch change, no security
impact). This extends an existing filter with one additional value.

**Implementation approach:**

1. Add `|apply_patch` to the tool_name regex in `lint-changed.ps1`
2. For path extraction: try `tool_input.filePath` first (likely available per VS Code
   camelCase convention). If absent, parse diff headers from `tool_input.patch`. If
   neither yields a path, return `{}` (graceful degradation matches existing AC).
3. Add test cases for `apply_patch` in `test_lint_guard_hook_210.py` — parallel to
   existing AC3a-AC3f but with `tool_name: "apply_patch"` and `tool_input.filePath`.
4. Builder should log actual `apply_patch` tool_input JSON during implementation to
   confirm the exact format (empirical verification, same approach as #532).

Challenge: FALLBACK — no recommendation to challenge (T1 filter extension).

## 5. Follow-up Tasks

#546 already exists at `ideation`. No new tasks needed. Updates:
- Add `depends_on: [210]` — script must exist before it can be modified
- Refine AC with tool_input discovery guidance from section 4
