# Slack Channel send_file via files_upload_v2

> **Owning task:** #552 — Add send_file to Slack channel via files_upload_v2
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

INT-17 from the integration audit flags that `SlackChannel` lacks a `send_file` method.
`ScreenshotService.deliver()` duck-types three tiers: `send_image` > `send_file` > `send`.
SlackChannel already has `send_image` (tier 1), so **screenshots are already delivered
via Slack** — the audit description is partially misleading. The actual gap is that
`send_file` does not exist on SlackChannel, creating an inconsistency where any code
calling `send_file` directly on a Slack channel would skip to the `send` fallback.

**Question:** Should we add `send_file` to SlackChannel, and if so — independent
implementation or thin wrapper around existing `send_image`?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Slack SDK `files_upload_v2` docs | <https://docs.slack.dev/tools/python-slack-sdk/web/index.html> | .95 — official SDK upload example |
| 2 | Slack `files.upload` API reference | <https://docs.slack.dev/reference/methods/files.upload> | .80 — confirms deprecation; v2 is required |
| 3 | slack_sdk `AsyncWebClient.files_upload_v2` source | <https://github.com/slackapi/python-slack-sdk/blob/main/slack_sdk/web/async_client.py> | .90 — confirms 3-step upload: getUploadURLExternal + upload + completeUploadExternal |
| 4 | OwlBear `SlackChannel.send_image` | `src/owlbear/channels/slack.py:178-222` | 1.0 — existing pattern to follow |
| 5 | OwlBear `CLIChannel.send_file` | `src/owlbear/channels/cli.py:51-67` | 1.0 — target signature contract |

## 3. Analysis

### send_image already covers screenshots

`ScreenshotService.deliver` resolution order:

1. `channel.send_image(path, caption=...)` — SlackChannel HAS this -> works
2. `channel.send_file(path, caption=...)` — SlackChannel MISSING -> skipped
3. `channel.send(f"[{caption}] {path}")` — universal fallback

Screenshots already flow via `send_image`. The gap only affects non-screenshot file
delivery (e.g., future toolsets that call `send_file` directly).

### Implementation options

| Criterion | A: Delegate to send_image (.85) | B: Independent impl (.65) | C: Refactor shared _upload (.40) |
|-----------|--------------------------------|--------------------------|----------------------------------|
| LOC | ~5 | ~20 | ~30 |
| DRY | Yes — reuses existing | No — duplicates logic | Yes — but creates abstraction |
| KISS | Highest | Medium | Lowest |
| YAGNI | Aligned | Slight over-build | Over-engineered |
| Title default | `path.name` via caption arg | `path.name` via kwargs | `path.name` via shared helper |
| Future divergence | Requires refactor later | Ready now | Ready now |

### Signature contract

Must match `CLIChannel.send_file`:

```
async def send_file(self, path: Path, *, caption: str | None = None) -> None
```

### Scope required

Bot token needs `files:write` scope — same as `send_image`. No new permissions.

## 4. Recommendation (.85 confidence)

**Option A: Thin delegate** — `send_file` calls `send_image(path, caption=caption or path.name)`.

Rationale:

- `files_upload_v2` handles all file types, not just images — `send_image` works for any file.
- Avoids duplicating the upload + fallback logic.
- `path.name` provides a meaningful title when no caption is given.
- If semantics diverge later, extracting a shared method is a ~10-minute refactor.

Risk: If `send_image` later gets image-specific behavior (e.g., thumbnail generation),
`send_file` would inherit it. Mitigated by: `send_image` delegates to `files_upload_v2`
which is file-type-agnostic; no image-specific logic exists today.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement send_file on SlackChannel" --priority nice-to-have --tags "channels,scope:channels" --status backlog --body "Add send_file(path, *, caption) to SlackChannel. Delegate to send_image(path, caption=caption or path.name). Match CLIChannel.send_file signature. Tests: send_file calls files_upload_v2, caption passed through, no-caption uses path.name, error fallback to send. ~5 LOC + ~15 LOC tests. See docs/research/slack-send-file.md"
```

Note: The implementation task replaces #552 which is the same scope. No additional
tasks needed — this is a single-method addition.
