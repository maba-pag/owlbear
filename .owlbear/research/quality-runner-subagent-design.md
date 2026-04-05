# Quality-Runner Subagent — Design Validation & Refinement

> **Owning task:** #263 — Create Quality-Runner subagent (agent.md + skill)
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #263 requests a Quality-Runner utility subagent per the design in `docs/research/subagent-nesting-architecture.md` §3c. This research validates the design, refines the tool list and security model, and confirms implementation readiness. The task is blocked by decision request `228-esub-utility-subagents` (unapproved).

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Built-in Tools Reference | https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .95 — canonical tool identifier list (7 sets, 31+ tools) |
| S2 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — assign vs inherit, agents array override, coordinator/worker |
| S3 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — user-invocable, disable-model-invocation, YAML frontmatter |
| S4 | OwlBear subagent-nesting-architecture.md | Local | .90 — parent research with Quality-Runner interface design |
| S5 | OwlBear pytest-and-linting skill | Local | .95 — 10+ pitfalls the Quality-Runner must encapsulate |
| S6 | OwlBear pipeline agent files (auditor, builder, reviewer, test-writer) | Local | .85 — current tool allocations for Quality-Runner consumers |

## 3. Analysis

### 3a. Tool List Refinement

The parent research (S4) proposed 6 tools. Cross-referencing with the canonical tool list (S1) and the pytest-and-linting skill (S5), the correct count is **8**:

| Tool | Purpose | In S4? | Essential? |
|------|---------|--------|------------|
| `execute/runInTerminal` | Run pytest, ruff, coverage | Yes | Must |
| `execute/getTerminalOutput` | Read background terminal output | Yes | Must |
| `execute/awaitTerminal` | Wait for background completion | Yes | Must |
| `execute/killTerminal` | Kill hung processes | Yes | Must |
| `read/readFile` | File-capture fallback, pyproject.toml | Yes | Must |
| `vscode/memory` | Agent memory for pitfall notes | Yes | Must |
| `read/terminalLastCommand` | Diagnose terminal issues for retries | No | Should |
| `execute/testFailure` | VS Code structured test failure data | No | Should |

**Rationale for additions:** `read/terminalLastCommand` is critical for the retry loop — when a command fails, diagnosing the last command's output helps determine whether to retry or report fatal. `execute/testFailure` provides structured test failure data that supplements raw terminal output parsing.

**Tools explicitly excluded:** `execute/runTests` (VS Code test runner — we use terminal pytest), `read/problems` (redundant with ruff terminal output), `search` (caller provides paths), `edit/*` (read-only agent), `agent` (no sub-subagents), `web` (no internet), `owlbear-kanban/*` (no kanban interaction).

### 3b. Security Model — disable-model-invocation

The parent research recommended `user-invocable: false` WITHOUT `disable-model-invocation: true`. However, the safer pattern used by all existing pipeline agents (S6) is:

| Property | Recommended | Rationale |
|----------|-------------|-----------|
| `user-invocable` | `false` | Hidden from picker (not user-facing) |
| `disable-model-invocation` | `true` | Prevents arbitrary agents from invoking it |
| Parent `agents:` array | Lists `quality-runner` | Overrides disable-model-invocation per S2/S3 |

This follows the principle of least privilege — only agents explicitly listed as consumers can invoke Quality-Runner. VS Code docs confirm: "Explicitly listing an agent in the `agents` array overrides `disable-model-invocation: true`" (S2).

### 3c. Model Selection

Quality-Runner is a mechanical utility agent (run commands, parse output, format report). A lighter model reduces cost and context overhead:

| Model | Suitability | Risk |
|-------|-------------|------|
| Claude Haiku 4.5 (copilot) | Best — fast, cheap, sufficient for structured output | May struggle with complex error diagnosis |
| GPT-5.4 mini (copilot) | Good — fast, cheap | Same risk profile |
| Claude Sonnet 4.6 (copilot) | Overkill — but safer for edge cases | Higher cost |

**Recommendation (.80 confidence):** Prioritized list `[Claude Haiku 4.5 (copilot), GPT-5.4 mini (copilot)]` with Sonnet fallback if Haiku proves insufficient during integration testing.

### 3d. Skill Auto-Loading Risk

When Quality-Runner runs as a subagent, workspace skills should auto-load by relevance (S3). The pytest-and-linting skill (S5) should match when the agent's context mentions "pytest" and "ruff". **Risk:** if skill auto-loading doesn't fire in subagent context, the 10+ pitfalls won't be available.

**Mitigation:** Embed the 5 most critical pitfalls directly in the agent.md body as a fallback:
1. Never pipe `uv run` output through PS cmdlets
2. Use bare `--cov` only (no `--cov=module.path`)
3. Use `isBackground=true` for full-suite runs
4. File-capture fallback for truncated output
5. WMI hang mitigation (kill zombie processes)

The remaining pitfalls (asyncio_mode strict, Rich Console flags, PYTEST_DISABLE_PLUGIN_AUTOLOAD, test markers) are agent-level concerns for the *caller*, not Quality-Runner.

### 3e. I/O Contract Validation

The parent research (S4 §3c) defined input/output contracts. Validated with one refinement:

**Input:** via `runSubagent` prompt — structured fields (mode, test_paths, task_id, coverage_modules, lint_paths). No changes needed.

**Output refinement:** Add `exit_codes` section for downstream decision-making:

```
## Tests
passed: N, failed: [{name, error}], skipped: N

## Lint
clean: bool, violations: [{file, line, code, msg}]

## Coverage
overall_pct: N, modules: [{name, pct}]

## Exit Codes
pytest: N, ruff: N

## Errors
[fatal error messages]
```

Exit codes let callers distinguish "tests failed" (exit 1) from "pytest crashed" (exit 2+) without parsing error text.

## 4. Recommendation (.85 confidence)

The Quality-Runner design from #228 is **valid and implementation-ready** with three refinements:

1. **8 tools** (add `read/terminalLastCommand` and `execute/testFailure`)
2. **Use `disable-model-invocation: true`** with explicit `agents:` array override in consumers
3. **Embed top 5 pitfalls** in agent body as skill-loading fallback

The task remains blocked by decision request `228-esub-utility-subagents`. No implementation should begin until that decision is approved.

## 5. Follow-up Tasks

No new tasks needed — #263 (create agent) and #264 (wire into pipeline) already exist with appropriate scope. The refined AC below should be applied to #263 by the architect.

**Refined AC for #263:**
- [ ] `agents/quality-runner.agent.md` exists with 8 assign-mode tools
- [ ] `user-invocable: false`, `disable-model-invocation: true`
- [ ] Model: `[Claude Haiku 4.5 (copilot), GPT-5.4 mini (copilot)]`
- [ ] Agent body embeds top 5 pytest-and-linting pitfalls
- [ ] Agent body specifies I/O contract (input fields, output sections with exit codes)
- [ ] Max 2 internal retries before reporting failure
- [ ] Timeout: 5 min full suite, 2 min scoped
- [ ] `skills/quality-runner/SKILL.md` documents consumer integration patterns
