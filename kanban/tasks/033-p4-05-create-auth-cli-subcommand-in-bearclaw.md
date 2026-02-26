---
id: 33
title: 'P4-05: Create auth CLI subcommand in BearClaw'
status: ideation
priority: high
created: 2026-02-24T15:15:59.8991499+01:00
updated: 2026-02-26T18:53:06.3575623+01:00
tags:
    - phase-4
    - cli
    - auth
depends_on:
    - 31
    - 32
    - 9
class: standard
---

AC: Update src/bearclaw/cli.py to replace placeholder auth commands with real implementations. (1) 'bearclaw auth login': run the full device-flow OAuth — call request_device_code(), print user_code + verification_uri, open browser, poll_for_access_token(), exchange_for_copilot_token(), save token. Use typer.echo for output and webbrowser.open for browser. (2) 'bearclaw auth status': load cached token, check expiry, print status (authenticated/expired/not found) + model name + base URL. Import from owlbear.auth.copilot and owlbear.config. Handle errors gracefully with typer.echo. File: src/bearclaw/cli.py
