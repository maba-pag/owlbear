# Sources

External repos and resources studied during OwlBear development.

## Orchestration & Agent Frameworks Epic (Task #580)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | MIT | Agent delegation, programmatic hand-off, deep agents, graphs | `docs/research/orchestration-agent-frameworks-research.md` | 2026-03-07 |
| AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT/CC-BY-4.0 | LLM-based speaker selection, candidate functions, user feedback | `docs/research/orchestration-agent-frameworks-research.md` | 2026-03-07 |
| CrewAI Crews docs | <https://docs.crewai.com/concepts/crews> | Apache-2.0 | Sequential/hierarchical process, memory, crew output, streaming | `docs/research/orchestration-agent-frameworks-research.md` | 2026-03-07 |

## Visuals, Diagrams & MCP Integrations (Task #582)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| hustcc/mcp-mermaid | <https://github.com/hustcc/mcp-mermaid> | MIT | MCP Mermaid rendering patterns, output format options | `docs/research/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| antoinebou12/uml-mcp | <https://github.com/antoinebou12/uml-mcp> | MIT | Python MCP server, Kroki fallback strategy, diagram type support | `docs/research/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| Kroki.io | <https://kroki.io/> | MIT | Unified diagram rendering API, supported types/formats | `docs/research/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| peng-shawn/mermaid-mcp-server | <https://github.com/peng-shawn/mermaid-mcp-server> | MIT | Puppeteer-based Mermaid rendering, file save patterns | `docs/research/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | MIT | MCP Apps extension, cheat-sheet tool pattern | `docs/research/excalidraw-mcp-research.md` | 2026-03-07 |
| yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | MIT | 26-tool programmatic canvas, element CRUD, WebSocket sync | `docs/research/visuals-diagrams-mcp-research.md` | 2026-03-07 |

## Visual Output Skill (Task #706)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer v0.6.3 | <https://github.com/nicobailon/visual-explainer> | MIT | Workflow phases (think/structure/style/deliver), Mermaid routing table, aesthetic constraints, anti-slop guards | `.github/skills/visual-output/SKILL.md` | 2026-03-10 |
| Anthropic Agent Skills spec | <https://agentskills.io> | Apache-2.0 | SKILL.md format standard (YAML frontmatter + markdown instructions) | `.github/skills/visual-output/SKILL.md` | 2026-03-10 |

## HTML Diagram Templates (Task #708)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer templates/ | <https://github.com/nicobailon/visual-explainer/tree/main/plugins/visual-explainer/templates> | MIT | 3 reference HTML templates: architecture (CSS Grid cards, depth tiers), data-table (HTML table, KPI cards, status badges), mermaid-flowchart (Mermaid CDN, zoom/pan JS) | `.github/skills/visual-output/templates/` | 2026-03-10 |
| nicobailon/visual-explainer css-patterns.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/references/css-patterns.md> | MIT | CSS reference patterns: theme setup, card components, depth tiers, grid layouts, Mermaid containers, animations, overflow protection | `docs/research/html-diagram-templates-research.md` | 2026-03-10 |

## Project-Recap Visual Command (Task #709)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer — project-recap.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/commands/project-recap.md> | MIT | 8-section project recap HTML structure, data gathering pattern | `.github/prompts/project-recap.prompt.md` | 2026-03-10 |
| Aider-AI/aider — RepoMap | <https://github.com/Aider-AI/aider/blob/main/aider/repomap.py> | Apache-2.0 | Repo overview concept validation (tree-sitter + PageRank codebase map) | `docs/research/project-recap-command-research.md` | 2026-03-10 |
| VS Code prompt files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | .prompt.md format specification (frontmatter, variables, tool lists) | `.github/prompts/project-recap.prompt.md` | 2026-03-10 |

## Session Hook Emission (Task #711)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Agents SDK — Lifecycle | <https://openai.github.io/openai-agents-python/ref/lifecycle/> | MIT | `on_agent_start`/`on_agent_end` hooks pattern, payload design | `docs/research/session-hook-emission-research.md` | 2026-03-09 |
| PydanticAI — Agents docs | <https://ai.pydantic.dev/agents/> | MIT | Agent run lifecycle, event streaming (no built-in session hooks) | `docs/research/session-hook-emission-research.md` | 2026-03-09 |

## Consolidate trafilatura Extras (Task #569)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python Packaging Guide â€” pyproject.toml | <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/> | CC-BY-SA-4.0 | Optional-dependencies syntax, extras best practices | `docs/research/consolidate-trafilatura-extras-research.md` | 2026-03-07 |
| uv docs â€” optional dependencies | <https://docs.astral.sh/uv/concepts/projects/dependencies/#optional-dependencies> | MIT | uv extras handling, self-referencing extras support | `docs/research/consolidate-trafilatura-extras-research.md` | 2026-03-07 |
| httpx pyproject.toml | <https://github.com/encode/httpx/blob/master/pyproject.toml> | BSD-3-Clause | Flat, self-contained extras pattern (prior art) | `docs/research/consolidate-trafilatura-extras-research.md` | 2026-03-07 |

## DAEMON_STARTUP Hook Event (Task #624)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| FastAPI lifespan events | <https://fastapi.tiangolo.com/advanced/events/> | MIT | Startup/shutdown event patterns, `on_event("startup")`, lifespan context manager | `docs/research/daemon-startup-hook-research.md` | 2026-03-07 |
| Starlette lifespan | <https://starlette.dev/lifespan/> | BSD-3-Clause | Lifespan async context manager, fire-before-serve pattern, state sharing | `docs/research/daemon-startup-hook-research.md` | 2026-03-07 |
| Django signals reference | <https://docs.djangoproject.com/en/5.0/ref/signals/> | BSD-3-Clause | Signal patterns (request_started, pre/post_migrate), no process-level startup signal | `docs/research/daemon-startup-hook-research.md` | 2026-03-07 |
| pydantic pyproject.toml | <https://github.com/pydantic/pydantic/blob/main/pyproject.toml> | MIT | Extras vs dependency-groups patterns (prior art) | `docs/research/consolidate-trafilatura-extras-research.md` | 2026-03-07 |

## Rigor Profiles (Task #618)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nWave `/nw:rigor` command | <https://github.com/nWave-ai/nWave> | MIT | 5-level rigor profile system, settings matrix, profile schema, per-task quality scaling | `docs/research/rigor-profiles-research.md` | 2026-03-07 |
| Conductor evaluate-loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Max-3 fix cycles, automated quality gates, model-agnostic eval approach | `docs/research/rigor-profiles-research.md` | 2026-03-07 |

## Retrospective Learning Hook (Task #621)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Conductor retrospective agent | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Post-track retrospective â†’ patterns.md + errors.json knowledge layer | `docs/research/retrospective-learning-hook-research.md` | 2026-03-07 |
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Verbal self-reflection stored in episodic memory buffer for agent learning | `docs/research/retrospective-learning-hook-research.md` | 2026-03-07 |

## WIP Continuity Store Research (Task #615)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| quoroom-ai/room agent-loop.ts | <https://github.com/quoroom-ai/room/blob/main/src/shared/agent-loop.ts> | MIT | WIP save/load pattern, CONTINUE FORWARD prompt injection, auto-WIP fallback, momentum gap | `docs/research/wip-continuity-store-research.md` | 2026-03-07 |
| LangGraph durable execution | <https://docs.langchain.com/oss/python/langgraph/durable-execution> | MIT | Checkpoint persistence concept, thread-id keyed state, resume semantics | `docs/research/wip-continuity-store-research.md` | 2026-03-07 |

## HeartbeatRunner Research (Task #616)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenClaw Heartbeat docs | <https://docs.openclaw.ai/gateway/heartbeat> | MIT | Proactive agent timer pattern, HEARTBEAT_OK suppression contract | `docs/research/heartbeat-runner-research.md` | 2026-03-07 |
| Python asyncio.TaskGroup docs | <https://docs.python.org/3.12/library/asyncio-task.html#task-groups> | PSF | TaskGroup structured concurrency for sibling coroutines | `docs/research/heartbeat-runner-research.md` | 2026-03-07 |
| APScheduler user guide | <https://apscheduler.readthedocs.io/en/latest/userguide.html> | MIT | Scheduler framework evaluation (rejected â€” YAGNI) | `docs/research/heartbeat-runner-research.md` | 2026-03-07 |

## Rich Table CLI Research (Task #630)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Rich Tables docs | <https://rich.readthedocs.io/en/latest/tables.html> | MIT | Table API, add_column, add_row, add_section, box styles, Column options | `docs/research/rich-table-cli-research.md` | 2026-03-07 |
| Rich Console docs | <https://rich.readthedocs.io/en/latest/console.html> | MIT | Terminal auto-detection, is_terminal, NO_COLOR env var, pipe behavior | `docs/research/rich-table-cli-research.md` | 2026-03-07 |

## Enhanced bearclaw status with rich.Panel (Task #631)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| rich-cli Panel + Table pattern | <https://github.com/Textualize/rich-cli/blob/main/src/rich_cli/__main__.py> | MIT | Panel wrapping Table for structured CLI output, border_style convention | `src/bearclaw/cli.py` (`_daemon_status`) | 2026-03-07 |
| Prefect server CLI status display | <https://github.com/PrefectHQ/prefect/blob/main/src/prefect/cli/_server_utils.py> | Apache-2.0 | Plain text for status, Table for service listing â€” informed key-value layout choice | `docs/research/enhanced-bearclaw-status-research.md` | 2026-03-07 |

## Knowledge Sub-Packages Research (Task #566)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex core layout | <https://github.com/run-llama/llama_index/tree/main/llama-index-core/llama_index/core> | MIT | Sub-package organization at scale (40+ dirs), splitting rationale | `docs/research/knowledge-subpackages-research.md` | 2026-03-07 |
| LangChain core layout | <https://github.com/langchain-ai/langchain/tree/master/libs/core/langchain_core> | MIT | Sub-package organization, domain grouping per concern | `docs/research/knowledge-subpackages-research.md` | 2026-03-07 |
| Python Guide â€” Structuring Your Project | <https://docs.python-guide.org/writing/structure/> | CC-BY-NC-SA-3.0 | PEP 20 "flat is better than nested", module/package guidance | `docs/research/knowledge-subpackages-research.md` | 2026-03-07 |
| Ionel Cristian Maries â€” Packaging a Python library | <https://blog.ionelmc.ro/2014/05/25/python-packaging/> | Blog | "Flat is better than nested" for data; src-layout advocacy | `docs/research/knowledge-subpackages-research.md` | 2026-03-07 |

## Role Policy Before Agent Construction (Task #561)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agent constructor docs | <https://ai.pydantic.dev/agents/> | MIT | Agent init signature, stateless construction, no I/O side effects | `docs/research/role-policy-before-agent-construction-research.md` | 2026-03-07 |
| PydanticAI Toolsets â€” FilteredToolset | <https://ai.pydantic.dev/toolsets/#filtering-tools> | MIT | `toolset.filtered()` API, compose-before-construct pattern | `docs/research/role-policy-before-agent-construction-research.md` | 2026-03-07 |

## Role System Complexity Evaluation (Task #565)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Toolsets â€” FilteredToolset | <https://ai.pydantic.dev/toolsets/#filtering-tools> | MIT | Native tool filtering as simpler alternative to custom role policy | `docs/research/role-system-complexity-research.md` | 2026-03-07 |
| CrewAI Agents docs | <https://docs.crewai.com/concepts/agents> | Apache-2.0 | Per-agent tools list, no role-based access abstraction | `docs/research/role-system-complexity-research.md` | 2026-03-07 |

## Workflow, Dashboards & Developer Tools (Task #583)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Textualize/rich | <https://github.com/Textualize/rich> | MIT | Terminal formatting: tables, progress bars, panels, tracebacks | `docs/research/workflow-dashboards-devtools-research.md` | 2026-03-07 |
| Textualize/textual | <https://github.com/Textualize/textual> | MIT | TUI framework evaluation for future dashboard | `docs/research/workflow-dashboards-devtools-research.md` | 2026-03-07 |
| otel-tui | <https://github.com/ymtdzzz/otel-tui> | Apache-2.0 | Terminal OTel viewer for observability display | `docs/research/workflow-dashboards-devtools-research.md` | 2026-03-07 |
| Rich progress docs | <https://rich.readthedocs.io/en/latest/progress.html> | MIT | Multi-task progress bar patterns | `docs/research/workflow-dashboards-devtools-research.md` | 2026-03-07 |

## Textual TUI Dashboard Evaluation (Task #633)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| darrenburns/posting | <https://github.com/darrenburns/posting> | Apache-2.0 | Textual HTTP client TUI â€” real-world complexity reference (~6k LOC) | `docs/research/textual-tui-dashboard-research.md` | 2026-03-07 |
| tconbeer/harlequin | <https://github.com/tconbeer/harlequin> | MIT | Textual SQL IDE â€” large-scale Textual app, DataTable usage | `docs/research/textual-tui-dashboard-research.md` | 2026-03-07 |
| Textual reactivity guide | <https://textual.textualize.io/guide/reactivity/> | MIT | Reactive attributes, watch methods, data binding for live updates | `docs/research/textual-tui-dashboard-research.md` | 2026-03-07 |
| Textual layout guide | <https://textual.textualize.io/how-to/design-a-layout/> | MIT | Dock, FR units, containers â€” dashboard panel layout patterns | `docs/research/textual-tui-dashboard-research.md` | 2026-03-07 |

## ks_ Rename Research (Task #560)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer docs â€” Custom Command Name | <https://typer.tiangolo.com/tutorial/commands/name/> | MIT | Function name vs CLI command name decoupling | `docs/research/ks-rename-research.md` | 2026-03-07 |
| Typer docs â€” SubCommands Single File | <https://typer.tiangolo.com/tutorial/subcommands/single-file/> | MIT | Canonical `{group}_{action}` function naming pattern | `docs/research/ks-rename-research.md` | 2026-03-07 |

## PydanticAI Deprecation Warnings Research (Task #556)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI changelog v0.8.1 | <https://ai.pydantic.dev/changelog/> | MIT | Deprecation of bare model names (PR #2711), required `provider:model` format | `docs/research/pydanticai-deprecation-warnings-research.md` | 2026-03-07 |
| PydanticAI `infer_model()` source | local `.venv/.../pydantic_ai/models/__init__.py` | MIT | Warning trigger logic: string without `:` + known prefix â†’ DeprecationWarning | `docs/research/pydanticai-deprecation-warnings-research.md` | 2026-03-07 |

## Conftest Extraction Research (Task #555)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pytest docs â€” conftest.py fixtures | <https://docs.pytest.org/en/stable/reference/fixtures.html> | MIT | Fixture scoping, conftest auto-discovery, sharing fixtures across files | `docs/research/conftest-extraction-research.md` | 2026-03-07 |
| pytest docs â€” how to use fixtures | <https://docs.pytest.org/en/stable/how-to/fixtures.html> | MIT | Factory-as-fixture pattern, fixture organization best practices | `docs/research/conftest-extraction-research.md` | 2026-03-07 |

## Optional Tool Graceful Degradation Research (Task #611)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain `guard_import()` | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/utils/utils.py> | MIT | `guard_import()` fail-with-guidance pattern for missing optional deps | `docs/research/optional-tool-graceful-degradation-research.md` | 2026-03-07 |
| Haystack `LazyImport` | <https://github.com/deepset-ai/haystack/blob/main/haystack/lazy_imports.py> | Apache-2.0 | Deferred `ImportError` context manager for optional deps | `docs/research/optional-tool-graceful-degradation-research.md` | 2026-03-07 |

## Slack Channel send_file Research (Task #552)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack SDK Web Client docs | <https://docs.slack.dev/tools/python-slack-sdk/web/index.html> | MIT | `files_upload_v2` usage pattern, parameters, threading support | `docs/research/slack-send-file-research.md` | 2026-03-07 |
| Slack `files.upload` API reference | <https://docs.slack.dev/reference/methods/files.upload> | N/A | Confirmed deprecation of old API; v2 via `getUploadURLExternal` + `completeUploadExternal` is required | `docs/research/slack-send-file-research.md` | 2026-03-07 |
| slack_sdk `AsyncWebClient` source | <https://github.com/slackapi/python-slack-sdk/blob/main/slack_sdk/web/async_client.py> | MIT | `files_upload_v2` 3-step implementation details | `docs/research/slack-send-file-research.md` | 2026-03-07 |

## Knowledge `__init__.py` Trim Research (Task #550)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PEP 8 â€” Public and Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | PSF | `__all__` guidance, public vs internal naming, re-export conventions | `docs/research/knowledge-init-trim-research.md` | 2026-03-07 |
| Google Python Style Guide â€” Imports | <https://google.github.io/styleguide/pyguide.html#22-imports> | CC-BY-3.0 | Import conventions, module-level imports, package API patterns | `docs/research/knowledge-init-trim-research.md` | 2026-03-07 |

## Rich Traceback and RichHandler Research (Task #632)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Rich logging docs | <https://rich.readthedocs.io/en/stable/logging.html> | MIT | `RichHandler` constructor params, Console isolation, markup=False safety | `docs/research/rich-traceback-richhandler-research.md` | 2026-03-07 |
| Rich traceback docs | <https://rich.readthedocs.io/en/stable/traceback.html> | MIT | `install()` API, `suppress` param, `show_locals` flag | `docs/research/rich-traceback-richhandler-research.md` | 2026-03-07 |
| `RichHandler` source (Textualize/rich) | <https://github.com/Textualize/rich/blob/master/rich/logging.py> | MIT | Handler emits via `Console.print()`, independent of other handlers' formatters | `docs/research/rich-traceback-richhandler-research.md` | 2026-03-07 |
| Litestar logging config | <https://github.com/litestar-org/litestar/blob/main/litestar/logging/config.py> | MIT | Prior art: `RichTracebackFormatter` usage in structured logging config | `docs/research/rich-traceback-richhandler-research.md` | 2026-03-07 |

## Re-exports in Empty `__init__.py` Research (Task #549)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python import system docs | <https://docs.python.org/3/reference/import.html#regular-packages> | PSF | `__init__.py` semantics, submodule binding rules | `docs/research/init-reexports-research.md` | 2026-03-07 |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> | MIT | 100+ re-export pattern for library public API | `docs/research/init-reexports-research.md` | 2026-03-07 |
| httpx `__init__.py` | <https://github.com/encode/httpx> | BSD-3 | Heavy re-export + `__all__` pattern for library | `docs/research/init-reexports-research.md` | 2026-03-07 |

## Lazy-Singleton OwlBearSettings Research (Task #536)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| FastAPI Settings docs | <https://fastapi.tiangolo.com/advanced/settings/> | MIT | `@lru_cache` singleton pattern for pydantic-settings; official recommendation from Typer/FastAPI author | `docs/research/lazy-singleton-settings-research.md` | 2026-03-07 |
| Typer Callback docs | <https://typer.tiangolo.com/tutorial/commands/callback/> | MIT | `@app.callback()` pattern for shared CLI state; sub-Typer propagation limitations | `docs/research/lazy-singleton-settings-research.md` | 2026-03-07 |

## Brittle Prompt Assertions Research (Task #554)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI test_agent.py | <https://github.com/pydantic/pydantic-ai/blob/main/tests/test_agent.py> | MIT | How PydanticAI tests agents â€” behavior-based, never asserts on prompt content | `docs/research/brittle-prompt-assertions-research.md` | 2026-03-07 |
| CheckList (Ribeiro et al. 2020) | <https://arxiv.org/abs/2005.04118> | N/A | Invariance/directional testing principles for ML â€” test properties not literals | `docs/research/brittle-prompt-assertions-research.md` | 2026-03-07 |
| Eugene Yan â€” Testing ML Systems | <https://eugeneyan.com/writing/testing-ml/> | N/A | Implementation vs learned-behavior tests; assert on properties not exact outputs | `docs/research/brittle-prompt-assertions-research.md` | 2026-03-07 |

## Docstring Style Standardization Research (Task #543)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Ruff pydocstyle convention docs | <https://docs.astral.sh/ruff/settings/#lintpydocstyleconvention> | MIT | `convention = "google"` setting; which D rules are included/excluded per convention | `docs/research/docstring-style-research.md` | 2026-03-07 |
| Ruff FAQ: Google/NumPy docstrings | <https://docs.astral.sh/ruff/faq/#does-ruff-support-numpy-or-google-style-docstrings> | MIT | Exact rule set for Google convention; incremental enablement workflow | `docs/research/docstring-style-research.md` | 2026-03-07 |

## Slack Sender Validation Research (Task #526)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack `message.im` event reference | <https://docs.slack.dev/reference/events/message.im> | Slack ToS | DM event payload structure; `user` field identifies sender | `docs/research/slack-sender-validation-research.md` | 2026-03-07 |
| Slack Events API docs | <https://docs.slack.dev/apis/events-api> | Slack ToS | Event wrapper structure; `user` field on inner event; `bot_message` subtype; server-side rate limits (30K/workspace/60min) | `docs/research/slack-sender-validation-research.md` | 2026-03-07 |

## ErrorJournal Async-Safety Research (Task #541)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” `asyncio.to_thread` | <https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread> | PSF | stdlib API for offloading blocking I/O to thread pool; confirmed uses `run_in_executor` internally | `docs/research/error-journal-async-research.md` | 2026-03-07 |
| aiofiles library (v25.1.0) | <https://github.com/Tinche/aiofiles> | Apache-2.0 | Async file I/O library; confirmed it also uses `run_in_executor` under the hood; evaluated as alternative approach | `docs/research/error-journal-async-research.md` | 2026-03-07 |

## Hardcoded Model Defaults Research (Task #551)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agent docs | <https://ai.pydantic.dev/agents/> | MIT | Agent model parameter patterns; model is caller-provided, not settings-integrated | `docs/research/hardcoded-model-defaults-research.md` | 2026-03-07 |
| pydantic-settings docs | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/> | MIT | BaseSettings as single source of truth pattern; env var override; field defaults centralized | `docs/research/hardcoded-model-defaults-research.md` | 2026-03-07 |

## BrowserConfig Nesting Research (Task #553)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pydantic-settings docs â€” nested models | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values> | MIT | `env_nested_delimiter`, `nested_model_default_partial_update`, nested BaseModel env var mapping | `docs/research/browser-config-nesting-research.md` | 2026-03-07 |
| pydantic-settings test suite | <https://github.com/pydantic/pydantic-settings/blob/main/tests/test_settings.py> | MIT | `test_nested_env_complex_values`, `test_class_nested_model_default_partial_update` â€” confirmed `env_prefix` + `env_nested_delimiter='__'` pattern works with nested BaseModel fields | `docs/research/browser-config-nesting-research.md` | 2026-03-07 |

## CLI Error-Exit Pattern Research (Task #532)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer â€” Terminating docs | <https://typer.tiangolo.com/tutorial/terminating/> | MIT | `typer.Exit` usage patterns, canonical error-exit idiom | `docs/research/cli-error-exit-research.md` | 2026-03-07 |
| Typer GitHub repo | <https://github.com/fastapi/typer> | MIT | Confirmed no built-in error helper; user-space pattern | `docs/research/cli-error-exit-research.md` | 2026-03-07 |
| Slack Security Best Practices | <https://docs.slack.dev/authentication/best-practices-for-security> | Slack ToS | "Validate message source" pattern; rate-limiting guidance; prompt injection mitigation for AI apps; comprehensive logging | `docs/research/slack-sender-validation-research.md` | 2026-03-07 |

## ErrorJournal Dedup Key Research (Task #567)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Sentry Issue Grouping docs | <https://docs.sentry.io/concepts/data-management/event-grouping/> | BSL-1.1 | Fingerprint-based event dedup: hash of (exception_type, value, stack_trace); grouping hierarchy; time-window suppression | `docs/research/error-journal-dedup-research.md` | 2026-03-07 |
| structlog processors docs | <https://www.structlog.org/en/stable/processors.html> | MIT | Processor-chain filtering pattern; `DropEvent` for dedup-style suppression; composable filter-before-write design | `docs/research/error-journal-dedup-research.md` | 2026-03-07 |

## Exception Hierarchy Research (Task #539)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx exceptions module | <https://github.com/encode/httpx/blob/master/httpx/_exceptions.py> | BSD-3 | Single-root `HTTPError(Exception)` hierarchy pattern; MI for timeout cross-cutting | `docs/research/exception-hierarchy-research.md` | 2026-03-07 |
| requests exceptions module | <https://github.com/psf/requests/blob/main/src/requests/exceptions.py> | Apache-2.0 | `RequestException(IOError)` root; MI pattern `ConnectTimeout(ConnectionError, Timeout)` | `docs/research/exception-hierarchy-research.md` | 2026-03-07 |
| Click exceptions module | <https://github.com/pallets/click/blob/main/src/click/exceptions.py> | BSD-3 | `ClickException(Exception)` root; intentional exclusion of `Abort`/`Exit` from hierarchy | `docs/research/exception-hierarchy-research.md` | 2026-03-07 |
| Django core exceptions | <https://github.com/django/django/blob/main/django/core/exceptions.py> | BSD-3 | No single root â€” flat exceptions; studied as anti-pattern | `docs/research/exception-hierarchy-research.md` | 2026-03-07 |

## Centralize trafilatura.extract Research (Task #537)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | Apache-2.0 | `extract()` API params (`output_format`, `include_links`, `url`); `extract_metadata()` API; `Extractor` settings class | `docs/research/centralize-trafilatura-research.md` | 2026-03-07 |
| trafilatura GitHub repo | <https://github.com/adbar/trafilatura> | Apache-2.0 | Confirmed extract API surface, optional params, metadata extraction | `docs/research/centralize-trafilatura-research.md` | 2026-03-07 |
| Slack `message` event subtypes | <https://docs.slack.dev/reference/events/message> | Slack ToS | `bot_message` subtype has no `user` field; full subtype taxonomy for filtering | `docs/research/slack-sender-validation-research.md` | 2026-03-07 |
| Bolt for Python event listening | <https://docs.slack.dev/tools/bolt-python/concepts/event-listening> | Slack ToS | Subtype filtering pattern; `bot_message` filter via event dict matching | `docs/research/slack-sender-validation-research.md` | 2026-03-07 |

## Declarative Tool Registration Research (Task #538)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Toolsets docs (v1.67) | <https://ai.pydantic.dev/toolsets/> | MIT | `FunctionToolset` registration APIs: `@toolset.tool`, `tools=` constructor, `add_function()`; no class-level declarative API exists | `docs/research/declarative-tool-registration-research.md` | 2026-03-07 |
| pydantic-ai-skills | <https://github.com/DougTrajano/pydantic-ai-skills> | MIT | Third-party `SkillsToolset`; uses same imperative `add_function()`-style pattern, no declarative class API | `docs/research/declarative-tool-registration-research.md` | 2026-03-07 |

## TOML Config Resolution Research (Task #545)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pydantic-settings docs â€” Other settings source | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#other-settings-source> | MIT | `TomlConfigSettingsSource` API, `toml_file` model_config, `settings_customise_sources` override pattern | `docs/research/toml-config-resolution-research.md` | 2026-03-07 |
| pydantic-settings docs â€” Field value priority | <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#field-value-priority> | MIT | Default source priority ordering (CLI > init > env > dotenv > secrets > defaults) | `docs/research/toml-config-resolution-research.md` | 2026-03-07 |

## Validator Role Policy Research (Task #524)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OWASP LLM06:2025 Excessive Agency | <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/> | CC-BY-SA | Least-privilege tool access for LLM agents; allow-list over deny-list; minimize extensions guidance | `docs/research/validator-role-policy-research.md` | 2026-03-07 |
| NVIDIA NeMo-Guardrails security guidelines | <https://github.com/NVIDIA/NeMo-Guardrails/blob/main/docs/security/guidelines.md> | Apache-2.0 | Scoped action permissions for AI agents; explicit tool grants | `docs/research/validator-role-policy-research.md` | 2026-03-07 |

## Security Audit Log Research (Task #525)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | CC-BY-SA-4.0 | Security event taxonomy (when/where/who/what), retention guidance, append-only audit trail, events to log | `docs/research/security-audit-log-research.md` | 2026-03-07 |
| Python logging.handlers docs | <https://docs.python.org/3/library/logging.handlers.html> | PSF | FileHandler append mode, RotatingFileHandler vs non-rotating, handler comparison for audit use case | `docs/research/security-audit-log-research.md` | 2026-03-07 |
| structlog docs | <https://www.structlog.org/en/stable/> | MIT | Structured logging approach evaluation, processor chain pattern | `docs/research/security-audit-log-research.md` | 2026-03-07 |

## Startfile Allowlist Research (Task #527)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python os.startfile docs | <https://docs.python.org/3/library/os.html#os.startfile> | PSF | ShellExecute behavior, security implications of opening arbitrary file types | `docs/research/startfile-allowlist-research.md` | 2026-03-07 |
| OWASP Unrestricted File Upload | <https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload> | CC-BY-SA | Allowlist-over-denylist guidance for file type validation | `docs/research/startfile-allowlist-research.md` | 2026-03-07 |

## Bootstrap Patching Elimination Research (Task #523)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Fowler â€” DI and IoC | <https://martinfowler.com/articles/injection.html> | CC-BY | Constructor injection as preferred DI form; setter injection anti-pattern when constructor is feasible | `docs/research/bootstrap-patching-elimination-research.md` | 2026-03-07 |
| python-dependency-injector docs | <https://python-dependency-injector.ets-labs.org/introduction/di_in_python.html> | BSD-3 | DI principles in Python; constructor injection vs service locator trade-offs | `docs/research/bootstrap-patching-elimination-research.md` | 2026-03-07 |

## Ingest Complexity Reduction Research (Task #517)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex IngestionPipeline | <https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/ingestion/pipeline.py> | MIT | Orchestrator-only pipeline pattern; separate docstore for status/dedup; composable transformation stages | `docs/research/ingest-complexity-reduction-research.md` | 2026-03-06 |
| Haystack Pipelines docs | <https://docs.haystack.deepset.ai/docs/pipelines> | Apache-2.0 | Directed graph of independent Component classes; pipeline as routing/orchestration only | `docs/research/ingest-complexity-reduction-research.md` | 2026-03-06 |
| Python Patterns: Composition over Inheritance | <https://python-patterns.guide/gang-of-four/composition-over-inheritance/> | CC-BY-SA | SRP via composition; delegate concerns to separate objects; orchestrator composes helpers | `docs/research/ingest-complexity-reduction-research.md` | 2026-03-06 |

## Slack Receive Timeout Research (Task #513)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | Slack ToS | WebSocket idle behavior, ping-pong keepalive, connection refresh, disconnect protocol | `docs/research/slack-receive-timeout-research.md` | 2026-03-06 |
| slack_sdk SocketModeClient (aiohttp) | <https://github.com/slackapi/python-slack-sdk/blob/main/slack_sdk/socket_mode/aiohttp/__init__.py> | MIT | Auto-reconnect, ping-pong monitoring, session lifecycle, `is_ping_pong_failing()` | `docs/research/slack-receive-timeout-research.md` | 2026-03-06 |
| Bolt for Python AsyncBaseSocketModeHandler | <https://github.com/slackapi/bolt-python/blob/main/slack_bolt/adapter/socket_mode/async_base_handler.py> | MIT | Official idle pattern: `asyncio.sleep(inf)` after connect, event-driven push model via listeners | `docs/research/slack-receive-timeout-research.md` | 2026-03-06 |

## Dependency Inversion Research (Task #502)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Cosmic Python Ch.3 â€” Coupling & Abstractions | <https://www.cosmicpython.com/book/chapter_03_abstractions.html> | CC-BY-NC-ND | Functional Core / Imperative Shell, dependency injection via abstractions, callback-based DI for decoupling I/O from business logic | `docs/research/memory-tools-dependency-inversion-research.md` | 2026-03-06 |
| Python typing.Protocol (PEP 544) | <https://docs.python.org/3/library/typing.html#typing.Protocol> | PSF | Protocol-based structural subtyping for dependency inversion, Callable type hints for callback injection | `docs/research/memory-tools-dependency-inversion-research.md` | 2026-03-06 |

## Agent Pattern Research (Task #22)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenClaw | <https://github.com/openclaw/openclaw> | MIT | Agent loop, ChannelPlugin adapter, JSONL sessions, hook system, heartbeat, auth rotation, build pipeline, AGENTS.md repo guidelines, multi-agent safety rules, docs linking conventions | `src/owlbear/core/agent.py` (agent loop), `src/owlbear/channels/` (ChannelPlugin adapter), `src/owlbear/memory/session.py` (JSONL sessions), `src/owlbear/core/hooks.py` (hook system), `.github/agents/orchestrator.agent.md` (multi-agent safety) | 2026-02-22 |
| Nanobot | <https://github.com/HKUDS/nanobot> | MIT | MessageBus, Tool ABC, LiteLLM provider, progressive skill loading, two-layer memory, SubagentManager (restricted tool sets, max iterations, result announcement) | `src/owlbear/channels/` (MessageBus), `src/owlbear/skills/registry.py` (progressive skill loading), `src/owlbear/memory/` (two-layer memory), `.github/agents/orchestrator.agent.md` (subagent dispatch pattern) | 2026-02-22 |
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | MIT | Claude Code hooks (13 event types), builder/validator team pattern, meta-agent factory, Plan W Team Lead (supervisor dispatch), TTS integration, safety guards, PostToolUse validators | `src/owlbear/core/hooks.py` (hook events), `.github/agents/builder.agent.md` (builder role), `.github/agents/reviewer.agent.md` (validator role), `.github/agents/architect.agent.md` (Plan W Team Lead + Meta-Agent reasoning), `.github/agents/writer.agent.md` (Validator report pattern) | 2026-02-22 |

## Agent Architecture Optimization (2026-02-26)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | MIT | Plan W Team Lead pattern (supervisor dispatch, dependency chains), Meta-Agent factory (architecture reasoning), Validator structured report (PASS/FAIL with evidence) | `.github/agents/architect.agent.md` (Plan W Team Lead + Meta-Agent inspiration), `.github/agents/writer.agent.md` (Validator report pattern), `.github/agents/orchestrator.agent.md` (named agent routing via `agentName`) | 2026-02-26 |
| OpenClaw | <https://github.com/openclaw/openclaw> | MIT | AGENTS.md repo guidelines, multi-agent workspace safety rules, docs linking conventions (Mintlify) | `.github/agents/writer.agent.md` (docs linking conventions), `.github/copilot-instructions.md` (multi-agent safety guardrails) | 2026-02-26 |
| Nanobot SubagentManager | <https://github.com/HKUDS/nanobot> | MIT | Restricted tool registration per subagent, max iteration limits, result injection via message bus | `.github/agents/orchestrator.agent.md` (dispatch routing with tool inheritance) | 2026-02-26 |
| CrewAI | <https://docs.crewai.com/> | MIT | Agent role/goal/backstory pattern, hierarchical process (manager agent), `allow_delegation`, sequential process, researcher â†’ reporting_analyst pattern | `.github/agents/architect.agent.md` (hierarchical manager pattern), `.github/agents/writer.agent.md` (reporting analyst pattern) | 2026-02-26 |

## Path Sandboxing Research (Task #497)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python pathlib docs | <https://docs.python.org/3/library/pathlib.html> | PSF | `Path.resolve()` + `Path.is_relative_to()` â€” canonical path sandbox pattern | `src/owlbear/paths.py` (`sandbox_path`) | 2026-03-06 |
| OWASP Path Traversal | <https://owasp.org/www-community/attacks/Path_Traversal> | CC BY-SA 4.0 | Threat model: `../` traversal, null-byte injection, absolute path escape | `src/owlbear/paths.py` (`sandbox_path`) | 2026-03-06 |

## kanban-md (Project Management Tool)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README + built-in skills | <https://github.com/antopolskiy/kanban-md> | MIT | CLI reference (commands, flags, output formats), built-in agent skills (`kanban-md` skill, `kanban-based-development` skill), config.yml schema, claim semantics, pick algorithm, classes of service | `.github/skills/kanban-md/SKILL.md` (adapted from built-in `kanban-md` skill), `.github/skills/kanban-based-development/SKILL.md` (adapted from built-in `kanban-based-development` skill), `kanban/config.yml` | 2026-02-07 |
| kanban-md v0.32.2 "Hotkey Net" release | <https://github.com/antopolskiy/kanban-md/releases/tag/v0.32.2> | MIT | TUI keyboard shortcuts, batch operations, compact output format | `.github/skills/kanban-md/SKILL.md` (TUI shortcuts section) | 2026-02-24 |
| kanban-md v0.33.0 "True North" release | <https://github.com/antopolskiy/kanban-md/releases/tag/v0.33.0> | MIT | `pick` self-contained output (prints full task details), `--no-body` flag, automatic ID consistency repair, malformed task detection | `.github/skills/kanban-md/SKILL.md` (pick command docs), `.github/skills/kanban-based-development/SKILL.md` (removed redundant show-after-pick) | 2026-02-26 |

## Ingest Concurrency Limit Research (Task #516)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” asyncio.Semaphore | <https://docs.python.org/3/library/asyncio-sync.html#semaphore> | PSF | Semaphore API for bounding concurrent coroutine access to a resource | `docs/research/ingest-concurrency-limit-research.md` | 2026-03-06 |
| Python docs â€” asyncio.TaskGroup | <https://docs.python.org/3/library/asyncio-task.html#task-groups> | PSF | Structured concurrency alternative (rejected â€” breaks fire-and-forget) | `docs/research/ingest-concurrency-limit-research.md` | 2026-03-06 |
| Python docs â€” create_task fire-and-forget | <https://docs.python.org/3/library/asyncio-task.html#creating-tasks> | PSF | Background-tasks set pattern, strong reference requirement | `docs/research/ingest-concurrency-limit-research.md` | 2026-03-06 |
| SuperFastPython â€” Asyncio Semaphore | <https://superfastpython.com/asyncio-semaphore/> | N/A | Worked example of semaphore limiting concurrent task execution | `docs/research/ingest-concurrency-limit-research.md` | 2026-03-06 |

## Error Recovery Research (Task #471)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python Logging Cookbook â€” Multiple handlers | <https://docs.python.org/3/howto/logging-cookbook.html> | PSF | Multi-handler pattern: if one sink fails, others capture. Validated that `logger.exception()` always reaches RotatingFileHandler. | `docs/research/recover-from-error-swallowing-research.md` | 2026-03-06 |
| 12-Factor App â€” XI. Logs | <https://12factor.net/logs> | CC-BY | "Treat logs as event streams." Errors must never vanish; local file logging is the backstop. | `docs/research/recover-from-error-swallowing-research.md` | 2026-03-06 |

## httpx Timeout Convention (Task #460)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx Timeouts docs | <https://www.python-httpx.org/advanced/timeouts/> | BSD-3 | `httpx.Timeout` API â€” per-phase timeout configuration (connect, read, write, pool) | `docs/research/httpx-timeout-research.md`, all `httpx.AsyncClient` call sites | 2026-03-06 |
| PydanticAI `cached_async_http_client` | <https://github.com/pydantic/pydantic-ai> | MIT | `DEFAULT_HTTP_TIMEOUT=600`, `connect=5` pattern for LLM streaming clients | `src/owlbear/providers/copilot.py` (`Timeout(600, connect=5)`) | 2026-03-06 |

## Bootstrap Startup Summary Research (Task #492)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Django System Check Framework | <https://docs.djangoproject.com/en/5.1/topics/checks/> | BSD-3 | Tagged checks with severity levels (Debug-Critical), extensible `@register` decorator, errors block startup. Severity classification model. | `docs/research/bootstrap-startup-summary-research.md` | 2026-03-06 |
| Celery Worker Banner | <https://github.com/celery/celery/blob/main/celery/apps/worker.py> | BSD-3 | `emit_banner()` prints `[config]`/`[queues]`/`[tasks]` sections at startup. Single structured dump of system state. Banner format inspiration. | `docs/research/bootstrap-startup-summary-research.md` | 2026-03-06 |
| Spring Boot Auto-configuration report | <https://docs.spring.io/spring-boot/reference/using/auto-configuration.html> | Apache-2.0 | `--debug` flag prints condition evaluation (positive/negative matches). Positive/negative match concept. | `docs/research/bootstrap-startup-summary-research.md` | 2026-03-06 |
| FastAPI Lifespan Events | <https://fastapi.tiangolo.com/advanced/events/> | MIT | `@asynccontextmanager` pattern for startup/shutdown lifecycle events. | `docs/research/bootstrap-startup-summary-research.md` | 2026-03-06 |

## Command Guard Blocklist Research (Task #494)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Code â€” Security + Sandboxing + Permissions docs | <https://code.claude.com/docs/en/security>, <https://code.claude.com/docs/en/sandboxing>, <https://code.claude.com/docs/en/permissions> | N/A (docs) | Permission-based architecture, OS-level sandbox (Seatbelt/bubblewrap) as primary control, command blocklist (`curl`/`wget`) as defense-in-depth, explicit "Bash permission patterns are fragile" warning | `docs/research/command-guard-blocklist-research.md` | 2026-03-06 |
| OpenAI Codex CLI â€” README (Security model) | <https://github.com/openai/codex/blob/main/codex-cli/README.md> | Apache-2.0 | 3-tier approval mode (Suggest/Auto Edit/Full Auto), OS sandbox (`sandbox-exec`/Docker), no command blocklist â€” relies on sandbox + approval | `docs/research/command-guard-blocklist-research.md` | 2026-03-06 |
| Docker seccomp profiles | <https://docs.docker.com/engine/security/seccomp/> | Apache-2.0 (docs) | Allowlist approach for syscalls (deny ~44 of 300+), defense-in-depth layering with capabilities | `docs/research/command-guard-blocklist-research.md` | 2026-03-06 |

## Toolset Alias Auto-Registration Research (Task #488)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PEP 487 â€” `__init_subclass__` | <https://peps.python.org/pep-0487/> | PSF | Subclass registration pattern via `__init_subclass__`; evaluated as Option B (rejected â€” requires mixin since PydanticAI `FunctionToolset` is external) | `docs/research/toolset-alias-auto-registration-research.md` | 2026-03-06 |
| Python Data Model â€” `__init_subclass__` | <https://docs.python.org/3/reference/datamodel.html#object.__init_subclass__> | PSF | Official reference for the `__init_subclass__` hook; used to verify Option B feasibility | `docs/research/toolset-alias-auto-registration-research.md` | 2026-03-06 |

## ClawFeed Research (Task #591)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kevinho/clawfeed | <https://github.com/kevinho/clawfeed> | MIT | Feed curation architecture, typed source registry with per-type config, externalized curation rules as markdown templates, raw_items dedup pipeline, fixed-length digest generation, SKILL.md convention, bookmark deep-dive pattern | `docs/research/clawfeed-research.md` | 2026-03-06 |

## Visual Explainer Research (Task #592)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nicobailon/visual-explainer | <https://github.com/nicobailon/visual-explainer> | MIT | Self-contained HTML diagram generation skill: SKILL.md workflow (think/structure/style/deliver), Mermaid routing table (content type â†’ rendering approach), aesthetic constraint system (forbidden colors/fonts, curated palettes), HTML templates (architecture, data-table, mermaid-flowchart, slide-deck), CSS patterns (theme vars, depth tiers, zoom controls), diff-review/project-recap command prompts | `docs/research/visual-explainer-research.md` | 2026-03-06 |
| Anthropic skills repo | <https://github.com/anthropics/skills> | Apache-2.0 | Agent Skills specification, plugin marketplace pattern, skill packaging conventions (SKILL.md + commands + references + templates) | `docs/research/visual-explainer-research.md` (prior art) | 2026-03-06 |
| Dammyjay93/interface-design | <https://github.com/Dammyjay93/interface-design> | MIT | Design system memory pattern (system.md persistence across sessions), design token management, audit/extract commands, direction presets | `docs/research/visual-explainer-research.md` (prior art comparison) | 2026-03-06 |

## Approval Scope Limits Research (Task #498)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OAuth 2.0 RFC 6749 S3.3 | <https://www.rfc-editor.org/rfc/rfc6749#section-3.3> | N/A (RFC) | Scope parameter for narrowing access tokens, `expires_in` for time-limited grants, refresh token rotation pattern | `docs/research/approval-scope-limits-research.md` | 2026-03-07 |
| GitHub OAuth Scopes | <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps> | N/A (docs) | Hierarchical scope model (parent absorbs child), fine-grained permission narrowing, normalized scopes | `docs/research/approval-scope-limits-research.md` | 2026-03-07 |
| AWS IAM Condition Keys | <https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html> | N/A (docs) | `StringEquals`/`StringLike` for arg-pattern conditions, `aws:TokenIssueTime` + date conditions for time-based expiry, request-context condition evaluation | `docs/research/approval-scope-limits-research.md` | 2026-03-07 |

## Bootstrap Split Research (Task #480)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” Regular packages | <https://docs.python.org/3/reference/import.html#regular-packages> | PSF | Module-to-package migration semantics, `__init__.py` re-export mechanism | `docs/research/bootstrap-split-research.md` | 2026-03-06 |
| Flask `__init__.py` | <https://github.com/pallets/flask/blob/main/src/flask/__init__.py> | BSD-3 | Re-export pattern: 39-line `__init__.py` re-exporting from submodules for backwards compatibility | `docs/research/bootstrap-split-research.md` | 2026-03-06 |
| Pydantic `__init__.py` | <https://github.com/pydantic/pydantic/blob/main/pydantic/__init__.py> | MIT | Lazy `__getattr__` re-export for large packages, `__all__` + `_dynamic_imports` pattern | `docs/research/bootstrap-split-research.md` | 2026-03-06 |
| PydanticAI toolsets/ package | <https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/toolsets> | MIT | Package split structure: abstract.py, function.py, combined.py, wrapper.py â€” one concern per file | `docs/research/bootstrap-split-research.md` | 2026-03-06 |

## Excalidraw Diagram Skill Research (Task #593)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | MIT | Prompt-driven Excalidraw JSON generation, render-view-fix loop via Playwright, modular reference files (color palette, element templates, JSON schema), section-by-section large diagram strategy | `docs/research/excalidraw-diagram-skill-research.md` | 2026-03-06 |
| yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | MIT | 26-tool MCP server architecture, element-level CRUD, describe_scene + get_canvas_screenshot closed feedback loop, read_diagram_guide design prompt pattern | `docs/research/excalidraw-diagram-skill-research.md` | 2026-03-06 |
| lesleslie/excalidraw-mcp | <https://github.com/lesleslie/excalidraw-mcp> | BSD-3 | Python FastMCP hybrid architecture, element_factory pattern, process_manager for canvas server lifecycle | `docs/research/excalidraw-diagram-skill-research.md` | 2026-03-06 |
| Excalidraw export utilities | <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export> | MIT | Official `exportToSvg`, `exportToCanvas`, `exportToBlob` APIs for programmatic rendering | `docs/research/excalidraw-diagram-skill-research.md` | 2026-03-06 |

## ExcalidrawRenderService Research (Task #629)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Kroki Excalidraw support | <https://kroki.io/#support> | MIT | Kroki already renders Excalidraw JSON to SVG via companion container; SVG-only output; font rendering issues (#1742) | `docs/research/excalidraw-render-service-research.md` | 2026-03-07 |
| yuzutech/kroki-excalidraw | <https://docs.kroki.io/kroki/setup/install/> | MIT | Companion container architecture, self-hosted font fix (#1998), companion required for Excalidraw diagram type | `docs/research/excalidraw-render-service-research.md` | 2026-03-07 |
| @excalidraw/utils (npm) | <https://www.npmjs.com/package/@excalidraw/utils> | MIT | Standalone export utilities (exportToSvg, exportToBlob) without React dependency, UMD bundle | `docs/research/excalidraw-render-service-research.md` | 2026-03-07 |

## CDP Context Isolation Research (Task #495)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Playwright `Browser.new_context()` API | <https://playwright.dev/python/docs/api/class-browser#browser-new-context> | Apache-2.0 | Context isolation guarantees ("won't share cookies/cache"), `Browser.close()` cleanup semantics for created contexts | `docs/research/cdp-context-isolation-research.md` | 2026-03-06 |
| Chrome DevTools Protocol â€” `Target.createBrowserContext` | <https://chromedevtools.github.io/devtools-protocol/tot/Target/#method-createBrowserContext> | BSD-3 | CDP-level mechanism for incognito-like context creation, `disposeOnDetach` option, `disposeBrowserContext` cleanup | `docs/research/cdp-context-isolation-research.md` | 2026-03-06 |
| Playwright `connect_over_cdp` API | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | Apache-2.0 | CDP connection fidelity considerations, default context access via `browser.contexts[0]` pattern | `docs/research/cdp-context-isolation-research.md` | 2026-03-06 |

## Copilot OAuth Research (Task #30)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Graphicator | `C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator` | (own project) | Device-flow OAuth (auth/copilot.py), agent factory routing (agents/__init__.py), provider config, editor headers, test patterns | `src/owlbear/auth/copilot.py`, `src/owlbear/providers/copilot.py` | 2026-02-26 |
| GitHub OAuth docs | <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow> | N/A | RFC 8628 device-flow spec, error codes (authorization_pending, slow_down, expired_token, access_denied), rate limits | `src/owlbear/auth/copilot.py` | 2026-02-26 |

## PydanticAI Integration Research (Tasks #37â€“#45)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI | <https://github.com/pydantic/pydantic-ai> | MIT | Agent class, messages.py, tools.py, providers/openai.py, FunctionToolset, TypeAdapter serialization | `src/owlbear/core/agent.py`, `src/owlbear/memory/session.py`, validation tests | 2026-02-26 |
| pydantic-deepagents | <https://github.com/vstorm-co/pydantic-deepagents> | MIT | HookEvent/HookRegistry pattern (middleware/hooks.py), SkillsToolset pattern, MEMORY.md persistence, agent factory anti-pattern | `src/owlbear/core/hooks.py` (adapted HookEvent/HookRegistry pattern) | 2026-02-26 |

## Teams Integration Research (Task #47)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| M365 Agents SDK (Python) | <https://github.com/microsoft/Agents-for-python> | MIT | Teams bot architecture, Activity model, migration from Bot Framework SDK | `docs/research/teams-integration-research.md` (comparison) | 2026-02-27 |
| M365 Agents SDK Migration Guide | <https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/bf-migration-python> | N/A | Package mapping, initialization patterns, Teams bot examples | `docs/research/teams-integration-research.md` (comparison) | 2026-02-27 |
| Microsoft Graph API â€” Teams notifications | <https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview> | N/A | Subscription model, webhook requirements, 60-min expiry | `docs/research/teams-integration-research.md` (real-time options analysis) | 2026-02-27 |
| Composio Microsoft Teams toolkit | <https://composio.dev/toolkits/microsoft_teams> | N/A | 180 Teams tools inventory, MCP gateway model, OAuth2 managed auth | `docs/research/teams-integration-research.md` (comparison) | 2026-02-27 |

## Slack Integration Research (Task #83)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | N/A | Socket Mode protocol: WebSocket connection, envelope acknowledgment, no public endpoint | `docs/research/slack-integration-research.md` (architecture analysis) | 2026-02-27 |
| Bolt for Python (slack_bolt) | <https://github.com/slackapi/bolt-python> | MIT | AsyncApp, SocketModeHandler, decorator patterns, AI Assistant class | `docs/research/slack-integration-research.md` (comparison) | 2026-02-27 |
| Python Slack SDK (slack_sdk) | <https://github.com/slackapi/python-slack-sdk> | MIT | SocketModeClient (aiohttp), AsyncWebClient, listener pattern | `docs/research/slack-integration-research.md` (recommendation), future `src/owlbear/channels/slack.py` | 2026-02-27 |
| slack_sdk Socket Mode docs | <https://docs.slack.dev/tools/python-slack-sdk/socket-mode> | N/A | Async SocketModeClient usage, aiohttp/websockets backends, event processing | `docs/research/slack-integration-research.md` (implementation approach) | 2026-02-27 |
| Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | MIT | Official AI assistant bot using Socket Mode, thread management, OpenAI integration | `docs/research/slack-integration-research.md` (prior art) | 2026-02-27 |

## Voice I/O Research (Task #49)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| faster-whisper | <https://github.com/SYSTRAN/faster-whisper> | MIT | CTranslate2-based Whisper reimplementation: 4x faster, int8 quantization, built-in Silero VAD, model size benchmarks (small CPU: 1m42s int8 vs 6m58s openai/whisper), no FFmpeg dependency | `docs/research/voice-io-research.md` (STT recommendation), future `src/owlbear/voice/stt.py` | 2026-02-27 |
| openai/whisper | <https://github.com/openai/whisper> | MIT | Reference Whisper implementation: model size table (tiny 39M â†’ large 1550M), accuracy baselines, .en model variants for English-only use | `docs/research/voice-io-research.md` (model size comparison) | 2026-02-27 |
| pyttsx3 | <https://pypi.org/project/pyttsx3/> | MPL-2.0 | Offline TTS library: SAPI5 on Windows, eSpeak on Linux, AVSpeech on macOS, sync API (engine.say/runAndWait), voice and rate configuration | `docs/research/voice-io-research.md` (TTS recommendation), future `src/owlbear/voice/tts.py` | 2026-02-27 |
| Silero VAD | <https://github.com/snakers4/silero-vad> | MIT | Voice Activity Detection: <1ms per chunk on CPU, integrated into faster-whisper's vad_filter parameter, 6000+ language support | `docs/research/voice-io-research.md` (VAD strategy) | 2026-02-27 |
| SpeechRecognition | <https://pypi.org/project/SpeechRecognition/> | BSD-3 | Unified STT API wrapping Whisper, faster-whisper, Google, Vosk; PyAudio microphone abstraction; evaluated but not recommended (unnecessary abstraction layer) | `docs/research/voice-io-research.md` (comparison) | 2026-02-27 |
| PyAudio | <https://pypi.org/project/PyAudio/> | MIT | PortAudio Python bindings for cross-platform mic capture; prebuilt Windows wheels; supports WASAPI, DirectSound, WDM-KS | `docs/research/voice-io-research.md` (audio input recommendation), future `src/owlbear/voice/recorder.py` | 2026-02-27 |
| edge-tts | <https://github.com/rany2/edge-tts> | GPL-3.0 | Microsoft Edge online TTS: high-quality neural voices, async Python API; evaluated but not recommended for MVP (requires internet, violates offline-first principle) | `docs/research/voice-io-research.md` (TTS comparison) | 2026-02-27 |

## Retry Decorators Research (Task #470)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | Apache-2.0 | `@retry` decorator API, `wait_exponential_jitter`, `retry_if_exception`, `before_sleep_log`, async support | `docs/research/retry-decorators-research.md` (retry policy design) | 2026-03-06 |
| Slack SDK RetryHandler docs | <https://docs.slack.dev/tools/python-slack-sdk/web/#retryhandler> | N/A | Built-in `ConnectionErrorRetryHandler` + `RateLimitErrorRetryHandler`, backoff+jitter | `docs/research/retry-decorators-research.md` (Slack retry strategy) | 2026-03-06 |
| AWS Exponential Backoff and Jitter | <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/> | N/A | Full Jitter algorithm for distributed retry, thundering herd prevention | `docs/research/retry-decorators-research.md` (wait strategy rationale) | 2026-03-06 |

## Multi-Agent Orchestration Research (Task #587)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| conductor-orchestrator-superpowers | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Evaluate-Loop (Planâ†’EvalPlanâ†’Executeâ†’EvalExecâ†’Fix), DAG parallel execution, file-based message bus, Board of Directors deliberation, agent-factory worker templates, retrospective agent pattern, anti-rationalization tables, plan-critiquer red-team framework, verification-before-completion iron law | `docs/research/conductor-orchestrator-superpowers-research.md` (analysis); future: retrospective hook, agent prompt enhancements | 2026-03-06 |
| obra/superpowers | <https://github.com/obra/superpowers> | MIT | Base skill framework conductor extends (72.6k stars); subagent-driven-development, dispatching-parallel-agents, verification-before-completion patterns | `docs/research/conductor-orchestrator-superpowers-research.md` (prior art validation) | 2026-03-06 |

## CDP Tab Groups Research (Task #65)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| CDP Target Domain (tip-of-tree) | <https://chromedevtools.github.io/devtools-protocol/tot/Target/> | N/A | Full Target domain spec: `createTarget` parameters, `TargetInfo` properties â€” confirmed no tab group support in CDP | `docs/research/cdp-tab-groups-research.md` (analysis) | 2026-02-27 |
| Chrome Extensions `tabGroups` API | <https://developer.chrome.com/docs/extensions/reference/api/tabGroups> | N/A | Tab group management API: `get`, `move`, `query`, `update` â€” only official way to manage tab groups | `docs/research/cdp-tab-groups-research.md` (analysis) | 2026-02-27 |
| Chrome Extensions `tabs.group()` | <https://developer.chrome.com/docs/extensions/reference/api/tabs#method-group> | N/A | `chrome.tabs.group()` â€” assigns tabs to groups, creates groups | `docs/research/cdp-tab-groups-research.md` (analysis) | 2026-02-27 |
| Puppeteer issue #13215 | <https://github.com/puppeteer/puppeteer/issues/13215> | N/A | Feature request for tab groups closed as "not planned" â€” confirms CDP limitation | `docs/research/cdp-tab-groups-research.md` (prior art) | 2026-02-27 |
| Playwright Chrome Extensions docs | <https://playwright.dev/python/docs/chrome-extensions> | N/A | Extension loading via `--load-extension`, persistent context requirement, Edge sideloading removal | `docs/research/cdp-tab-groups-research.md` (feasibility) | 2026-02-27 |

## Token Usage Tracking Research (Task #82)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI `pydantic_ai.usage` | <https://ai.pydantic.dev/api/usage/> | MIT | `RunUsage`/`RequestUsage` dataclasses, `RequestUsage.extract()` genai-prices integration, token fields (input, output, cache_write, cache_read), `total_tokens` property | `docs/research/token-usage-tracking-research.md` (analysis), future `src/owlbear/observability/usage.py` | 2026-02-27 |
| genai-prices (Pydantic) | <https://github.com/pydantic/genai-prices> | MIT | `calc_price()` API for LLM cost estimation, `Usage` dataclass, `UpdatePrices` background updater, provider/model coverage (900+ models, 30+ providers) | `docs/research/token-usage-tracking-research.md` (recommendation), future `src/owlbear/observability/cost.py` | 2026-02-27 |
| LiteLLM | <https://github.com/BerriAI/litellm> | MIT | `model_prices_and_context_window.json` comprehensive pricing DB, cost tracking patterns in proxy server | `docs/research/token-usage-tracking-research.md` (comparison, not adopted â€” too heavy) | 2026-02-27 |

## Knowledge Graph Research (Task #50)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| tool.graphicator | (own project) | â€” | SQLite + sqlite-vec knowledge graph: schema.py (DDL, freeze triggers), graph.py (CRUD), vectors.py (rowid_map bridge, similarity search), models.py (Pydantic records) | `src/owlbear/memory/knowledge/` (schema, graph, vectors, models adapted from db/ package) | 2026-02-27 |
| sqlite-vec | <https://github.com/asg017/sqlite-vec> | Apache-2.0/MIT | Vector search SQLite extension: vec0 virtual table, float/int8/binary vectors, metadata filtering, KNN queries | `src/owlbear/memory/knowledge/schema.py`, `src/owlbear/memory/knowledge/vectors.py` | 2026-02-27 |
| FastEmbed (Qdrant) | <https://github.com/qdrant/fastembed> | Apache-2.0 | Local ONNX-based embedding generation: TextEmbedding API, BAAI/bge-small-en-v1.5 default model (384-dim), no GPU needed | `src/owlbear/memory/knowledge/embeddings.py` | 2026-02-27 |
| nano-graphrag | <https://github.com/gusye1234/nano-graphrag> | MIT | Minimal GraphRAG (~1100 LOC): networkx graph + nano-vectordb, pluggable backends | `docs/research/knowledge-graph-research.md` (architecture comparison) | 2026-02-27 |
| LightRAG (HKUDS) | <https://github.com/HKUDS/LightRAG> | MIT | Full-featured GraphRAG: 4-storage-type architecture, networkx default graph, entity-relationship extraction | `docs/research/knowledge-graph-research.md` (architecture comparison) | 2026-02-27 |

## Terminal Tool Research (Task #121)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio subprocess docs | <https://docs.python.org/3/library/asyncio-subprocess.html> | PSF | `create_subprocess_shell` API, `communicate()` + `wait_for()` timeout pattern, process cleanup on timeout | `docs/research/terminal-tool-research.md` (implementation approach), future `src/owlbear/tools/terminal.py` | 2026-02-27 |
| OpenHands ActionExecutor | <https://github.com/All-Hands-AI/OpenHands> | MIT | `CmdRunAction` â†’ `CmdOutputObservation` pattern: structured command results with exit codes, BashSession management | `docs/research/terminal-tool-research.md` (prior art comparison) | 2026-02-27 |
| Aider run_cmd | <https://github.com/Aider-AI/aider> | Apache-2.0 | Shell command execution with `subprocess.run`, token-aware output handling, git/test/lint command patterns | `docs/research/terminal-tool-research.md` (prior art comparison) | 2026-02-27 |

## Embedding & Vector DB Research (Tasks #232â€“#239)

### Papers & Academic Sources

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Cormack et al. (2009) â€” RRF paper | <https://dl.acm.org/doi/10.1145/1571941.1572114> | N/A | Original Reciprocal Rank Fusion algorithm: `1/(k+rank)`, k=60, outperforms Condorcet and individual rank learning on TREC | `docs/research/dual-embedding-rrf-research.md` (RRF formula and analysis) | 2026-02-28 |
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | N/A | Single model producing dense (1024-d) + sparse + ColBERT; self-knowledge distillation; MIRACL/MLDR/NarrativeQA benchmarks; ColBERT reranking quality tables | `docs/research/dual-embedding-rrf-research.md`, `docs/research/graph-augmented-retrieval-research.md`, `docs/research/bge-m3-integration-research.md`, `docs/research/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| Wang et al. 2024 "Best Practices in RAG" | <https://arxiv.org/abs/2407.01219> | N/A | RAG pipeline analysis with retrieval + reranking strategy recommendations | `docs/research/retrieve-rerank-research.md` (prior art) | 2026-02-28 |

### Embedding Model Cards (HuggingFace)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BAAI/bge-m3 | <https://huggingface.co/BAAI/bge-m3> | MIT | Multi-functionality (dense+sparse+ColBERT), 8192 tokens, FP16/FP32 CPU behavior, ONNX file tree (dense-only ONNX, .pt linear heads) | `docs/research/dual-embedding-rrf-research.md`, `docs/research/retrieve-rerank-research.md`, `docs/research/graph-augmented-retrieval-research.md`, `docs/research/bge-m3-integration-research.md` | 2026-02-28 |
| BAAI/bge-large-en-v1.5 | <https://huggingface.co/BAAI/bge-large-en-v1.5> | MIT | MTEB scores (64.23 avg, 54.29 retrieval), 335M params, 1024d, ONNX available | `docs/research/retrieve-rerank-research.md` (comparison) | 2026-02-28 |
| BAAI/bge-reranker-v2-m3 | <https://huggingface.co/BAAI/bge-reranker-v2-m3> | Apache-2.0 | Cross-encoder specs (568M params), BEIR NDCG@10 (54.17), MIRACL reranking eval | `docs/research/retrieve-rerank-research.md`, `docs/research/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| snowflake-arctic-embed-l | <https://huggingface.co/Snowflake/snowflake-arctic-embed-l> | Apache-2.0 | Best BEIR retrieval score (55.98) among FastEmbed models, 335M params, 1024d, purpose-built for retrieval | `docs/embedding-model-shootout.md` (recommendation) | 2026-02-28 |
| mxbai-embed-large-v1 | <https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1> | Apache-2.0 | Best overall MTEB average (64.68), Matryoshka + binary quantization support, 335M, 1024d | `docs/embedding-model-shootout.md` (runner-up) | 2026-02-28 |
| nomic-embed-text-v1.5 | <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5> | Apache-2.0 | Matryoshka dims (64â€“768), 8192 context, 137M params, MTEB avg 62.28 | `docs/research/dual-embedding-rrf-research.md`, `docs/research/retrieve-rerank-research.md`, `docs/embedding-model-shootout.md` | 2026-02-28 |
| gte-large-en-v1.5 | <https://huggingface.co/Alibaba-NLP/gte-large-en-v1.5> | MIT | 8192 tokens, 409M params, 1024d, best retrieval (57.91) of any feasible model, custom architecture | `docs/embedding-model-shootout.md` (deferred) | 2026-02-28 |
| jina-embeddings-v3 | <https://huggingface.co/jinaai/jina-embeddings-v3> | CC-BY-NC-4.0 | 0.6B params, CC-BY-NC-4.0 license confirmed (non-commercial only), not in FastEmbed | `docs/research/retrieve-rerank-research.md`, `docs/embedding-model-shootout.md` | 2026-02-28 |
| e5-mistral-7b-instruct | <https://huggingface.co/intfloat/e5-mistral-7b-instruct> | MIT | 7B params, 4096d, infeasible on 16 GB RAM (FP16 â‰ˆ 14 GB), no ONNX | `docs/embedding-model-shootout.md` (disqualified) | 2026-02-28 |
| MTEB Leaderboard | <https://huggingface.co/spaces/mteb/leaderboard> | N/A | Third-party benchmark scores for embedding models (MTEB avg, BEIR retrieval nDCG@10) | `docs/embedding-model-shootout.md` (benchmarks) | 2026-02-28 |

### Reranker Model Cards

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| jina-reranker-v2-base-multilingual | <https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual> | CC-BY-NC-4.0 | 278M params, BEIR/MIRACL benchmarks (54.83 NDCG@10), CC-BY-NC-4.0 license restriction | `docs/research/retrieve-rerank-research.md` (comparison) | 2026-02-28 |
| cross-encoder/ms-marco-MiniLM-L-12-v2 | <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2> | Apache-2.0 | 33M param lightweight reranker, MS Marco TREC DL'19 (74.31), MRR@10 (39.02) | `docs/research/retrieve-rerank-research.md` (comparison) | 2026-02-28 |

### Vector Database & Retrieval Tools

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| qdrant-client (v1.17.0) | <https://github.com/qdrant/qdrant-client> | Apache-2.0 | Local mode (QdrantLocal), brute-force numpy, persistence (SQLite+pickle), portalocker locking, 20K threshold, congruence tests | `docs/research/qdrant-local-research.md`, `docs/research/qdrant-local-features-research.md` | 2026-02-28 |
| Qdrant vectors docs | <https://qdrant.tech/documentation/concepts/vectors> | N/A | Named vectors, sparse vectors, multivectors (ColBERT MAX_SIM) | `docs/research/qdrant-local-research.md` | 2026-02-28 |
| Qdrant hybrid queries docs | <https://qdrant.tech/documentation/concepts/hybrid-queries> | N/A | Prefetch, RRF/DBSF fusion, multi-stage queries | `docs/research/qdrant-local-research.md` | 2026-02-28 |
| Qdrant "Hybrid Search Revamped" article | <https://qdrant.tech/articles/hybrid-search> | N/A | ColBERT HNSW optimization (m=0), prefetchâ†’ColBERT rescore pattern, fusion vs reranking comparison | `docs/research/qdrant-local-research.md`, `docs/research/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| Qdrant late-interaction article | <https://qdrant.tech/articles/late-interaction-models/> | N/A | BEIR late-interaction benchmarks, ColBERT quantization impact, output-token reranking | `docs/research/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| Azure AI Search â€” RRF docs | <https://learn.microsoft.com/azure/search/hybrid-search-ranking> | N/A | Production RRF implementation: parallel query execution, k=60, weighted fusion, score decomposition | `docs/research/dual-embedding-rrf-research.md` (prior art) | 2026-02-28 |
| Milvus multi-vector hybrid search | <https://milvus.io/docs/multi-vector-search.md> | N/A | Dense + sparse + RRF in production: `AnnSearchRequest`, `RRFRanker`, BGE-M3 example | `docs/research/dual-embedding-rrf-research.md` (prior art) | 2026-02-28 |
| FastEmbed supported models | <https://qdrant.github.io/fastembed/examples/Supported_Models/> | Apache-2.0 | Full ONNX model inventory (dense, sparse SPLADE++, late-interaction ColBERT, rerankers) with sizes; bge-m3 absent from all lists | `docs/embedding-model-shootout.md`, `docs/research/dual-embedding-rrf-research.md`, `docs/research/retrieve-rerank-research.md`, `docs/research/graph-augmented-retrieval-research.md`, `docs/research/bge-m3-integration-research.md` | 2026-02-28 |

### Integration Samples & GitHub Repos

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| bge-m3-qdrant-sample | <https://github.com/yuniko-software/bge-m3-qdrant-sample> | N/A | Full bge-m3 + Qdrant integration: collection creation, embedding, named vectors, hybrid search | `docs/research/qdrant-local-research.md`, `docs/research/bge-m3-integration-research.md` | 2026-02-28 |
| workshop-ultimate-hybrid-search | <https://github.com/qdrant/workshop-ultimate-hybrid-search> | N/A | Official Qdrant hybrid search evaluation workshop; `query_points` API patterns for sparse/RRF search | `docs/research/qdrant-local-research.md`, `tests/benchmarks/search.py` (`_sparse_search`, `_hybrid_rrf_search`) | 2026-02-28 |
| FlagEmbedding (v1.3.5) | <https://github.com/FlagOpen/FlagEmbedding> | MIT | M3Embedder/BGEM3FlagModel code analysis: constructor behavior (NOT lazy), encode() internals, sparse/ColBERT processing, FP16 CPU auto-disable, dependency chain | `docs/research/bge-m3-integration-research.md` | 2026-02-28 |
| FastEmbed issue #107 (bge-m3 support) | <https://github.com/qdrant/fastembed/issues/107> | N/A | 2+ year open issue; maintainer confirmed sparse/ColBERT heads need ONNX export | `docs/research/bge-m3-integration-research.md` | 2026-02-28 |
| FastEmbed PR #602 (bge-m3 dense only) | <https://github.com/qdrant/fastembed/pull/602> | N/A | Feb 2026 PR adding dense-only ONNX bge-m3 embedding, no sparse/ColBERT, no reviewer | `docs/research/bge-m3-integration-research.md` | 2026-02-28 |
| RAG-Fusion | <https://github.com/Raudaschl/rag-fusion> | N/A | Multi-query + RRF pattern: generate query variants, search each, fuse results | `docs/research/dual-embedding-rrf-research.md` (prior art) | 2026-02-28 |
| Microsoft GraphRAG | <https://microsoft.github.io/graphrag/query/local_search> | MIT | Local Search entity expansion pattern: embed query â†’ find entities â†’ fan out to neighbors, community reports â†’ prioritize â†’ fill context window | `docs/research/graph-augmented-retrieval-research.md` (prior art, architecture) | 2026-02-28 |
| neo4j-graphrag-python | <https://github.com/neo4j/neo4j-graphrag-python> | Apache-2.0 | VectorCypherRetriever pattern: vector search â†’ Cypher graph traversal â†’ collect neighbor data â†’ merge into context | `docs/research/graph-augmented-retrieval-research.md` (prior art) | 2026-02-28 |
| SBERT Retrieve & Re-Rank guide | <https://www.sbert.net/examples/applications/retrieve_rerank/> | N/A | Canonical bi-encoder + cross-encoder architecture description, quality hierarchy (cross-encoder > ColBERT > bi-encoder) | `docs/research/retrieve-rerank-research.md`, `docs/research/colbert-vs-crossencoder-research.md` | 2026-02-28 |

## Moonshine Voice Research (Task #240)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | MIT | STT engine with native streaming (ergodic encoder), OnnxRuntime C++ backend, Python/Swift/Java bindings, Tinyâ€“Medium model range (26Mâ€“245M), bundled native .dll/.so | `docs/research/moonshine-vs-whisper-research.md` (recommendation) | 2026-02-28 |
| Moonshine v2 paper | <https://arxiv.org/abs/2602.12241> | N/A | Ergodic streaming encoder architecture, sliding-window attention, benchmark methodology | `docs/research/moonshine-vs-whisper-research.md` (architecture analysis) | 2026-02-28 |
| Moonshine v1 paper | <https://arxiv.org/abs/2410.15608> | N/A | First-gen flexible-duration input (no fixed 30s Whisper window) | `docs/research/moonshine-vs-whisper-research.md` (architecture analysis) | 2026-02-28 |
| Flavors of Moonshine paper | <https://arxiv.org/abs/2509.02523> | N/A | Language-specific mono-lingual models, per-language accuracy analysis | `docs/research/moonshine-vs-whisper-research.md` (analysis) | 2026-02-28 |
| HuggingFace OpenASR Leaderboard | <https://huggingface.co/spaces/hf-audio/open_asr_leaderboard> | N/A | Independent WER scoring methodology for STT models, English benchmark standard | `docs/research/moonshine-vs-whisper-research.md` (benchmark verification) | 2026-02-28 |
| whisper.cpp (ggml-org) | <https://github.com/ggml-org/whisper.cpp> | MIT | C/C++ Whisper implementation, quantization (Q5_0), AVX2 optimization, Vulkan GPU support, stream example | `docs/research/moonshine-vs-whisper-research.md` (comparison) | 2026-02-28 |

## Knowledge Pipeline Framework Research (Task #262)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex | <https://github.com/run-llama/llama_index> | MIT | Full RAG framework; PropertyGraphIndex; Qdrant integration; document management; embedding integrations; 300+ integration packages | `docs/research/knowledge-pipeline-research.md` (comparison matrix) | 2026-02-28 |
| Cognee | <https://github.com/topoteretes/cognee> | Apache 2.0 | Knowledge engine with KG+vector; EmbeddingEngine Protocol pattern; task pipeline architecture; provenance tracking (source_pipeline/source_task); Kuzu embedded graph DB; ontology resolution; cloned to `docs/research/cognee/` for deep analysis | `docs/research/knowledge-pipeline-research.md` (comparison matrix, provenance pattern recommendation) | 2026-02-28 |
| Microsoft GraphRAG | <https://github.com/microsoft/graphrag> | MIT | Graph enrichment pipeline; community detection (Leiden algorithm); hierarchical summaries; global search patterns; v3 modular packages | `docs/research/knowledge-pipeline-research.md` (comparison matrix, community detection recommendation) | 2026-02-28 |
| txtai | <https://github.com/neuml/txtai> | Apache 2.0 | All-in-one embeddings DB; graph module (NetworkX); topic modeling via community detection; config-driven graph building; embedding-similarity edges | `docs/research/knowledge-pipeline-research.md` (comparison matrix, config-driven graph pattern) | 2026-02-28 |
| Haystack (deepset) | <https://github.com/deepset-ai/haystack> | Apache 2.0 | Pipeline orchestrator; Component protocol design; `qdrant-haystack` integration; typed input/output pipeline validation; DocumentStore abstraction | `docs/research/knowledge-pipeline-research.md` (comparison matrix, component protocol validation) | 2026-02-28 |
| R2R (SciPhi) | <https://github.com/SciPhi-AI/R2R> | MIT | Server-based RAG system; REST API architecture; knowledge graph features; eliminated due to server-only architecture | `docs/research/knowledge-pipeline-research.md` (elimination analysis) | 2026-02-28 |
| Unstructured.io | <https://github.com/Unstructured-IO/unstructured> | Apache 2.0 | Document processing library; 130+ format support; eliminated â€” intake layer only | `docs/research/knowledge-pipeline-research.md` (elimination analysis) | 2026-02-28 |

## Web Search Tool Research (Task #292)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ddgs (deedy5) | <https://github.com/deedy5/ddgs> | MIT | DuckDuckGo metasearch library: `DDGS().text()` API returning `{title, href, body}` dicts, multi-engine fallback, `RatelimitException`, sync-only API wrapped with `asyncio.to_thread()` | `src/owlbear/tools/web_search.py` (`_web_search` tool) | 2026-03-01 |
| LangChain DuckDuckGoSearchRun | <https://python.langchain.com/docs/integrations/tools/ddg> | MIT | Thin wrapper over `duckduckgo-search`; snippet-concatenation formatting pattern (adapted to numbered markdown list) | `src/owlbear/tools/web_search.py` (result formatting inspiration) | 2026-03-01 |
| trafilatura | <https://github.com/adbar/trafilatura> | Apache-2.0 | Web content extraction: `extract()` with `output_format="markdown"`, `include_links=True`; fallback-to-raw-HTML pattern | `src/owlbear/tools/web_search.py` (`_web_read` tool) | 2026-03-01 |

## Conversation Router Research (Task #296)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen SelectorGroupChat | <https://github.com/microsoft/autogen> | MIT | LLM-based speaker selection with prompt template (`{roles}`, `{participants}`, `{history}`), `selector_func` override, `candidate_func` filtering, retry with feedback | `docs/research/conversation-router-research.md` (prior art comparison), `src/owlbear/agents/orchestrator.md` (prompt-based routing pattern) | 2026-03-01 |
| Semantic Router (aurelio-labs) | <https://github.com/aurelio-labs/semantic-router> | MIT | Embedding-based intent routing: `Route` objects with utterances, cosine similarity classification, sub-10ms decisions; evaluated but not adopted (YAGNI â€” embedding infra overkill for 6-agent system) | `docs/research/conversation-router-research.md` (prior art comparison) | 2026-03-01 |
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | MIT | Agent delegation pattern, output functions for hand-off, `RunContext.usage` propagation; confirmed prompt-based routing as simplest approach | `docs/research/conversation-router-research.md` (recommendation basis), `src/owlbear/agents/orchestrator.md` (routing rules) | 2026-03-01 |

## Bootstrap/Assembly Research (Task #263)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Nanobot (deep read) | <https://github.com/HKUDS/nanobot> | MIT | Startup wiring sequence (gateway command), MessageBus pattern, ChannelManager config-driven init, ContextBuilder system prompt assembly, MemoryStore two-layer consolidation (MEMORY.md + HISTORY.md via LLM tool call), SessionManager JSONL + last_consolidated pointer | `docs/research/bootstrap-assembly-research.md` (analysis), `src/owlbear/bootstrap.py`, future `src/owlbear/channels/manager.py` | 2026-02-28 |

## Browser Automation Research (Task #264)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| browser-use (v0.12.0) | <https://github.com/browser-use/browser-use> | MIT | CDP `cdp_url` parameter, `channel: 'msedge'`, `enable_default_extensions`, AI browser agent architecture | `docs/research/browser-automation-research.md` (comparison) | 2026-02-28 |
| crawl4ai (v0.8.0) | <https://github.com/unclecode/crawl4ai> | Apache 2.0 | `BrowserConfig.cdp_url`, `browser_mode` enum, deep crawl strategies (BFS/DFS + crash recovery), prefetch mode | `docs/research/browser-automation-research.md` (comparison) | 2026-02-28 |
| Stagehand (v3.6.1) | <https://github.com/browserbase/stagehand> | MIT | AI browser automation framework, TypeScript-first, Browserbase cloud service dependency â€” eliminated | `docs/research/browser-automation-research.md` (comparison) | 2026-02-28 |
| readabilipy (v0.3.0) | <https://pypi.org/project/readabilipy/> | MIT | Mozilla Readability.js Python wrapper, Node.js dependency | `docs/research/browser-automation-research.md` (content extraction comparison) | 2026-02-28 |

## Moonshine Streaming Research (Task #246)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | MIT | Transcriber/Stream/MicTranscriber Python API, event model (LineStarted/LineTextChanged/LineCompleted), VAD integration, ModelArch enum, audio format requirements, session lifecycle | `docs/research/moonshine-streaming-research.md`, future `src/owlbear/voice/stt.py`, future `src/owlbear/voice/streaming_stt.py` | 2026-02-28 |

## Content Hashing Research (Task #253)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain indexing API | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/indexing/api.py> | MIT | Content+metadata dual hashing (SHA-1/SHA-256), RecordManager pattern, cleanup modes (incremental/full/scoped_full), `_get_document_with_hash()`, `IndexingResult` tracking | `docs/research/content-hashing-research.md` (comparison), future `src/owlbear/memory/knowledge/ingest.py` (delta re-ingest pattern) | 2026-02-28 |
| LlamaIndex IngestionPipeline | <https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/> | MIT | `doc_id â†’ document_hash` map in docstore, duplicate detection, skip-if-unchanged pattern, IngestionCache for node+transformation hashing | `docs/research/content-hashing-research.md` (comparison) | 2026-02-28 |
| LightRAG (content hashing) | <https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py> | MIT | MD5 content-addressed document IDs, DocStatusStorage (PENDINGâ†’PROCESSINGâ†’PROCESSED/FAILED), `adelete_by_doc_id()` comprehensive deletion cascade (chunks â†’ entities â†’ relationships â†’ rebuild affected graph), duplicate detection via `full_docs.filter_keys()` | `docs/research/content-hashing-research.md` (deletion pattern, comparison) | 2026-02-28 |

## Intra-Document Graph Builder Research (Task #255)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG (Edge et al.) | <https://arxiv.org/abs/2404.16130> | N/A | Entity merge + description summarization pattern; cross-chunk consolidation | `docs/research/intra-document-graph-research.md`, future `src/owlbear/memory/knowledge/graph_builder.py` | 2026-02-28 |
| MS GraphRAG Dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow> | MIT | 6-phase indexing pipeline architecture | `docs/research/intra-document-graph-research.md` | 2026-02-28 |
| LlamaIndex PropertyGraphIndex | <https://developers.llamaindex.ai/docs/llamaindex/module_guides/indexing/lpg_index_guide> | MIT | SchemaLLMPathExtractor, constrained extraction | `docs/research/intra-document-graph-research.md` | 2026-02-28 |
| nano-graphrag (intra-doc patterns) | <https://github.com/gusye1234/nano-graphrag> | MIT | Minimal extract-merge-summarize pattern (~1100 LOC) | `docs/research/intra-document-graph-research.md` | 2026-02-28 |

## Source Registry Research (Task #254)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex Data Connectors | <https://developers.llamaindex.ai/python/framework/module_guides/loading/connector/> | MIT | Reader â†’ Document pattern, LlamaHub connector registry, type-specific loaders â€” informed SourceType enum design | `docs/research/source-registry-research.md` (comparison) | 2026-03-01 |
| APScheduler v4 (pre-release) | <https://github.com/agronholm/apscheduler> | MIT | Cron/interval/calendar triggers, SQLite data store, async-native v4 â€” evaluated but not adopted (YAGNI; manual refresh recommended, scheduling deferred to phase-14) | `docs/research/source-registry-research.md` (scheduling comparison) | 2026-03-01 |

## Inter-Document Graph Builder Research (Task #256)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG (Edge et al.) | <https://arxiv.org/abs/2404.16130> | N/A | Scaling data (~8Kâ€“15K entities per 1M tokens), entity merging by name match, Leiden community detection pipeline â€” used as comparison baseline; implementation chose embedding pre-filter approach instead | `docs/research/inter-document-graph-builder-research.md` (comparison analysis, scaling reference) | 2026-02-28 |
| GraphRAG Indexing Dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow/> | MIT | 6-phase pipeline (chunk â†’ extract â†’ graph â†’ community â†’ summarize â†’ embed) â€” evaluated as approach D; not adopted (YAGNI â€” community detection not needed yet) | `docs/research/inter-document-graph-builder-research.md` (pipeline comparison) | 2026-02-28 |
| Neo4j entity resolution (Senzing) | <https://neo4j.com/developer-blog/entity-resolved-knowledge-graphs/> | N/A | Entity deduplication across datasets via record linkage; different use case from relationship inference â€” not adopted | `docs/research/inter-document-graph-builder-research.md` (comparison) | 2026-02-28 |

## Project Definition Workflow Research (Task #294)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| gpt-engineer preprompts | <https://github.com/gpt-engineer-org/gpt-engineer/tree/main/gpt_engineer/preprompts> | MIT | `clarify` â†’ `generate` two-phase pipeline; clarify asks one question at a time; philosophy sets coding constraints | `docs/research/project-definition-workflow-research.md`, `.github/skills/project-definition/SKILL.md` (workflow step design) | 2026-03-01 |
| Devika ARCHITECTURE.md | <https://github.com/stitionai/devika/blob/main/ARCHITECTURE.md> | MIT | Agent Core â†’ Planner â†’ Researcher â†’ Coder pipeline; Planner generates step-by-step plan with focus area; agents are stateless, core manages state | `docs/research/project-definition-workflow-research.md`, `.github/skills/project-definition/SKILL.md` (6-step workflow pattern) | 2026-03-01 |
| PydanticAI output docs | <https://ai.pydantic.dev/output/> | MIT | `output_type=SomeModel` for structured output; validated structured extraction pattern (`Agent[None, ProjectDefinition]`) | `docs/research/project-definition-workflow-research.md` (recommendation B: internal structured extraction) | 2026-03-01 |
| aider chat modes | <https://aider.chat/docs/usage/modes.html> | N/A | ask/code workflow â€” discuss first, execute second; architect mode pairs reasoning model with editor model | `docs/research/project-definition-workflow-research.md` (prior art comparison) | 2026-03-01 |

## Slack Rich Messaging Research (Task #297)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Block Kit â€” Blocks reference | <https://docs.slack.dev/reference/block-kit/blocks> | N/A | Block types (header, section, actions, divider, image, context), max 50 blocks/message, mrkdwn text type | `src/owlbear/channels/slack.py` (`send_blocks`), `docs/research/slack-rich-messaging-research.md` | 2026-03-01 |
| slack_sdk `AsyncWebClient` (v3.40.1) | <https://github.com/slackapi/python-slack-sdk> | MIT | `chat_postMessage(blocks=...)`, `files_upload_v2` 3-step upload, `thread_ts` threading | `src/owlbear/channels/slack.py` (`send_blocks`, `send_image`), `docs/research/slack-rich-messaging-research.md` | 2026-03-01 |
| Slack mrkdwn formatting | <https://api.slack.com/reference/surfaces/formatting> | N/A | Markdown â†’ mrkdwn conversion rules: bold, italic, strike, links, code passthrough | `src/owlbear/channels/slack_mrkdwn.py` (`markdown_to_mrkdwn`), `docs/research/slack-rich-messaging-research.md` | 2026-03-01 |

## Multi-Project Session Research (Task #300)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Devika ProjectManager | <https://github.com/stitionai/devika> | MIT | SQLite-backed `Projects` model, per-project conversation stacks, name â†’ slug pattern, CRUD store pattern | `src/owlbear/projects/models.py` (`_slugify`, `Project` model), `src/owlbear/projects/store.py` (`ProjectStore` CRUD), `docs/research/multi-project-session-research.md` | 2026-03-01 |
| Nanobot SessionManager | <https://github.com/HKUDS/nanobot> | MIT | JSONL sessions keyed by workspace, workspace-scoped context loading, consolidation pattern | `docs/research/multi-project-session-research.md` (architecture reference) | 2026-03-01 |
| Mem0 memory scoping | <https://github.com/mem0ai/mem0> | Apache-2.0 | Multi-level memory via user_id/agent_id/run_id metadata, scope-as-filter-parameter pattern | `docs/research/multi-project-session-research.md` (scoping pattern analysis) | 2026-03-01 |

## Error Recovery Research (Tasks #357â€“#358)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Retries docs | <https://ai.pydantic.dev/retries/> | MIT | `AsyncTenacityTransport`, `RetryConfig`, `wait_retry_after` for HTTP-level retry with Retry-After header support | `src/owlbear/providers/copilot.py` (`_build_retry_transport`, `create_copilot_client`) | 2026-03-01 |

## JsonlStore Base Class Research (Task #465)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain BaseStore | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/stores.py> | MIT | `Generic[K, V]` ABC pattern for typed storage with abstract methods | `docs/research/jsonl-store-base-class-research.md` (design pattern reference) | 2026-03-06 |

## SLF001 Public API Research (Task #466)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Ruff SLF001 rule | <https://docs.astral.sh/ruff/rules/private-member-access/> | MIT | Rule definition, Pythonic fix pattern (use public interface) | `docs/research/slf001-public-api-research.md` | 2026-03-06 |

## Terminal CWD Confinement Research (Task #467)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Aider `Commands.cmd_run()` | <https://github.com/Aider-AI/aider/blob/main/aider/commands.py> | Apache-2.0 | Forces `cwd=self.coder.root` for all shell commands; path confinement via `startswith()` | `docs/research/terminal-cwd-confinement-research.md` | 2026-03-06 |

## Restrict Token File Permissions Research (Task #468)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|

## Copilot Transport Retry Network Errors Research (Task #469)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx Exceptions docs | <https://www.python-httpx.org/exceptions/> | BSD-3 | Exception hierarchy: `ConnectError`/`TimeoutException` are `TransportError` subtypes, separate from `HTTPStatusError` | `docs/research/copilot-retry-network-errors-research.md` | 2026-03-06 |
| tenacity API docs | <https://tenacity.readthedocs.io/en/latest/api.html> | Apache-2.0 | `retry_if_exception_type` accepts tuple of exception types for multi-type retry | `docs/research/copilot-retry-network-errors-research.md` | 2026-03-06 |
| PydanticAI `retries.py` | <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/retries.py> | MIT | `AsyncTenacityTransport` wraps inner transport call in tenacity `@retry` â€” network exceptions caught if retry condition matches | `docs/research/copilot-retry-network-errors-research.md` | 2026-03-06 |

## Symphony Multi-Agent Orchestration Research (Task #584)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| openai/symphony | <https://github.com/openai/symphony> | Apache-2.0 | Poll-dispatch-reconcile daemon pattern, workspace isolation, continuation turns, exponential backoff retry, WORKFLOW.md config/prompt contract, orchestrator state machine, agent runner protocol, stall detection | `docs/research/symphony-research.md` | 2026-03-06 |
| Harness Engineering (OpenAI blog) | <https://openai.com/index/harness-engineering/> | N/A | Agent-first development philosophy: repo as system of record, AGENTS.md as table of contents, layered architecture enforcement, progressive disclosure, entropy/garbage-collection patterns | `docs/research/symphony-research.md` | 2026-03-06 |
| Codex ExecPlans (OpenAI cookbook) | <https://developers.openai.com/cookbook/articles/codex_exec_plans> | N/A | Self-contained living execution plan documents (PLANS.md): Progress/Decision Log/Surprises sections, milestone-based validation, self-contained novice-guiding specs | `docs/research/symphony-research.md` | 2026-03-06 |
| Ansible VaultEditor.write_data() | <https://github.com/ansible/ansible/blob/devel/lib/ansible/parsing/vault/__init__.py> | GPL-3.0 | Secure file write pattern: `os.umask(0o077)` â†’ `os.open(path, O_CREAT\|O_EXCL\|O_RDWR\|O_TRUNC, 0o600)` â†’ `os.write()`. Atomic creation with restricted permissions, no TOCTOU race. | `docs/research/restrict-token-permissions-research.md` | 2026-03-06 |
| Python `os.open()` / `os.chmod()` docs | <https://docs.python.org/3/library/os.html#os.open> | PSF | `os.open(path, flags, mode)` creates files atomically with permissions. On Windows, `os.chmod` only affects read-only flag; ACLs need `icacls` or `pywin32`. | `docs/research/restrict-token-permissions-research.md` | 2026-03-06 |

## Multi-Agent Swarm Research (Task #588)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| quoroom-ai/room | <https://github.com/quoroom-ai/room> | MIT | Queen/Worker/Quorum swarm architecture, agent-loop.ts (adaptive cycle gap, quiet hours, rate-limit recovery, stuck detection), queen-tools.ts (role-based tool partitioning: QUEEN_TOOLS vs WORKER_TOOLS, delegate_task, control-plane policy), WIP continuity (save_wip/CONTINUE FORWARD pattern), session compression, skills context-activation, self-mod safety guards, process-supervisor.ts (managed child PID tree cleanup) | `docs/research/quoroom-room-research.md` | 2026-03-06 |
| microsoft/autogen | <https://github.com/microsoft/autogen> | MIT/CC-BY-4.0 | AgentTool pattern (wrap agent as callable tool for delegation), multi-agent orchestration via tool composition, AgentChat API group chat patterns | `docs/research/quoroom-room-research.md` (comparison reference) | 2026-03-06 |
| Python `pathlib.PurePath.is_relative_to()` | <https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.is_relative_to> | PSF | String-based comparison; must call `.resolve()` first to eliminate `..` segments | `docs/research/terminal-cwd-confinement-research.md` | 2026-03-06 |
| OWASP A01:2021 Broken Access Control | <https://owasp.org/Top10/A01_2021-Broken_Access_Control/> | CC BY-SA 4.0 | Path traversal as canonical broken-access-control vulnerability | `docs/research/terminal-cwd-confinement-research.md` | 2026-03-06 |
| PEP 8 Â§Designing for Inheritance | <https://peps.python.org/pep-0008/#designing-for-inheritance> | PSF | "use properties to hide functional implementation behind simple data attribute access syntax" | `docs/research/slf001-public-api-research.md` | 2026-03-06 |
| Real Python â€” property() | <https://realpython.com/python-property/> | â€” | Property/setter patterns for replacing private attribute access | `docs/research/slf001-public-api-research.md` | 2026-03-06 |
| OWASP Error Handling Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html> | CC BY-SA 4.0 | Never expose implementation details to users; return generic messages; log details server-side | `docs/research/error-message-sanitization-research.md` | 2026-03-06 |
| OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | CC BY-SA 4.0 | Data to exclude from user-visible output: access tokens, session IDs, passwords, connection strings, file paths | `docs/research/error-message-sanitization-research.md` | 2026-03-06 |
| Django SafeExceptionReporterFilter | <https://github.com/django/django/blob/main/django/views/debug.py> | BSD-3 | HIDDEN_SETTINGS regex for API/TOKEN/KEY/SECRET/PASS; cleansed_substitute pattern; type-based cleansing | `docs/research/error-message-sanitization-research.md` | 2026-03-06 |
| Sentry Python SDK filtering | <https://docs.sentry.io/platforms/python/configuration/filtering/> | BSL-1.1 | before_send hook pattern â€” classify exception then modify/drop before external delivery | `docs/research/error-message-sanitization-research.md` | 2026-03-06 |
| jsonlines library | <https://jsonlines.readthedocs.io/en/latest/> | BSD-3 | JSONL append/read patterns, custom serializer hooks, line-oriented persistence | `docs/research/jsonl-store-base-class-research.md` (design validation) | 2026-03-06 |
| Pydantic TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | MIT | `TypeAdapter.dump_json`/`validate_json` for arbitrary types, create-once-reuse pattern | `docs/research/jsonl-store-base-class-research.md` (serialization approach) | 2026-03-06 |
| tenacity docs | <https://tenacity.readthedocs.io/> | Apache-2.0 | `retry_if_exception_type`, `stop_after_attempt`, `wait_exponential` composable retry primitives | `src/owlbear/providers/copilot.py` (`_build_retry_transport`), `src/owlbear/core/errors.py` (classification categories aligned to retry policies) | 2026-03-01 |
| PydanticAI ModelRetry docs | <https://ai.pydantic.dev/agents/#reflection-and-self-correction> | MIT | `ModelRetry` exception pattern â€” tool tells LLM "try again" with hint; informed TOOL_SEMANTIC error category design | `src/owlbear/core/errors.py` (`ErrorCategory.TOOL_SEMANTIC`) | 2026-03-01 |

## Knowledge Toolset Research (Task #291)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI RAG example | <https://ai.pydantic.dev/examples/rag/> | MIT | Official RAG pattern: `@agent.tool` â†’ embed query â†’ vector search â†’ format results; adapted for KnowledgeToolset query_knowledge flow | `src/owlbear/tools/knowledge.py` (`_query_knowledge` tool), `docs/research/knowledge-toolset-research.md` | 2026-03-01 |
| PydanticAI FunctionToolset docs | <https://ai.pydantic.dev/toolsets/> | MIT | `FunctionToolset` subclass API, `add_function()` registration, toolset composition pattern | `src/owlbear/tools/knowledge.py` (`KnowledgeToolset` class), `docs/research/knowledge-toolset-research.md` | 2026-03-01 |

## Hybrid Search Benchmark Harness (Tasks #377, #379)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BEIR (beir-cellar) | <https://github.com/beir-cellar/beir> | Apache-2.0 | Standard IR benchmark library: `GenericDataLoader` for dataset download + loading, NFCorpus qrels (multi-level relevance 0/1/2), corpus/queries/qrels 3-tuple format | `tests/benchmarks/corpus.py` (`load_nfcorpus`), `tests/benchmarks/conftest.py` (session fixtures) | 2026-03-02 |
| ranx (Bassani) | <https://github.com/AmenRa/ranx> | MIT | IR evaluation library: `Qrels.from_dict()` for ground-truth construction, `Run.from_dict()` for result sets, `evaluate()` for nDCG@10 scoring, `compare()` for multi-run comparison with paired t-test statistical significance | `tests/benchmarks/harness.py` (`build_qrels`, `build_run`), `tests/benchmarks/search.py` (run construction), `tests/benchmarks/evaluate.py` (`evaluate_runs`, `format_results`, `write_results_doc`) | 2026-03-02 |
| workshop-ultimate-hybrid-search | <https://github.com/qdrant/workshop-ultimate-hybrid-search> | N/A | Qdrant `query_points` API patterns: sparse-only `SparseVector` query, dense+sparse `Prefetch` with `FusionQuery(Fusion.RRF)` fusion | `tests/benchmarks/search.py` (`_sparse_search`, `_hybrid_rrf_search`) | 2026-03-02 |

## Programmatic Agent Registration Research (Task #559)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI Agents docs | <https://ai.pydantic.dev/agents/> | MIT | Agent creation patterns â€” agents are plain objects with no registry, fully programmatic | `docs/research/programmatic-agent-registration-research.md` | 2026-03-07 |

## Poll-Dispatch-Reconcile Research (Task #614)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| openai/symphony SPEC.md | <https://github.com/openai/symphony/blob/main/SPEC.md> | MIT | Poll-dispatch-reconcile tick sequence, orchestrator state machine, retry/backoff formulas, reconciliation pattern, reference algorithms | `docs/research/poll-dispatch-reconcile-research.md` | 2026-03-07 |
| Python asyncio.TaskGroup docs | <https://docs.python.org/3.12/library/asyncio-task.html#task-groups> | PSF | TaskGroup for dual-coroutine daemon architecture | `docs/research/poll-dispatch-reconcile-research.md` | 2026-03-07 |

## OwlBearError Exception Hierarchy Research (Task #576)

## Context Condenser Research (Task #619)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|

## Session-Memory Hook Research (Task #622)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangGraph Checkpointer | <https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint> | MIT | Checkpoint persistence pattern: thread-scoped state save/restore, BaseCheckpointSaver interface | `docs/research/session-memory-hook-research.md` (comparison target) | 2026-03-07 |

## Stale Execution Detector Research (Task #623)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nWave StaleExecutionDetector | docs/nwave-research.md Â§3.3 P4 | MIT | Wall-clock stale scan pattern: configurable threshold on IN_PROGRESS tasks | `docs/research/stale-execution-detector-research.md` | 2026-03-07 |
| Quoroom Room stuck detection | docs/quoroom-room-research.md Â§3.4 | MIT | Progress-based detection: productiveToolCalls counter, STUCK directive injection | `docs/research/stale-execution-detector-research.md` | 2026-03-07 |
| Symphony reconciliation | docs/symphony-research.md Â§3.2 | MIT | Per-tick reconcile pattern: stall detection + state refresh for running tasks | `docs/research/stale-execution-detector-research.md` | 2026-03-07 |

## Enhanced bearclaw status with rich.Panel (Task #631)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| rich.Panel API reference | <https://rich.readthedocs.io/en/stable/reference/panel.html> | MIT | Panel constructor params, fit(), nesting renderables, border_style | `docs/research/enhanced-bearclaw-status-research.md` | 2026-03-07 |
| rich-cli Panel + Table composition | <https://github.com/Textualize/rich-cli/blob/main/src/rich_cli/__main__.py> | MIT | Panel wrapping Table pattern: `Panel(table, border_style="dim", title=...)` | `docs/research/enhanced-bearclaw-status-research.md` | 2026-03-07 |
| Prefect server CLI _server_utils.py | <https://github.com/PrefectHQ/prefect/blob/main/src/prefect/cli/_server_utils.py> | Apache-2.0 | PID file management, _is_process_running(), generate_welcome_blurb text pattern | `docs/research/enhanced-bearclaw-status-research.md` | 2026-03-07 |
| Temporal Activity Heartbeats | <https://docs.temporal.io/develop/go/failure-detection> | MIT | Heartbeat timeout pattern: periodic progress pings, timeout-based failure detection | `docs/research/stale-execution-detector-research.md` | 2026-03-07 |

## pytest-cov + pydantic RootModel MRO Crash (Task #646)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pydantic #6584 â€” ImportError with coverage | <https://github.com/pydantic/pydantic/issues/6584> | MIT | Same `sys_modules_saved` root cause; dotted `--cov` sub-package triggers pydantic re-import crash | `docs/research/pytest-cov-pydantic-mro-crash-research.md` | 2026-03-07 |
| coverage.py `SysModuleSaver` (misc.py) | local venv `coverage/misc.py` | Apache-2.0 | Module cleanup after `find_spec` probing breaks `@functools.cache` identity | `docs/research/pytest-cov-pydantic-mro-crash-research.md` | 2026-03-07 |
| coverage.py `InOrOut` (inorout.py) | local venv `coverage/inorout.py` | Apache-2.0 | `source_pkgs` vs `source_dirs` classification via `os.path.isdir()` | `docs/research/pytest-cov-pydantic-mro-crash-research.md` | 2026-03-07 |
| pydantic `import_cached_base_model` | local venv `pydantic/_internal/_import_utils.py` | MIT | `@functools.cache` on `from pydantic import BaseModel` â€” fragile identity assumption | `docs/research/pytest-cov-pydantic-mro-crash-research.md` | 2026-03-07 |
| Celery task_time_limit | <https://docs.celeryq.dev/en/stable/userguide/configuration.html> | BSD-3-Clause | Hard/soft dual timeout pattern: task_time_limit (SIGKILL) + task_soft_time_limit (catchable) | `docs/research/stale-execution-detector-research.md` | 2026-03-07 |
| OpenHands Condenser | <https://github.com/OpenHands/OpenHands/tree/main/openhands/memory/condenser> | MIT | RollingCondenser pattern: should_condense/condense contract, condensation events, LLM summarization for context reduction | `docs/research/session-memory-hook-research.md` (prior art for LLM summary approach) | 2026-03-07 |
| OpenClaw session-memory hook | <https://docs.openclaw.ai/gateway/hooks> | N/A | Hook-based session context persistence on session reset, structured summary generation | `docs/research/session-memory-hook-research.md` (primary inspiration) | 2026-03-07 |
| PydanticAI Agent API docs | <https://ai.pydantic.dev/api/agent/> | MIT | HistoryProcessor type alias definition, `_process_message_history` validation logic, processor execution point | `docs/research/context-condenser-research.md` | 2026-03-07 |
| PydanticAI Messages API docs | <https://ai.pydantic.dev/api/messages/> | MIT | ModelMessage/ModelRequest/ModelResponse structure, part types, tool-call pairing | `docs/research/context-condenser-research.md` | 2026-03-07 |
| OpenHands LLMSummarizingCondenser | <https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/memory/condenser/impl/llm_summarizing_condenser.py> | MIT | Rolling-window LLM summarization pattern: max_size, keep_first, target_size, head+summary+tail | `docs/research/context-condenser-research.md` | 2026-03-07 |
| OpenHands Condenser base classes | <https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/memory/condenser/condenser.py> | MIT | RollingCondenser ABC, condense() contract | `docs/research/context-condenser-research.md` | 2026-03-07 |

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx exceptions | <https://github.com/encode/httpx/blob/master/httpx/_exceptions.py> | BSD-3 | Exception hierarchy pattern: `HTTPError` base â†’ `RequestError` â†’ `TransportError` â†’ leaf types; centralized `__all__` exports; no-import base classes | `docs/research/owlbear-error-hierarchy-research.md` | 2026-03-07 |
| PydanticAI exceptions | <https://ai.pydantic.dev/api/exceptions/> | MIT | Flat hierarchy pattern: `AgentRunError(RuntimeError)` base with leaf subclasses; separate trees for different concerns; no single root | `docs/research/owlbear-error-hierarchy-research.md` | 2026-03-07 |
| CrewAI Agents docs | <https://docs.crewai.com/concepts/agents> | Apache-2.0 | Dual registration: YAML config (recommended) + direct `Agent()` code definition; both first-class | `docs/research/programmatic-agent-registration-research.md` | 2026-03-07 |

## Mission Control Research (Task #598)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| MeisnerDan/mission-control | <https://github.com/MeisnerDan/mission-control> | MIT | Daemon architecture (dispatcher, runner, scheduler, health monitor), loop detection (`LoopDetectionState` with per-task attempt counters + error history, escalation after 3 failures), session resilience (auto-continuation on timeout/max-turns, configurable `maxTaskContinuations`), cost/token tracking (per-session input/output/cache_read/cache_creation capture), credential scrubbing (15+ regex patterns), safe subprocess env (`buildSafeEnv` strips all vars except PATH/HOME/APPDATA/TEMP), token-optimized context snapshot (`generate-context.ts` â†’ ~650 token `ai-context.md`), retry queue with exponential backoff, Eisenhower matrix prioritization, Zod + async-mutex concurrent write safety | `docs/research/mission-control-research.md` | 2026-03-06 |

## Context-Aware Knowledge Injection Research (Tasks #305, #408)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI runtime `instructions=` param | <https://ai.pydantic.dev/agents/#instructions> | MIT | Dynamic instructions via `.run(instructions="...")` â€” reevaluated per-run, caller-provided; chosen over `@agent.instructions` decorator (which lacks prompt access) | `src/owlbear/core/agent.py` (`turn()` knowledge injection via `run_kwargs["instructions"]`), `docs/research/context-aware-knowledge-injection-research.md` | 2026-03-02 |
| MemGPT (Packer et al., 2023) | <https://arxiv.org/abs/2310.08560> | N/A | OS-inspired hierarchical memory: auto-retrieve from archival â†’ inject into working context per turn; inspired per-turn auto-inject approach over tool-based RAG | `docs/research/context-aware-knowledge-injection-research.md` (architecture comparison), `src/owlbear/memory/knowledge/query_service.py` (per-turn injection pattern) | 2026-03-02 |
| LlamaIndex ContextChatEngine | <https://docs.llamaindex.ai> | MIT | Auto-retrieves relevant nodes pre-query; prepends to system prompt with top-k + token budget; informed token-budgeted injection design | `docs/research/context-aware-knowledge-injection-research.md` (architecture comparison), `src/owlbear/memory/knowledge/query_service.py` (token-budget pattern) | 2026-03-02 |

## CLI Split Research (Task #481)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Typer docs: Add Typer | <https://typer.tiangolo.com/tutorial/subcommands/add-typer/> | MIT | `app.add_typer()` pattern for composing sub-apps; named vs unnamed (top-level promotion) | `docs/research/cli-split-research.md` | 2026-03-06 |

## Shell Injection Mitigation Research (Task #493)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Codex CLI â€” Security model & permissions | <https://github.com/openai/codex/blob/main/codex-cli/README.md> | Apache-2.0 | 3-tier approval model (Suggest/Auto Edit/Full Auto), OS-level sandboxing (macOS Seatbelt `sandbox-exec`, Docker on Linux), network disabled in Full Auto, writes limited to workdir | `docs/research/shell-injection-mitigation-research.md` | 2026-03-06 |
| Claude Code â€” Security docs | <https://code.claude.com/docs/en/security> | N/A (docs) | Permission-based architecture, bash sandbox mode with filesystem/network isolation, command blocklist (curl/wget by default), allowlisting safe commands per-user/per-codebase, write restriction to project folder, command injection detection classifier | `docs/research/shell-injection-mitigation-research.md` | 2026-03-06 |

## Orchestrator Rewrite: Pure Sequencer Research (Task #682)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangGraph Plan-and-Execute | <https://blog.langchain.com/planning-agents/> | N/A (blog) | Plannerâ†’executorâ†’re-planner loop; sequencer architecture for multi-step agents | `docs/research/orchestrator-rewrite-sequencer-research.md`, `.github/agents/orchestrator.agent.md` (8-step sequencer) | 2026-03-08 |
| Plan-and-Solve Prompting (Wang et al., 2023) | <https://arxiv.org/abs/2305.04091> | arXiv | Divide task into subtasks per plan, execute per plan; theoretical basis for planning agents | `docs/research/orchestrator-rewrite-sequencer-research.md` | 2026-03-08 |
| LLMCompiler (Kim et al., 2023) | <https://arxiv.org/abs/2312.04511> | arXiv | Planner streams DAG, Task Fetching Unit dispatches when deps met, Joiner decides replan/finish | `docs/research/orchestrator-rewrite-sequencer-research.md`, `.github/agents/orchestrator.agent.md` (wave dispatch pattern) | 2026-03-08 |

## Typed Hook Payloads Research (Task #483)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python TypedDict spec (PEP 589 + 655 + 728) | <https://typing.python.org/en/latest/spec/typeddict.html> | PSF | TypedDict inheritance, NotRequired, structural subtyping for event payloads | `docs/research/typed-hook-payloads-research.md` | 2026-03-08 |
| Pluggy hook system (_hooks.py) | <https://github.com/pytest-dev/pluggy/blob/main/src/pluggy/_hooks.py> | MIT | TypedDict usage for HookspecOpts/HookimplOpts, hook calling convention | `docs/research/typed-hook-payloads-research.md` | 2026-03-08 |
| Python NotRequired (PEP 655) | <https://docs.python.org/3/library/typing.html#typing.NotRequired> | PSF | NotRequired qualifier for optional TypedDict fields, stdlib since 3.11 | `docs/research/typed-hook-payloads-research.md` | 2026-03-08 |
| CrewAI Flows | <https://docs.crewai.com/concepts/flows> | N/A (docs) | Event-driven @startâ†’@listen pipeline; Flow class is a code state machine, not an LLM | `docs/research/orchestrator-rewrite-sequencer-research.md`, `.github/agents/orchestrator.agent.md` (step-based state machine) | 2026-03-08 |
| AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT | PlanningAgent produces agent:task assignments; team infrastructure dispatches mechanically | `docs/research/orchestrator-rewrite-sequencer-research.md`, `.github/agents/orchestrator.agent.md` (planner dispatch pattern) | 2026-03-08 |

## Evaluator Agent Final Disposition (Task #681)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Agents SDK v0.11.1 — Orchestration | <https://openai.github.io/openai-agents-python/multi_agent/> | MIT | Eval pattern is code-level while-loop, not separate agent; agents-as-tools + handoffs | `docs/research/evaluator-agent-final-disposition.md` | 2026-03-09 |
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Guided retry via verbal self-reflection — evaluator's unique value prop | `docs/research/evaluator-agent-final-disposition.md` | 2026-03-09 |

## Evaluator Agent Revisited Research (Task #681)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Agents SDK | <https://github.com/openai/openai-agents-python> | MIT | No evaluator agent; uses Guardrails + Handoffs; evaluation implicit in framework Runner | `docs/research/evaluator-agent-revisited.md` | 2026-03-09 |
| Anthropic Bash Tool â€” Security section | <https://platform.claude.com/docs/en/docs/agents-and-tools/tool-use/bash-tool> | N/A (docs) | Recommended Docker/VM isolation, command filtering/allowlists, resource limits (ulimit), logging all commands; example blocklist pattern in docs | `docs/research/shell-injection-mitigation-research.md` | 2026-03-06 |
| Anthropic Computer Use â€” Security considerations | <https://platform.claude.com/docs/en/docs/agents-and-tools/computer-use> | N/A (docs) | VM/container with minimal privileges, domain allowlisting, human confirmation for real-world consequences, prompt injection classifier defense layer | `docs/research/shell-injection-mitigation-research.md` | 2026-03-06 |
| Typer docs: One File Per Command | <https://typer.tiangolo.com/tutorial/one-file-per-command/> | MIT | Multi-file CLI structure with package layout; callback behavior with sub-apps | `docs/research/cli-split-research.md` | 2026-03-06 |
| Prefect CLI (prefecthq/prefect) | <https://github.com/prefecthq/prefect/tree/main/src/prefect/cli> | Apache-2.0 | Real-world example of 25+ command files in cli/ package, wired in `__init__.py` | `docs/research/cli-split-research.md` | 2026-03-06 |

## Daemon Retry Reconciliation Research (Task #512)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AWS Builders' Library â€” Timeouts, retries, and backoff with jitter | <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/> | N/A | Single-point-in-stack retry principle, multiplicative retry anti-pattern, jitter strategy | `docs/research/daemon-retry-reconciliation-research.md` | 2026-03-06 |
| Microsoft Azure â€” Retry Pattern | <https://learn.microsoft.com/en-us/azure/architecture/patterns/retry> | N/A (docs) | Layered retry guidance: lower-level should fail fast, higher-level owns policy; idempotency considerations | `docs/research/daemon-retry-reconciliation-research.md` | 2026-03-06 |

## Claude Code Tips Research (Task #596)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ykdojo/claude-code-tips | <https://github.com/ykdojo/claude-code-tips> | All Rights Reserved | 45 workflow tips, 6 skills (handoff, clone, half-clone, review-claudemd, gha, reddit-fetch), GLOBAL-CLAUDE.md patterns, command decomposition for approval gates, context token management strategies, structured handoff documents, instruction review from session history, agentic coding spectrum (4 levels) | `docs/research/claude-code-tips-research.md` | 2026-03-06 |

## Global vs Scoped Instructions Audit (Task #705)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Stripe Minions Part 2 — Rule files | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2> | N/A (blog) | Directory-scoped rule strategy, avoid global rules for context window savings | `docs/research/global-vs-scoped-instructions-audit.md` | 2026-03-10 |
| VS Code — Custom instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | CC-BY-4.0 | `applyTo` glob behavior, always-on vs file-based instruction loading, scoping best practices | `docs/research/global-vs-scoped-instructions-audit.md` | 2026-03-10 |

## Screenshot Visual Feedback Research (Task #302)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Claude Computer Use docs | <https://docs.anthropic.com/en/docs/build-with-claude/computer-use> | N/A | Screenshot-after-every-action pattern; base64 in tool_result; coordinate scaling; informed ScreenshotService capture/deliver architecture | `docs/research/screenshot-visual-feedback-research.md` (architecture analysis), `src/owlbear/tools/screenshot.py` (service pattern) | 2026-03-03 |
| Anthropic quickstart (computer-use-demo) | <https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo> | MIT | Agent loop: action â†’ screenshot â†’ send to LLM; screenshot quality/resize tradeoffs; informed auto-capture-on-error hook design | `docs/research/screenshot-visual-feedback-research.md` (prior art), `src/owlbear/tools/screenshot_hook.py` (hook pattern) | 2026-03-03 |

## Project Workspace Research (Task #303)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| cookiecutter | <https://github.com/cookiecutter/cookiecutter> | BSD-3 | Jinja2 project templates from repos, `cookiecutter.json` config; informed hardcoded-template approach (simpler, YAGNI) | `docs/research/project-workspace-research.md` (comparison), `src/owlbear/projects/workspace.py` (template dispatch pattern) | 2026-03-03 |
| copier | <https://github.com/copier-org/copier> | MIT | Template lifecycle (scaffold + update), `copier.yml` questions; evaluated but not adopted (YAGNI â€” update lifecycle not needed) | `docs/research/project-workspace-research.md` (comparison) | 2026-03-03 |

## Source Discovery & Bookmarking Research (Task #304)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Karakeep (fka Hoarder) | <https://github.com/karakeep-app/karakeep> | AGPL-3.0 | AI-based auto-tagging via LLM prompt; bookmark â†’ extract â†’ tag pipeline; inspired `SourceEvaluator` LLM scoring pattern | `docs/research/source-discovery-bookmarking-research.md` (prior art), `src/owlbear/memory/knowledge/evaluator.py` (LLM eval pattern) | 2026-03-03 |
| Pinboard API v1 | <https://pinboard.in/api/> | N/A | Minimal bookmark model: url, title, description, tags, datetime, toread flag; `posts/suggest` for tag recommendations; informed `BookmarkStore` field design | `docs/research/source-discovery-bookmarking-research.md` (data model comparison) | 2026-03-03 |
| Omnivore digest-score | <https://github.com/omnivore-app/omnivore/tree/main/ml/digest-score> | N/A | ML-based relevance scoring (random forest); evaluated but not adopted (too complex for LLM-scored approach) | `docs/research/source-discovery-bookmarking-research.md` (comparison) | 2026-03-03 |

## Slack Structured Proposals Research (Task #307)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode â€” interactive features | <https://docs.slack.dev/apis/events-api/using-socket-mode/#interactivity> | N/A | `type: "interactive"` envelope, `block_actions` payload, `envelope_id` acknowledgment | `src/owlbear/channels/slack.py` (`_handle_socket_event` interactive branch), `docs/research/slack-structured-proposals-research.md` | 2026-03-03 |
| Slack Button element reference | <https://docs.slack.dev/reference/block-kit/block-elements/button-element> | N/A | `action_id`, `value`, `style` (primary/danger), `confirm` dialog; informed approval/interactive proposal button design | `src/owlbear/channels/slack_templates.py` (`format_approval_blocks`, `format_interactive_proposal_blocks`) | 2026-03-03 |
| Bolt for Python â€” action listener | <https://docs.slack.dev/tools/bolt-python/concepts/actions> | N/A | `@app.action("action_id")` pattern, `ack()` + `say()` response; informed handler acknowledgment pattern | `docs/research/slack-structured-proposals-research.md` (architecture comparison) | 2026-03-03 |
| Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | MIT | Thread-based AI assistant pattern, message-per-thread model; informed thread registry design | `src/owlbear/channels/slack.py` (`_thread_registry`, `get_or_create_thread`), `docs/research/slack-structured-proposals-research.md` | 2026-03-03 |

## BGE-M3 Evaluation Research (Task #375)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | N/A | MIRACL/MLDR benchmarks for dense/sparse/ColBERT quality comparison; self-knowledge distillation training methodology | `docs/bge-m3-evaluation.md` | 2026-03-03 |
| Yannael â€” OpenAI vs open-source embeddings (TDS) | <https://towardsdatascience.com/openai-vs-open-source-multilingual-embedding-models-e5ccb7c90f05> | N/A | Independent MRR evaluation of bge-m3 vs OpenAI embeddings on multilingual retrieval tasks | `docs/bge-m3-evaluation.md` | 2026-03-03 |
| FastEmbed issue #107 (bge-m3 support) | <https://github.com/qdrant/fastembed/issues/107> | N/A | 2+ year open issue tracking bge-m3 3-output support status (dense+sparse+ColBERT via ONNX) | `docs/bge-m3-evaluation.md` | 2026-03-03 |

## Voice Channel Import Research (Task #458)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Rasa `core/channels/` | <https://github.com/RasaHQ/rasa/tree/main/rasa/core/channels> | MIT | Channel adapter organization: all channels (incl. `twilio_voice.py`) co-located in `channels/` dir; thin wrapper pattern | `docs/research/voice-channel-import-research.md` (prior art comparison for relocate-vs-fix decision) | 2026-03-06 |

## SQLite Connection Lifecycle Research (Task #459)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” `sqlite3.Connection.close()` | <https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.close> | PSF | `close()` is sync, rolls back pending txn, Python 3.13 emits `ResourceWarning` on unclosed connections | `docs/research/sqlite-connection-lifecycle-research.md` | 2026-03-06 |
| Datasette `database.py` | <https://github.com/simonw/datasette/blob/main/datasette/database.py> | Apache 2.0 | Long-running daemon SQLite lifecycle: `_all_file_connections` tracking list, explicit `close()` iterates all | `docs/research/sqlite-connection-lifecycle-research.md` | 2026-03-06 |
| Flask `ctx.py` teardown | <https://github.com/pallets/flask/blob/main/src/flask/ctx.py> | BSD-3 | Cleanup-list pattern: `pop()` iterates teardown callbacks with error suppression | `docs/research/sqlite-connection-lifecycle-research.md` | 2026-03-06 |

## httpx Timeout Configuration Research (Task #460)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx official docs â€” Timeouts | <https://www.python-httpx.org/advanced/timeouts/> | BSD-3 | `httpx.Timeout` fine-grained config (connect/read/write/pool), default 5s, per-client vs per-request | `docs/research/httpx-timeout-research.md` | 2026-03-06 |
| PydanticAI `cached_async_http_client` | <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/models/__init__.py> | MIT | `DEFAULT_HTTP_TIMEOUT=600`, `connect=5`, `httpx.Timeout(timeout=timeout, connect=connect)` pattern for LLM clients | `docs/research/httpx-timeout-research.md` | 2026-03-06 |

## Ingest DRY Refactor Research (Task #464)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Refactoring.Guru â€” Extract Method | <https://refactoring.guru/extract-method> | N/A | Canonical Extract Method refactoring pattern: replace duplicated code fragment with call to extracted method | `docs/research/ingest-dry-refactor-research.md` | 2026-03-06 |
| SourceMaking â€” Extract Method | <https://sourcemaking.com/refactoring/extract-method> | N/A | Independent reference for Extract Method: "Less code duplication. Replace duplicates with calls to your new method." | `docs/research/ingest-dry-refactor-research.md` | 2026-03-06 |

## Shutdown Event Research (Task #509)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python docs â€” `loop.add_signal_handler` | <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.add_signal_handler> | PSF-2.0 | Unix-only limitation; idiomatic asyncio signal pattern | `docs/research/shutdown-event-research.md` | 2026-03-06 |
| Python docs â€” `signal.signal` | <https://docs.python.org/3/library/signal.html#signal.signal> | PSF-2.0 | Signal handler execution semantics; Windows signal limitations | `docs/research/shutdown-event-research.md` | 2026-03-06 |
| Python docs â€” `loop.call_soon_threadsafe` | <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_soon_threadsafe> | PSF-2.0 | "safe to be called from a reentrant context or signal handler"; thread-safe scheduling | `docs/research/shutdown-event-research.md` | 2026-03-06 |
| Python docs â€” `asyncio.Event` | <https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event> | PSF-2.0 | "Not thread-safe" caveat; `set()`/`is_set()`/`wait()` API | `docs/research/shutdown-event-research.md` | 2026-03-06 |

## Agent Orchestrator Research (Task #585)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ComposioHQ/agent-orchestrator | <https://github.com/ComposioHQ/agent-orchestrator> | MIT | 8-slot plugin architecture (Runtime, Agent, Workspace, Tracker, SCM, Notifier, Terminal, Lifecycle); config-driven reaction engine (eventâ†’action with retry/escalation); priority-routed notifications; 3-layer prompt builder (base + config + user rules); session lifecycle state machine (15 statuses); flat-file metadata | `docs/research/agent-orchestrator-research.md` (analysis) | 2026-03-06 |

## Axon Code Intelligence Research (Task #586)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| harshkedia177/axon v0.2.4 | <https://github.com/harshkedia177/axon> | MIT | Code knowledge graph engine: 12-phase ingestion pipeline, KuzuDB storage with StorageBackend Protocol, hybrid search (BM25+vector+fuzzy via RRF), MCP server with next-step hint pattern, watch mode with tiered re-indexing, community detection (Leiden), execution flow tracing, impact analysis, dead code detection, change coupling | `docs/research/axon-code-intelligence-research.md` (analysis) | 2026-03-06 |
| Aider RepoMap | <https://aider.chat/docs/repomap.html> | Apache-2.0 | tree-sitter code structure graphs, token-budgeted context selection for LLMs, graph ranking for relevance optimization | `docs/research/axon-code-intelligence-research.md` (comparison) | 2026-03-06 |

## nWave Multi-Agent Research (Task #589)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| nWave-ai/nWave | <https://github.com/nWave-ai/nWave> | MIT | Wave-based multi-agent pipeline (23 agents), DES enforcement hooks (PreToolUse/PostToolUse/SubagentStop), rigor profiles (lean/standard/thorough/exhaustive), reviewer pairing pattern, stale execution detection, turn limits per task type, hexagonal architecture in enforcement layer, skill-loading-per-phase pattern | `docs/research/nwave-research.md` (analysis) | 2026-03-06 |
| CrewAI Crews docs | <https://docs.crewai.com/concepts/crews> | N/A | Hierarchical process (manager agent), sequential/async execution, step_callback/task_callback hooks, planning LLM, knowledge sources at crew level | `docs/research/nwave-research.md` (comparison) | 2026-03-06 |

## OpenClaw Skills Ecosystem Research (Task #590)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenClaw main repo | <https://github.com/openclaw/openclaw> | MIT | Heartbeat proactive agent loop (30m timer, `HEARTBEAT.md` self-updating checklist, `HEARTBEAT_OK` suppression), hooks system (13 event types, bundled session-memory/boot-md hooks), cron scheduler (isolated sessions, retry policy), skills framework (SKILL.md format, gating, ClawHub registry), AGENTS.md repo guidelines, coding-agent delegation pattern | `docs/research/openclaw-skills-research.md` (analysis) | 2026-03-06 |
| OpenClaw Heartbeat docs | <https://docs.openclaw.ai/gateway/heartbeat> | N/A | Periodic agent self-initiation: configurable interval, active hours, per-agent config, lightweight bootstrap context, manual wake via system events | `docs/research/openclaw-skills-research.md` (heartbeat pattern) | 2026-03-06 |
| OpenClaw Hooks docs | <https://docs.openclaw.ai/gateway/hooks> | N/A | Event-driven hook system: 13 event types, directory-based discovery, bundled hooks (session-memory saves context on reset, boot-md runs startup instructions) | `docs/research/openclaw-skills-research.md` (hook comparison) | 2026-03-06 |
| OpenClaw Cron docs | <https://docs.openclaw.ai/gateway/cron-jobs> | N/A | Built-in scheduler: main vs isolated sessions, persistent job store, delivery modes, retry with transient/permanent error classification | `docs/research/openclaw-skills-research.md` (cron analysis) | 2026-03-06 |
| OpenClaw Browser docs | <https://docs.openclaw.ai/tools/browser-use> | N/A | CDP + Playwright browser control: managed profile isolation, AI/role snapshot system with numeric refs, SSRF guards, multi-profile support | `docs/research/openclaw-skills-research.md` (browser comparison) | 2026-03-06 |
| OpenClaw Skills docs | <https://docs.openclaw.ai/tools/skills> | N/A | AgentSkills-compatible SKILL.md format: YAML frontmatter gating (bins, env, config, OS), bundled/managed/workspace discovery, ClawHub registry | `docs/research/openclaw-skills-research.md` (skills framework) | 2026-03-06 |
| OpenClaw Lobster workflow shell | <https://github.com/openclaw/lobster> | MIT | Typed JSON-first pipelines, approval gates, step dependencies (`stdin: $stepId.stdout`), `openclaw.invoke` tool shim â€” evaluated and rejected (YAGNI) | `docs/research/openclaw-skills-research.md` (workflow comparison) | 2026-03-06 |

## Excalidraw MCP App Server Research (Task #594)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | MIT | MCP Apps architecture (toolâ†’resourceâ†’iframe), tool visibility scoping (`_meta.ui.visibility`), cheat-sheet companion tool pattern (`read_me`), checkpoint store with ID validation + path-traversal guard, dual-transport factory (`createServer()` for stateless HTTP and stdio) | `docs/research/excalidraw-mcp-research.md` | 2026-03-06 |
| MCP Apps extension spec | <https://modelcontextprotocol.io/docs/extensions/apps> | N/A | MCP Apps protocol: tool declares `_meta.ui.resourceUri`, host renders sandboxed iframe, bidirectional postMessage communication, CSP policy, supported clients (Claude, VS Code, ChatGPT, Goose) | `docs/research/excalidraw-mcp-research.md` | 2026-03-06 |
| ext-apps SDK repo | <https://github.com/modelcontextprotocol/ext-apps> | Apache-2.0 | SDK packages (`/server`, `/react`, `/app-bridge`), 20+ example servers, Python example servers (`qr-server`, `say-server`), agent skills for scaffolding MCP Apps | `docs/research/excalidraw-mcp-research.md` | 2026-03-06 |

## EdgeQuake Graph-RAG Research (Task #597)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| raphaelmansuy/edgequake | <https://github.com/raphaelmansuy/edgequake> | Apache-2.0 | Rust LightRAG implementation: tuple-based entity extraction, cooperative pipeline cancellation (CancellationToken), resilient partial-failure processing, per-operation LLM cost tracking (ModelPricing/OperationCost), entity normalization (UPPERCASE_UNDERSCORE, 36-40% dedup), gleaning multi-pass extraction (+18-25% recall), document lineage, 6 query modes, MCP agent integration server | `docs/research/edgequake-research.md` | 2026-03-06 |
| LightRAG paper (Guo et al. 2024) | <https://arxiv.org/abs/2410.05779> | N/A | Original LightRAG algorithm: entity extraction â†’ knowledge graph â†’ dual-level retrieval (local entity + global community). EdgeQuake implements this in Rust. | `docs/research/edgequake-research.md` (algorithm reference) | 2026-03-06 |

## PinchTab Browser Control Research (Task #595)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pinchtab/pinchtab | <https://github.com/pinchtab/pinchtab> | MIT | Accessibility-tree snapshot approach (stable element refs, token-efficient extraction), semantic element matching (combined lexical + hashing embedder), intent cache + stale-ref self-healing recovery, tiered token-cost model (text ~800, interactive ~3600, full ~10500), single-tool MCP plugin design, SKILL.md + TRUST.md security model pattern, pluggable strategy registry with factory + OrchestratorAware injection, auto-restart with exponential backoff | `docs/research/pinchtab-research.md` | 2026-03-06 |

## ChannelPlugin Protocol Extension Research (Task #482)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PEP 544 â€” Protocols: Structural subtyping | <https://peps.python.org/pep-0544/> | N/A | Protocol default method bodies, Protocol inheritance, `runtime_checkable` semantics, structural vs nominal subtyping interaction | `docs/research/channel-protocol-extension-research.md` | 2026-03-06 |
| mypy Protocol documentation | <https://mypy.readthedocs.io/en/stable/protocols.html> | N/A | Default implementations in Protocols, mixin usage with Protocols, explicit vs structural conformance | `docs/research/channel-protocol-extension-research.md` | 2026-03-06 |

## Typed Hook Payloads Research (Task #483)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python TypedDict spec | <https://typing.python.org/en/latest/spec/typeddict.html> | N/A | TypedDict inheritance, Required/NotRequired, ReadOnly, structural subtyping rules for event payload typing | `docs/research/typed-hook-payloads-research.md` | 2026-03-06 |
| Python typing docs (TypedDict) | <https://docs.python.org/3/library/typing.html#typing.TypedDict> | PSF | Class-based and functional syntax, runtime behavior, optional fields | `docs/research/typed-hook-payloads-research.md` | 2026-03-06 |
| Pluggy (pytest hook system) | <https://github.com/pytest-dev/pluggy> | MIT | TypedDict for hook options (HookspecOpts, HookimplOpts), Protocol-based typed hookspecs, `**kwargs: object` calling convention | `docs/research/typed-hook-payloads-research.md` | 2026-03-06 |

## ReDoS Protection Research (Task #496)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OWASP ReDoS | <https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS> | CC BY-SA 4.0 | Evil regex patterns (nested quantifiers, overlapping alternation), NFA backtracking attack mechanics | `docs/research/redos-protection-research.md` | 2026-03-06 |
| Google RE2 | <https://github.com/google/re2> | BSD-3 | Linear-time regex engine, safety-first design, no backtracking by construction | `docs/research/redos-protection-research.md` (comparison) | 2026-03-06 |
| `google-re2` PyPI | <https://pypi.org/project/google-re2/> | BSD-3 | Python bindings for RE2, API compatibility notes, PCRE feature gaps | `docs/research/redos-protection-research.md` (comparison) | 2026-03-06 |
| `regex` PyPI (mrab-regex) | <https://pypi.org/project/regex/> | Apache-2.0 | Drop-in `re` replacement with native `timeout` parameter on match/search/sub, C-level timeout checking | `docs/research/redos-protection-research.md` (recommended approach) | 2026-03-06 |

## Qdrant Batch Retrieve Research (Task #506)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Qdrant Points docs | <https://qdrant.tech/documentation/concepts/points/#retrieve-points> | Apache-2.0 | Batch retrieve by IDs: `POST /collections/{name}/points` with `"ids": [0, 3, 100]` | Task #506 body (feasibility validation) | 2026-03-06 |

## Circuit Breaker Research (Task #515)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pybreaker | <https://github.com/danielfm/pybreaker> | BSD-3 | Circuit breaker pattern implementation: `fail_max`, `reset_timeout`, `success_threshold`, `exclude` list, `CircuitBreakerListener`, Redis backing, state management API | `docs/research/circuit-breaker-research.md` | 2026-03-06 |
| aiobreaker | <https://github.com/arlyon/aiobreaker> | BSD-3 | Asyncio fork of pybreaker: native async decorator, `timedelta`-based timeout | `docs/research/circuit-breaker-research.md` | 2026-03-06 |
| tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | Apache-2.0 | Custom stop/retry/wait callbacks; `RetryCallState` for state inspection; `AsyncRetrying` for async retry blocks | `docs/research/circuit-breaker-research.md` | 2026-03-06 |
| Circuit Breaker pattern (Nygard) | <https://microservices.io/patterns/reliability/circuit-breaker.html> | â€” | Canonical pattern: closed â†’ open (after N failures) â†’ half-open (after timeout) â†’ closed (on success) / open (on failure) | `docs/research/circuit-breaker-research.md` | 2026-03-06 |
| qdrant-client Python API | <https://python-client.qdrant.tech/qdrant_client.qdrant_client> | Apache-2.0 | `retrieve(collection_name, ids=Sequence[int\|str\|UUID], with_payload=True)` accepts list of IDs natively | Task #506 body (API confirmation) | 2026-03-06 |

## httpx AsyncClient Reuse Research (Task #507)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| httpx docs â€” Clients | <https://www.python-httpx.org/advanced/clients/> | BSD-3 | Connection pooling benefits, client reuse pattern, `base_url` config, `.close()` explicit cleanup | `docs/research/httpx-client-reuse-research.md` | 2026-03-06 |
| httpx docs â€” Async Support | <https://www.python-httpx.org/async/#opening-and-closing-clients> | BSD-3 | `AsyncClient` lifecycle: `async with` vs `await client.aclose()`, warning against instantiating multiple clients in hot loops | `docs/research/httpx-client-reuse-research.md` | 2026-03-06 |
| PydanticAI `cached_async_http_client` | <https://github.com/pydantic/pydantic-ai> (models/__init__.py) | MIT | `@cache`-based client singleton per provider, `is_closed` guard, `Timeout(600, connect=5)` defaults | `docs/research/httpx-client-reuse-research.md` | 2026-03-06 |

## OpenClaw Ecosystem & Skills Epic Synthesis (Task #581)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenHands SDK | <https://github.com/OpenHands/OpenHands> | MIT | Skill system (3 types: repo/keyword/task trigger), condenser architecture (rolling-window LLM summarization with threshold detection), microagent concept, AGENTS.md conventions | `docs/research/openclaw-ecosystem-research.md` (cross-system comparison) | 2026-03-07 |
| OpenHands Skill docs | <https://docs.openhands.dev/sdk/arch/skill> | N/A | Trigger-based skill activation (always/keyword/task), MCP tool embedding in skills, markdown+frontmatter format, `.cursorrules` compat | `docs/research/openclaw-ecosystem-research.md` (skill comparison) | 2026-03-07 |
| OpenHands Condenser docs | <https://docs.openhands.dev/sdk/arch/condenser> | N/A | LLMSummarizingCondenser: rolling window (keep head+tail, summarize middle), threshold detection, pipeline chaining, condensation events with forgotten_event_ids | `docs/research/openclaw-ecosystem-research.md` (condenser pattern) | 2026-03-07 |
| SWE-agent | <https://github.com/SWE-agent/SWE-agent> | MIT | RetryAgentConfig (meta-agent with multiple configs), max_requeries=3 for format/block/syntax errors, YAML tool bundles, history processors | `docs/research/openclaw-ecosystem-research.md` (retry comparison) | 2026-03-07 |
| SWE-agent config docs | <https://swe-agent.com/latest/reference/agent_config/> | N/A | Agent config Pydantic models (DefaultAgentConfig, RetryAgentConfig, ShellAgentConfig), tool config, history processors, action samplers | `docs/research/openclaw-ecosystem-research.md` (self-correction patterns) | 2026-03-07 |

## Hook Protocol Research (Task #564)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pluggy docs (v1.6) | <https://pluggy.readthedocs.io/en/stable/> | MIT | Marker-based hook detection, PluginManager.register() auto-discovery, hookspec/hookimpl decorators; designed for external plugin ecosystems (1400+ pytest plugins), not internal wiring | `docs/research/hook-protocol-research.md` | 2026-03-07 |
| blinker docs (v1.9) | <https://blinker.readthedocs.io/en/stable/> | MIT | Named signal pattern, signal.connect() explicit registration, no auto-discovery; anonymous signals as class attributes | `docs/research/hook-protocol-research.md` | 2026-03-07 |
| Django signals docs (v5.1) | <https://docs.djangoproject.com/en/5.1/topics/signals/> | BSD-3 | Signal.connect() explicit registration; warning: "signals give the appearance of loose coupling, but they can quickly lead to code that is hard to understand" â€” prefer direct calls for internal code | `docs/research/hook-protocol-research.md` | 2026-03-07 |

## pyttsx3 Maintenance & TTS Alternatives Research (Task #570)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| pyttsx3 PyPI (release history) | <https://pypi.org/project/pyttsx3/#history> | MIT | Release cadence: v2.92-2.99 (Sep 2024 - Jul 2025); project no longer dormant | `docs/research/pyttsx3-tts-alternatives-research.md` | 2026-03-07 |
| pyttsx3 GitHub issues | <https://github.com/nateshmbhat/pyttsx3/issues> | MIT | 74 open issues; macOS NSSpeechSynthesizer deprecated (#347); run-loop bugs | `docs/research/pyttsx3-tts-alternatives-research.md` | 2026-03-07 |
| edge-tts PyPI & GitHub | <https://pypi.org/project/edge-tts/> | GPL-3.0 | v7.2.7 (Dec 2025); 10.2k stars; online neural TTS; async-native; requires network | `docs/research/pyttsx3-tts-alternatives-research.md` | 2026-03-07 |
| pyttsx4 PyPI | <https://pypi.org/project/pyttsx4/> | MIT | v3.0.15 (Jun 2023); stale fork of pyttsx3; not viable | `docs/research/pyttsx3-tts-alternatives-research.md` | 2026-03-07 |
| Coqui TTS PyPI | <https://pypi.org/project/TTS/> | MPL-2.0 | v0.22.0 (Dec 2023); heavy ML framework; Python <3.12 only; overkill | `docs/research/pyttsx3-tts-alternatives-research.md` | 2026-03-07 |

## DiagramService Kroki HTTP API Research (Task #617)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Kroki docs â€” Usage | <https://docs.kroki.io/kroki/setup/usage/> | MIT | POST API contract: text/JSON formats, no encoding needed for POST | `docs/research/diagram-service-kroki-research.md` | 2026-03-07 |
| Kroki docs â€” HTTP Clients | <https://docs.kroki.io/kroki/setup/http-clients/> | MIT | cURL/HTTPie request examples, Content-Type patterns | `docs/research/diagram-service-kroki-research.md` | 2026-03-07 |
| yuzutech/kroki DiagramHandler.java | <https://github.com/yuzutech/kroki> | MIT | Error handling: BadRequestException codes, empty body/source validation, UnsupportedFormatException | `docs/research/diagram-service-kroki-research.md` | 2026-03-07 |
| Kroki docs â€” Install | <https://docs.kroki.io/kroki/setup/install/> | MIT | Core vs companion container diagram type availability | `docs/research/diagram-service-kroki-research.md` | 2026-03-07 |

## HeartbeatRunner Test Coverage Research (Task #638)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python unittest.mock docs | <https://docs.python.org/3/library/unittest.mock.html> | PSF | AsyncMock, side_effect, assert_awaited patterns for async test prior art | `docs/research/heartbeat-tests-research.md` | 2026-03-09 |
| PydanticAI test_agent.py | <https://github.com/pydantic/pydantic-ai/blob/main/tests/test_agent.py> | MIT | Agent test patterns: AsyncMock, behavior-based assertions | `docs/research/heartbeat-tests-research.md` | 2026-03-09 |

## Task-Level Retry Research (Task #625)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| OpenAI Symphony SPEC.md (via prior research) | `docs/research/symphony-research.md` S3.2 | N/A | Task-level exponential backoff formula `min(10s * 2^(n-1), max)`, continuation turns after success, retry scheduling in poll-dispatch loop | `docs/research/task-level-retry-research.md` | 2026-03-07 |
| AWS Builders' Library â€” Timeouts, retries, and backoff with jitter | <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/> | N/A | Single retry layer per stack level, multiplicative retry anti-pattern (3^5 = 243x), full jitter recommendation for distributed backoff | `docs/research/task-level-retry-research.md` | 2026-03-07 |
| Celery task retry docs | <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying> | BSD-3 | `autoretry_for`, `retry_backoff=True` (1s base, 2x growth), `retry_backoff_max=600s`, `retry_jitter=True`, `max_retries=3` default, `MaxRetriesExceededError` on exhaustion | `docs/research/task-level-retry-research.md` | 2026-03-07 |

## Planner Agent: Board Reading + Wave Planning (Task #680)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AutoGen SelectorGroupChat + PlanningAgent | <https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT/CC-BY-4.0 | Dedicated PlanningAgent pattern: breaks tasks, assigns to specialists, checks progress; separation of planning from execution | `docs/research/planner-agent-research.md` | 2026-03-08 |
| CrewAI AgentPlanner | <https://docs.crewai.com/concepts/planning> | Apache-2.0 | Separate LLM planning call before crew execution; `planning=True` injects step-by-step plan into task descriptions | `docs/research/planner-agent-research.md` | 2026-03-08 |
| Conductor DAG + topological dispatch | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | DAG construction â†’ topological sort â†’ wave dispatch pattern (re-examined for planner output contract design) | `docs/research/planner-agent-research.md` | 2026-03-08 |

## Test-Writer Agent Research (Task #683)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| AgentCoder (Huang et al., 2024) | <https://arxiv.org/abs/2312.13010> | CC-BY-4.0 | 3-agent framework (programmer, test designer, test executor); independent test generation achieves 87.8% accuracy vs 61% single-agent; RQ6 empirical evidence for separation | `docs/research/test-writer-agent-research.md` | 2026-03-08 |
| ChatDev (Qian et al., 2024) | <https://arxiv.org/abs/2307.07924> | arXiv | 7-agent pipeline with tester role; tests-after-coding approach (less adversarial) | `docs/research/test-writer-agent-research.md` | 2026-03-08 |
| MetaGPT (Hong et al., 2024) | <https://arxiv.org/abs/2308.00352> | CC-BY-4.0 | Assembly-line with QA engineer; 79% test accuracy baseline for comparison | `docs/research/test-writer-agent-research.md` | 2026-03-08 |
| Uncle Bob â€” The Cycles of TDD | <https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html> | Blog | Red/Green/Refactor theory; Three Laws of TDD; natural agent-role mapping | `docs/research/test-writer-agent-research.md` | 2026-03-08 |
| Self-Collaboration (Dong et al., 2023) | <https://arxiv.org/abs/2304.07590> | arXiv | analyst-coder-tester multi-role pattern; LLM prediction vs execution distinction | `docs/research/test-writer-agent-research.md` | 2026-03-08 |

## Evaluator Agent Research (Task #681)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | CC-BY-4.0 | Explicit Evaluator (M_e) scoring Actor output; separate Self-Reflection (M_sr) generating verbal feedback; binary reward signal triggering retry | `docs/research/evaluator-agent-research.md` | 2026-03-08 |
| LATS (Zhou et al., 2023) | <https://arxiv.org/abs/2310.04406> | CC-BY-4.0 | LM-powered value function evaluating node quality; routing search decisions (expand/backtrack/select); reasoned scores | `docs/research/evaluator-agent-research.md` | 2026-03-08 |
| Conductor evaluate-loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | Planâ†’EvalPlanâ†’Executeâ†’EvalExecâ†’Fix cycle (max 3); structured eval-then-fix pattern | `docs/research/evaluator-agent-research.md` | 2026-03-08 |
| AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | MIT/CC-BY-4.0 | Model-based routing with custom selector/candidate functions; next-speaker selection pattern | `docs/research/evaluator-agent-research.md` | 2026-03-08 |

## Inter-Agent Communication Protocol (Task #684)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangGraph Agent Supervisor blog | <https://blog.langchain.com/langgraph-multi-agent-workflows/> | CC-BY-4.0 | Independent scratchpads per agent; only final responses to supervisor; shared vs independent scratchpad trade-offs | `docs/research/inter-agent-communication-protocol-research.md` | 2026-03-08 |
| OpenAI Swarm | <https://github.com/openai/swarm> | MIT | `Result(value, agent, context_variables)` â€” explicit separation of routing return value vs shared state | `docs/research/inter-agent-communication-protocol-research.md` | 2026-03-08 |
| Blackboard design pattern (Wikipedia) | <https://en.wikipedia.org/wiki/Blackboard_(design_pattern)> | CC-BY-SA-4.0 | Structured global memory + selective reading by control component; knowledge source independence | `docs/research/inter-agent-communication-protocol-research.md` | 2026-03-08 |
| CrewAI Collaboration docs | <https://docs.crewai.com/concepts/collaboration> | Apache-2.0 | Task `context=[previous_task]` chain; lead agent sees delegation results only; hierarchical collaboration pattern | `docs/research/inter-agent-communication-protocol-research.md` | 2026-03-08 |

## Task Decomposition Rules (Task #685)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| ChatDev (Qian et al., ACL 2024) | <https://arxiv.org/abs/2307.07924> | arXiv non-exclusive | Chat chain phase-scoped subtask decomposition; single-concern per subtask pair | `docs/research/task-decomposition-rules-research.md` | 2026-03-08 |
| MetaGPT (Hong et al., ICLR 2024) | <https://arxiv.org/abs/2308.00352> | MIT | SOP-driven decomposition; assembly-line paradigm with intermediate verification | `docs/research/task-decomposition-rules-research.md` | 2026-03-08 |
| OpenHands agent delegation | <https://github.com/All-Hands-AI/OpenHands> | MIT | Subtask/delegation hierarchy; bounded scope per agent conversation | `docs/research/task-decomposition-rules-research.md` | 2026-03-08 |
| Fowler â€” Bounded Context (DDD) | <https://martinfowler.com/bliki/BoundedContext.html> | Blog | Domain boundaries by model/language differences; explicit integration points | `docs/research/task-decomposition-rules-research.md` | 2026-03-08 |

## Instruction Token Audit (Task #686)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Liu et al. "Lost in the Middle" (2023) | <https://arxiv.org/abs/2307.03172> | arXiv | Performance degrades with context length; middle-positioned info systematically missed | `docs/research/instruction-token-audit-research.md` | 2026-03-08 |
| Li et al. "Long-context LLMs Struggle" (2024) | <https://arxiv.org/abs/2404.02060> | arXiv | Classification accuracy drops as in-context examples/instructions grow | `docs/research/instruction-token-audit-research.md` | 2026-03-08 |
| Anthropic Prompt Engineering Best Practices | <https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct> | N/A | Conciseness, long-context structuring, queries-at-end boosts quality 30% | `docs/research/instruction-token-audit-research.md` | 2026-03-08 |
| OpenAI Prompt Engineering Guide | <https://developers.openai.com/api/docs/guides/prompt-engineering> | N/A | Clear sections, minimal context, prompt caching for repeated prefixes | `docs/research/instruction-token-audit-research.md` | 2026-03-08 |

## Stripe Minions Agentic Toolchain (Task #647)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Stripe Minions Part 1 | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents> | N/A (blog) | Unattended one-shot agent UX, Slack/CLI entry points, shift-left feedback, max 2 CI rounds | `docs/research/stripe-minions-research.md` | 2026-03-08 |
| Stripe Minions Part 2 | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2> | N/A (blog) | Blueprints (hybrid workflow+agent), devboxes, Toolshed MCP registry, scoped rule files, context pre-hydration | `docs/research/stripe-minions-research.md` | 2026-03-08 |
| Anthropic â€” Building Effective Agents | <https://www.anthropic.com/engineering/building-effective-agents> | N/A (blog) | Workflows vs agents taxonomy, orchestrator-workers pattern, tool prompt engineering | `docs/research/stripe-minions-research.md` | 2026-03-08 |

## GCP Always-On Memory Agent (Task #700)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GCP always-on-memory-agent | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent> | MIT | Always-on memory pattern, consolidation loop, importance scoring, ADK agent orchestration | `docs/research/gcp-always-on-memory-agent.md` | 2026-03-09 |
| Mem0 (mem0ai/mem0) | <https://github.com/mem0ai/mem0> | Apache-2.0 | Persistent agent memory layer, LLM-extracted facts, multi-level memory (user/session/agent) | `docs/research/gcp-always-on-memory-agent.md` | 2026-03-09 |

## Always-On Memory Integration (Task #701)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GCP always-on-memory-agent research (#700) | `docs/research/gcp-always-on-memory-agent.md` | N/A (internal) | Consolidation pattern, importance scoring, component mapping | `docs/research/always-on-memory-integration-research.md` | 2026-03-09 |
| Mem0 architecture | <https://github.com/mem0ai/mem0> | Apache-2.0 | Multi-level memory, LLM-extracted structured facts, hybrid search | `docs/research/always-on-memory-integration-research.md` | 2026-03-09 |
| OwlBear context-aware injection research | `docs/research/context-aware-knowledge-injection-research.md` | N/A (internal) | Hybrid auto-inject + tool-based RAG pattern | `docs/research/always-on-memory-integration-research.md` | 2026-03-09 |
| OwlBear MemoryConsolidator research (#485) | `docs/research/memory-consolidator-research.md` | N/A (internal) | Session consolidation YAGNI precedent | `docs/research/always-on-memory-integration-research.md` | 2026-03-09 |
| Generative Agents (Park et al.) | <https://arxiv.org/abs/2304.03442> | N/A (paper) | Recency × relevance × importance retrieval scoring | `docs/research/always-on-memory-integration-research.md` | 2026-03-09 |

## GCP generative-ai Repo Audit (Task #702)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| GCP agents/genai-experience-concierge | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/genai-experience-concierge> | Apache-2.0 | Guardrail classifier, semantic router, task planner design patterns (LangGraph) | `docs/research/gcp-generative-ai-audit-research.md` | 2026-03-09 |
| GCP evaluation/evaluating_adk_agent | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/evaluation> | Apache-2.0 | ADK agent evaluation, trajectory_single_tool_use metric, behavioral eval dataset design | `docs/research/gcp-generative-ai-audit-research.md` | 2026-03-09 |
| GCP use-cases/graphrag | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/use-cases/graphrag> | Apache-2.0 | Agentic GraphRAG with Neo4j + ADK, multi-hop graph traversal | `docs/research/gcp-generative-ai-audit-research.md` | 2026-03-09 |

## Cheat-Sheet Tool Pattern Research (Task #718)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | MIT | Evolved `read_diagram_guide` tool pattern (26 tools), skill with cheatsheet.md, design quality guidance for AI-generated diagrams | `docs/research/cheat-sheet-tool-pattern-research.md` | 2026-07-27 |
| PMCP (ViperJuice/pmcp) | <https://github.com/ViperJuice/pmcp> | MIT | L0-L3 progressive disclosure layers, 80% token reduction, 14 meta-tools instead of 50+, meta-gateway pattern | `docs/research/cheat-sheet-tool-pattern-research.md` | 2026-07-27 |
