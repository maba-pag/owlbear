# Notification Hook Research — Alert User on Task Completion or Question

> **Owning task:** #125 — Notification hook — alert user on task completion or question
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear runs as a background daemon. When an agent finishes work, encounters an error, or needs user input, the user may not be watching the terminal. Task #125 requires a `NotificationHook` that alerts the user through the best available channel.

Key questions:

1. What notification mechanisms work on Windows for a background daemon?
2. What Python libraries support Windows toast notifications?
3. How do other AI systems (CrewAI, AutoGPT) notify users?
4. Should notifications use the existing `ChannelPlugin` or a separate system?
5. What events should trigger notifications, and how should preferences be configured?

Constraints: Windows-primary, async/non-blocking, KISS, must work from a background daemon process.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| winotify | <https://github.com/versa-syahptr/winotify> | .80 | Pure Python Windows 10 toast via PowerShell XML; no deps, action center persistence, sound, buttons |
| windows-toasts | <https://github.com/DatGuy1/Windows-Toasts> | .85 | WinRT-based toast notifications; click callbacks, active maintenance (v1.3.1, Jun 2025), Win 10/11 |
| plyer | <https://github.com/kivy/plyer> | .55 | Cross-platform notifications; uses win32 balloon tips on Windows (legacy), last release 2022-11 |
| Python winsound (stdlib) | <https://docs.python.org/3/library/winsound.html> | .70 | Stdlib audio: `Beep()`, `PlaySound()`, `MessageBeep()` — zero dependencies, sync API |
| CrewAI event system | <https://docs.crewai.com/concepts/event-listener> | .85 | Event bus: `BaseEventListener` + `setup_listeners()`, scoped handlers, 30+ event types |
| CrewAI task callbacks | <https://docs.crewai.com/concepts/tasks> | .80 | `callback=` on Task: fires after completion, receives `TaskOutput`, used for notifications |
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | .75 | TTS priority chain (ElevenLabs → OpenAI → pyttsx3) in post-task hooks |
| OwlBear hook system | `src/owlbear/core/hooks.py` | .95 | HookRegistry + HookEvent enum, async emit, error isolation — the integration target |
| OwlBear voice-io-research | `docs/research/voice-io.md` | .85 | TTSEngine plan: pyttsx3, `asyncio.to_thread()`, optional dep `[voice]` |

## 3. Analysis

### 3.1 Windows Notification Mechanisms from Background Daemon

| Mechanism | Works from Daemon? | User-Visible? | Dependencies | KISS |
|-----------|--------------------|---------------|--------------|------|
| Windows toast (WinRT) | Yes | Yes — action center | windows-toasts (pywinrt) | Medium |
| Windows toast (PowerShell) | Yes | Yes — action center | winotify (pure Python) | High |
| Console bell (`\a`) | Only if terminal active | Taskbar flash + sound | None (stdlib) | Highest |
| `winsound.MessageBeep()` | Yes | System sound only | None (stdlib) | High |
| TTS speech (pyttsx3) | Yes (SAPI5 COM) | Audible speech | pyttsx3 (optional) | Medium |
| Slack message | Yes | Phone/desktop push | slack_sdk (already in stack) | High |
| System tray icon | Requires UI thread | Balloon notification | pystray or custom | Low |

### 3.2 Python Toast Notification Libraries

| Criterion | winotify (.75) | windows-toasts (.85) | plyer (.40) |
|-----------|---------------|---------------------|-------------|
| API | `Notification().show()` | `WindowsToaster().show_toast()` | `notification.notify()` |
| Windows native | Win10 toast (PowerShell XML) | Win10/11 toast (WinRT) | Win32 balloon tip (legacy) |
| Action center persistence | Yes | Yes | No |
| Click callbacks | Yes (via Notifier) | Yes (`on_activated`) | No |
| Sound support | Built-in audio module | Yes | No |
| Buttons | Up to 5 | Yes | No |
| Async-friendly | Sync (fast — spawns PowerShell) | Sync (WinRT dispatch) | Sync |
| Active maintenance | Last commit 4y ago | Active (v1.3.1, Jun 2025) | Last release 2022 |
| Dependencies | None (pure Python + PowerShell) | pywinrt bindings | Varies by platform |
| Stars | 89 | 139 | 1.8k (multi-platform) |
| Windows-only | Yes | Yes | No (cross-platform) |

### 3.3 How AI Systems Handle Notifications

| System | Mechanism | Pattern |
|--------|-----------|---------|
| **CrewAI** | `callback=` on Task fires after completion; EventListener bus with 30+ typed events (TaskCompletedEvent, AgentExecutionCompletedEvent) | Event bus + per-task callback; no built-in desktop notifications — callbacks are user-defined |
| **Disler claude-code-hooks** | TTS priority chain in post-task hooks (ElevenLabs → OpenAI → pyttsx3 fallback); spoken task completion summaries | Hook-based, TTS as notification channel, graceful fallback chain |
| **AutoGPT** | No built-in notification system; relies on terminal output and optional Telegram/Discord plugins | Plugin-based, community-provided |

**Key pattern:** All systems use an **event/callback mechanism** — none embed notification logic in the agent core. Notifications are always a hook or listener that consumes events. This matches OwlBear's existing `HookRegistry` perfectly.

### 3.4 Notification Channel vs ChannelPlugin

| Approach | Description | Coupling | KISS |
|----------|-------------|----------|------|
| A. Reuse ChannelPlugin.send() | NotificationHook calls `channel.send("Task done!")` | High — needs channel reference | Medium |
| B. Separate NotificationBackend | NotificationHook has its own backends (toast, sound, TTS, Slack) | Low — hook is self-contained | High |
| C. Hybrid | Use Slack if configured, else toast/sound/bell independently | Medium | Highest |

**Recommendation (.85):** Option C — hybrid. The `NotificationHook` maintains a priority-ordered list of backends. It tries each in order until one succeeds. Channels (Slack) and notifications (toast, sound) serve different purposes: channels are bidirectional I/O, notifications are one-way alerts. Mixing them conflates concerns.

### 3.5 Event Trigger Design

The current `HookEvent` enum has: `SESSION_START`, `SESSION_END`, `PRE_TOOL_USE`, `POST_TOOL_USE`, `ON_MESSAGE`, `ON_ERROR`, `SUBAGENT_COMPLETE`. The AC calls for `ON_TASK_COMPLETE` and `ON_QUESTION` — these don't exist yet.

| Option | Description | KISS |
|--------|-------------|------|
| A. Add new events to HookEvent | `TASK_COMPLETE`, `QUESTION_PENDING` alongside existing events | High |
| B. Reuse SUBAGENT_COMPLETE + ON_ERROR | Map existing events to notifications | Medium (semantic mismatch) |
| C. Separate NotificationEvent enum | New enum, new registry | Low (redundant) |

**Recommendation (.90):** Option A — extend `HookEvent` with `TASK_COMPLETE` and `QUESTION_PENDING`. These are genuine lifecycle events other hooks may also want. Keep one event enum, one registry.

### 3.6 Notification Backend Priority Chain

Inspired by Disler's TTS priority chain, the hook should try backends in configurable order:

1. **Slack message** — if Slack is configured, post to channel (highest reach — phone push)
2. **Windows toast** — if on Windows, show toast notification (visible in action center)
3. **TTS speech** — if `[voice]` extra installed, speak the message
4. **Console bell** — `sys.stdout.write('\a')` — always available, lowest fidelity

Each backend is optional. The hook tries the first enabled backend and stops (or tries all — configurable). Failed backends log a warning and fall through to the next.

### 3.7 Configuration Design

| Approach | Description | KISS |
|----------|-------------|------|
| A. OwlBearSettings fields | `notification_events: list[str]`, `notification_backends: list[str]` | High |
| B. Separate NotificationSettings model | Nested Pydantic model | Medium |
| C. TOML config file | Separate notification.toml | Low (YAGNI) |

**Recommendation (.85):** Option A — add fields to `OwlBearSettings`:

```python
notification_events: list[str] = ["task_complete", "question_pending", "on_error"]
notification_backends: list[str] = ["toast", "sound"]  # priority order
```

Environment variables: `OWLBEAR_NOTIFICATION_EVENTS`, `OWLBEAR_NOTIFICATION_BACKENDS`.

## 4. Recommendation (.85 confidence)

**Implement `NotificationHook` as a self-contained hook with a priority-chain of backends.**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Toast library | **windows-toasts** | Active, WinRT-based, click callbacks, Win 10/11 support |
| Sound fallback | **winsound.MessageBeep** (stdlib) | Zero deps, works from daemon |
| TTS integration | **Import TTSEngine if available** | Optional dep, `asyncio.to_thread()` |
| Slack integration | **Use AsyncWebClient directly** | Already in stack, highest reach |
| Console fallback | **`\a` bell character** | Always works, zero cost |
| Event enum | **Extend HookEvent** with TASK_COMPLETE, QUESTION_PENDING | One registry, clean semantics |
| Configuration | **OwlBearSettings fields** | Existing config pattern, env-var override |
| Architecture | **NotificationHook + NotificationBackend protocol** | KISS, testable, backend-swappable |

Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| windows-toasts adds pywinrt dep (~5MB) | Low | Optional extra: `[notifications]` in pyproject.toml |
| Toast not visible if Focus Assist on | Low | Sound fallback plays regardless; Slack always delivers |
| pyttsx3 COM init in daemon thread | Low | Wrap in `asyncio.to_thread()`, lazy init |
| Over-notification fatigue | Medium | Configurable event list, default to task_complete + on_error only |

## 5. Follow-up Tasks

1. **Extend HookEvent enum** — add `TASK_COMPLETE` and `QUESTION_PENDING` events
2. **Add notification config to OwlBearSettings** — `notification_events`, `notification_backends`
3. **Create NotificationBackend protocol + backends** — toast, sound, TTS, Slack, bell
4. **Create NotificationHook** — registers on configured events, dispatches to backend chain
5. **Add `[notifications]` optional dependency group** — `windows-toasts` in pyproject.toml
6. **Write tests** — hook fires on correct events, backend fallback chain, config respected
