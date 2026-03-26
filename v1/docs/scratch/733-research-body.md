## Research

- Doc: docs/research/cooperative-cancellation.md
- Attribution updated: docs/sources/overview.md
- Key findings:
  - Daemon loops already use `shutdown_event`; the real gaps are operation-level checks in `RefreshOrchestrator`, `crawl_and_ingest()`, `IngestPipeline._run_extract()`, `BookmarkPipeline.process()`, and `GraphEnricher` background tasks.
  - Reusing the daemon-wide `shutdown_event` everywhere is the wrong abstraction; a separate per-operation signal composed with daemon shutdown is the better fit.
  - `asyncio.Event` should gate source/page/chunk/stage boundaries, while `Task.cancel()` and timeouts remain the hard-stop mechanism for blocked awaits.
- Created ideation follow-ups:
  - #870 Implement operation-scoped cancellation signal for knowledge pipelines
  - #871 Manage GraphEnricher background-task cancellation and draining
  - #872 Add cooperative cancellation regression coverage for knowledge pipelines
- Follow-up commands executed:
  - `kanban\kanban-md.exe create "Implement operation-scoped cancellation signal for knowledge pipelines" --priority nice-to-have --status ideation --tags "scope:core,type:build"`
  - `kanban\kanban-md.exe create "Manage GraphEnricher background-task cancellation and draining" --priority nice-to-have --status ideation --tags "scope:core,type:build" --depends-on 870`
  - `kanban\kanban-md.exe create "Add cooperative cancellation regression coverage for knowledge pipelines" --priority nice-to-have --status ideation --tags "scope:core,type:test" --depends-on 870,871`
