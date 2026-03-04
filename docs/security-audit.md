# OwlBear Security Audit Report

> **Owning task:** Security audit request
> **Date:** 2026-03-03 **Status:** Complete

## Executive Summary

OwlBear is a laptop-resident AI system with **broad system access**: shell execution, filesystem operations, browser automation, network requests, and Slack integration — all directed by LLM-generated decisions. This architecture creates a large attack surface where **prompt injection is the primary threat vector**: a compromised or manipulated LLM can invoke any tool with arbitrary arguments.

The project has a **strong security posture relative to its design goals** — path traversal guards on filesystem tools, URL safety guards on browser navigation, a command blocklist, and approval gates for destructive operations. However, several high-severity issues exist around the fundamental reliance on regex-based command guards, plaintext token storage, and the absence of process-level sandboxing for shell execution.

**Critical/High findings: 5 | Medium: 7 | Low: 4 | Info: 3**

---

## Findings

### SEC-01 — Shell Command Injection via Terminal Toolset
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **CRITICAL** |
| **Affected** | `src/owlbear/tools/terminal.py` L172 |

**Description:** `TerminalToolset.run_command()` passes LLM-provided command strings directly to `asyncio.create_subprocess_shell()`. The only defense is the regex-based `CommandSafetyGuard`, which is fundamentally bypassable.

**Evidence:**
```python
# terminal.py L172
proc = await asyncio.create_subprocess_shell(
    command,  # <-- LLM-controlled string
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=cwd,
)
```

**Bypass examples for the guard patterns:**
- `rm -rf /` blocked, but `rm  -rf  /` (double space), `r\m -rf /` or `find / -delete` are not
- `echo cm0gLXJmIC8K | base64 -d | bash` encodes `rm -rf /`
- `python -c "import shutil; shutil.rmtree('/')"` uses a different vector
- `;` and `&&` chaining after an innocent command
- Environment variable expansion: `$PATH` manipulation

**Recommendation:** This is an unavoidable design tension — OwlBear *needs* shell execution. Mitigate with:
1. Add `run_command` to the default approval policy (require user approval for every shell command)
2. Consider allowlist-only mode for shell commands in production
3. Add process-level sandboxing (e.g., restrict to workspace directory via `--restricted-shell` or container)

---

### SEC-02 — Terminal Toolset Has No Working Directory Confinement
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **HIGH** |
| **Affected** | `src/owlbear/tools/terminal.py` L160-167 |

**Description:** The `working_dir` parameter accepts any absolute path. While filesystem tools are sandboxed to `workspace_root`, terminal commands can operate on the entire filesystem.

**Evidence:**
```python
# terminal.py L164-167
if working_dir is None:
    cwd = self._workspace_root
else:
    cwd_path = Path(working_dir)
    cwd = cwd_path if cwd_path.is_absolute() else self._workspace_root / cwd_path
    # No validation that cwd is within workspace_root
```

**Recommendation:** Apply the same `_safe_path` pattern from `FileToolset` — validate that `working_dir` resolves within `workspace_root`. Log and reject attempts to escape.

---

### SEC-03 — Token Stored as World-Readable Plaintext
| Field | Value |
|---|---|
| **OWASP** | A02:2021 Cryptographic Failures |
| **Severity** | **HIGH** |
| **Affected** | `src/owlbear/auth/copilot.py` L175-179 |

**Description:** `save_token()` writes the Copilot session token as plaintext JSON to `~/.owlbear/copilot_token.json` using `Path.write_text()` with default permissions. On multi-user systems, other users can read this file. On Windows, the default ACL inherits from the parent directory.

**Evidence:**
```python
# copilot.py L175-179
def save_token(token_data: dict[str, Any], path: Path | None = None) -> None:
    path = path or _DEFAULT_TOKEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token_data))  # <-- no permission restriction
```

**Recommendation:**
1. Set restrictive file permissions after write: `os.chmod(path, 0o600)` on Unix, or use Windows ACL APIs
2. Consider using the OS credential store (Windows Credential Manager / macOS Keychain) for token storage
3. At minimum, set restrictive permissions on the `~/.owlbear/` directory itself

---

### SEC-04 — Command Guard Blocklist Is Fundamentally Bypassable
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **HIGH** |
| **Affected** | `src/owlbear/core/command_guard.py` L24-37 |

**Description:** The `DEFAULT_BLOCKED_COMMANDS` list uses regex patterns to block dangerous commands. Regex-based blocklists are provably insufficient for shell command safety — the shell language has too many ways to express the same operation.

**Evidence:**
```python
DEFAULT_BLOCKED_COMMANDS: list[str] = [
    r"rm\s+-rf\s+/",           # bypassable: rm -r -f /, rm --recursive --force /
    r"git\s+push\s+--force",   # bypassable: git push -f
    r"(?<!uv )(?<!uv run )pip\s+install",  # bypassable: python -m pip install
    r"format\s+[cC]:",         # Windows-specific
    r"del\s+/[sS]\s+/[qQ]",   # bypassable: del /S/Q or powershell equivalents
    r"sudo\s+rm",              # bypassable: su -c "rm ..."
]
```

**Specific bypasses:**
- `rm -r -f /` (space between flags)
- `git push -f origin main` (`-f` not `--force`)
- `python -m pip install malware`
- `powershell -c "Remove-Item -Recurse -Force C:\"`

**Recommendation:** The blocklist provides defense-in-depth but should not be the primary control. Primary control should be the approval gate (SEC-01). Expand the blocklist to cover common variations, but document that it is not a security boundary.

---

### SEC-05 — `run_command` Not in Default Approval Policy
| Field | Value |
|---|---|
| **OWASP** | A05:2021 Security Misconfiguration |
| **Severity** | **HIGH** |
| **Affected** | `src/owlbear/config.py` L81-85 |

**Description:** The default `approval_policy` gates `git_push`, `create_pr`, and `deploy` — but `run_command` (shell execution) is NOT gated. This means an LLM can execute arbitrary shell commands without user approval.

**Evidence:**
```python
# config.py L81-85
approval_policy: list[dict[str, Any]] = [
    {"tool_name": "git_push"},
    {"tool_name": "create_pr"},
    {"tool_name": "deploy"},
    # run_command is MISSING
]
```

**Recommendation:** Add `{"tool_name": "run_command"}` to the default approval policy. This is the single most impactful change for improving OwlBear's security posture.

---

### SEC-06 — JavaScript Injection in Browser Title Prefix
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/tools/browser/toolset.py` L110 |

**Description:** The `task_label` parameter is interpolated directly into a JavaScript string passed to `page.evaluate()` without escaping. A `task_label` containing a single quote breaks the JS or allows arbitrary code execution in the browser context.

**Evidence:**
```python
# toolset.py L110
await self.page.evaluate(f"document.title = '{prefix} ' + document.title")
# If prefix = "Task'; alert('xss');//", this becomes:
# document.title = 'Task'; alert('xss');//' + document.title
```

**Recommendation:** Use `page.evaluate()` with argument passing instead of string interpolation:
```python
await self.page.evaluate("(prefix) => { document.title = prefix + ' ' + document.title }", prefix)
```

---

### SEC-07 — CDP Mode Inherits Full Browser Session
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/tools/browser/toolset.py` L112, `src/owlbear/tools/browser/manager.py` L96 |

**Description:** In CDP mode, OwlBear attaches to the user's existing browser, gaining access to all authenticated sessions, cookies, and stored credentials. The code warns about this (`logger.warning("CDP mode: attached to user browser — full session access")`), but there are no mitigations.

**Evidence:**
```python
# manager.py L96
self._context = self._browser.contexts[0]  # <-- user's authenticated context
self._page = await self._context.new_page()
```

**Recommendation:**
1. Create a new isolated context (`browser.new_context()`) in CDP mode instead of reusing `contexts[0]`
2. Document the security implications clearly for users who enable CDP mode
3. Consider adding a config flag like `cdp_isolated_context: bool = True`

---

### SEC-08 — Error Messages Leak to Communication Channels
| Field | Value |
|---|---|
| **OWASP** | A02:2021 Cryptographic Failures / Sensitive Data Exposure |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/daemon.py` L228, L234, L237; `src/bearclaw/cli.py` L1090 |

**Description:** Exception details are sent to the user channel (Slack or CLI) via `f"Error: {exc}"`. Exception messages from HTTP libraries can include URLs with tokens, authentication headers, or internal infrastructure details.

**Evidence:**
```python
# daemon.py L237
await channel.send(f"Error: {exc}")

# cli.py L1090
await channel.send(f"Error: {exc}")
```

**Recommendation:** Sanitize error messages before sending to channels. Create an `error_to_user_message()` helper that strips sensitive data (URLs, headers, full stack traces) and returns only the error category and a safe description.

---

### SEC-09 — ReDoS in Filesystem Search Content Regex
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/tools/filesystem.py` L202 |

**Description:** The `content_regex` parameter in `_search_files` is compiled from LLM-provided input without complexity guards. A malicious regex like `(a+)+b` applied against large files can cause catastrophic backtracking (ReDoS), consuming CPU indefinitely.

**Evidence:**
```python
# filesystem.py L202
compiled = re.compile(content_regex) if content_regex else None
# No timeout, no complexity limit
```

**Recommendation:**
1. Wrap regex compilation in a try/except for `re.error`
2. Set a timeout using `re.search` with a watchdog or use the `regex` library with timeout support
3. Reject patterns exceeding a complexity heuristic (e.g., nested quantifiers)

---

### SEC-10 — URL Safety Guard Tool Name Mismatch
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/tools/browser/safety.py` L75 |

**Description:** The `URLSafetyGuard` hook callback checks for `tool_name == "navigate"`, but the actual registered tool name is `"browser_navigate"`. The hook would never match via the PRE_TOOL_USE hook pathway — only the direct `check_url()` call in `browser_navigate()` action provides protection.

**Evidence:**
```python
# safety.py L75
if data.get("tool_name") != "navigate":  # <-- checks for "navigate"
    return

# toolset.py L152 — registered as "browser_navigate"
self.add_function(self._navigate, name="browser_navigate", ...)
```

The direct call in `actions.py` L49 (`guard.check_url(url)`) does work, so navigation IS protected. But the hook-based guard path is broken — defense-in-depth is compromised.

**Recommendation:** Change the hook check to `"browser_navigate"` or add both names. Also add a test that verifies the hook integration works end-to-end.

---

### SEC-11 — Knowledge Intake Has No Path Sandboxing
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/memory/knowledge/intake.py` L36-42 |

**Description:** The `read_file()` function in the intake module reads any file path without sandboxing. If an LLM-directed ingestion specifies a path like `/etc/passwd` or `~/.ssh/id_rsa`, the content will be ingested into the knowledge base.

**Evidence:**
```python
# intake.py L36-42
async def read_file(path: str | Path) -> IntakeResult:
    p = anyio.Path(path)
    content = await p.read_text(encoding="utf-8")  # <-- no path validation
    return IntakeResult(content=content, source=str(p), ...)
```

**Recommendation:** Add a workspace-root validation check similar to `FileToolset._safe_path()`, or require that ingestion paths are explicitly approved.

---

### SEC-12 — "Approve All" Grants Are Session-Wide Without Scope Limits
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **MEDIUM** |
| **Affected** | `src/owlbear/safety/gate.py` L146-153, `src/owlbear/safety/policy.py` L94-109 |

**Description:** When a user responds "approve all git_push", all future `git_push` calls are approved for the entire session with no further review. The grant applies to any arguments — so approving one `git push origin main` also approves `git push --force origin main`.

**Evidence:**
```python
# gate.py L146-153
if normalised.startswith("approve all "):
    tool_to_grant = normalised[len("approve all "):]
    self.session.grant(tool_to_grant)  # <-- blanket grant, no arg constraints
```

**Recommendation:**
1. Limit pre-grants to a configurable maximum number of uses (e.g., 5)
2. Add expiry: clear pre-grants after N minutes
3. Consider arg-scoped grants ("approve all git_push to origin/main")

---

### SEC-13 — Dependencies Use Minimum Version Specifiers
| Field | Value |
|---|---|
| **OWASP** | A06:2021 Vulnerable and Outdated Components |
| **Severity** | **LOW** |
| **Affected** | `pyproject.toml` L13-25 |

**Description:** All dependencies use `>=` specifiers (e.g., `httpx>=0.28.0`). While a `uv.lock` file exists (which pins exact versions for reproducible installs), the `pyproject.toml` allows any future version — including potentially compromised releases — when the lockfile is regenerated.

**Evidence:**
```toml
dependencies = [
  "httpx>=0.28.0",
  "openai>=1.60.0",
  ...
]
```

**Mitigating factor:** The `uv.lock` file exists, providing actual version pinning for installations.

**Recommendation:** This pattern is standard and acceptable with a lockfile. Consider running `uv audit` or `pip-audit` in CI to catch known vulnerabilities. Add a Dependabot or Renovate configuration for automated security updates.

---

### SEC-14 — No Dedicated Security Audit Log
| Field | Value |
|---|---|
| **OWASP** | A09:2021 Security Logging and Monitoring Failures |
| **Severity** | **LOW** |
| **Affected** | Multiple files — security events use standard Python logging |

**Description:** Security-relevant events (blocked commands, approval decisions, authentication failures, token refreshes) are logged via Python's `logging` module mixed with application logs. The `RotatingFileHandler` in `daemon.py` rotates at 5MB with 3 backups — security events can be lost in rotation.

**Evidence:** The `ErrorJournal` exists but tracks operational errors, not security events. Approval decisions are emitted as POST_TOOL_USE hook events (written to `events.jsonl` via `ObservabilityHook`), which is good, but there's no separation or alerting for security events specifically.

**Recommendation:**
1. Create a dedicated `SecurityAuditLog` that writes to a separate, append-only file
2. Log: blocked commands, approval prompts/decisions, authentication events, path traversal attempts, URL blocks
3. Do not rotate the security log (or rotate with longer retention)

---

### SEC-15 — Slack Message Queue Not Sanitized
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **LOW** |
| **Affected** | `src/owlbear/channels/slack.py` L259-264 |

**Description:** Messages from Slack DMs are placed into the `_message_queue` and fed to the agent as user prompts with no sanitization. While this is the intended behavior (user messages drive the agent), a compromised Slack workspace could inject crafted prompts.

**Evidence:**
```python
# slack.py L259-264
if event.get("type") == "message" and event.get("channel_type") == "im":
    text = event.get("text", "")
    await self._message_queue.put(text)  # <-- raw Slack message
```

**Recommendation:** This is inherent to the design (Slack IS an input channel). Mitigate with:
1. Validate that messages come from expected user IDs (not bots or unauthorized users)
2. Add rate limiting on incoming messages
3. Log all incoming Slack messages for audit purposes

---

### SEC-16 — `os.startfile` in CLI Channel
| Field | Value |
|---|---|
| **OWASP** | A01:2021 Broken Access Control |
| **Severity** | **LOW** |
| **Affected** | `src/owlbear/channels/cli.py` L74 |

**Description:** `send_file()` calls `os.startfile(path)` on Windows, which opens a file in the default system handler. If the LLM can control the path, it could open executables or documents that trigger macro execution.

**Evidence:**
```python
if sys.platform == "win32" and hasattr(os, "startfile"):
    os.startfile(path)  # noqa: S606
```

**Recommendation:** Restrict `startfile` to known-safe file types (images, text) or require user confirmation before opening.

---

### SEC-17 — Schema Migrations Use f-string Table Names
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **INFO** |
| **Affected** | `src/owlbear/memory/knowledge/schema.py` L172, L323 |

**Description:** Schema migration functions use f-strings to construct SQL with table names:
```python
conn.execute(f"ALTER TABLE {table} ADD COLUMN scope TEXT DEFAULT 'global'")
conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_scope ON {table}(scope)")
```
The table names come from a hardcoded constant (`_SCOPE_TABLES`), so this is not exploitable. Noted for awareness only.

**Recommendation:** No action needed — the table names are compile-time constants. The `# noqa: S608` suppressions are justified.

---

### SEC-18 — Ingest Pipeline SQL Uses Parameterized f-strings Correctly
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **INFO** |
| **Affected** | `src/owlbear/memory/knowledge/ingest.py` L238-243 |

**Description:** The `delete_document_data` method builds placeholder strings dynamically but passes values as parameters:
```python
placeholders = ", ".join("?" for _ in entity_ids)
conn.execute(f"DELETE FROM edges WHERE source_id IN ({placeholders})", [...entity_ids...])
```
This pattern is safe — the f-string only constructs the `?` placeholder list, while actual values go through parameterized binding.

**Recommendation:** No action needed. Pattern is correct.

---

### SEC-19 — Subprocess Calls in Hooks Use Hardcoded Commands
| Field | Value |
|---|---|
| **OWASP** | A03:2021 Injection |
| **Severity** | **INFO** |
| **Affected** | `src/owlbear/core/lint_hook.py`, `context_hook.py`, `test_hook.py`, `subagent_hook.py` |

**Description:** Several hooks invoke `subprocess.run()` with `# noqa: S603`. In all cases, the commands are constructed from hardcoded values (`["uv", "run", "ruff", "check", ...]`), not user input. The `lint_hook.py` does interpolate a `file_path` from tool args, but this comes from the LLM — however, the worst case is that `ruff` receives an unusual path argument, which is low-risk.

**Recommendation:** The `lint_hook.py` should validate that `file_path` is within the workspace before passing it to `ruff`. Other hooks are safe.

---

## Overall Security Posture

| Area | Rating | Notes |
|---|---|---|
| **Filesystem Access Control** | **Good** | `_safe_path()` with resolve + boundary check, null byte rejection |
| **Browser URL Safety** | **Good** | Blocklist + allowlist with regex, CDP localhost-only validation |
| **Approval Gates** | **Adequate** | Present but missing `run_command` — the most dangerous tool |
| **Command Guard** | **Weak** | Regex blocklist is defense-in-depth only, not a security boundary |
| **Token Storage** | **Weak** | Plaintext JSON file with no permission restrictions |
| **Error Handling** | **Adequate** | Structured error classification, but messages leak to channels |
| **Dependency Management** | **Good** | Lockfile exists, minimum versions specified |
| **Logging & Audit** | **Adequate** | Observability hooks exist but no dedicated security audit trail |
| **Input Validation** | **Adequate** | Generally good on filesystem/browser, weak on terminal/regex |
| **Subprocess Security** | **Mixed** | `create_subprocess_shell` for terminal (risky), `create_subprocess_exec` for git/kanban (safe) |

### Priority Remediation Order

1. **SEC-05** — Add `run_command` to default approval policy (immediate, minimal effort)
2. **SEC-03** — Restrict token file permissions (immediate, minimal effort)
3. **SEC-02** — Add working directory confinement to terminal toolset (low effort)
4. **SEC-08** — Sanitize error messages before sending to channels (low effort)
5. **SEC-06** — Fix JS injection in browser title (trivial fix)
6. **SEC-10** — Fix URL safety guard tool name mismatch (trivial fix)
7. **SEC-11** — Add path sandboxing to knowledge intake (medium effort)
8. **SEC-07** — Isolate browser context in CDP mode (medium effort)
9. **SEC-04/01** — Document guard limitations, consider allowlist mode (design decision)
10. **SEC-14** — Dedicated security audit log (medium effort)

## Follow-up Tasks

```
kanban\kanban-md.exe create "SEC-05: Add run_command to default approval policy" --priority critical --status todo --tags "security,config" --body "Add {\"tool_name\": \"run_command\"} to the default approval_policy in config.py. This is the single highest-impact security fix — shell execution is currently ungated. AC: run_command in default policy, tests verify it triggers approval."

kanban\kanban-md.exe create "SEC-03: Restrict token file permissions" --priority needed --status todo --tags "security,auth" --body "Set 0o600 permissions on copilot_token.json after write in save_token(). On Windows, restrict ACL to current user. AC: token file not readable by other users, test verifies permissions."

kanban\kanban-md.exe create "SEC-02: Add working directory confinement to terminal toolset" --priority needed --status todo --tags "security,tools" --body "Validate that working_dir resolves within workspace_root in TerminalToolset.run_command(). AC: PermissionError raised for paths outside workspace, test covers traversal attempt."

kanban\kanban-md.exe create "SEC-08: Sanitize error messages sent to channels" --priority needed --status todo --tags "security,channels" --body "Create error_to_user_message() helper that strips URLs, headers, and stack traces. Use in daemon.py and cli.py error paths. AC: no raw exception sent to channel, test verifies sanitization."

kanban\kanban-md.exe create "SEC-06+10: Fix browser JS injection and URL guard mismatch" --priority needed --status todo --tags "security,browser" --body "1) Use page.evaluate() with argument passing instead of f-string in toolset.py setup(). 2) Fix URLSafetyGuard hook to check 'browser_navigate' not 'navigate'. AC: both issues fixed with tests."

kanban\kanban-md.exe create "SEC-11: Add path sandboxing to knowledge intake" --priority important --status todo --tags "security,knowledge" --body "Add workspace-root boundary check to intake.py read_file(). AC: PermissionError for paths outside workspace, test covers traversal."

kanban\kanban-md.exe create "SEC-07: Isolate browser context in CDP mode" --priority important --status todo --tags "security,browser" --body "In BrowserManager._enter_cdp(), create a new browser context instead of reusing contexts[0]. AC: CDP mode uses isolated context, test verifies no cookie sharing."

kanban\kanban-md.exe create "SEC-14: Create dedicated security audit log" --priority important --status backlog --tags "security,observability" --body "Create SecurityAuditLog class that writes blocked commands, approvals, auth events to a separate append-only file. AC: security events in dedicated file, not lost in log rotation."

kanban\kanban-md.exe create "SEC-09+12: Harden regex and approval grants" --priority important --status backlog --tags "security,tools" --body "1) Add try/except for re.error in _search_files content_regex. 2) Add max-uses limit and expiry to ApprovalSession pre-grants. AC: malformed regex handled gracefully, grants expire."
```

## Attribution Updates

| Source | URL | What | Where Used | Date |
|---|---|---|---|---|
| OWASP Top 10 2021 | https://owasp.org/Top10/ | Security audit framework and category taxonomy | docs/security-audit.md | 2026-03-03 |
| CWE-78 OS Command Injection | https://cwe.mitre.org/data/definitions/78.html | Shell injection analysis methodology | SEC-01, SEC-04 findings | 2026-03-03 |
