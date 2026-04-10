---
id: 776
title: 'P0-01: Implement cdp-spike.py per research #752'
status: research
priority: critical
created: '2026-04-10T11:45:19.715661+00:00'
updated: '2026-04-10T11:45:19.715661+00:00'
tags:
- phase-0
- scope:browser
parent: 751
depends_on:
- 752
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Implement the CDP validation spike script at `.owlbear/scratch/cdp-spike.py` using the design from `.owlbear/research/cdp-spike-752.md` §3.3.

**Critical constraint (Chrome 136):** `--remote-debugging-port` no longer works with the default Edge profile. The script MUST use `--user-data-dir` with a fresh profile directory and test whether Windows Integrated Auth provides automatic SSO.

AC:
1. Script exists at `.owlbear/scratch/cdp-spike.py`
2. Runnable with `uv run python .owlbear/scratch/cdp-spike.py`
3. Finds Edge executable at standard Windows paths
4. Launches Edge with `--remote-debugging-port=9222 --user-data-dir=.owlbear/scratch/cdp-spike-profile`
5. Connects via `playwright.chromium.connect_over_cdp("http://127.0.0.1:9222", is_local=True)`
6. Navigates to a configurable target URL (default: a known SharePoint page)
7. Detects SSO redirect vs auto-authentication vs login page
8. Extracts `page.inner_text("body")` and logs text length
9. Handles all error cases from research §3.4 with clear messages
10. Logs timestamps for EDR/DLP correlation
11. Cleans up (disconnect, terminate subprocess) on all exit paths