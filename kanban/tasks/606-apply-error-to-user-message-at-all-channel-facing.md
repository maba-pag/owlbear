---
id: 606
title: Apply error_to_user_message() at all channel-facing call sites
status: archived
priority: needed
created: 2026-03-06T12:21:55.4951768+01:00
updated: 2026-03-06T19:28:36.3155345+01:00
started: 2026-03-06T15:28:04.8121552+01:00
completed: 2026-03-06T19:28:36.3155345+01:00
tags:
    - security
    - channels
depends_on:
    - 472
class: standard
---

## Replace raw exception strings with error_to_user_message()

Mechanical replacement at all HIGH/MEDIUM risk call sites identified in docs/error-message-sanitization-research.md section 3.1.

### Acceptance Criteria

1. `daemon.py` lines ~222, 232, 236: `channel.send(f'Error: {exc}')` -> `channel.send(f'Error: {error_to_user_message(exc)}')`
2. `cli.py` line ~1099: same pattern in REPL exception handler
3. `cli.py` lines ~772, 802: `typer.echo(f'Error: Slack API request failed: {exc}')` -> use error_to_user_message
4. `cli.py` line ~900: `typer.echo(f'Login failed: {exc}')` -> use error_to_user_message
5. `escalation.py` line ~82: `f'  {error}'` -> `f'  {error_to_user_message(error)}'`
6. `web_search.py` line ~202: `f'Error fetching {url}: {exc}'` -> `f'Error fetching page: {error_to_user_message(exc)}'` (URL itself may contain tokens)
7. `delegation.py` line ~143: `f'delegation to ...failed: {exc}'` -> use error_to_user_message
8. LOW RISK sites (ValueError, FileNotFoundError in cli.py) -- no change needed, these are benign
9. Verification: every `channel.send()`, `_channel.send()`, and `typer.echo()` call that interpolates an exception variable (`{exc}`, `{error}`, `{last_exc}`, `{retry_exc}`) either (a) wraps it in `error_to_user_message()` or (b) is LOW RISK per AC#8. Grep: `grep -rn '{exc}\|{error}\|{last_exc}\|{retry_exc}' src/ --include='*.py'` -- all channel/echo hits wrapped.
10. `import error_to_user_message from owlbear.core.errors` added at each modified file
11. `ruff check` clean

### Architecture notes

Import `error_to_user_message` from `owlbear.core.errors` at each call site.
All sites already import from that module or can add the import trivially.
