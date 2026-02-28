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

## Terminal Tool Research (Task #121)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Python asyncio subprocess docs | <https://docs.python.org/3/library/asyncio-subprocess.html> | PSF | `create_subprocess_shell` API, `communicate()` + `wait_for()` timeout pattern, process cleanup on timeout | `docs/terminal-tool-research.md` (implementation approach), future `src/owlbear/tools/terminal.py` | 2026-02-27 |
| OpenHands ActionExecutor | <https://github.com/All-Hands-AI/OpenHands> | MIT | `CmdRunAction` → `CmdOutputObservation` pattern: structured command results with exit codes, BashSession management | `docs/terminal-tool-research.md` (prior art comparison) | 2026-02-27 |
| Aider run_cmd | <https://github.com/Aider-AI/aider> | Apache-2.0 | Shell command execution with `subprocess.run`, token-aware output handling, git/test/lint command patterns | `docs/terminal-tool-research.md` (prior art comparison) | 2026-02-27 |

## Embedding & Vector DB Research (Tasks #232–#239)

### Papers & Academic Sources

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Cormack et al. (2009) — RRF paper | <https://dl.acm.org/doi/10.1145/1571941.1572114> | N/A | Original Reciprocal Rank Fusion algorithm: `1/(k+rank)`, k=60, outperforms Condorcet and individual rank learning on TREC | `docs/dual-embedding-rrf-research.md` (RRF formula and analysis) | 2026-02-28 |
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | N/A | Single model producing dense (1024-d) + sparse + ColBERT; self-knowledge distillation; MIRACL/MLDR/NarrativeQA benchmarks; ColBERT reranking quality tables | `docs/dual-embedding-rrf-research.md`, `docs/graph-augmented-retrieval-research.md`, `docs/bge-m3-integration-research.md`, `docs/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| Wang et al. 2024 "Best Practices in RAG" | <https://arxiv.org/abs/2407.01219> | N/A | RAG pipeline analysis with retrieval + reranking strategy recommendations | `docs/retrieve-rerank-research.md` (prior art) | 2026-02-28 |

### Embedding Model Cards (HuggingFace)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| BAAI/bge-m3 | <https://huggingface.co/BAAI/bge-m3> | MIT | Multi-functionality (dense+sparse+ColBERT), 8192 tokens, FP16/FP32 CPU behavior, ONNX file tree (dense-only ONNX, .pt linear heads) | `docs/dual-embedding-rrf-research.md`, `docs/retrieve-rerank-research.md`, `docs/graph-augmented-retrieval-research.md`, `docs/bge-m3-integration-research.md` | 2026-02-28 |
| BAAI/bge-large-en-v1.5 | <https://huggingface.co/BAAI/bge-large-en-v1.5> | MIT | MTEB scores (64.23 avg, 54.29 retrieval), 335M params, 1024d, ONNX available | `docs/retrieve-rerank-research.md` (comparison) | 2026-02-28 |
| BAAI/bge-reranker-v2-m3 | <https://huggingface.co/BAAI/bge-reranker-v2-m3> | Apache-2.0 | Cross-encoder specs (568M params), BEIR NDCG@10 (54.17), MIRACL reranking eval | `docs/retrieve-rerank-research.md`, `docs/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| snowflake-arctic-embed-l | <https://huggingface.co/Snowflake/snowflake-arctic-embed-l> | Apache-2.0 | Best BEIR retrieval score (55.98) among FastEmbed models, 335M params, 1024d, purpose-built for retrieval | `docs/embedding-model-shootout.md` (recommendation) | 2026-02-28 |
| mxbai-embed-large-v1 | <https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1> | Apache-2.0 | Best overall MTEB average (64.68), Matryoshka + binary quantization support, 335M, 1024d | `docs/embedding-model-shootout.md` (runner-up) | 2026-02-28 |
| nomic-embed-text-v1.5 | <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5> | Apache-2.0 | Matryoshka dims (64–768), 8192 context, 137M params, MTEB avg 62.28 | `docs/dual-embedding-rrf-research.md`, `docs/retrieve-rerank-research.md`, `docs/embedding-model-shootout.md` | 2026-02-28 |
| gte-large-en-v1.5 | <https://huggingface.co/Alibaba-NLP/gte-large-en-v1.5> | MIT | 8192 tokens, 409M params, 1024d, best retrieval (57.91) of any feasible model, custom architecture | `docs/embedding-model-shootout.md` (deferred) | 2026-02-28 |
| jina-embeddings-v3 | <https://huggingface.co/jinaai/jina-embeddings-v3> | CC-BY-NC-4.0 | 0.6B params, CC-BY-NC-4.0 license confirmed (non-commercial only), not in FastEmbed | `docs/retrieve-rerank-research.md`, `docs/embedding-model-shootout.md` | 2026-02-28 |
| e5-mistral-7b-instruct | <https://huggingface.co/intfloat/e5-mistral-7b-instruct> | MIT | 7B params, 4096d, infeasible on 16 GB RAM (FP16 ≈ 14 GB), no ONNX | `docs/embedding-model-shootout.md` (disqualified) | 2026-02-28 |
| MTEB Leaderboard | <https://huggingface.co/spaces/mteb/leaderboard> | N/A | Third-party benchmark scores for embedding models (MTEB avg, BEIR retrieval nDCG@10) | `docs/embedding-model-shootout.md` (benchmarks) | 2026-02-28 |

### Reranker Model Cards

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| jina-reranker-v2-base-multilingual | <https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual> | CC-BY-NC-4.0 | 278M params, BEIR/MIRACL benchmarks (54.83 NDCG@10), CC-BY-NC-4.0 license restriction | `docs/retrieve-rerank-research.md` (comparison) | 2026-02-28 |
| cross-encoder/ms-marco-MiniLM-L-12-v2 | <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2> | Apache-2.0 | 33M param lightweight reranker, MS Marco TREC DL'19 (74.31), MRR@10 (39.02) | `docs/retrieve-rerank-research.md` (comparison) | 2026-02-28 |

### Vector Database & Retrieval Tools

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| qdrant-client (v1.17.0) | <https://github.com/qdrant/qdrant-client> | Apache-2.0 | Local mode (QdrantLocal), brute-force numpy, persistence (SQLite+pickle), portalocker locking, 20K threshold, congruence tests | `docs/qdrant-local-research.md`, `docs/qdrant-local-features-research.md` | 2026-02-28 |
| Qdrant vectors docs | <https://qdrant.tech/documentation/concepts/vectors> | N/A | Named vectors, sparse vectors, multivectors (ColBERT MAX_SIM) | `docs/qdrant-local-research.md` | 2026-02-28 |
| Qdrant hybrid queries docs | <https://qdrant.tech/documentation/concepts/hybrid-queries> | N/A | Prefetch, RRF/DBSF fusion, multi-stage queries | `docs/qdrant-local-research.md` | 2026-02-28 |
| Qdrant "Hybrid Search Revamped" article | <https://qdrant.tech/articles/hybrid-search> | N/A | ColBERT HNSW optimization (m=0), prefetch→ColBERT rescore pattern, fusion vs reranking comparison | `docs/qdrant-local-research.md`, `docs/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| Qdrant late-interaction article | <https://qdrant.tech/articles/late-interaction-models/> | N/A | BEIR late-interaction benchmarks, ColBERT quantization impact, output-token reranking | `docs/colbert-vs-crossencoder-research.md` | 2026-02-28 |
| Azure AI Search — RRF docs | <https://learn.microsoft.com/azure/search/hybrid-search-ranking> | N/A | Production RRF implementation: parallel query execution, k=60, weighted fusion, score decomposition | `docs/dual-embedding-rrf-research.md` (prior art) | 2026-02-28 |
| Milvus multi-vector hybrid search | <https://milvus.io/docs/multi-vector-search.md> | N/A | Dense + sparse + RRF in production: `AnnSearchRequest`, `RRFRanker`, BGE-M3 example | `docs/dual-embedding-rrf-research.md` (prior art) | 2026-02-28 |
| FastEmbed supported models | <https://qdrant.github.io/fastembed/examples/Supported_Models/> | Apache-2.0 | Full ONNX model inventory (dense, sparse SPLADE++, late-interaction ColBERT, rerankers) with sizes; bge-m3 absent from all lists | `docs/embedding-model-shootout.md`, `docs/dual-embedding-rrf-research.md`, `docs/retrieve-rerank-research.md`, `docs/graph-augmented-retrieval-research.md`, `docs/bge-m3-integration-research.md` | 2026-02-28 |

### Integration Samples & GitHub Repos

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| bge-m3-qdrant-sample | <https://github.com/yuniko-software/bge-m3-qdrant-sample> | N/A | Full bge-m3 + Qdrant integration: collection creation, embedding, named vectors, hybrid search | `docs/qdrant-local-research.md`, `docs/bge-m3-integration-research.md` | 2026-02-28 |
| workshop-ultimate-hybrid-search | <https://github.com/qdrant/workshop-ultimate-hybrid-search> | N/A | Official Qdrant hybrid search evaluation workshop | `docs/qdrant-local-research.md` | 2026-02-28 |
| FlagEmbedding (v1.3.5) | <https://github.com/FlagOpen/FlagEmbedding> | MIT | M3Embedder/BGEM3FlagModel code analysis: constructor behavior (NOT lazy), encode() internals, sparse/ColBERT processing, FP16 CPU auto-disable, dependency chain | `docs/bge-m3-integration-research.md` | 2026-02-28 |
| FastEmbed issue #107 (bge-m3 support) | <https://github.com/qdrant/fastembed/issues/107> | N/A | 2+ year open issue; maintainer confirmed sparse/ColBERT heads need ONNX export | `docs/bge-m3-integration-research.md` | 2026-02-28 |
| FastEmbed PR #602 (bge-m3 dense only) | <https://github.com/qdrant/fastembed/pull/602> | N/A | Feb 2026 PR adding dense-only ONNX bge-m3 embedding, no sparse/ColBERT, no reviewer | `docs/bge-m3-integration-research.md` | 2026-02-28 |
| RAG-Fusion | <https://github.com/Raudaschl/rag-fusion> | N/A | Multi-query + RRF pattern: generate query variants, search each, fuse results | `docs/dual-embedding-rrf-research.md` (prior art) | 2026-02-28 |
| Microsoft GraphRAG | <https://microsoft.github.io/graphrag/query/local_search> | MIT | Local Search entity expansion pattern: embed query → find entities → fan out to neighbors, community reports → prioritize → fill context window | `docs/graph-augmented-retrieval-research.md` (prior art, architecture) | 2026-02-28 |
| neo4j-graphrag-python | <https://github.com/neo4j/neo4j-graphrag-python> | Apache-2.0 | VectorCypherRetriever pattern: vector search → Cypher graph traversal → collect neighbor data → merge into context | `docs/graph-augmented-retrieval-research.md` (prior art) | 2026-02-28 |
| SBERT Retrieve & Re-Rank guide | <https://www.sbert.net/examples/applications/retrieve_rerank/> | N/A | Canonical bi-encoder + cross-encoder architecture description, quality hierarchy (cross-encoder > ColBERT > bi-encoder) | `docs/retrieve-rerank-research.md`, `docs/colbert-vs-crossencoder-research.md` | 2026-02-28 |

## Moonshine Voice Research (Task #240)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | MIT | STT engine with native streaming (ergodic encoder), OnnxRuntime C++ backend, Python/Swift/Java bindings, Tiny–Medium model range (26M–245M), bundled native .dll/.so | `docs/moonshine-vs-whisper-research.md` (recommendation) | 2026-02-28 |
| Moonshine v2 paper | <https://arxiv.org/abs/2602.12241> | N/A | Ergodic streaming encoder architecture, sliding-window attention, benchmark methodology | `docs/moonshine-vs-whisper-research.md` (architecture analysis) | 2026-02-28 |
| Moonshine v1 paper | <https://arxiv.org/abs/2410.15608> | N/A | First-gen flexible-duration input (no fixed 30s Whisper window) | `docs/moonshine-vs-whisper-research.md` (architecture analysis) | 2026-02-28 |
| Flavors of Moonshine paper | <https://arxiv.org/abs/2509.02523> | N/A | Language-specific mono-lingual models, per-language accuracy analysis | `docs/moonshine-vs-whisper-research.md` (analysis) | 2026-02-28 |
| HuggingFace OpenASR Leaderboard | <https://huggingface.co/spaces/hf-audio/open_asr_leaderboard> | N/A | Independent WER scoring methodology for STT models, English benchmark standard | `docs/moonshine-vs-whisper-research.md` (benchmark verification) | 2026-02-28 |
| whisper.cpp (ggml-org) | <https://github.com/ggml-org/whisper.cpp> | MIT | C/C++ Whisper implementation, quantization (Q5_0), AVX2 optimization, Vulkan GPU support, stream example | `docs/moonshine-vs-whisper-research.md` (comparison) | 2026-02-28 |

## Knowledge Pipeline Framework Research (Task #262)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LlamaIndex | <https://github.com/run-llama/llama_index> | MIT | Full RAG framework; PropertyGraphIndex; Qdrant integration; document management; embedding integrations; 300+ integration packages | `docs/knowledge-pipeline-research.md` (comparison matrix) | 2026-02-28 |
| Cognee | <https://github.com/topoteretes/cognee> | Apache 2.0 | Knowledge engine with KG+vector; EmbeddingEngine Protocol pattern; task pipeline architecture; provenance tracking (source_pipeline/source_task); Kuzu embedded graph DB; ontology resolution; cloned to `docs/research/cognee/` for deep analysis | `docs/knowledge-pipeline-research.md` (comparison matrix, provenance pattern recommendation) | 2026-02-28 |
| Microsoft GraphRAG | <https://github.com/microsoft/graphrag> | MIT | Graph enrichment pipeline; community detection (Leiden algorithm); hierarchical summaries; global search patterns; v3 modular packages | `docs/knowledge-pipeline-research.md` (comparison matrix, community detection recommendation) | 2026-02-28 |
| txtai | <https://github.com/neuml/txtai> | Apache 2.0 | All-in-one embeddings DB; graph module (NetworkX); topic modeling via community detection; config-driven graph building; embedding-similarity edges | `docs/knowledge-pipeline-research.md` (comparison matrix, config-driven graph pattern) | 2026-02-28 |
| Haystack (deepset) | <https://github.com/deepset-ai/haystack> | Apache 2.0 | Pipeline orchestrator; Component protocol design; `qdrant-haystack` integration; typed input/output pipeline validation; DocumentStore abstraction | `docs/knowledge-pipeline-research.md` (comparison matrix, component protocol validation) | 2026-02-28 |
| R2R (SciPhi) | <https://github.com/SciPhi-AI/R2R> | MIT | Server-based RAG system; REST API architecture; knowledge graph features; eliminated due to server-only architecture | `docs/knowledge-pipeline-research.md` (elimination analysis) | 2026-02-28 |
| Unstructured.io | <https://github.com/Unstructured-IO/unstructured> | Apache 2.0 | Document processing library; 130+ format support; eliminated — intake layer only | `docs/knowledge-pipeline-research.md` (elimination analysis) | 2026-02-28 |

## Bootstrap/Assembly Research (Task #263)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Nanobot (deep read) | <https://github.com/HKUDS/nanobot> | MIT | Startup wiring sequence (gateway command), MessageBus pattern, ChannelManager config-driven init, ContextBuilder system prompt assembly, MemoryStore two-layer consolidation (MEMORY.md + HISTORY.md via LLM tool call), SessionManager JSONL + last_consolidated pointer | `docs/bootstrap-assembly-research.md` (analysis), future `src/owlbear/bootstrap.py`, future `src/owlbear/memory/consolidation.py`, future `src/owlbear/channels/manager.py` | 2026-02-28 |

## Browser Automation Research (Task #264)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| browser-use (v0.12.0) | <https://github.com/browser-use/browser-use> | MIT | CDP `cdp_url` parameter, `channel: 'msedge'`, `enable_default_extensions`, AI browser agent architecture | `docs/browser-automation-research.md` (comparison) | 2026-02-28 |
| crawl4ai (v0.8.0) | <https://github.com/unclecode/crawl4ai> | Apache 2.0 | `BrowserConfig.cdp_url`, `browser_mode` enum, deep crawl strategies (BFS/DFS + crash recovery), prefetch mode | `docs/browser-automation-research.md` (comparison) | 2026-02-28 |
| Stagehand (v3.6.1) | <https://github.com/browserbase/stagehand> | MIT | AI browser automation framework, TypeScript-first, Browserbase cloud service dependency — eliminated | `docs/browser-automation-research.md` (comparison) | 2026-02-28 |
| readabilipy (v0.3.0) | <https://pypi.org/project/readabilipy/> | MIT | Mozilla Readability.js Python wrapper, Node.js dependency | `docs/browser-automation-research.md` (content extraction comparison) | 2026-02-28 |

## Moonshine Streaming Research (Task #246)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Moonshine Voice (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | MIT | Transcriber/Stream/MicTranscriber Python API, event model (LineStarted/LineTextChanged/LineCompleted), VAD integration, ModelArch enum, audio format requirements, session lifecycle | `docs/moonshine-streaming-research.md`, future `src/owlbear/voice/stt.py`, future `src/owlbear/voice/streaming_stt.py` | 2026-02-28 |

## Content Hashing Research (Task #253)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| LangChain indexing API | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/indexing/api.py> | MIT | Content+metadata dual hashing (SHA-1/SHA-256), RecordManager pattern, cleanup modes (incremental/full/scoped_full), `_get_document_with_hash()`, `IndexingResult` tracking | `docs/content-hashing-research.md` (comparison), future `src/owlbear/memory/knowledge/ingest.py` (delta re-ingest pattern) | 2026-02-28 |
| LlamaIndex IngestionPipeline | <https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/> | MIT | `doc_id → document_hash` map in docstore, duplicate detection, skip-if-unchanged pattern, IngestionCache for node+transformation hashing | `docs/content-hashing-research.md` (comparison) | 2026-02-28 |
| LightRAG (content hashing) | <https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py> | MIT | MD5 content-addressed document IDs, DocStatusStorage (PENDING→PROCESSING→PROCESSED/FAILED), `adelete_by_doc_id()` comprehensive deletion cascade (chunks → entities → relationships → rebuild affected graph), duplicate detection via `full_docs.filter_keys()` | `docs/content-hashing-research.md` (deletion pattern, comparison) | 2026-02-28 |

## Intra-Document Graph Builder Research (Task #255)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| Microsoft GraphRAG (Edge et al.) | <https://arxiv.org/abs/2404.16130> | N/A | Entity merge + description summarization pattern; cross-chunk consolidation | `docs/intra-document-graph-research.md`, future `src/owlbear/memory/knowledge/graph_builder.py` | 2026-02-28 |
| MS GraphRAG Dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow> | MIT | 6-phase indexing pipeline architecture | `docs/intra-document-graph-research.md` | 2026-02-28 |
| LlamaIndex PropertyGraphIndex | <https://developers.llamaindex.ai/docs/llamaindex/module_guides/indexing/lpg_index_guide> | MIT | SchemaLLMPathExtractor, constrained extraction | `docs/intra-document-graph-research.md` | 2026-02-28 |
| nano-graphrag (intra-doc patterns) | <https://github.com/gusye1234/nano-graphrag> | MIT | Minimal extract-merge-summarize pattern (~1100 LOC) | `docs/intra-document-graph-research.md` | 2026-02-28 |
