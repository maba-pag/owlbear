---
id: 703
title: Design context pre-hydration for agent dispatch
status: todo
priority: important
created: 2026-03-09T05:12:16.9107366+01:00
updated: 2026-03-09T16:33:54.7883085+01:00
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

- [ ] New module `src/owlbear/core/context_hydration.py`:
  - `extract_urls(text: str) -> list[str]`  regex extraction of http/https URLs from plain text and markdown link syntax `[text](url)`
  - `extract_file_paths(text: str, workspace_root: Path) -> list[Path]`  extract file-like references, validate via `sandbox_path(workspace_root, p)` from `owlbear.paths`; silently skip paths that raise `PermissionError`
  - `async fetch_url(url: str, url_checker: Callable[[str], None] | None, ...) -> str`  if `url_checker` provided, call first (raises ValueError on reject); then httpx GET + `trafilatura.extract(output_format='markdown', include_links=True)`
  - `read_file_safe(path: Path, workspace_root: Path) -> str`  read file; validate with `sandbox_path(workspace_root, path)`
  - `async hydrate(body: str, workspace_root: Path, url_checker: Callable[[str], None] | None = None, max_content_bytes: int = 50_000) -> HydrationResult`  orchestrates extract + fetch + read
- [ ] `HydrationResult` frozen Pydantic model: `urls: dict[str, str]` (url to content), `files: dict[str, str]` (path to content), `errors: list[str]` (logged failures)
- [ ] `max_content_bytes` parameter caps total pre-hydrated content (sum of url+file content); truncate last item to fit
- [ ] Module imports only leaf modules (`owlbear.paths`). No imports from `tools/`, `agents/`, or `memory/`. URL safety guard comes via callable DI.
- [ ] Failed fetches/reads logged at WARNING and collected in `errors`  never fail the dispatch
- [ ] When trafilatura not installed (optional dep `owlbear[crawl]`), URL fetching skipped with logged warning; file extraction still works
- [ ] Config field `prehydration_enabled: bool = Field(default=False)` in `OwlBearSettings`
- [ ] Integration in `daemon.py:poll_tick()`:
  - New param `hydrator: Callable[[str, Path], Awaitable[HydrationResult]] | None = None`
  - Call in **both** dispatch paths: retry dispatch (step 3, ~L666) and new task dispatch (step 7, ~L697)
  - Append HydrationResult content to prompt after task details
  - `bootstrap.py` constructs hydrator with settings + URL guard patterns; passes `None` when disabled
- [ ] Brief doc note in `.github/agents/builder.agent.md` mentioning daemon pre-hydration exists
- [ ] Tests written by test-writer in #712

## Architecture Notes

- **Module:** `core/context_hydration.py`  imports only `owlbear.paths` (leaf). No upward deps.
- **Integration:** `poll_tick()` in `daemon.py` (assembly). Two paths: retry (step 3) and new task (step 7).
- **URL safety:** `url_checker: Callable[[str], None] | None` via DI. Same blocked/allowed regex logic as `WebSearchToolset._check_url` and `URLSafetyGuard.check_url`, wired at bootstrap.
- **Workspace confinement:** `sandbox_path()` from `owlbear.paths`  matches FileToolset/TerminalToolset pattern.
- **Content extraction:** `trafilatura.extract(output_format='markdown', include_links=True)` per content_extractor.py and web_search.py.
- **DI wiring:** bootstrap builds a partial/lambda closing over workspace_root + url_checker; passes to poll_loop -> poll_tick.

## Dependencies

- Preceding test task: #712 (must complete RED phase first)

[[2026-03-09]] Mon 16:33
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| extract_urls regex | Clear input/output types | Keep |
| extract_file_paths with sandbox_path | Prior AC used is_relative_to; refined to sandbox_path from paths.py (existing leaf pattern) | Refined |
| fetch_url with url_checker DI | Prior AC referenced WebSearchToolset._check_url directly (layering risk); refined to Callable DI | Refined |
| read_file_safe with sandbox_path | Prior AC used is_relative_to; refined to sandbox_path | Refined |
| hydrate orchestrator function | Full typed signature now specified | Keep |
| HydrationResult frozen model | Clear structure | Keep |
| max_content_bytes budget | Clear, prevents context blowout | Keep |
| Module import constraint | Prior notes said 'no owlbear imports'; corrected to 'only leaf modules (paths.py)' | Refined |
| Error handling policy | WARNING + errors list, never fail dispatch | Keep |
| trafilatura optional | Already handled in deps | Keep |
| Config toggle prehydration_enabled | Follows opt-in bool=False convention | Keep |
| poll_tick integration | Prior AC didn't specify both dispatch paths; added explicit step 3 + step 7 callout | Refined |
| Builder doc note | Minor AC, clear | Keep |
| Test task #712 | Exists in backlog, comprehensive AC | Verified |

### Architecture Notes
Module layering verified: core/ -> paths.py (leaf) is valid. No upward deps.
URL guard via DI avoids importing tools/browser/safety.py or tools/web_search.py into core/.
sandbox_path() is the canonical file confinement utility (used by 5 modules).
Two dispatch paths in poll_tick() explicitly called out to prevent builder missing retry path.
bootstrap.py is the only module that wires the hydrator (assembly layer).

### Changes Made
- Replaced body: specified sandbox_path reuse, url_checker DI callable, both dispatch paths, corrected import constraint
- Verified #712 test task exists with matching AC
- Moved to todo

### Dependencies
- Verified: #712 (RED-phase tests) in backlog  must proceed through pipeline first
- Verified: trafilatura in optional deps (owlbear[crawl])
- Verified: httpx in deps
- Verified: sandbox_path in paths.py (leaf module)

[[2026-03-09]] Mon 16:33
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| extract_urls regex | Clear input/output types | Keep |
| extract_file_paths with sandbox_path | Prior AC used is_relative_to; refined to sandbox_path from paths.py (existing leaf pattern) | Refined |
| fetch_url with url_checker DI | Prior AC referenced WebSearchToolset._check_url directly (layering risk); refined to Callable DI | Refined |
| read_file_safe with sandbox_path | Prior AC used is_relative_to; refined to sandbox_path | Refined |
| hydrate orchestrator function | Full typed signature now specified | Keep |
| HydrationResult frozen model | Clear structure | Keep |
| max_content_bytes budget | Clear, prevents context blowout | Keep |
| Module import constraint | Prior notes said 'no owlbear imports'; corrected to 'only leaf modules (paths.py)' | Refined |
| Error handling policy | WARNING + errors list, never fail dispatch | Keep |
| trafilatura optional | Already handled in deps | Keep |
| Config toggle prehydration_enabled | Follows opt-in bool=False convention | Keep |
| poll_tick integration | Prior AC didn't specify both dispatch paths; added explicit step 3 + step 7 callout | Refined |
| Builder doc note | Minor AC, clear | Keep |
| Test task #712 | Exists in backlog, comprehensive AC | Verified |

### Architecture Notes
Module layering verified: core/ -> paths.py (leaf) is valid. No upward deps.
URL guard via DI avoids importing tools/browser/safety.py or tools/web_search.py into core/.
sandbox_path() is the canonical file confinement utility (used by 5 modules).
Two dispatch paths in poll_tick() explicitly called out to prevent builder missing retry path.
bootstrap.py is the only module that wires the hydrator (assembly layer).

### Changes Made
- Replaced body: specified sandbox_path reuse, url_checker DI callable, both dispatch paths, corrected import constraint
- Verified #712 test task exists with matching AC
- Moved to todo

### Dependencies
- Verified: #712 (RED-phase tests) in backlog  must proceed through pipeline first
- Verified: trafilatura in optional deps (owlbear[crawl])
- Verified: httpx in deps
- Verified: sandbox_path in paths.py (leaf module)
