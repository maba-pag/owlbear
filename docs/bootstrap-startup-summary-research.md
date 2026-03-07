# Bootstrap Startup Summary Research

> **Owning task:** #492 — Improve bootstrap error reporting with structured startup summary
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Bootstrap has 9 `except Exception` sites (lines 323, 424, 474, 520, 540, 629, 642, 750, 845) that all log at WARNING and return `None`. A misconfigured `github_token` or wrong DB path produces a silently crippled agent. The user has no single place to see what loaded and what failed.

**Question:** What pattern should OwlBear adopt to emit a structured startup summary listing loaded/failed toolsets?

## 2. Sources Studied

| # | Source | URL | Relevance | What we studied |
|---|--------|-----|-----------|-----------------|
| 1 | Django System Check Framework | https://docs.djangoproject.com/en/5.1/topics/checks/ | .90 | Tagged checks returning `CheckMessage` (Debug/Info/Warning/Error/Critical). Errors block `runserver`. Extensible via `@register`. |
| 2 | Celery Worker Banner | https://github.com/celery/celery/blob/main/celery/apps/worker.py | .85 | `emit_banner()` prints `[config]`, `[queues]`, `[tasks]` sections at startup. Single structured dump of system state. |
| 3 | Spring Boot ConditionEvaluationReport | https://docs.spring.io/spring-boot/reference/using/auto-configuration.html | .75 | `--debug` prints positive/negative matches for auto-configuration. Shows what loaded and why. |
| 4 | FastAPI Lifespan | https://fastapi.tiangolo.com/advanced/events/ | .50 | `@asynccontextmanager` for startup/shutdown. More about lifecycle than error reporting. |

## 3. Analysis

### 3.1 Current bootstrap exception sites

| Site | Line | Component | Catches | Current behavior |
|------|------|-----------|---------|-----------------|
| `_build_knowledge_infra` | 323 | Knowledge DB/vectors | `Exception` | WARNING + return None |
| `_build_knowledge_toolset` | 424 | KnowledgeToolset | `Exception` | WARNING + return None |
| `_build_bookmark_toolset` | 474 | BookmarkToolset | `Exception` | WARNING + return None |
| `_build_knowledge_source_toolset` | 520 | KnowledgeSourceToolset | `Exception` | WARNING + return None |
| `_build_web_search_toolset` | 540 | WebSearchToolset | `Exception` | WARNING + return None |
| SkillRegistry | 629 | SkillRegistry | `Exception` | WARNING, no return |
| GitHubToolset | 642 | GitHubToolset | `Exception` | WARNING, no return |
| `build_mcp_registry` | 750 | MCP servers | `Exception` | WARNING, returns registry |
| `_add_project_toolset` | 845 | ProjectToolset | `Exception` | WARNING, no return |

All 9 sites use `exc_info=True` (good for debug logs) but produce scattered, easy-to-miss warnings.

### 3.2 Pattern comparison

| Criterion | Django checks (.90) | Celery banner (.85) | Spring Boot report (.75) |
|-----------|---------------------|---------------------|--------------------------|
| Summary format | List of CheckMessage objects | Formatted text banner | Condition eval report |
| Severity levels | 5 (Debug-Critical) | N/A (info only) | positive/negative match |
| Blocks startup on error | Yes (Critical/Error) | No | No |
| User visibility | Console + management command | Console (stdout) | Console (--debug flag) |
| Extensibility | `@register` decorator | N/A | Auto from classpath |
| KISS alignment | Medium (full framework) | High (simple format) | Low (complex) |
| Fit for OwlBear | Good severity model | Good banner format | Over-engineered |

### 3.3 Fatal vs warn classification

Not all failures are equal. A failed optional dependency (ddgs not installed) is informational, while a configured-but-broken token is an error.

| Component | When to ERROR | When to WARN | When to skip silently |
|-----------|---------------|--------------|----------------------|
| GitHubToolset | `github_token` is set but init fails | Never (always configured) | `github_token` is not set |
| KnowledgeInfra | DB path exists but init fails | Optional dep import fails | Never attempted |
| WebSearchToolset | N/A | Import fails (optional dep) | Never |
| SkillRegistry | Skills dir exists but read fails | N/A | Skills dir doesn't exist |
| MCP servers | Server configured but connection fails | N/A | No servers configured |
| ProjectToolset | Active project set but init fails | N/A | No active project |

**Key insight from Django:** classify by "did the user intend this?" If a user configured something explicitly, failure is ERROR. If it's an optional auto-detected feature, failure is WARNING.

## 4. Recommendation (.85 confidence)

**Celery-inspired banner + Django-inspired severity classification.**

### 4.1 Data model

A simple `@dataclass` collecting results as bootstrap proceeds:

```
@dataclass
class ComponentStatus:
    name: str
    loaded: bool
    error: str | None = None  # exception message when loaded=False
    level: str = "INFO"       # INFO | WARNING | ERROR

@dataclass
class StartupSummary:
    components: list[ComponentStatus]
    workspace: Path
    project: str | None
    channel: str
```

### 4.2 Emission strategy

1. **Collect** — Each `_build_*` helper appends to the summary instead of only logging.
2. **Classify** — Use "configured but failed" = ERROR vs "optional dep missing" = WARNING.
3. **Emit via logger** — Single `logger.info()` with the full summary at end of `bootstrap()`.
4. **Emit via channel** — `channel.send()` a formatted summary so CLI/Slack users see it.

### 4.3 Output format (CLI example)

```
OwlBear startup summary
  Workspace: /home/user/projects/myapp
  Project:   my-project
  Channel:   cli

  [toolsets]
  OK  FileToolset
  OK  TerminalToolset
  OK  GitLocalToolset
  OK  KanbanToolset
  OK  BrowserToolset
  OK  KnowledgeToolset
  OK  BookmarkToolset
  FAIL  GitHubToolset — AuthenticationError: invalid token
  SKIP  WebSearchToolset — duckduckgo_search not installed

  [other]
  OK  MCP registry (2 servers)
  OK  Agent registry (5 agents)

  9 loaded, 1 failed, 1 skipped
```

### 4.4 Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Summary adds noise for users who don't care | Gate behind `log_startup_summary` setting (default: True) |
| `channel.send()` not yet available at summary time | Channel is created at step 1 in bootstrap, summary emitted at end — no issue |
| Summary format ties to specific toolset names | Use class name dynamically, not hardcoded strings |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add StartupSummary dataclass and collection to bootstrap" --priority needed --status backlog --tags "audit,resilience,scope:core" --body "Implement ComponentStatus and StartupSummary dataclasses. Modify each _build_* helper in bootstrap.py to append results. Emit structured summary via logger.info and channel.send at end of bootstrap(). Classify failures: ERROR when user-configured component fails, WARNING when optional dep missing. Gate behind log_startup_summary setting. AC: (1) bootstrap() collects status for all 9 exception sites, (2) single summary logged at INFO, (3) summary sent to channel, (4) user-configured failures logged at ERROR. See docs/bootstrap-startup-summary-research.md."

kanban\kanban-md.exe create "Add log_startup_summary config setting" --priority important --status backlog --tags "config,scope:core" --depends-on 492 --body "Add log_startup_summary: bool = True to OwlBearSettings. When False, suppress channel.send of startup summary (still log at DEBUG). See docs/bootstrap-startup-summary-research.md §4.4."

kanban\kanban-md.exe create "Test bootstrap startup summary output" --priority important --status backlog --tags "test,resilience,scope:core" --depends-on 492 --body "Write tests verifying: (1) all-OK summary when everything loads, (2) FAIL entry when a configured component fails, (3) SKIP entry when optional dep missing, (4) channel.send called with formatted summary, (5) summary suppressed when log_startup_summary=False. See docs/bootstrap-startup-summary-research.md."
```
