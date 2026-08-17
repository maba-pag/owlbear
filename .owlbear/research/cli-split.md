# Split bearclaw/cli.py into Subcommand Modules

> **Owning task:** #481 — Split bearclaw/cli.py into subcommand modules
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`src/bearclaw/cli.py` is 1200 lines with 10 concern areas. The task requires splitting it into `bearclaw/commands/{module}.py` and wiring via `app.add_typer()`, with cli.py reduced to <200 lines. Entry point (`bearclaw.cli:app` in pyproject.toml) must remain stable.

**Key question:** What Typer pattern handles both sub-groups (auth, browser, slack, project, usage, voice, knowledge_source) and top-level commands (chat, daemon run/stop/status) when splitting into separate files?

## 2. Sources Studied

| Source | URL | Relevance |
|---|---|---|
| Typer docs: Add Typer | <https://typer.tiangolo.com/tutorial/subcommands/add-typer/> | .95 |
| Typer docs: One File Per Command | <https://typer.tiangolo.com/tutorial/one-file-per-command/> | .95 |
| Prefect CLI (prefecthq/prefect) | <https://github.com/prefecthq/prefect/tree/main/src/prefect/cli> | .80 |

**Key finding from Typer docs (both sources):** `app.add_typer(sub_app, name="x")` groups commands under `x`. `app.add_typer(sub_app)` **without a name** promotes commands to top-level. This handles both sub-groups and top-level commands.

**Prefect validates at scale:** Their CLI splits ~25 command files into `prefect/cli/`, each exporting its own Typer app, wired in `__init__.py`.

## 3. Analysis

### Current structure — line count by concern

| Concern | Lines | Approx LOC | Type |
|---|---|---|---|
| Imports + app + Typer defs | 1–100 | 100 | Wiring |
| Project commands | 101–233 | 133 | Sub-group |
| Voice commands | 250–340 | 91 | Sub-group |
| Knowledge-source commands | 341–514 | 174 | Sub-group |
| Usage helpers + command | 515–659 | 145 | Sub-group |
| Slack commands | 660–793 | 134 | Sub-group |
| Browser commands | 794–843 | 50 | Sub-group |
| Auth commands | 844–865 | 22 | Sub-group |
| Chat command | 866–1031 | 166 | Top-level |
| Daemon commands | 1032–1175 | 144 | Top-level |
| Global options | 1176–1200 | 25 | Wiring |

### Pattern comparison

| Criterion | A: Flat modules + add_typer (.85) | B: Package __init__ as hub (.70) | C: Register functions (.60) |
|---|---|---|---|
| Complexity | Low — each file self-contained | Medium — __init__.py does wiring | Medium — callback pattern |
| Typer-idiomatic | Yes — official pattern | Yes | No — custom convention |
| Top-level cmds | `add_typer(app)` without name | Same | Pass `app` as arg |
| Test impact | Minimal — `app` still from cli.py | Same | Same |
| KISS alignment | High | Medium | Low |

### Shared state analysis

| Shared dependency | Used by | Migration impact |
|---|---|---|
| `OwlBearSettings()` | All groups | None — each module instantiates fresh |
| `error_to_user_message()` | chat, slack | None — import from owlbear.core.errors |
| `asyncio.run()` | auth, voice, browser, chat, daemon | None — stdlib import |
| `httpx` + `truststore` | slack, auth | None — direct import |

No singleton state. No shared mutable globals. Each module handles its own imports.

### Test dependency map

| Test file | Imports from cli.py | Migration |
|---|---|---|
| test_cli.py | `app` | No change — stays in cli.py |
| test_cli_auth.py | `app` | No change |
| test_cli_browser.py | `app` | No change |
| test_cli_chat.py | `app`, `_detect_github_remote` | Update `_detect_github_remote` import |
| test_cli_daemon.py | `app`, `_daemon_status`, `_daemon_stop`, `_get_config_dir`, `_is_process_alive`, `_poll_pid_removal` | Update 5 private imports |
| test_cli_knowledge_source.py | `app` | No change |
| test_cli_project.py | `app` | No change |
| test_cli_voice.py | `app` | No change |

Only 2 test files need import path changes (6 symbols total).

## 4. Recommendation (.85 confidence)

**Pattern A: Flat modules with `add_typer()`** — each command group in its own file under `bearclaw/commands/`, wired in cli.py via `add_typer()`.

### Proposed file layout

```
src/bearclaw/
  __init__.py         (existing, unchanged)
  cli.py              (~60 lines: app, version callback, wiring imports)
  commands/
    __init__.py       (empty — just marks package)
    auth.py           (~45 lines)
    browser.py        (~55 lines)
    chat.py           (~175 lines)
    daemon.py         (~150 lines)
    knowledge_source.py (~180 lines)
    project.py        (~140 lines)
    slack.py          (~140 lines)
    usage.py          (~150 lines)
    voice.py          (~100 lines)
```

### Wiring pattern for cli.py

```python
# Sub-groups (named → nested commands)
from bearclaw.commands.auth import app as auth_app

app.add_typer(auth_app, name="auth")

# Top-level commands (unnamed → promoted to root)
from bearclaw.commands.chat import app as chat_app

app.add_typer(chat_app)
from bearclaw.commands.daemon import app as daemon_app

app.add_typer(daemon_app)
```

### Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Import order issues | Low | Explicit imports in cli.py, no circular deps |
| Test breakage | Low | Only 2 test files need import updates |
| Callback not firing | Low | Typer docs confirm callbacks work with named sub-apps |
| Entry point change | None | `bearclaw.cli:app` stays unchanged |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create bearclaw/commands/ package with __init__.py" --priority needed --status todo --tags "refactor,scope:cli" --body "Create src/bearclaw/commands/__init__.py (empty package marker). AC: package exists, importable."

kanban\kanban-md.exe create "Extract auth commands to bearclaw/commands/auth.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move auth_app, login, _login_async, auth status from cli.py to commands/auth.py. Wire via add_typer(auth_app, name='auth'). AC: bearclaw auth login/status work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract browser commands to bearclaw/commands/browser.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move browser_app, start, stop, browser_status from cli.py. AC: bearclaw browser start/stop/status work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract slack commands to bearclaw/commands/slack.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move slack_app, _slack_ssl_context, _load_slack_settings, _require_slack_settings, slack_auth/test/status from cli.py. AC: bearclaw slack auth/test/status work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract project commands to bearclaw/commands/project.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move project_app, _get_project_store, project_create/list/switch/archive/new from cli.py. AC: bearclaw project create/list/switch/archive/new work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract usage commands to bearclaw/commands/usage.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move usage_app, _get_usage_path, _resolve_usage_window, _aggregate_by_model, _print_usage_table, usage_show from cli.py. AC: bearclaw usage works, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract voice commands to bearclaw/commands/voice.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move voice_app, _make_voice_channel, voice_listen/speak/brainstorm from cli.py. AC: bearclaw voice listen/speak/brainstorm work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract knowledge-source commands to bearclaw/commands/knowledge_source.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move knowledge_source_app, _get_source_store, _VALID_SOURCE_TYPES, ks_add/list/show/remove from cli.py. AC: bearclaw knowledge-source add/list/show/remove work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract chat command to bearclaw/commands/chat.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move chat, _read_multiline, _detect_github_remote, _build_chat_session, _chat_async, _chat_loop, _EXIT_KEYWORDS from cli.py. Wire via add_typer(chat_app) WITHOUT name (top-level). Update test_cli_chat.py import for _detect_github_remote. AC: bearclaw chat works, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Extract daemon commands to bearclaw/commands/daemon.py" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "Move run_cmd, stop_cmd, status_cmd, _daemon_stop, _daemon_status, _get_config_dir, _is_process_alive, _poll_pid_removal from cli.py. Wire via add_typer(daemon_app) WITHOUT name (top-level). Update test_cli_daemon.py imports. AC: bearclaw run/stop/status work, tests pass. See docs/research/cli-split.md."

kanban\kanban-md.exe create "Slim cli.py to wiring-only hub (<200 lines)" --priority needed --status todo --tags "refactor,scope:cli" --depends-on 481 --body "After all extractions: cli.py should only contain app creation, version callback, global callback, and add_typer wiring. AC: cli.py <200 lines, all bearclaw commands work, all tests pass, ruff clean. See docs/research/cli-split.md."
```

