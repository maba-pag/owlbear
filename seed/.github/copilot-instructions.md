# Project Copilot Instructions

<!-- Replace this title with your project name and keep the section structure. -->

## 1. Project Identity

Describe your project in 2-4 sentences.

<!-- Customize this paragraph for your project domain, users, and delivery model. -->

## 2. Directory Structure

<!-- Replace example paths below with your actual repository layout. -->
<!-- Include source packages, frontend root, and test paths so generated answers are path-aware. -->

| Path | Purpose |
| --- | --- |
| `src/` | Main application or library source code |
| `src/domain/` | Core business logic modules (example) |
| `frontend/` or `web/` | Frontend root for UI code (example) |
| `tests/` | Unit and integration tests |
| `tests/e2e/` | End-to-end tests (if used) |
| `docs/` | Documentation and architecture notes |

## 3. Tech Stack

<!-- Replace with concrete language, framework, runtime, and package manager details. -->

| Component | Technology | Notes |
| --- | --- | --- |
| Backend | Python / Node.js / Go (example) | Add your actual backend stack |
| Frontend | React / Vue / Svelte (example) | Keep only what you use |
| Testing | pytest / vitest / playwright (example) | List real commands |
| Tooling | ruff / eslint / mypy (example) | Remove tools you do not run |

## 4. Working Rules

<!-- Customize these rules to match your engineering process. -->

- Prefer small, focused changes tied to one task.
- Run tests and lint checks before completing work.
- Match existing code style and avoid unrelated refactors.

## 5. Useful Commands

<!-- Replace command examples with your project's real commands. -->

- `npm test` or `uv run pytest`
- `npm run lint` or `uv run ruff check`
- `npm run build` or your production build command

## 6. Resources

<!-- Add links or file paths your team wants Copilot to use as primary references. -->

- `README.md`
- `CONTRIBUTING.md`
- `docs/architecture.md`
