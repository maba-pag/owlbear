---
id: 703
title: Design context pre-hydration for agent dispatch
status: backlog
priority: important
created: 2026-03-09T05:12:16.9107366+01:00
updated: 2026-03-09T15:33:02.0283034+01:00
tags:
    - phase-research
    - scope:core
    - agent
depends_on:
    - 712
class: standard
---

Deterministically parse task body for URLs and file paths, fetch/read them, and inject as structured pre-context into the agent dispatch prompt. Saves tokens and reduces first-turn hallucination.

See docs/research/stripe-minions-research.md S3e and S5 for rationale.

## Acceptance Criteria

- [ ] New module `core/context_hydration.py` with async `hydrate(body: str, ...) -> HydrationResult`
- [ ] `extract_urls(text: str) -> list[str]`  regex extraction of http/https URLs from plain text and markdown link syntax
- [ ] `extract_file_paths(text: str, workspace_root: Path) -> list[Path]`  extract file-like references, resolve relative to workspace, reject paths outside workspace via `is_relative_to(workspace_root)`
- [ ] `fetch_url(url: str, ...) -> str`  async httpx GET + `trafilatura.extract()` for content; apply URL safety check (blocked_urls/allowed_urls pattern from `WebSearchToolset._check_url`) before fetching
- [ ] `read_file_safe(path: Path, workspace_root: Path) -> str`  read file content with workspace confinement check
- [ ] `HydrationResult` frozen Pydantic model: `urls: dict[str, str]` (urlcontent), `files: dict[str, str]` (pathcontent), `errors: list[str]` (logged failures)
- [ ] `max_content_bytes: int = 50_000` parameter caps total pre-hydrated content size (prevents context blowout)
- [ ] Failed fetches/reads logged at WARNING and collected in `errors`  never fail the dispatch
- [ ] New config field `prehydration_enabled: bool = False` in `OwlBearSettings` (opt-in toggle)
- [ ] Integrate into `poll_tick()` in `daemon.py`: after building the prompt from task details, call `hydrate()` on the body and append `HydrationResult` content to the prompt (gated by config toggle)
- [ ] trafilatura is already an optional dep (`owlbear[crawl]`); when not installed, URL fetching is skipped with a logged warning

## Architecture Notes

- **Module location:** `core/context_hydration.py`  uses only stdlib + httpx + trafilatura (no owlbear module imports). Core layer is valid because no upward deps.
- **Integration point:** `poll_tick()` in `daemon.py` (assembly layer), NOT the VS Code orchestrator agent (which has no file/HTTP tools).
- **URL safety:** Reuse the blocked_urls/allowed_urls pattern from `WebSearchToolset` (`tools/web_search.py`). Extract the guard logic into a shared helper or pass the guard callable via DI at bootstrap.
- **Workspace confinement:** File paths validated with `is_relative_to(workspace_root)`  same pattern as `FileToolset`.
- **Content extraction:** Reuse `trafilatura.extract(output_format='markdown', include_links=True)` call pattern from `content_extractor.py` and `web_search.py`.
- **DI wiring:** `poll_tick()` receives a `hydrator` callable (or None when disabled)  bootstrap constructs it with settings + URL guard.

## Dependencies

- Preceding test task: #712 (must be completed first)

[[2026-03-09]] Mon 15:33
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Pre-hydration function parses URLs/paths | Vague  no regex spec, no return type | Rewritten: extract_urls + extract_file_paths with typed returns |
| Fetch URLs via trafilatura | Missing URL safety check (SSRF risk) | Added: blocked/allowed URL guard requirement |
| Read files into context dict | Missing workspace confinement | Added: is_relative_to(workspace_root) check |
| Integrate into orchestrator dispatch Step 3 | Ambiguous  VS Code orchestrator has no file/HTTP tools | Rewritten: integrate into poll_tick() in daemon.py |
| Config toggle | OK but not specified as opt-in | Rewritten: prehydration_enabled: bool = False |
| Tests for extraction + error handling | No preceding test task | Created #712 (RED-phase test task) |
| (missing) Token budget | Not mentioned  could blow context | Added: max_content_bytes=50_000 cap |
| (missing) HydrationResult type | No return type specified | Added: frozen Pydantic model |
| (missing) Error handling policy | Silent vs. raise unclear | Added: log WARNING, collect in errors list, never fail dispatch |

### Architecture Notes
- Module: core/context_hydration.py  only stdlib + httpx + trafilatura, no owlbear imports. Core layer valid.
- Integration: poll_tick() in daemon.py (assembly layer). DI via hydrator callable param.
- URL safety: reuse blocked/allowed pattern from WebSearchToolset (tools/web_search.py). Extract guard or pass via DI.
- Workspace confinement: is_relative_to(workspace_root) per FileToolset pattern.
- Content extraction: trafilatura.extract(output_format='markdown') pattern from content_extractor.py and web_search.py.

### Changes Made
- Rewrote AC with 11 precise, verifiable criteria
- Added architecture notes section with module location, integration point, patterns
- Created test task #712 (TDD RED phase)
- Added depends_on: [712] to task #703
- Specified HydrationResult frozen model, token budget, error handling policy, URL safety

### Dependencies
- Created: #712 (RED-phase tests)  must complete before #703 implementation
- Verified: trafilatura already optional dep (owlbear[crawl])
- Verified: httpx already in deps
