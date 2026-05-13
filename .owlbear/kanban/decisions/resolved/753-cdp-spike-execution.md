---
# >> Your action: set response to completed or rejected when done
response: completed
notes: "NO-GO for CDP. Corporate Group Policy (RemoteDebuggingAllowed=0) blocks CDP for both Edge and Chrome. PIVOT: Playwright Chromium + Microsoft SSO extension from managed Chrome works. E2E validated against SharePoint (automatic SSO), Jira (one-time Windows login), and Confluence (shared session). See .owlbear/research/cdp-spike-results.md."
request_type: action
task_id: 753
agent: builder
created: 2026-04-13
urgency: blocking
---

# Action: Execute CDP Spike on Corporate Laptop

## Context

Task #753 requires physically running the CDP spike script on your corporate laptop with an active Edge SSO session. The script (`.owlbear/scratch/cdp-spike.py`) was implemented in #776 and is ready. This action cannot be automated — it requires observing EDR/DLP reactions and making a go/no-go judgment call.

## Steps

1. [ ] Close all Edge instances
2. [ ] `uv pip install playwright` (done)
3. [ ] `playwright install chromium` (done)
4. [ ] Run the spike: `uv run python .owlbear/scratch/cdp-spike.py`
5. [ ] Observe: CDP connectivity? SSO cookie extraction? EDR alerts? DLP alerts?
6. [ ] (Optional) Hash stability check: `uv run python .owlbear/scratch/cdp-spike.py --hash-stability`
7. [ ] Document results in `.owlbear/research/cdp-spike-results.md`
8. [ ] Record go/no-go decision

## Completion Instructions

Fill in the results below, then set `response: completed` and add your go/no-go verdict in `notes:`.

**Results template** (paste into `.owlbear/research/cdp-spike-results.md`):
- CDP connectivity: pass/fail
- SSO extraction: pass/fail
- EDR reaction: {describe any alerts/blocks}
- DLP reaction: {describe any alerts}
- SharePoint boilerplate behavior: {describe}
- **Go/no-go:** GO → proceed Phase 1 / NO-GO → pivot strategy

## User Findings

When running, this happens:
````powershell
(owlbear) PS C:\Users\p362329\Coding\Projects\owlbear-dev> uv run python .owlbear/scratch/cdp-spike.py
[2026-04-13T21:56:26+00:00] CDP spike starting
[2026-04-13T21:56:28+00:00] Launching Edge: C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
[2026-04-13T21:56:29+00:00] Edge launched — PID=3732
[2026-04-13T21:56:35+00:00] Connecting to CDP endpoint http://127.0.0.1:9222
(node:13320) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
(Use `node --trace-deprecation ...` to show where the warning was created)
CDP connection failed — could not connect to http://127.0.0.1:9222: BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:9222
Call log:
  - <ws preparing> retrieving websocket url from http://127.0.0.1:9222

Traceback (most recent call last):
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.owlbear\scratch\cdp-spike.py", line 480, in <module>
    sys.exit(main())
             ^^^^^^
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.owlbear\scratch\cdp-spike.py", line 455, in main
    browser = _connect_cdp(pw, port=port)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.owlbear\scratch\cdp-spike.py", line 114, in _connect_cdp
    browser = pw.chromium.connect_over_cdp(endpoint, is_local=True)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.venv\Lib\site-packages\playwright\sync_api\_generated.py", line 14969, in connect_over_cdp
    self._sync(
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.venv\Lib\site-packages\playwright\_impl\_sync_base.py", line 115, in _sync
    return task.result()
           ^^^^^^^^^^^^^
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.venv\Lib\site-packages\playwright\_impl\_browser_type.py", line 206, in connect_over_cdp
    response = await self._channel.send_return_as_dict(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.venv\Lib\site-packages\playwright\_impl\_connection.py", line 83, in send_return_as_dict
    return await self._connection.wrap_api_call(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\p362329\Coding\Projects\owlbear-dev\.venv\Lib\site-packages\playwright\_impl\_connection.py", line 559, in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
playwright._impl._errors.Error: BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:9222
Call log:
  - <ws preparing> retrieving websocket url from http://127.0.0.1:9222

(owlbear) PS C:\Users\p362329\Coding\Projects\owlbear-dev>
```
