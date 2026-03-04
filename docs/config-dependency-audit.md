# Configuration & Dependency Audit

> **Date:** 2026-03-03 **Status:** Complete

## 1. Context and Question

Full audit of OwlBear's dependency health, version pinning, optional dependency
organisation, configuration design, secret management, import guards, and build
system correctness.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| uv docs — lock files | <https://docs.astral.sh/uv/concepts/projects/sync/#checking-if-the-lockfile-is-up-to-date> | .90 |
| pydantic-settings docs | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/> | .85 |
| PyPI — genai-prices | <https://pypi.org/project/genai-prices/> | .80 |
| PyPI — FlagEmbedding | <https://pypi.org/project/FlagEmbedding/> | .75 |
| PyPI — moonshine-voice | <https://pypi.org/project/moonshine-voice/> | .70 |
| Python Packaging Guide | <https://packaging.python.org/en/latest/guides/> | .80 |

## 3. Findings

### A. Dependency Health Table

| Dependency | Version Spec | Maintained? | Risk | Notes |
|---|---|---|---|---|
| genai-prices | `>=0.0.1` | Low maturity | **Medium** | Pre-1.0 with open floor; API may break |
| httpx | `>=0.28.0` | Active | Low | Stable, well-maintained |
| openai | `>=1.60.0` | Active | Low | Fast iteration; open floor is fine |
| pydantic | `>=2.10.0` | Active | Low | |
| pydantic-ai | `>=0.1.0` | Active | **Medium** | Pre-1.0; breaking changes expected |
| pydantic-settings | `>=2.7.0` | Active | Low | |
| tenacity | `>=9.0.0` | Active | Low | Stable retry lib |
| truststore | `>=0.10.0` | Active | Low | |
| typer | `>=0.15.0` | Active | Low | |
| playwright | `>=1.40.0` | Active | Low | Good guard |
| trafilatura | `>=2.0.0` | Active | Low | Good guard |
| qdrant-client | `>=1.13` | Active | Low | Good guard |
| FlagEmbedding | `>=1.3.5` | Active | **Medium** | Heavy dep tree (torch); partial guard |
| duckduckgo-search | `>=7.0` | Active | Low | Good guard |
| slack_sdk | `>=3.27.0` | Active | **High** | **No import guard** (see F-03) |
| moonshine-voice | `>=0.0.49,<0.1.0` | Low maturity | **Medium** | Pre-1.0; upper bound is good |
| numpy | `>=1.26` | Active | Low | |
| pyttsx3 | `>=2.90` | Dormant | **Medium** | Last PyPI release 2023; alternatives exist |
| sounddevice | *(missing)* | Active | **High** | Used but not declared (see F-05) |
| beir | *(unpinned)* | Active | Low | Benchmark-only |
| ranx | *(unpinned)* | Active | Low | Benchmark-only |

### B. Findings Detail

#### F-01 — Severity: LOW — `genai-prices` version floor too loose

`>=0.0.1` accepts every version ever published. Since the package is pre-1.0,
a breaking change in 0.1 → 0.2 will silently enter.

**Recommendation:** Pin to `>=0.0.1,<1.0` or tighter once the API stabilises.

---

#### F-02 — Severity: MEDIUM — `pydantic-ai` version floor may break

`>=0.1.0` with no ceiling. PydanticAI is pre-1.0 and actively refactoring
(toolset APIs, run context, etc.). A breaking minor bump will silently enter.

**Recommendation:** Add a ceiling: `>=0.1.0,<0.3` (or whatever current is),
and bump deliberately. The lock file mitigates day-to-day risk, but fresh
`uv sync` on a new machine or CI could pull a breaker.

---

#### F-03 — Severity: HIGH — `slack_sdk` has NO import guard

[channels/slack.py](src/owlbear/channels/slack.py#L9-L11) imports `slack_sdk`
at the module top level with no `try/except ImportError` guard:

```python
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient
```

Worse, [channels/\_\_init\_\_.py](src/owlbear/channels/__init__.py#L7) re-exports
`SlackChannel` unconditionally, so `from owlbear.channels import SlackChannel`
(or even `import owlbear.channels`) crashes without `slack_sdk` installed.

`bootstrap.py` correctly uses a deferred import, but the `__init__.py` defeats it.

**Recommendation:** Remove `SlackChannel` from `channels/__init__.py` (keep
the deferred import in `bootstrap.py`). Add a `try/except` guard in
`slack.py` like the browser/voice/knowledge modules do.

---

#### F-04 — Severity: HIGH — Broken import path `owlbear.channels.voice`

[bootstrap.py L232](src/owlbear/bootstrap.py#L232) imports:

```python
from owlbear.channels.voice import VoiceChannel
```

but `src/owlbear/channels/voice.py` does **not exist**. The voice channel lives
at `src/owlbear/voice/channel.py`. This will raise `ModuleNotFoundError` at
runtime when a user requests the voice channel.

The CLI ([cli.py L264](src/bearclaw/cli.py#L264)) uses the correct path:
`from owlbear.voice.channel import VoiceChannel`.

**Recommendation:** Fix bootstrap.py to
`from owlbear.voice import VoiceChannel`.

---

#### F-05 — Severity: HIGH — `sounddevice` used but not declared

[voice/channel.py L42](src/owlbear/voice/channel.py#L42) imports `sounddevice`
(with a graceful `try/except` guard), but the package is **not listed** in the
`[voice]` optional dependency group in `pyproject.toml`. Users who install
`owlbear[voice]` will get `moonshine-voice`, `numpy`, and `pyttsx3` but not
`sounddevice`. Voice recording will silently fail.

**Recommendation:** Add `"sounddevice>=0.4"` to the `voice` extras.

---

#### F-06 — Severity: MEDIUM — `FlagEmbedding` reranker has no import guard

[reranker.py L48](src/owlbear/memory/knowledge/reranker.py#L48) does a bare
`from FlagEmbedding import FlagReranker` with no `try/except`. If the
`knowledge` extra is not installed, `_ensure_model()` raises a raw
`ModuleNotFoundError` instead of the actionable message pattern used
everywhere else.

Compare with [embeddings.py L63-L71](src/owlbear/memory/knowledge/embeddings.py#L63-L71)
which correctly wraps the import.

**Recommendation:** Add the same `try/except ImportError` pattern with an
actionable message: `"Install with: uv sync --extra knowledge"`.

---

#### F-07 — Severity: MEDIUM — `bookmark_pipeline.py` trafilatura import unguarded

[bookmark_pipeline.py L185](src/owlbear/memory/knowledge/bookmark_pipeline.py#L185)
does `import trafilatura` inside `_default_web_read()` without a guard. If
neither `crawl` nor `search` extras are installed, this raises a raw
`ModuleNotFoundError`.

**Recommendation:** Add `try/except ImportError` with actionable message
pointing to `--extra crawl` or `--extra search`.

---

#### F-08 — Severity: LOW — `trafilatura` duplicated across two extras

`trafilatura>=2.0.0` appears in both the `crawl` and `search` extras.
Not a bug, but creates confusion about which extra to install for web
reading. The `bookmark_pipeline` (knowledge module) also needs it but
doesn't declare a dependency.

**Recommendation:** Consider a shared `web` extra that both `crawl` and
`search` depend on, or document that `crawl` provides trafilatura.

---

#### F-09 — Severity: LOW — No TOML config file support

`copilot-instructions.md` states the project uses "Env vars + TOML config file"
but `OwlBearSettings` only configures `env_prefix = "OWLBEAR_"`. There is no
`settings_customise_sources` override to add `TomlConfigSettingsSource`.
Configuration is env-vars-only.

**Recommendation:** Either add TOML file support via pydantic-settings
`TomlConfigSettingsSource` (e.g., `~/.owlbear/config.toml`) or update the
docs to reflect env-vars-only.

---

#### F-10 — Severity: LOW — `pyttsx3` maintenance risk

`pyttsx3` last published to PyPI in 2023. The project has open issues with
Python 3.12 compatibility on some platforms. Works on Windows but problematic
on macOS/Linux.

**Recommendation:** Monitor; consider `edge-tts` or system TTS as fallback.
Low urgency since voice is optional and planned.

---

#### F-11 — Severity: LOW — `knowledge/__init__.py` imports `QdrantVectorStore` eagerly

[knowledge/\_\_init\_\_.py L34](src/owlbear/memory/knowledge/__init__.py#L34)
imports `QdrantVectorStore` at module level. The `qdrant.py` module itself has
a `try/except` guard so the import won't crash, but it means `import
owlbear.memory.knowledge` loads the qdrant module even when only using the
graph/schema/chunker. This increases import time unnecessarily.

**Recommendation:** Move `QdrantVectorStore` to a lazy import or remove from
`__init__.py`; callers can import directly from `.qdrant`.

---

#### F-12 — Severity: INFO — Build system and lock file are correct

- `hatchling` build backend with `packages = ["src/owlbear", "src/bearclaw"]` ✓
- `uv.lock` exists and is git-tracked ✓
- `bearclaw` CLI entry point declared ✓
- `requires-python = ">=3.12"` matches `target-version = "py312"` ✓

---

#### F-13 — Severity: INFO — Secret management is sound

- `slack_app_token`, `slack_bot_token`, `github_token` all use `SecretStr` ✓
- Copilot token stored in a file (`copilot_token_path`), not in env var ✓
- Slack all-or-nothing validator prevents partial config ✓
- `.gitignore` covers `.env`, `.env.*`, `*.secret`, `*.local.toml` ✓

---

#### F-14 — Severity: LOW — No validators on several config fields

`temporal_decay_rate`, `temporal_recency_weight`, `embedding_idle_timeout`,
and `approval_timeout` have no validators. Negative or zero values would
cause subtle bugs (e.g., negative decay inverts the formula).

**Recommendation:** Add `@field_validator` for non-negative constraints on
numeric config fields.

---

#### F-15 — Severity: LOW — `beir` and `ranx` unpinned in benchmark extra

`benchmark = ["beir", "ranx"]` has no version specifiers. While benchmark-only,
unpinned deps can break CI unexpectedly.

**Recommendation:** Add minimum versions: `"beir>=2.0.0"`, `"ranx>=0.3"`.

## 4. Recommendation Summary

| ID | Severity | Confidence | Fix Effort |
|----|----------|------------|------------|
| F-03 | HIGH | .95 | Small — remove from `__init__`, add guard |
| F-04 | HIGH | .95 | Trivial — fix import path |
| F-05 | HIGH | .90 | Trivial — add to pyproject.toml |
| F-06 | MEDIUM | .90 | Small — add try/except |
| F-07 | MEDIUM | .85 | Small — add try/except |
| F-02 | MEDIUM | .80 | Small — add version ceiling |
| F-09 | LOW | .85 | Medium — add TOML source or update docs |
| F-14 | LOW | .85 | Small — add validators |
| F-01 | LOW | .75 | Trivial — tighten version spec |
| F-08 | LOW | .70 | Medium — restructure extras |
| F-10 | LOW | .65 | N/A — monitor only |
| F-11 | LOW | .80 | Small — lazy import |
| F-15 | LOW | .75 | Trivial — add version specs |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Fix slack_sdk missing import guard" --priority critical --status backlog --tags "config,bugfix" --body "F-03: channels/slack.py imports slack_sdk at top level with no try/except guard. channels/__init__.py re-exports SlackChannel unconditionally. Fix: (1) Remove SlackChannel from channels/__init__.py, (2) Add try/except ImportError guard in slack.py top-level imports. See docs/config-dependency-audit.md F-03."

kanban\kanban-md.exe create "Fix broken voice channel import in bootstrap.py" --priority critical --status backlog --tags "config,bugfix" --body "F-04: bootstrap.py L232 imports from owlbear.channels.voice which doesn't exist. Should be owlbear.voice or owlbear.voice.channel. See docs/config-dependency-audit.md F-04."

kanban\kanban-md.exe create "Add sounddevice to voice extras" --priority needed --status backlog --tags "config,deps" --body "F-05: voice/channel.py imports sounddevice but it's not declared in pyproject.toml [voice] extras. Add sounddevice>=0.4 to the voice dependency group. See docs/config-dependency-audit.md F-05."

kanban\kanban-md.exe create "Add import guard to FlagEmbedding reranker" --priority important --status backlog --tags "config,bugfix" --body "F-06: reranker.py L48 does bare FlagEmbedding import without try/except. Add the standard guard pattern with actionable error message. See docs/config-dependency-audit.md F-06."

kanban\kanban-md.exe create "Add import guard to bookmark_pipeline trafilatura" --priority important --status backlog --tags "config,bugfix" --body "F-07: bookmark_pipeline.py _default_web_read() imports trafilatura without guard. Add try/except with install instructions. See docs/config-dependency-audit.md F-07."

kanban\kanban-md.exe create "Add version ceilings to pre-1.0 deps" --priority nice-to-have --status backlog --tags "config,deps" --body "F-01/F-02: genai-prices and pydantic-ai have open-floor version specs. Add ceilings to prevent silent breaks on major API changes. See docs/config-dependency-audit.md."

kanban\kanban-md.exe create "Add config field validators for numeric bounds" --priority nice-to-have --status backlog --tags "config" --body "F-14: temporal_decay_rate, temporal_recency_weight, embedding_idle_timeout, approval_timeout have no validators. Add non-negative/positive constraints. See docs/config-dependency-audit.md F-14."

kanban\kanban-md.exe create "Resolve TOML config support — add or update docs" --priority nice-to-have --status ideation --tags "config,docs" --body "F-09: copilot-instructions.md claims TOML config but OwlBearSettings is env-only. Either add TomlConfigSettingsSource or correct the docs. See docs/config-dependency-audit.md F-09."
```
