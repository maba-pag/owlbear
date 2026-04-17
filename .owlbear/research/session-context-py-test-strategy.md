# Session-Context Python Hook Test Strategy

> **Owning task:** #893 — Tests: session-context SessionStart hook equivalence
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #893 requires RED-phase tests for `session-context.py` (the Python port of `session-context.ps1`). The tests must verify the JSON I/O contract, git invocation, failure handling, and malformed input — all via subprocess, all failing RED until #896 creates the implementation.

Key question: what test architecture supports subprocess-level testing with git mocking on all platforms?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | VS Code hooks docs (4/15/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — SessionStart I/O: `{source: "new"}` stdin, `{hookSpecificOutput: {hookEventName, additionalContext}}` stdout |
| 2 | `session-context.ps1` | `.owlbear/hooks/session-context.ps1` | 1.0 — reference implementation, 53 LOC, defines exact I/O contract |
| 3 | `test_session_context_hook_590.py` | `tests/test_session_context_hook_590.py` | 1.0 — prior art, ~450 LOC, covers PS1 version exhaustively |
| 4 | #890 parent / brief | `.owlbear/briefs/draft-macos-compat/brief.md` | .90 — D7 bug-for-bug fidelity, D8 fail-open, D10 clean break |

## 3. Analysis

### 3.1 I/O Contract (from PS1 source)

| Aspect | Value |
|--------|-------|
| Input | stdin JSON (any valid JSON; `{source: "new"}` from VS Code) |
| Output (happy) | `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Branch: X \| Commits: a \| b \| c"}}` |
| Output (error) | `{}` with exit 0 |
| Git commands | `git branch --show-current`, `git log --oneline -3 --no-decorate` |
| Fail-open | Empty stdin, malformed JSON, git failure, no git repo → all return `{}` exit 0 |

### 3.2 Invocation Approach

| Option | Command | Pros | Cons | Fit |
|--------|---------|------|------|-----|
| **A: sys.executable** | `[sys.executable, script_path]` | Uses same Python as test env, no uv dependency | Doesn't test `uv run` path | High |
| B: uv run | `["uv", "run", "python", script_path]` | Matches actual agent invocation | Slower (~500ms uv overhead), uv must be installed | Medium |

**Recommendation: Option A.** The hook is a standalone script using only stdlib (`sys`, `json`, `subprocess`). Testing via `sys.executable` validates the script logic without coupling to the uv launcher. The agent command field (`uv run python`) is an integration concern tested separately.

### 3.3 Git Mocking Strategy

Since the hook runs as a subprocess, Python-level `unittest.mock` cannot intercept its git calls. Options:

| Approach | How | Pros | Cons |
|----------|-----|------|------|
| **A: Fake git on PATH** | Create executable script in tmpdir, prepend to PATH in subprocess env | Full control over git output, verifies exact commands | Requires platform-aware script creation |
| B: Real git in tmpdir repo | `git init` a tmpdir, make commits | No mocking needed | Slower, non-deterministic commit hashes, can't test failure modes |
| C: No git mock | Run in repo as-is | Simplest | Non-deterministic (branch/commits change), can't verify specific commands called |

**Recommendation: Option A (fake git on PATH).** The AC explicitly requires verifying that specific git commands are called. A fake `git` script that logs args to a file and returns controlled output satisfies all AC requirements:
- Verify `git branch --show-current` and `git log --oneline -3 --no-decorate` called
- Control output for deterministic assertions
- Simulate failures (non-zero exit) for error handling tests

Implementation pattern:
```python
# In tmpdir, create executable `git` that logs args and returns controlled output
fake_git = tmp_path / "git"
fake_git.write_text("#!/bin/sh\necho \"$@\" >> git_log.txt\n...")
fake_git.chmod(0o755)
env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
subprocess.run([sys.executable, hook_path], env=env, ...)
```

### 3.4 Test Structure

| Test class | Coverage |
|------------|----------|
| `TestScriptExists` | RED gate: `.owlbear/hooks/session-context.py` exists and is non-empty |
| `TestJsonIoContract` | Happy path: stdin JSON → stdout JSON with `hookSpecificOutput`, `hookEventName`, `additionalContext` |
| `TestGitInvocation` | Fake git verifies exact commands: `branch --show-current`, `log --oneline -3 --no-decorate` |
| `TestGitFailureHandling` | Non-zero git exit → `{}` exit 0, git not found → `{}` exit 0 |
| `TestMalformedInput` | Truncated JSON, empty stdin, BOM prefix, binary data → all `{}` exit 0 |

### 3.5 RED Phase Mechanism

The script `session-context.py` does not exist yet. Tests in `TestScriptExists` fail with assertion error. Tests invoking subprocess fail with `FileNotFoundError` (raised by helper, matching _590 pattern). All tests fail RED.

### 3.6 Differences from _590 Test

| Aspect | _590 (PS1) | #893 (Python) |
|--------|-----------|---------------|
| Target | `session-context.ps1` | `session-context.py` |
| Invocation | `powershell -NoProfile -NonInteractive -File` | `sys.executable` (Python) |
| Platform skip | `@pytest.mark.skipif(sys.platform != "win32")` | None needed |
| Git mocking | None (real git) | Fake git on PATH (AC requirement) |
| Agent config tests | Yes (3 agent frontmatter classes) | No (not in AC) |
| Performance test | Yes (5s limit) | Not in AC, but worth including |

## 4. Recommendation (.90 confidence)

Proceed with test architecture described in §3.2–3.5. The approach is well-grounded in prior art (_590 test), the AC is specific, and the implementation is straightforward (~120 LOC estimated).

Challenge: N/A — trivial adaptation of established pattern. No architectural decisions, no new capabilities, no trade-offs requiring deliberation.

**Tier classification:** T1 — Autonomous. Test file for an established hook pattern.

## 5. Follow-up Tasks

No new follow-up tasks needed. #896 (Port session-context to Python) already exists and depends on #893.
