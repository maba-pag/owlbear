# Slack Notification Integration for v2 Orchestrator

> **Owning task:** #26 — Slack notification integration
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #26 asks for Slack notification support in the v2 orchestrator so it can
alert users on dispatch, completion, and decision requests. The v2 orchestrator
(`packages/orchestrator/`) is architecturally different from v1: no hook
system, no NotificationBackend protocol, no ChannelPlugin — just a dispatch
loop + JSONL audit log. Dependency #21 (audit log) is archived and satisfied.

Key questions:
1. What Slack sending mechanism fits a send-only, fire-and-forget notification module?
2. Should we add `slack_sdk` as a dependency or use stdlib/lightweight HTTP?
3. Where does the notifier integrate with the dispatch loop?
4. How should decision-request notifications work?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Slack Incoming Webhooks docs | .90 | Single-URL POST for send-only messages; no auth flow needed [docs.slack.dev] |
| S2 | `slack_sdk` v3.41.0 (PyPI, GitHub) | .90 | `WebhookClient`, `AsyncWebhookClient`, `AsyncWebClient`; aiohttp required for async |
| S3 | OwlBear `packages/orchestrator/src/owlbear/orchestrator/loop.py` | 1.0 | Dispatch loop: `dispatch_entry()`, `dispatch_wave()`, `run_loop()`, `CycleResult` |
| S4 | OwlBear `packages/orchestrator/src/owlbear/audit/models.py` | 1.0 | `DispatchEvent`, `CompletionEvent` — existing typed event models |
| S5 | OwlBear `docs/research/slack-integration.md` | .85 | v1 research: `slack_sdk` chosen over `slack_bolt`; Socket Mode for bidirectional |
| S6 | OwlBear `docs/research/slack-notification-backend.md` | .85 | v1 `SlackNotificationBackend` pattern: import guard, constructor injection, ~35 LOC |
| S7 | OwlBear `docs/research/notification-hook.md` | .80 | v1 notification architecture: priority chain, backend protocol, event triggers |
| S8 | OwlBear `packages/orchestrator/pyproject.toml` | 1.0 | Current deps: ACP, pydantic, typer (3 total) |
| S9 | Slack `chat.postMessage` docs | .85 | Bot token approach: `xoxb-` token + channel ID; `chat:write` scope [docs.slack.dev] |

## 3. Analysis

### 3.1 Sending Mechanism Comparison

| Criterion | A: Webhook + urllib (.85) | B: slack_sdk Webhook (.75) | C: Bot Token + slack_sdk (.65) |
|-----------|:------------------------:|:--------------------------:|:------------------------------:|
| New deps | 0 | 1 (slack_sdk) | 1 (slack_sdk + aiohttp) |
| Config vars | 1 (webhook URL) | 1 (webhook URL) | 2 (bot token + channel) |
| Async-native | No (asyncio.to\_thread) | Yes (AsyncWebhookClient) | Yes (AsyncWebClient) |
| Channel flexibility | Fixed to 1 | Fixed to 1 | Any channel |
| LOC estimate | ~35 | ~25 | ~40 |
| KISS | Highest | High | Medium |
| Error handling | HTTP status codes | SlackApiError types | SlackApiError types |
| Forward compat | Replace if SDK needed | Upgrade to WebClient | Full Slack features |

Option A is the KISS winner because it adds zero dependencies to a package that
currently has only 3. The `asyncio.to_thread` wrapper for the sync `urllib` POST
adds ~5ms overhead — negligible for fire-and-forget notifications. [S1, S2, S8]

Option C matches the AC wording ("Slack token and channel via environment
variables") but adds `slack_sdk` + `aiohttp` (~15+ transitive deps) for a feature
that is `nice-to-have` priority. YAGNI. [S2, S8]

### 3.2 Integration Points in Dispatch Loop

The notifier hooks into `run_loop()` at three points [S3]:

| Event | Where | Data available |
|-------|-------|----------------|
| Task dispatched | After `dispatch_entry()` call | task\_id, agent name |
| Task completed | In `_apply_wave_result()` | task\_id, agent, success/failure |
| Decision request | Separate blocked-task scan per cycle | task\_id, block reason |

**Injection pattern:** Add an optional `notifier` parameter to `run_loop()`.
When `None`, no notifications are sent. This keeps the core loop unchanged when
Slack is not configured. [S3]

For decision requests, the loop currently calls `read_board()` with
`--unblocked --not-blocked` filters. A separate `read_board()` call with
`--blocked` would detect newly blocked tasks. This runs once per cycle, before
wave assembly. [S3]

### 3.3 Notifier Protocol

```
class Notifier(Protocol):
    async def on_dispatch(self, task_id: int, agent: str) -> None: ...
    async def on_completion(self, task_id: int, agent: str, success: bool) -> None: ...
    async def on_decision_request(self, task_id: int, reason: str) -> None: ...
```

`SlackNotifier` implements this using Incoming Webhooks (Option A). The protocol
allows future backends (Discord, email, toast) without modifying the loop. [S6, S7]

### 3.4 Message Format

Plain text with mrkdwn labels, matching v1 research recommendations [S6]:

- Dispatch: `*Dispatched* #480 to builder`
- Success: `:white_check_mark: *Completed* #480 (builder) — success`
- Failure: `:x: *Failed* #480 (builder)`
- Decision: `:warning: *Decision needed* #480 — {block reason}`

No Block Kit — YAGNI for fire-and-forget alerts. [S1, S6]

### 3.5 Configuration

| Env var | Required | Default |
|---------|----------|---------|
| `OWLBEAR_SLACK_WEBHOOK_URL` | No | None (notifications disabled) |

Single env var. When unset, `SlackNotifier` is not instantiated and `run_loop()`
gets `notifier=None`. No validation needed — absent means opt-out. [S1, S8]

### 3.6 Testing Strategy

| Layer | Approach |
|-------|----------|
| Unit: SlackNotifier | Mock `urllib.request.urlopen`; verify JSON payload, URL, headers |
| Unit: loop integration | Pass mock notifier; verify callbacks fire at correct points |
| Protocol compliance | `isinstance(SlackNotifier(...), Notifier)` |
| Integration (optional) | `@pytest.mark.api` test with real webhook URL |

All unit tests use mocked HTTP — no network calls. [S6]

## 4. Recommendation (.85 confidence)

**Option A: Incoming Webhook + stdlib urllib** with the `Notifier` protocol.

Rationale:
1. Zero new dependencies — preserves v2's minimal footprint [S8]
2. Single env var config — simplest possible opt-in [S1]
3. ~35 LOC implementation [S6]
4. KISS/YAGNI-aligned — send-only notifications don't need an SDK [S1, S2]
5. Forward-compatible — replace urllib with `slack_sdk` if bidirectional Slack is
   added later (task #83 lineage) [S5]

Risk: If threading or message updates are needed, we'd migrate to `slack_sdk`.
Mitigation: The `Notifier` protocol isolates the loop from the backend — swap
without touching `loop.py`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement Notifier protocol and SlackNotifier (webhook + urllib)" --priority nice-to-have --status ideation --tags phase-3,scope:notifications,scope:orchestrator,type:build --depends-on 26
kanban\kanban-md.exe create "Integrate Notifier into dispatch loop (run_loop)" --priority nice-to-have --status ideation --tags phase-3,scope:orchestrator,type:build --depends-on 26
kanban\kanban-md.exe create "Add blocked-task scan for decision-request notifications" --priority nice-to-have --status ideation --tags phase-3,scope:orchestrator,scope:notifications,type:build --depends-on 26
```
