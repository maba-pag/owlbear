---
id: 578
title: 'Recurring: Dependency update audit (every 3 days)'
status: backlog
priority: important
created: 2026-03-04T08:03:38.3917383+01:00
updated: 2026-03-04T08:03:38.3917383+01:00
tags:
    - recurring
    - sop
class: standard
---

## Purpose

Track updates to all dependencies declared in `pyproject.toml`. When a dependency has a new version, analyze for breaking changes, new features, deprecations, and security fixes. Create tasks for beneficial updates.

## Schedule

- **Type:** recurring
- **Frequency:** every 3 days
- **Last run:** never
- **Next due:** immediately

## Execution Protocol

1. The orchestrator creates a subtask: `Dependency update audit — YYYY-MM-DD` with `--parent 578 --status ideation --tags "sop-run,dependency-check"`
2. The subtask moves through the full pipeline (ideation → … → done)
3. After the subtask reaches `done`, update `Last run` date in this task's body

## SOP: Dependency Update Audit

### Phase 1: Inventory

1. Read `pyproject.toml` — extract all dependencies:
   - **Core** (9): genai-prices, httpx, openai, pydantic, pydantic-ai, pydantic-settings, tenacity, truststore, typer
   - **browser** (1): playwright
   - **crawl** (1): trafilatura
   - **knowledge** (2): qdrant-client, FlagEmbedding
   - **search** (2): duckduckgo-search, trafilatura
   - **slack** (2): slack_sdk, aiohttp
   - **voice** (3): moonshine-voice, numpy, pyttsx3
   - **benchmark** (3): beir, psutil, ranx
   - **dev** (6): bandit, pre-commit, pytest, pytest-asyncio, pytest-cov, ruff
2. Read `uv.lock` — extract currently pinned versions for each dependency
3. For each dependency, note: name, version spec from pyproject.toml, pinned version from uv.lock, which extras group(s) it belongs to

### Phase 2: Check for Updates

For each dependency:

1. Check PyPI (or GitHub releases for packages not on PyPI) for versions newer than the pinned version
2. Record: package name, current pinned version, latest available version, all versions between
3. Classify the update type:
   - **Major bump** (e.g., 1.x → 2.x) — likely breaking changes
   - **Minor bump** (e.g., 1.2 → 1.3) — new features, possible deprecations
   - **Patch bump** (e.g., 1.2.3 → 1.2.4) — bugfixes, security patches

### Phase 3: Analyze Each Update

For each dependency with available updates:

#### 3a. Changelog Review

1. Read the changelog, release notes, or CHANGES file for all versions between current and latest
2. Categorize each change: breaking, deprecation, new feature, bugfix, security fix, performance improvement

#### 3b. Impact Assessment

1. **Breaking changes**: Search our codebase for usage of affected APIs. Which files would need modification? Estimate effort (trivial / moderate / significant)
2. **Deprecations**: Are we using any newly deprecated APIs? What's the deprecation timeline? When will they be removed?
3. **New features**: Would any new features benefit OwlBear? Which modules? Be specific about the use case
4. **Security fixes**: Are any CVEs patched? Do the affected code paths exist in our usage?
5. **Performance**: Any significant performance improvements relevant to our usage patterns?

#### 3c. Rating

- `skip` — no relevant changes, or update is risky with no benefit
- `nice-to-have` — minor improvements, no urgency
- `important` — useful features or non-critical fixes that improve our code
- `needed` — security fixes, deprecation timeline approaching, or significant improvements
- `critical` — active CVE affecting us, or breaking change in a dependency we must upgrade (e.g., our version spec would start failing)

### Phase 4: Create Tasks

For each update rated `nice-to-have` or above:

1. **Check existing board** — `kanban-md list --tag dependency-update` to avoid duplicates
2. Create a kanban task in `ideation` with:
   - Title: `Update {package} from {current} to {target}`
   - Body: changelog summary, impact assessment, which files need changes, migration steps for breaking changes
   - Tags: `dependency-update`, plus relevant module tags (e.g., `knowledge`, `voice`, `dev`)
   - Priority matching the rating from 3c
3. For **breaking changes**, the task body must include explicit migration steps — not just "update code"
4. For **security fixes**, reference CVE numbers where available

### Phase 5: Version Spec Review

1. Check if any version specs in `pyproject.toml` are **too loose** — could pull in a breaking major version (e.g., `>=1.0` when 2.0 exists with breaking changes)
2. Check if any version specs are **too tight** — blocking beneficial updates unnecessarily (e.g., pinned to exact version when a range would be safe)
3. Create tasks for spec adjustments if needed, tagged `dependency-update,config`

### Phase 6: Lock File Health

1. Run `uv lock --check` to verify the lock file is consistent with pyproject.toml
2. Check for any dependency conflicts or resolution warnings
3. Note any transitive dependencies with known issues

### Phase 7: Report

Append a summary to the subtask body:

- Dependencies checked: N (core: X, extras groups: Y each)
- Updates available: N (major: X, minor: Y, patch: Z)
- Tasks created: N (list task IDs and titles)
- Security-relevant updates: list with CVE references
- Dependencies at latest version: list names
- Version spec issues found: list

## Quality Gates

- Every dependency in `pyproject.toml` must be checked — including all extras groups
- Breaking changes must include **specific migration guidance** referencing our files, not just "update code"
- Security fixes must reference CVE numbers where available
- New feature analysis must reference our **actual codebase usage**, not just summarize the feature generically
- Do not create duplicate tasks — check existing board first with `kanban-md list --tag dependency-update`
- Transitive dependencies are out of scope unless they have security implications
