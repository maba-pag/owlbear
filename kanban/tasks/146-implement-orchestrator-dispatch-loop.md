---
id: 146
title: Implement orchestrator dispatch loop
status: todo
priority: needed
created: 2026-03-29T16:23:47.2530291+02:00
updated: 2026-03-30T22:58:00.2187751+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 145
    - 19
class: standard
---

See docs/research/orchestrator-dispatch-loop.md for validated research.
See docs/research/build-dispatch-planner.md S3.2 for parent design.

## Acceptance Criteria

### waves.py — packages/orchestrator/src/owlbear/orchestrator/waves.py

- [ ] `AgentCategory` StrEnum: `AUDITOR`, `BUILDER`, `LIGHT_FLEX`, `HEAVY_FLEX` (4 values — auditor and builder are separate categories because the wave algorithm treats them differently in Phases 2 and 3)
- [ ] Module-level `AGENT_CATEGORY: dict[str, AgentCategory]` mapping:
  - `auditor` → `AUDITOR`
  - `builder` → `BUILDER`
  - light_flex: `researcher`, `writer`, `architect`, `kanban-planner`, `curator`
  - heavy_flex: `reviewer`, `test-writer`
- [ ] `Wave` — `@dataclasses.dataclass` (mutable, not frozen): `entries: list[DispatchEntry] = field(default_factory=list)`. Mutable because Phase 5 (curator injection) appends to entries in-place.
- [ ] `def assemble_waves(entries: list[DispatchEntry], *, wave_size: int = 4, cycle: int) -> list[Wave]`
  - Four-bucket algorithm per orchestration skill Steps 1-7:
    1. Bucket sort entries by AGENT_CATEGORY
    2. Auditor waves: 1 auditor + fill remaining slots with light flex (priority order)
    3. Builder waves: 1 builder + fill with light flex first, then heavy flex (priority order)
    4. Overflow waves: remaining flex agents, up to wave_size per wave
    5. Periodic curator: every 5th cycle (cycle % 5 == 0), add curator DispatchEntry to last wave with free slot; skip if all full
    6. Consolidation: SKIP (deactivated per skill doc)
    7. Drop rule: solo non-auditor waves dropped; exception: keep first non-auditor wave if dropping would eliminate all
  - Pure function — no I/O, no side effects
  - Returns `list[Wave]` in dispatch order

### loop.py — packages/orchestrator/src/owlbear/orchestrator/loop.py

- [ ] Module-level `AGENT_PROMPT_PREFIX: dict[str, str]`:
  - architect: "Architect Review", builder: "Build", reviewer: "Review", test-writer: "Write tests", researcher: "Research", writer: "Docs Gate", auditor: "Audit", kanban-planner: "Plan", curator: "Curate: Periodic curation"
- [ ] `def format_prompt(entry: DispatchEntry) -> str`
  - Returns `"{prefix}: #{task_id}"` using AGENT_PROMPT_PREFIX
  - If `entry.retry_hint` is truthy, appends `"\nRetry context: {entry.retry_hint}"`
  - Curator exception: returns prefix string only (no `: #{task_id}` appended)
- [ ] `@dataclass(frozen=True)` `CycleResult`:
  - `successes: list[int]` — task IDs where agent returned normally
  - `failures: list[int]` — task IDs where agent crashed twice
  - `rate_limited: bool` — True if any dispatch hit rate limit in this cycle
- [ ] `@dataclass` `LoopState`:
  - `stale_retried: set[int]` — task IDs dispatched with retry_hint (tracked cross-cycle)
  - `sequential_remaining: int = 0` — rate-limit sequential counter
  - `crash_failures: set[int]` — task IDs that crashed twice (passed to planner next cycle)
  - `cycle: int = 0` — cycle counter for curator scheduling
- [ ] `async def dispatch_entry(entry: DispatchEntry, client: AcpClient) -> bool`
  - Creates new session via `client.new_session(cwd=..., mcp_servers=[])`
  - Sends prompt via `client.prompt(session_id=..., prompt=[text_block(format_prompt(entry))])`
  - Returns True on success, False on AcpClientError or TimeoutError
  - Does NOT retry — caller handles retry
- [ ] `async def dispatch_wave(wave: Wave, client: AcpClient, state: LoopState) -> CycleResult`
  - If `state.sequential_remaining > 0`: dispatch entries one-by-one, decrement counter each
  - Otherwise: dispatch entries in parallel via `asyncio.gather(return_exceptions=True)`
  - Error handling per entry:
    - Rate-limit detection: error message contains "rate-limited", "rate_limited", or "rate limits" — set `state.sequential_remaining = 3`, mark rate_limited=True
    - Non-rate-limit error: retry once; if second crash, record as failure
  - Returns CycleResult
- [ ] `async def run_loop(kanban_bin: Path, kanban_dir: Path, client: AcpClient, *, scope: str | None = None) -> None`
  - Testable loop core (client injected for mocking)
  - Loop: read_board() (#144) then select_tasks() (#145) then assemble_waves() then dispatch_wave() per wave then re-plan
  - Stops when DispatchPlan.entries is empty
  - Pre-filters crash_failures from task list before calling select_tasks(): `select_tasks([t for t in tasks if t.id not in state.crash_failures])` — avoids interface changes to #145's selector
  - stale_retried tracked in LoopState for logging only (not passed to select_tasks)
  - Forwards `scope` parameter to read_board()
  - Increments LoopState.cycle each iteration
  - Uses Python `logging` module: log each dispatch (task_id, agent, wave#) and each cycle summary (successes, failures count)
- [ ] `async def orchestrate(kanban_bin: Path, kanban_dir: Path, copilot_cmd: list[str], *, scope: str | None = None) -> None`
  - Public entry point — wires ProcessSupervisor and AcpClient, then delegates to run_loop
  - Creates ProcessSupervisor(copilot_cmd) as async context manager
  - ensure_running() to get (stdin, stdout) streams
  - connect_to_agent(callback_client, stdin, stdout) to get ClientSideConnection
  - AcpClient(conn) wraps connection
  - client.initialize(protocol_version=PROTOCOL_VERSION) before entering loop
  - Calls run_loop(kanban_bin, kanban_dir, client, scope=scope)
  - Calls supervisor.mark_healthy() after successful dispatches
  - Minimal Client subclass for ACP callbacks following hello_world.py pattern (session_update stub, permission denied, ext_method stubs)

### DispatchEntry model extension

- [ ] Add `retry_hint: str = ""` field to DispatchEntry in planner/models.py (one-line addition to existing frozen Pydantic model; default empty preserves backward compat)

### __init__.py — packages/orchestrator/src/owlbear/orchestrator/__init__.py

- [ ] Module docstring, public imports: orchestrate, run_loop, assemble_waves, format_prompt, Wave, LoopState, CycleResult

### Patterns to follow

- Subprocess: ProcessSupervisor (owlbear_orchestrator/process_supervisor.py)
- AcpClient: existing wrapper (owlbear_orchestrator/acp_client.py)
- Error classification: AcpClientError.category (ErrorCategory enum)
- Frozen models: ConfigDict(frozen=True) per planner/models.py
- Errors: OwlBearError base from owlbear.errors
- ACP lifecycle: hello_world.py connect_to_agent pattern (initialize, new_session, prompt)
- Board reading: owlbear.planner.read_board (from #144)
- Task selection: owlbear.planner select_tasks (from #145, depends_on)

[[2026-03-30]] Mon 08:25
## Architecture Review
See docs/scratch/146-architect.md for full review.
Verdict: REFINE. AC rewritten with precise function signatures. Test task #208 created at todo. depends_on updated to include #208.

[[2026-03-30]] Mon 22:51
## Architecture Review (cycle 2)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AgentCategory: RESTRICTED (3 values) | Wrong: Phases 2-3 treat auditor/builder separately | Fixed: 4 values (AUDITOR, BUILDER, LIGHT_FLEX, HEAVY_FLEX) |
| AGENT_CATEGORY restricted grouping | Misleading: auditor+builder not interchangeable | Fixed: separate entries |
| Wave frozen Pydantic BaseModel | Wrong: Phase 5 mutates entries (curator append) | Fixed: mutable @dataclasses.dataclass |
| writer prefix "Docs" | Should match docs-gate skill naming | Fixed: "Docs Gate" |
| crash_failures/stale_retried to select_tasks | Interface mismatch with #145's selector | Fixed: pre-filter crash_failures from task list |
| scope param forwarding | Not explicitly noted | Added: "Forwards scope to read_board()" |
| All other AC lines | Precise and testable | Kept |

### Architecture Notes
- Layering OK: waves.py imports planner.models; loop.py imports waves, planner.board, planner.selector, owlbear_orchestrator.acp_client
- Single domain: scope:orchestrator
- Existing impl from #208 TDD covers waves.py + loop.py (100% coverage). Builder finalizes: orchestrate(), __init__.py exports, scope forwarding, logging.
- Wave as mutable dataclass is correct KISS for Phase 5 in-place mutation.
- Pre-filtering crash_failures avoids cross-task interface pollution on #145.

### Changes Made
- Fixed AgentCategory: 4 enum values
- Fixed AGENT_CATEGORY mapping: auditor/builder separate
- Fixed Wave: mutable dataclass not frozen Pydantic
- Fixed writer prefix: "Docs Gate"
- Fixed run_loop: pre-filter crash_failures, scope forwarding
- Approved to todo

### Dependencies
- #19 (ACP client) archived
- #145 (planner gate checker) in-progress, correctly blocks builder phase
- #208 (TDD RED tests) at review, 51 tests, 100% coverage
