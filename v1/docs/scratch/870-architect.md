## Architecture Review
__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Add cancellation.py with CancelSignal protocol + LinkedCancelSignal in memory/knowledge/ | Precise. Module does not exist yet. Protocol shape (is_set() -> bool) is explicit. Placement respects YAGNI — only knowledge consumers today. | Approved as written. |
| 2. Thread optional cancel through refresh, refresh_all, _ingest_items, crawl_and_ingest, ingest, ingest_text, _ingest_from_intake, _run_extract, BookmarkPipeline.process | Precise. refresh() and ingest() lack cancel today. refresh_all, _ingest_items, and crawl_and_ingest have cancel but do not thread it to downstream calls yet. The listed surfaces are exactly the gaps. | Approved as written. |
| 3. Check cancel.is_set() at source/item/page/chunk/stage boundaries; return partial work | Precise and mechanically testable. Existing boundary checks in refresh_all, _ingest_items, crawl_and_ingest, _run_extract, BookmarkPipeline.process follow this pattern already for a subset. | Approved as written. |
| 4. Do not catch or translate outer asyncio.CancelledError | Precise. _ingest_from_intake already re-raises CancelledError from _run_extract via asyncio.gather. Builder must preserve this and not introduce new catch sites. | Approved as written. |
| 5. Compose only in RetrospectiveHook daemon-owned path; tool paths stay #877 | Precise scope boundary. See Architecture Notes for bootstrap wiring guidance. | Approved with notes. |
| 6. All #880 tests pass; builder-discovered coverage stays in listed test modules | Clear gate with file-scope restriction. | Approved as written. |

### Architecture Notes

**Module layering for LinkedCancelSignal instantiation.**
CancelSignal protocol and LinkedCancelSignal in memory/knowledge/cancellation.py is correct. However, core/retrospective_hook.py cannot import from memory/ at runtime per architecture standards. The composition site for AC 5 should be bootstrap/__init__.py (_wire_post_model_hooks), which can import from all layers. Concretely:

- _wire_post_model_hooks() needs to accept shutdown_event (currently not passed).
- Bootstrap creates LinkedCancelSignal(shutdown_event) and passes it to RetrospectiveHook.__init__ as a pre-composed cancel signal.
- RetrospectiveHook stores the signal and forwards it to ingest_text() calls.
- RetrospectiveHook imports CancelSignal only under TYPE_CHECKING for annotation.
- Note: retrospective_hook.py already has a runtime import from memory.usage (record_agent_usage) — a pre-existing layering bend in this boundary module. Prefer the bootstrap injection approach over adding another core->memory runtime import.

**shutdown_event temporal ordering.**
shutdown_event is created inside run_daemon() in daemon.py, AFTER bootstrap() returns. Two viable approaches: (a) create shutdown_event earlier in the CLI command/daemon setup and pass it through bootstrap, or (b) have run_daemon() post-inject it into the hook via a setter. Approach (a) is cleaner — pass shutdown_event as a kwarg through bootstrap -> _wire_post_model_hooks -> RetrospectiveHook.

**Type annotation migration.**
Existing cancel: asyncio.Event | None annotations (added by #880's builder) should migrate to cancel: CancelSignal | None. asyncio.Event satisfies the protocol via is_set(), so all #880 tests continue to pass with the type change.

**Internal method threading.**
AC 2 lists top-level surfaces. Internal handlers (_handle_url_list, _handle_file_glob, _handle_crawl) also need cancel threaded to _ingest_items; this is implied by the refresh -> _ingest_items chain and does not require separate AC.

**Existing patterns.**
GraphEnricher in memory/knowledge/enrichment.py owns _background_tasks + Semaphore — local precedent for task-set ownership. The CancelSignal protocol is complementary (polling at loop boundaries) not overlapping.

**Failure mode map.**
CancelSignal.is_set() is a pure read with no exception risk. No new failure modes introduced — the cancel check is best-effort cooperative (skip remaining work), and CancelledError propagation is explicitly preserved.

### Changes Made
- Verified refined AC against codebase state: confirmed refresh() and ingest() lack cancel, confirmed threading gaps in refresh_all->refresh, _ingest_items->pipeline.ingest, crawl_and_ingest->pipeline.ingest_text.
- Verified bootstrap wiring does not currently pass shutdown_event to RetrospectiveHook (gap for AC 5 that builder must address).
- Approved #870 for the GREEN phase.

### Dependencies
- Verified: #880 (RED test task) is archived. TDD compliance satisfied.
- Verified: #871 (GraphEnricher cancellation) at ideation, depends on #870.
- Verified: #872 (regression coverage) at ideation, depends on #870 and #871.
- Verified: #877 (tool/runtime shutdown propagation) at ideation, depends on #870.