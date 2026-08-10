# Voice Addon Stdio Protocol Design

> **Owning task:** #49 — Implement voice addon stdio protocol
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #30 selected "standalone process with stdio pipes" as the v2 voice integration architecture. This research defines the concrete NDJSON protocol between owlbear and the voice addon — message types, framing, lifecycle management, and error handling — so the builder can implement without ambiguity.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | NDJSON spec v1.0.0 | <https://github.com/ndjson/ndjson-spec> | .95 — framing standard |
| 2 | JSON Lines spec | <https://jsonlines.org/> | .90 — complementary NDJSON spec |
| 3 | MCP stdio transport spec | <https://modelcontextprotocol.io/specification/2025-03-26/basic/transports> | .95 — gold-standard subprocess stdio protocol |
| 4 | MCP Python SDK stdio client | <https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/stdio.py> | .90 — subprocess lifecycle + shutdown sequence |
| 5 | ACP Python SDK `examples/client.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py> | .85 — asyncio subprocess spawn/terminate pattern |
| 6 | OwlBear ACP protocol research | `docs/research/acp-protocol.md` | .90 — our own NDJSON/stdio patterns |
| 7 | OwlBear ACP error handling | `docs/research/acp-error-handling-strategy.md` | .85 — crash detection + restart limits |
| 8 | v1 voice module | `v1/src/owlbear/voice/` | .90 — VoiceChannel, STT/TTS wrappers |

## 3. Analysis

### 3.1 Framing: NDJSON

All sources (1–6) converge on NDJSON framing for stdio IPC: one JSON object per line, UTF-8, `\n` terminated, no embedded newlines. This is the same format used by MCP, ACP, and our existing `JsonlStore`.

### 3.2 Protocol Complexity: Tagged Messages vs JSON-RPC

| Approach | KISS | Fits voice use case | Prior art | Score |
|----------|------|---------------------|-----------|-------|
| **A. Tagged messages** (`{"type":"..."}`) | High (.90) | Perfect — mostly fire-and-forget | Custom but trivial | .85 |
| **B. JSON-RPC 2.0** (request/response IDs) | Medium (.65) | Overkill — voice has no request/response | MCP, ACP (Sources 3, 6) | .55 |

JSON-RPC adds request IDs, method dispatching, and error codes — designed for bidirectional RPC. Voice is simpler: transcript lines flow one way, speak commands flow the other. Tagged messages with a `type` discriminator field (Pydantic tagged union) are sufficient and KISS-aligned.

### 3.3 Message Type Catalog

**Voice process → Owlbear (stdout):**

| Type | Fields | Purpose |
|------|--------|---------|
| `transcript` | `text: str`, `line_idx: int`, `final: bool` | Completed transcription line |
| `partial` | `text: str`, `line_idx: int` | Intermediate partial text (for live display) |
| `status` | `state: ready\|listening\|speaking\|idle\|shutdown` | Lifecycle state changes |
| `error` | `code: str`, `message: str` | Error reports (model load failure, device error) |

**Owlbear → Voice process (stdin):**

| Type | Fields | Purpose |
|------|--------|---------|
| `speak` | `text: str`, `interrupt: bool` | Synthesize and play text; interrupt cancels current speech |
| `config` | `settings: dict` | Runtime config updates (volume, rate, model) |
| `shutdown` | _(none)_ | Request graceful shutdown |

### 3.4 Lifecycle Management

Based on MCP SDK (Source 4) and ACP error handling (Source 7):

**Spawn:**
1. `asyncio.create_subprocess_exec("python", "-m", "owlbear_voice", stdin=PIPE, stdout=PIPE, stderr=PIPE)`
2. Inherit only safe env vars (MCP SDK pattern, Source 4)
3. Wait for `{"type":"status","state":"ready"}` with 30s timeout (init timeout from Source 7)

**Health check:** Voice process sends periodic `status` messages. Owlbear checks `proc.returncode is not None` before each write (ACP pattern, Source 5). No active heartbeat needed — process death is detected via broken pipe or returncode.

**Graceful shutdown** (MCP three-phase pattern, Source 4):
1. Send `{"type":"shutdown"}\n` on stdin
2. Close stdin (`proc.stdin.close()`)
3. `asyncio.wait_for(proc.wait(), timeout=5.0)` — wait for graceful exit
4. `proc.terminate()` if still alive
5. `asyncio.wait_for(proc.wait(), timeout=2.0)` — wait for SIGTERM
6. `proc.kill()` as last resort

**Restart limits:** Max 3 automatic restarts (ACP pattern, Source 7), then report failure to user.

### 3.5 Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| Process crash | `proc.returncode is not None`, EOF on stdout | Auto-restart (up to 3x) |
| Broken pipe (write) | `BrokenPipeError` on stdin write | Treat as crash, restart |
| Malformed JSON line | `json.JSONDecodeError` on stdout read | Log warning, skip line |
| Unknown message type | Pydantic validation error | Log warning, skip message |
| Init timeout | No `ready` status within 30s | Kill process, report error |
| Device unavailable | `error` message with `code: "device"` | Surface to user, no restart |

### 3.6 Architecture Fit

| Component | Location | Role |
|-----------|----------|------|
| Protocol models | `src/owlbear/voice/protocol.py` | Pydantic models with Literal type discriminator |
| Voice process manager | `src/owlbear/voice/process.py` | Spawn, lifecycle, read/write loops |
| VoiceChannel | `src/owlbear/voice/channel.py` | ChannelPlugin adapter wrapping process manager |
| Voice addon entry point | `src/owlbear_voice/__main__.py` | The subprocess itself (reads stdin, writes stdout) |

The `VoiceChannel` implements `ChannelPlugin` — `send()` writes `speak` messages to stdin, `receive()` reads `transcript` messages from stdout. The process manager runs asyncio read/write tasks. This mirrors v1's `VoiceChannel` (Source 8) but delegates ML work to the subprocess.

### 3.7 Pydantic Model Design

Use `Literal` discriminated unions for type-safe (de)serialization:

```python
# Tagged union: VoiceOutMessage = Annotated[TranscriptMsg | PartialMsg | StatusMsg | ErrorMsg, Field(discriminator="type")]
# TaggedUnion: VoiceInMessage = Annotated[SpeakMsg | ConfigMsg | ShutdownMsg, Field(discriminator="type")]
# Serialize: msg.model_dump_json() + "\n"
# Deserialize: TypeAdapter(VoiceOutMessage).validate_json(line)
```

This matches the `TypeAdapter` pattern used in `SessionStore` and `JsonlStore` (codebase Source 8).

## 4. Recommendation (.85 confidence)

**NDJSON-framed tagged messages with Pydantic discriminated unions.** The protocol is intentionally minimal (7 message types, no RPC overhead) and follows established patterns from MCP/ACP for subprocess lifecycle. Key design choices:

- NDJSON framing (not JSON-RPC) — KISS for fire-and-forget messaging
- Pydantic `Literal` discriminator for type-safe parsing (matches existing codebase patterns)
- MCP three-phase shutdown sequence (stdin close → SIGTERM → SIGKILL)
- Max 3 restart attempts before surfacing failure

**Risk:** The `partial` message type adds complexity for live display. If brainstorm mode is deferred, `partial` can be dropped and added later without protocol breaks.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement voice protocol Pydantic models" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nDefine the NDJSON protocol models for voice addon communication.\n\n## Acceptance Criteria\n- [ ] VoiceOutMessage union: transcript, partial, status, error (Literal discriminator)\n- [ ] VoiceInMessage union: speak, config, shutdown (Literal discriminator)\n- [ ] Serialize via model_dump_json(), deserialize via TypeAdapter.validate_json()\n- [ ] Located in src/owlbear/voice/protocol.py\n- [ ] Unit tests for round-trip serialization of all 7 message types\n\n## Context\nSee docs/research/voice-stdio-protocol.md S3.3 and S3.7"
kanban\kanban-md.exe create "Implement voice process manager" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nBuild the owlbear-side subprocess manager for the voice addon.\n\n## Acceptance Criteria\n- [ ] Spawn voice process via asyncio.create_subprocess_exec\n- [ ] Async read loop: parse NDJSON lines from stdout into VoiceOutMessage\n- [ ] Async write method: serialize VoiceInMessage to stdin\n- [ ] Three-phase shutdown: shutdown msg, close stdin, terminate, kill\n- [ ] Health check: detect process crash via returncode/EOF\n- [ ] Auto-restart up to 3 attempts\n- [ ] Init timeout: 30s wait for ready status\n- [ ] Unit tests with mocked subprocess\n\n## Context\nSee docs/research/voice-stdio-protocol.md S3.4-S3.5. Follow MCP SDK shutdown pattern."
kanban\kanban-md.exe create "Implement VoiceChannel adapter" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nBuild the ChannelPlugin adapter that wraps the voice process manager.\n\n## Acceptance Criteria\n- [ ] Implements ChannelPlugin protocol (name, send, receive)\n- [ ] send() writes speak message to voice process stdin\n- [ ] receive() reads next transcript message from voice process stdout\n- [ ] Lazy process spawn on first receive() call\n- [ ] Delegates lifecycle to VoiceProcessManager\n- [ ] Unit tests with mocked process manager\n\n## Context\nSee docs/research/voice-stdio-protocol.md S3.6. Mirrors v1 VoiceChannel pattern."
```
