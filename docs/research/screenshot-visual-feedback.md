# Screenshot and Visual Feedback — Capture and Share Project State

> **Owning task:** #302 — Screenshot and visual feedback — capture and share project state
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Users need visibility into what OwlBear is doing — browser pages, terminal output, code diffs.
The `BrowserToolset` has a screenshot action returning base64 PNG, but there's no pipeline to
save screenshots to disk or deliver them via channels. `SlackChannel.send_image()` exists (from
# 297) but nothing calls it with screenshots. `CLIChannel` has no image delivery at all.

**Key questions:**

1. How should screenshots flow from capture → save → deliver?
2. Should this be a new toolset, an extension of existing toolsets, or a service?
3. How to wire automatic screenshot-on-error via the hook system?
4. What minimal config settings are needed?

## 2. Sources Studied

| Source | URL | Relevance | What |
|---|---|---|---|
| Claude Computer Use | platform.claude.com/docs/en/docs/build-with-claude/computer-use | .90 | Screenshot-after-every-action pattern; base64 in tool_result; coordinate scaling |
| Playwright Python screenshots | playwright.dev/python/docs/screenshots | .85 | `page.screenshot(path=..., full_page=True)`; buffer capture; element screenshots |
| Anthropic quickstart impl | github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo | .80 | Agent loop: action → screenshot → send to LLM; screenshot quality/resize tradeoffs |
| OwlBear `browser_screenshot()` | `src/owlbear/tools/browser/actions.py` L160–192 | .95 | Returns base64 PNG; supports selector + full_page; no disk save |
| OwlBear `SlackChannel.send_image()` | `src/owlbear/channels/slack.py` L116–160 | .90 | Accepts path/bytes + caption; uses `files_upload_v2`; fallback to text |
| OwlBear `HookedToolset` | `src/owlbear/tools/hooked.py` | .85 | Wraps all tools; emits PRE/POST_TOOL_USE; ON_ERROR in agent.turn() |

## 3. Analysis

### 3.1 Architecture Options

| Criterion | A: New ScreenshotService + Toolset (.80) | B: Extend existing toolsets (.55) | C: Hook-only (.50) |
|---|---|---|---|
| Separation of concerns | High — capture/save/deliver decoupled | Low — mixes I/O into browser/terminal | Medium — hooks handle delivery |
| Agent-callable | Yes — dedicated `share_screenshot` tool | Yes — but overloads existing tools | No — hooks are fire-and-forget |
| Auto-on-error | Yes — hook calls service | Awkward — toolset calling another toolset | Yes — natural fit |
| Testability | High — mock service, mock channel | Low — coupled to browser/terminal | Medium — mock hook data |
| New modules | 2 files (~200 LOC) | 0 new files | 1 file (~80 LOC) |
| KISS score | Medium | High initially, degrades | High but limited |

### 3.2 Capture Types

| Type | Source | Format | Implementation |
|---|---|---|---|
| Browser screenshot | `browser_screenshot()` → base64 | PNG file | Decode base64, write to disk |
| Terminal output | `TerminalResult.stdout/stderr` | `.txt` file | Save formatted text |
| Code diff | `difflib.unified_diff()` (stdlib) | `.diff` text file | Generate from before/after strings |

### 3.3 Channel Delivery

| Channel | Image delivery | Text file delivery | KISS approach |
|---|---|---|---|
| Slack | `send_image(path, caption)` — already exists | Attach as file via `files_upload_v2` | Use `send_image()` for screenshots |
| CLI | No `send_image()` method | Print path, optionally `os.startfile()` on Windows | Add `send_file(path, caption)` to CLI |
| ChannelPlugin | Protocol lacks `send_image()`/`send_file()` | — | Add optional `send_file()` method |

### 3.4 Screenshot-on-Error Strategy

The `ON_ERROR` hook in `OwlBearAgent.turn()` fires with `{"error": exc, "prompt": prompt}`.
A `ScreenshotOnErrorHook` can:

1. Check if browser is active (has a page)
2. Capture screenshot → save to `.owlbear/screenshots/`
3. Optionally deliver to user via channel

**Risk:** Browser may be in bad state during error. Mitigation: wrap capture in try/except,
log failure, continue. The hook system already swallows handler errors.

### 3.5 Config Settings

| Setting | Type | Default | Purpose |
|---|---|---|---|
| `screenshot_mode` | `Literal["auto", "manual", "on_error"]` | `"on_error"` | When to auto-capture |
| `screenshot_dir` | Derived from workspace | `{workspace}/.owlbear/screenshots/` | Not user-configurable (YAGNI) |

`"auto"` = capture after every browser action (Claude-style); `"manual"` = only when agent
explicitly calls the tool; `"on_error"` = auto-capture on tool/turn failure.

**KISS recommendation:** Start with `on_error` default. `auto` is expensive and noisy —
add later if needed (YAGNI).

## 4. Recommendation (.80 confidence)

**Option A: `ScreenshotService` + `VisualFeedbackToolset` + `ScreenshotOnErrorHook`.**

Three small, focused components:

1. **`ScreenshotService`** (~80 LOC in `src/owlbear/tools/screenshot.py`):
   - `save(image_bytes: bytes, name: str, workspace: Path) → Path` — saves PNG to
     `.owlbear/screenshots/{timestamp}_{name}.png`
   - `deliver(path: Path, channel: ChannelPlugin, caption: str)` — dispatches via
     `send_image()` (Slack) or `send()` with file path (CLI)
   - `capture_browser(page: Page) → bytes` — thin wrapper calling `page.screenshot()`
   - `capture_terminal(result: TerminalResult) → bytes` — renders text to file

2. **`VisualFeedbackToolset(FunctionToolset)`** (~60 LOC):
   - `share_screenshot(caption: str) → str` — captures browser → saves → delivers → returns path
   - `share_terminal_output(output: str, caption: str) → str` — saves text → delivers → returns path
   - Injected with `ScreenshotService`, `ChannelPlugin`, `BrowserToolset` ref

3. **`ScreenshotOnErrorHook`** (~40 LOC):
   - Registers on `ON_ERROR` event
   - If browser toolset is available and has active page, captures + saves
   - Controlled by `screenshot_mode` config setting

4. **Config:** Add `screenshot_mode` to `OwlBearSettings`. Start with `"on_error"` default.

5. **Channel extension:** Add `send_file(path, caption)` to `CLIChannel` — prints path
   and optionally opens viewer. `ChannelPlugin` protocol stays minimal (duck typing
   via `hasattr` check in service).

**Risks and mitigations:**

- Browser page may not exist when error occurs → guard with `hasattr` + try/except
- Screenshots accumulate on disk → timestamp-based naming + future cleanup task (YAGNI now)
- CLI has no image viewer → print path, let user open manually; `os.startfile` on Windows

**Total estimate:** ~200 LOC across 2 new files + minor additions to existing files.

## 5. Follow-up Tasks

1. **ScreenshotService** — core save/deliver logic
2. **VisualFeedbackToolset** — agent-callable screenshot/share tools
3. **ScreenshotOnErrorHook** — auto-capture on tool/turn failure
4. **Config: screenshot_mode** — add setting to OwlBearSettings
5. **CLIChannel.send_file()** — file delivery for CLI channel
6. **Bootstrap wiring** — register toolset, hook, and config in bootstrap
7. **Unit tests** — mock browser, mock channel, service tests
