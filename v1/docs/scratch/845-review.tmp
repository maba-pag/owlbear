## Architecture Review
**Verdict:** APPROVED (with refinement below)

### Dependency Update Needed
depends_on frontmatter must be updated to include 1003 (test task). kanban-md edit does not support --depends-on. Builder or test-writer should update the YAML frontmatter.

### AC Assessment
- Original AC1 (poll_tick calls record): Vague, replaced with precise params
- Original AC2 (usage accumulator or wrapper): Decision made by research (Option A), replaced
- Original AC3 (existing tests pass): Kept as AC7
- Researcher AC1 (tracker/provider on poll_tick/poll_loop): Missing model param, refined
- Researcher AC2 (thread from run_daemon): Missing chat_model, refined
- Researcher AC3 (record in _run_builder_with_context): Missing session_id pin, refined
- Researcher AC4 (both call sites): Clear, kept
- Researcher AC5 (existing tests + new tests): Mixed impl and test concerns, split

### Refined AC (replaces original and researcher AC)
1. _run_builder_with_context accepts new params tracker (UsageTracker or None, default None), model (str, default ""), provider (str, default "copilot"). Existing callers unaffected by defaults.
2. After awaiting the builder result in the normal (kwargs-accepted) code path, record_agent_usage is called with tracker, result, model, provider, session_id "background:builder_dispatch", operation "builder_dispatch".
3. After awaiting the builder result in the TypeError-fallback code path, the same record_agent_usage call is made with identical arguments.
4. poll_tick accepts new params tracker (UsageTracker or None, default None), model (str, default ""), provider (str, default "copilot") and threads them to both the retry-dispatch and fresh-dispatch _run_builder_with_context call sites.
5. poll_loop accepts tracker (UsageTracker or None, default None) and provider (str, default "copilot") and threads them plus settings.chat_model as model to poll_tick.
6. run_daemon passes agent.tracker and settings.provider and settings.chat_model to poll_loop at the existing call site.
7. All pre-existing daemon tests pass unchanged.

### TDD Compliance
- Created 1003 (Test: Track LLM usage in daemon poll_tick builder dispatch) at ideation.
- 845 depends on 1003 (dependency needs frontmatter update).

### Architecture Notes
- Single domain: daemon dispatch (scope:core). No multi-domain concern.
- Module layering: daemon.py (application) imports from owlbear.memory.usage (memory layer). Direction is valid (downward).
- Pattern: follows 844 condenser pattern at src/owlbear/core/condenser.py L88-100 exactly.
- Security surface: no new system boundaries. record_agent_usage swallows its own exceptions.
- Interface: _run_builder_with_context is a private module function. Signature change is safe.
- Both code paths in _run_builder_with_context return coroutines. Recording must happen inside _await_run wrapper after awaiting, not outside.
- Import: record_agent_usage from owlbear.memory.usage. UsageTracker under TYPE_CHECKING only.

### Failure Mode Map
- record_agent_usage inside _await_run: JSONL write fails. Swallowed by record_agent_usage. Usage record lost, builder result unaffected.
- record_agent_usage with None tracker: No-op. No impact.

### Changes Made
- Created 1003 (test task) at ideation
- Appended architecture review with refined AC to 845
- depends_on 1003 needs frontmatter update (kanban-md limitation)