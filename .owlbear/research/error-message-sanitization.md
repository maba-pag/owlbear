# Error Message Sanitization Before Channel Delivery

> **Owning task:** #472 — Sanitize error messages before sending to channels
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-08 from the security audit: exception details are sent via `f"Error: {exc}"` to Slack/CLI channels. httpx exceptions embed full URLs (with query-param tokens), hostnames, and may reference auth headers. The question: what sanitization approach best balances safety, simplicity, and debuggability?

## 2. Sources Studied

| Source | URL | Relevance | What was taken |
|--------|-----|-----------|----------------|
| OWASP Error Handling Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html> | .90 | Never expose implementation details to users; return generic messages; log full details server-side |
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | .85 | Data to exclude from user-visible output: access tokens, session IDs, passwords, connection strings, file paths |
| Django SafeExceptionReporterFilter | <https://github.com/django/django/blob/main/django/views/debug.py> | .80 | `HIDDEN_SETTINGS` regex for API/TOKEN/KEY/SECRET/PASS; `cleansed_substitute` pattern; type-based cleansing |
| Sentry Python SDK filtering | <https://docs.sentry.io/platforms/python/configuration/filtering/> | .75 | `before_send` hook pattern — classify exception, modify or drop before external delivery |
| httpx exceptions docs | <https://www.python-httpx.org/exceptions/> | .90 | Exception hierarchy; `str(exc)` on HTTPStatusError includes full URL; `.request` attr holds URL + headers |

## 3. Analysis

### 3.1 Leak Sites Identified (18 call sites)

**HIGH RISK — exception flows to Slack or user channel:**

| File | Line(s) | Pattern | What leaks |
|------|---------|---------|------------|
| `daemon.py` | 222, 232, 236 | `channel.send(f"Error: {exc}")` | httpx URLs with tokens, auth headers, hostnames |
| `cli.py` | 1099 | `channel.send(f"Error: {exc}")` | Same — REPL mode |
| `escalation.py` | ~82 | `f"  {error}\n\n"` | Raw exception in escalation prompt to user |

**MEDIUM RISK — CLI output or LLM-facing tool return:**

| File | Line | Pattern | What leaks |
|------|------|---------|------------|
| `cli.py` | 772, 802 | `typer.echo(f"Error: Slack API request failed: {exc}")` | httpx exc with Slack API URL |
| `cli.py` | 900 | `typer.echo(f"Login failed: {exc}")` | OAuth flow details |
| `web_search.py` | 202 | `return f"Error fetching {url}: {exc}"` | URL + exception |
| `delegation.py` | 143 | `ToolError(message=f"...failed: {exc}")` | Exc in LLM-facing ToolError |

**LOW RISK — exception type is known/benign (ValueError, ImportError, FileNotFoundError):**
`cli.py` lines 130, 229, 280, 299, 324, 857; `projects/toolset.py:135`; `knowledge_source.py:127`

### 3.2 What httpx Exceptions Expose

```
httpx.HTTPStatusError: "Client error '401 Unauthorized' for url 'https://api.individual.githubcopilot.com/chat?token=ghp_abc123...'"
httpx.ConnectError: "All connection attempts failed" (includes hostname)
httpx.TimeoutException: includes request URL
```

The `.request` attribute contains `request.url` (full, with query params) and `request.headers` (including `Authorization: Bearer ...`).

### 3.3 Design Options

| Criterion | A. Regex scrub `str(exc)` | B. Type-based fixed messages | C. Hybrid (rec) |
|-----------|---------------------------|------------------------------|------------------|
| Safety | Medium — regex can miss patterns | High — nothing from exc leaks | High |
| Debuggability | High — partial original msg | Low — generic only | Medium — type name + generic |
| KISS | High — one function | High — one dict lookup | Medium — two paths |
| Maintainability | Low — regex must track new patterns | High — add type → msg entry | Medium |
| Implementation effort | ~30 LOC | ~25 LOC | ~40 LOC |

## 4. Recommendation (.85 confidence)

**Option C: Hybrid** — type-based mapping for known exception types + regex scrub fallback.

```python
# In core/errors.py, next to classify_error()

_SAFE_MESSAGES: dict[type, str] = {
    httpx.HTTPStatusError: "HTTP request failed (status {status_code})",
    httpx.ConnectError: "Connection failed",
    httpx.TimeoutException: "Request timed out",
    openai.AuthenticationError: "Authentication failed",
    openai.PermissionDeniedError: "Permission denied",
    pydantic.ValidationError: "Validation error",
    FileNotFoundError: "File not found",
    PermissionError: "Permission denied",
}

_SCRUB_PATTERNS = [
    (re.compile(r"https?://\S+"), "[URL]"),  # URLs with potential tokens
    (re.compile(r"Bearer\s+\S+"), "[REDACTED]"),  # Bearer tokens
    (re.compile(r"(?i)(token|key|secret|password)=\S+"), r"\1=[REDACTED]"),
    (re.compile(r"[A-Za-z]:\\[\w\\]+|/[\w/]+\.py"), "[PATH]"),  # file paths
]


def error_to_user_message(exc: Exception) -> str:
    """Return a safe, user-facing error description. Full details stay in logs."""
    for exc_type, template in _SAFE_MESSAGES.items():
        if isinstance(exc, exc_type):
            return template.format_map(...)  # extract safe attrs only
    # Fallback: scrub sensitive patterns from str(exc)
    msg = str(exc)
    for pattern, replacement in _SCRUB_PATTERNS:
        msg = pattern.sub(replacement, msg)
    return f"{type(exc).__name__}: {msg}"
```

**Risk:** Regex fallback could miss novel secret patterns. Mitigation: log the full exception server-side (already done via `logger.exception`), so no debugging information is lost.

**Architecture fit:** `core/errors.py` already has `classify_error()` and `ErrorCategory`. Adding `error_to_user_message()` in the same module keeps error handling logic co-located. Every `channel.send(f"Error: {exc}")` call site replaces `{exc}` with `error_to_user_message(exc)`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement error_to_user_message() in core/errors.py" --priority needed --status backlog --tags "security,channels,phase-4" --body "Add error_to_user_message() to core/errors.py. Type-based safe messages for httpx/openai/pydantic exceptions; regex fallback for unknown types. Strip URLs, Bearer tokens, file paths, secret query params. ~40 LOC. AC: (1) known httpx exceptions produce safe message without URL/token, (2) unknown exceptions have URLs/paths/tokens scrubbed, (3) exception type name preserved for debuggability. See docs/research/error-message-sanitization.md §4."

kanban\kanban-md.exe create "Replace raw exception sends in daemon.py with error_to_user_message()" --priority needed --status backlog --tags "security,channels,phase-4" --depends-on 472 --body "Replace 3 instances of channel.send(f'Error: {exc}') in _recover_from_error() with error_to_user_message(). AC: no raw exception string reaches channel.send() in daemon.py. See docs/research/error-message-sanitization.md §3.1."

kanban\kanban-md.exe create "Replace raw exception sends in cli.py with error_to_user_message()" --priority needed --status backlog --tags "security,channels,phase-4" --depends-on 472 --body "Replace channel.send and typer.echo error paths in cli.py (lines 772, 802, 900, 1099) with error_to_user_message(). Low-risk sites (ValueError, ImportError) can keep str(exc) since they don't contain secrets. AC: no httpx/openai exception string reaches user output. See docs/research/error-message-sanitization.md §3.1."

kanban\kanban-md.exe create "Sanitize error in escalation.py escalation prompt" --priority needed --status backlog --tags "security,channels,phase-4" --depends-on 472 --body "Replace f'  {error}' in EscalationHook.escalate() with error_to_user_message(error). AC: escalation prompt to user contains no raw exception details. See docs/research/error-message-sanitization.md §3.1."

kanban\kanban-md.exe create "Sanitize error strings in tool return values" --priority important --status backlog --tags "security,channels,phase-4" --depends-on 472 --body "Replace f-string exception returns in web_search.py:202 and delegation.py:143 with error_to_user_message(). These flow to LLM context, not directly to user, so lower priority but still good hygiene. AC: no raw httpx exception in tool return strings. See docs/research/error-message-sanitization.md §3.1."

kanban\kanban-md.exe create "Test error_to_user_message() with httpx token-bearing exceptions" --priority needed --status backlog --tags "security,test,phase-4" --depends-on 472 --body "Unit tests: (1) httpx.HTTPStatusError with token in URL → safe message, (2) httpx.ConnectError with hostname → safe message, (3) unknown exception with URL → URL scrubbed, (4) unknown exception with Bearer token → token scrubbed, (5) benign ValueError → type name + original message preserved. Target: 100% branch coverage on error_to_user_message(). See docs/research/error-message-sanitization.md §4."
```
