# Add `run_command` to Default Approval Policy

> **Owning task:** #461 — Add run_command to default approval policy
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-05 from `docs/security-audit.md`: the default `approval_policy` gates `git_push`, `create_pr`, and `deploy` — but `run_command` (shell execution via `asyncio.create_subprocess_shell()`) is ungated. An LLM can execute arbitrary shell commands without user approval. This is the single highest-impact security misconfiguration (OWASP A05:2021).

**Question:** Should `run_command` be added to the default approval policy? Any nuances to consider?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Anthropic Computer Use Docs | <https://platform.claude.com/docs/en/docs/agents-and-tools/computer-use> | .85 | "Asking a human to confirm decisions that may result in meaningful real-world consequences"; auto-classifier steers to user confirmation on prompt injection |
| PydanticAI ApprovalRequiredToolset | <https://ai.pydantic.dev/toolsets/#requiring-tool-approval> | .90 | Framework-native tool approval gates; `ApprovalRequiredToolset` wraps any toolset |
| OwlBear security audit (SEC-05) | `docs/security-audit.md` L132-155 | 1.0 | Identifies missing `run_command` gate as HIGH severity |
| OwlBear approval gates research | `docs/research/approval-gates.md` | .95 | Prior art analysis; chose `ApprovalGateToolset(WrapperToolset)` pattern |
| VS Code Copilot agent mode | (built-in behavior) | .80 | Requires explicit user confirmation before every terminal command execution |

## 3. Analysis

### 3.1 Should ALL shell execution require approval?

| Approach | Pros | Cons | KISS |
|----------|------|------|------|
| A: Gate all `run_command` calls (.90) | Maximum safety; matches VS Code Copilot behavior | Approval fatigue for frequent shell use | High |
| B: Gate only commands matching blocklist patterns (.50) | Less friction | Regex blocklist proven bypassable (SEC-01, SEC-04) | Low |
| C: Gate with session pre-grants (.85) | Safety + UX balance | Already supported by `ApprovalSession` | High |

**Key insight:** Option A is the correct default. Users who want less friction can (1) use session pre-grants (`ApprovalSession.grant("run_command")`) which already work, or (2) remove `run_command` from their config's `approval_policy`. The *default* must be secure.

### 3.2 Implementation surface

The change is a **1-line default value edit** in `src/owlbear/config.py`:

| Component | File | Current state | Change needed |
|-----------|------|---------------|---------------|
| Default policy | `config.py` L78-83 | 3 rules: `git_push`, `create_pr`, `deploy` | Add `{"tool_name": "run_command"}` |
| Bootstrap wiring | `bootstrap.py` L628-653 | `TerminalToolset` already in `_destructive` set | None — already wrapped by `ApprovalGateToolset` |
| Policy model | `safety/policy.py` | `requires_approval()` checks tool name match | None — works as-is |
| Tests | `tests/test_approval_policy.py` | Tests policy model, not default config | Add test for default config including `run_command` |

### 3.3 Risk assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Approval fatigue (too many prompts) | Medium | Session pre-grants already supported; user can approve once per session |
| Existing users lose automation | Low | Config override removes `run_command` from policy; N/A for OwlBear's current user base |
| Breaking existing tests | Low | No test asserts the absence of `run_command` in defaults |

## 4. Recommendation (.95 confidence)

Add `{"tool_name": "run_command"}` to the default `approval_policy` in `config.py`. This is a 1-line change with zero architectural risk. The mechanism is already fully wired — `TerminalToolset` is in the `_destructive` set and gets wrapped by `ApprovalGateToolset`. The only missing piece is the rule.

Write one test: verify that `OwlBearSettings().approval_policy` includes a dict with `tool_name == "run_command"`, and that `ApprovalPolicy` built from those defaults returns `True` for `requires_approval("run_command", {})`.

## 5. Follow-up Tasks

Task #461 itself is the implementation task. No additional tasks needed — the fix is atomic.

```powershell
kanban\kanban-md.exe edit 461 --body "SEC-05 fix: Add run_command to default approval_policy in config.py.\n\n**AC:**\n- [ ] config.py approval_policy default includes {\"tool_name\": \"run_command\"}\n- [ ] Test: OwlBearSettings().approval_policy contains run_command entry\n- [ ] Test: ApprovalPolicy built from defaults returns requires_approval(\"run_command\", {}) == True\n- [ ] No other code changes needed (TerminalToolset already in _destructive set)\n\nSee docs/research/run-command-approval-gate.md for details."
```
