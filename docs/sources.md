# Sources

External repos and resources studied during OwlBear development.

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
| CrewAI | <https://docs.crewai.com/> | MIT | Agent role/goal/backstory pattern, hierarchical process (manager agent), `allow_delegation`, sequential process, researcher → reporting_analyst pattern | `.github/agents/architect.agent.md` (hierarchical manager pattern), `.github/agents/writer.agent.md` (reporting analyst pattern) | 2026-02-26 |

## kanban-md (Project Management Tool)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| kanban-md README + built-in skills | <https://github.com/antopolskiy/kanban-md> | MIT | CLI reference (commands, flags, output formats), built-in agent skills (`kanban-md` skill, `kanban-based-development` skill), config.yml schema, claim semantics, pick algorithm, classes of service | `.github/skills/kanban-md/SKILL.md` (adapted from built-in `kanban-md` skill), `.github/skills/kanban-based-development/SKILL.md` (adapted from built-in `kanban-based-development` skill), `kanban/config.yml` | 2026-02-07 |
| kanban-md v0.32.2 "Hotkey Net" release | <https://github.com/antopolskiy/kanban-md/releases/tag/v0.32.2> | MIT | TUI keyboard shortcuts, batch operations, compact output format | `.github/skills/kanban-md/SKILL.md` (TUI shortcuts section) | 2026-02-24 |
| kanban-md v0.33.0 "True North" release | <https://github.com/antopolskiy/kanban-md/releases/tag/v0.33.0> | MIT | `pick` self-contained output (prints full task details), `--no-body` flag, automatic ID consistency repair, malformed task detection | `.github/skills/kanban-md/SKILL.md` (pick command docs), `.github/skills/kanban-based-development/SKILL.md` (removed redundant show-after-pick) | 2026-02-26 |

## Copilot OAuth Research (Task #30)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Graphicator | `C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator` | (own project) | Device-flow OAuth (auth/copilot.py), agent factory routing (agents/__init__.py), provider config, editor headers, test patterns | `src/owlbear/auth/copilot.py`, `src/owlbear/providers/copilot.py` | 2026-02-26 |
| GitHub OAuth docs | <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow> | N/A | RFC 8628 device-flow spec, error codes (authorization_pending, slow_down, expired_token, access_denied), rate limits | `src/owlbear/auth/copilot.py` | 2026-02-26 |

## PydanticAI Integration Research (Tasks #37–#45)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI | <https://github.com/pydantic/pydantic-ai> | MIT | Agent class, messages.py, tools.py, providers/openai.py, FunctionToolset, TypeAdapter serialization | `src/owlbear/core/agent.py`, `src/owlbear/memory/session.py`, validation tests | 2026-02-26 |
| pydantic-deepagents | <https://github.com/vstorm-co/pydantic-deepagents> | MIT | HookEvent/HookRegistry pattern (middleware/hooks.py), SkillsToolset pattern, MEMORY.md persistence, agent factory anti-pattern | `src/owlbear/core/hooks.py` (adapted HookEvent/HookRegistry pattern) | 2026-02-26 |

## Teams Integration Research (Task #47)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| M365 Agents SDK (Python) | <https://github.com/microsoft/Agents-for-python> | MIT | Teams bot architecture, Activity model, migration from Bot Framework SDK | `docs/teams-integration-research.md` (comparison) | 2026-02-27 |
| M365 Agents SDK Migration Guide | <https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/bf-migration-python> | N/A | Package mapping, initialization patterns, Teams bot examples | `docs/teams-integration-research.md` (comparison) | 2026-02-27 |
| Microsoft Graph API — Teams notifications | <https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview> | N/A | Subscription model, webhook requirements, 60-min expiry | `docs/teams-integration-research.md` (real-time options analysis) | 2026-02-27 |
| Composio Microsoft Teams toolkit | <https://composio.dev/toolkits/microsoft_teams> | N/A | 180 Teams tools inventory, MCP gateway model, OAuth2 managed auth | `docs/teams-integration-research.md` (comparison) | 2026-02-27 |

## Slack Integration Research (Task #83)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | N/A | Socket Mode protocol: WebSocket connection, envelope acknowledgment, no public endpoint | `docs/slack-integration-research.md` (architecture analysis) | 2026-02-27 |
| Bolt for Python (slack_bolt) | <https://github.com/slackapi/bolt-python> | MIT | AsyncApp, SocketModeHandler, decorator patterns, AI Assistant class | `docs/slack-integration-research.md` (comparison) | 2026-02-27 |
| Python Slack SDK (slack_sdk) | <https://github.com/slackapi/python-slack-sdk> | MIT | SocketModeClient (aiohttp), AsyncWebClient, listener pattern | `docs/slack-integration-research.md` (recommendation), future `src/owlbear/channels/slack.py` | 2026-02-27 |
| slack_sdk Socket Mode docs | <https://docs.slack.dev/tools/python-slack-sdk/socket-mode> | N/A | Async SocketModeClient usage, aiohttp/websockets backends, event processing | `docs/slack-integration-research.md` (implementation approach) | 2026-02-27 |
| Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | MIT | Official AI assistant bot using Socket Mode, thread management, OpenAI integration | `docs/slack-integration-research.md` (prior art) | 2026-02-27 |

## Voice I/O Research (Task #49)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| faster-whisper | <https://github.com/SYSTRAN/faster-whisper> | MIT | CTranslate2-based Whisper reimplementation: 4x faster, int8 quantization, built-in Silero VAD, model size benchmarks (small CPU: 1m42s int8 vs 6m58s openai/whisper), no FFmpeg dependency | `docs/voice-io-research.md` (STT recommendation), future `src/owlbear/voice/stt.py` | 2026-02-27 |
| openai/whisper | <https://github.com/openai/whisper> | MIT | Reference Whisper implementation: model size table (tiny 39M → large 1550M), accuracy baselines, .en model variants for English-only use | `docs/voice-io-research.md` (model size comparison) | 2026-02-27 |
| pyttsx3 | <https://pypi.org/project/pyttsx3/> | MPL-2.0 | Offline TTS library: SAPI5 on Windows, eSpeak on Linux, AVSpeech on macOS, sync API (engine.say/runAndWait), voice and rate configuration | `docs/voice-io-research.md` (TTS recommendation), future `src/owlbear/voice/tts.py` | 2026-02-27 |
| Silero VAD | <https://github.com/snakers4/silero-vad> | MIT | Voice Activity Detection: <1ms per chunk on CPU, integrated into faster-whisper's vad_filter parameter, 6000+ language support | `docs/voice-io-research.md` (VAD strategy) | 2026-02-27 |
| SpeechRecognition | <https://pypi.org/project/SpeechRecognition/> | BSD-3 | Unified STT API wrapping Whisper, faster-whisper, Google, Vosk; PyAudio microphone abstraction; evaluated but not recommended (unnecessary abstraction layer) | `docs/voice-io-research.md` (comparison) | 2026-02-27 |
| PyAudio | <https://pypi.org/project/PyAudio/> | MIT | PortAudio Python bindings for cross-platform mic capture; prebuilt Windows wheels; supports WASAPI, DirectSound, WDM-KS | `docs/voice-io-research.md` (audio input recommendation), future `src/owlbear/voice/recorder.py` | 2026-02-27 |
| edge-tts | <https://github.com/rany2/edge-tts> | GPL-3.0 | Microsoft Edge online TTS: high-quality neural voices, async Python API; evaluated but not recommended for MVP (requires internet, violates offline-first principle) | `docs/voice-io-research.md` (TTS comparison) | 2026-02-27 |

## CDP Tab Groups Research (Task #65)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| CDP Target Domain (tip-of-tree) | <https://chromedevtools.github.io/devtools-protocol/tot/Target/> | N/A | Full Target domain spec: `createTarget` parameters, `TargetInfo` properties — confirmed no tab group support in CDP | `docs/cdp-tab-groups-research.md` (analysis) | 2026-02-27 |
| Chrome Extensions `tabGroups` API | <https://developer.chrome.com/docs/extensions/reference/api/tabGroups> | N/A | Tab group management API: `get`, `move`, `query`, `update` — only official way to manage tab groups | `docs/cdp-tab-groups-research.md` (analysis) | 2026-02-27 |
| Chrome Extensions `tabs.group()` | <https://developer.chrome.com/docs/extensions/reference/api/tabs#method-group> | N/A | `chrome.tabs.group()` — assigns tabs to groups, creates groups | `docs/cdp-tab-groups-research.md` (analysis) | 2026-02-27 |
| Puppeteer issue #13215 | <https://github.com/puppeteer/puppeteer/issues/13215> | N/A | Feature request for tab groups closed as "not planned" — confirms CDP limitation | `docs/cdp-tab-groups-research.md` (prior art) | 2026-02-27 |
| Playwright Chrome Extensions docs | <https://playwright.dev/python/docs/chrome-extensions> | N/A | Extension loading via `--load-extension`, persistent context requirement, Edge sideloading removal | `docs/cdp-tab-groups-research.md` (feasibility) | 2026-02-27 |

## Token Usage Tracking Research (Task #82)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI `pydantic_ai.usage` | <https://ai.pydantic.dev/api/usage/> | MIT | `RunUsage`/`RequestUsage` dataclasses, `RequestUsage.extract()` genai-prices integration, token fields (input, output, cache_write, cache_read), `total_tokens` property | `docs/token-usage-tracking-research.md` (analysis), future `src/owlbear/observability/usage.py` | 2026-02-27 |
| genai-prices (Pydantic) | <https://github.com/pydantic/genai-prices> | MIT | `calc_price()` API for LLM cost estimation, `Usage` dataclass, `UpdatePrices` background updater, provider/model coverage (900+ models, 30+ providers) | `docs/token-usage-tracking-research.md` (recommendation), future `src/owlbear/observability/cost.py` | 2026-02-27 |
| LiteLLM | <https://github.com/BerriAI/litellm> | MIT | `model_prices_and_context_window.json` comprehensive pricing DB, cost tracking patterns in proxy server | `docs/token-usage-tracking-research.md` (comparison, not adopted — too heavy) | 2026-02-27 |

## Knowledge Graph Research (Task #50)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| tool.graphicator | (own project) | — | SQLite + sqlite-vec knowledge graph: schema.py (DDL, freeze triggers), graph.py (CRUD), vectors.py (rowid_map bridge, similarity search), models.py (Pydantic records) | `src/owlbear/memory/knowledge/` (schema, graph, vectors, models adapted from db/ package) | 2026-02-27 |
| sqlite-vec | <https://github.com/asg017/sqlite-vec> | Apache-2.0/MIT | Vector search SQLite extension: vec0 virtual table, float/int8/binary vectors, metadata filtering, KNN queries | `src/owlbear/memory/knowledge/schema.py`, `src/owlbear/memory/knowledge/vectors.py` | 2026-02-27 |
| FastEmbed (Qdrant) | <https://github.com/qdrant/fastembed> | Apache-2.0 | Local ONNX-based embedding generation: TextEmbedding API, BAAI/bge-small-en-v1.5 default model (384-dim), no GPU needed | `src/owlbear/memory/knowledge/embeddings.py` | 2026-02-27 |
| nano-graphrag | <https://github.com/gusye1234/nano-graphrag> | MIT | Minimal GraphRAG (~1100 LOC): networkx graph + nano-vectordb, pluggable backends | `docs/knowledge-graph-research.md` (architecture comparison) | 2026-02-27 |
| LightRAG (HKUDS) | <https://github.com/HKUDS/LightRAG> | MIT | Full-featured GraphRAG: 4-storage-type architecture, networkx default graph, entity-relationship extraction | `docs/knowledge-graph-research.md` (architecture comparison) | 2026-02-27 |
