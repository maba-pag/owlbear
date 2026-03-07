# Resolve TOML Config Support: Add or Update Docs

> **Owning task:** #545 — Resolve TOML config support: add or update docs
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

`copilot-instructions.md` (line 49, Config row) claims:

> `pydantic-settings` — Env vars + TOML config file, validated at startup

`OwlBearSettings` in `src/owlbear/config.py` only configures
`model_config = {"env_prefix": "OWLBEAR_"}`. There is no
`settings_customise_sources` override, no `TomlConfigSettingsSource`, and no
`.owlbear.toml` or `config.toml` file anywhere in the repository.

**Question:** Should we add TOML file support or correct the documentation?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | pydantic-settings docs — TomlConfigSettingsSource | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#other-settings-source> | 1.0 |
| 2 | pydantic-settings docs — Field value priority | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#field-value-priority> | .9 |
| 3 | OwlBear config-dependency-audit F-09 | docs/config-dependency-audit.md | 1.0 |
| 4 | OwlBear config.py (OwlBearSettings) | src/owlbear/config.py | 1.0 |

## 3. Analysis

### 3a. Current state

- `OwlBearSettings` extends `BaseSettings` with `env_prefix="OWLBEAR_"`.
- All 30+ fields have sensible defaults; users override via `OWLBEAR_*` env vars.
- No TOML config file exists. No `settings_customise_sources` override.
- The docs claim is factually wrong — configuration is env-vars-only.

### 3b. Options

| Criterion | A: Fix docs (.85) | B: Add TOML support (.50) |
|---|---|---|
| Effort | ~1 line in copilot-instructions.md | ~15 LOC in config.py + create config template |
| KISS | High — no new code | Medium — new settings source, file discovery |
| YAGNI | High — env vars work, no user request for TOML | Low — building something nobody asked for |
| User benefit | Docs match reality | Easier to see all settings in one file |
| Risk | None | Must decide file location, handle missing file, test priority ordering |
| New deps | None | None (TomlConfigSettingsSource is built-in) |
| Backwards compat | N/A | N/A (no TOML users exist) |

### 3c. If TOML were added later

pydantic-settings makes this straightforward. The pattern from the official docs:

1. Add `toml_file` to `model_config` (e.g., `~/.owlbear/config.toml`)
2. Override `settings_customise_sources` to include `TomlConfigSettingsSource`
3. Priority: env vars > TOML file > defaults (standard pydantic-settings order)

This is a clean ~15 LOC change with no new dependencies. It can be a separate
task whenever there's actual demand for file-based config.

## 4. Recommendation (.85 confidence)

**Option A: Fix the docs.** Change the Config row in `copilot-instructions.md`
from "Env vars + TOML config file" to "Env vars (`OWLBEAR_` prefix)".

Rationale:

- **YAGNI** — No user, agent, or test currently reads a TOML config file.
  Adding it now builds complexity for zero benefit.
- **KISS** — Env vars are the simplest config mechanism. The system works.
- **Low risk** — TOML support can be added later in ~15 LOC if demand arises.
- The audit (F-09) already flagged this at LOW severity.

Risk: None. If TOML is needed later, the follow-up task below covers it.

## 5. Follow-up Tasks

### Task 1: Fix the docs claim (this task — #545)

The builder should change `copilot-instructions.md` line 49 Config Notes from:

```
Env vars + TOML config file, validated at startup
```

to:

```
Env vars (`OWLBEAR_` prefix), validated at startup
```

### Task 2: Optional future TOML support (new task)

```
kanban\kanban-md.exe create "Add optional TOML config file support to OwlBearSettings" --priority someday --tags config,feature --status ideation --body "Add ~/.owlbear/config.toml support via pydantic-settings TomlConfigSettingsSource. ~15 LOC. Only implement if users request file-based config. See docs/toml-config-resolution-research.md for approach. AC: (1) OwlBearSettings reads ~/.owlbear/config.toml if present, (2) env vars override TOML values, (3) missing file is silently ignored, (4) tests cover priority ordering."
```
