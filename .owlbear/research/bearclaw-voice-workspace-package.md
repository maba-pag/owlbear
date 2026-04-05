# Owlbear-Voice Workspace Package Scaffolding

> Note: Package renamed to owlbear-voice per v2 convention (#64).

> **Owning task:** #52 — Create owlbear-voice workspace package
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #52 requires scaffolding the voice addon as a uv workspace member package
with moonshine-voice STT, kokoro TTS (optional), pyttsx3 fallback, and a
process entry point. Key questions: what are the exact dependency specs, how
should extras be structured, and what blockers exist?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| uv workspace docs | https://docs.astral.sh/uv/concepts/projects/workspaces/ | .95 | Workspace member config, requires-python intersection |
| moonshine-voice 0.0.51 (PyPI) | https://pypi.org/project/moonshine-voice/ | .95 | Deps: numpy, sounddevice, requests, tqdm, filelock, platformdirs; MIT |
| kokoro 0.9.4 (PyPI) | https://pypi.org/project/kokoro/ | .90 | Deps: huggingface-hub, loguru, misaki[en], numpy, torch, transformers; Apache-2.0; **requires `<3.13,>=3.10`** |
| monorepo-tooling research | docs/research/monorepo-tooling.md | .90 | uv_build backend, workspace source pattern, package naming convention |
| voice-addon-architecture | docs/research/voice-addon-architecture.md | .95 | STT/TTS choices, stdio protocol, process isolation design |
| v1 voice module | v1/src/owlbear/voice/ | .85 | Prior art: lazy loading, async wrappers, streaming STT |
| pydantic-ai monorepo | https://github.com/pydantic/pydantic-ai | .80 | Reference workspace member structure with extras |

## 3. Analysis

### 3.1 Dependency Structure

| Dep group | Packages | Disk footprint | Required? |
|-----------|----------|---------------|-----------|
| Base STT | moonshine-voice>=0.0.49 | ~55-85 MB (platform wheel includes ONNX runtime) | Yes |
| Base TTS | pyttsx3>=2.90 | ~10 KB (uses system TTS engine) | Yes |
| Audio I/O | sounddevice>=0.4, numpy>=1.26 | ~5 MB | Yes |
| Kokoro extra | kokoro>=0.9.4, soundfile | ~2.3 GB (torch+transformers+models) | No (optional) |

moonshine-voice already depends on numpy and sounddevice, so declaring them
explicitly in the package is redundant but makes the requirements visible.

### 3.2 Python Version Constraint (Critical)

kokoro 0.9.4 requires `>=3.10,<3.13`. uv workspaces enforce a single
`requires-python` as the intersection of all members. If owlbear-voice sets
`>=3.12`, the workspace stays at `>=3.12` — fine. kokoro's `<3.13` is a package-
level constraint that uv enforces during dependency resolution, not a workspace
member constraint.

**Impact:** On Python 3.13+, `uv sync --extra kokoro` will fail for
owlbear-voice, but the base install (pyttsx3 TTS) works. This is acceptable
since kokoro is explicitly optional. When kokoro adds 3.13 support, no
owlbear-voice changes are needed.

### 3.3 Package Naming Inconsistency

The monorepo-tooling research established `owlbear-{name}` as the naming
convention (owlbear-orchestrator, owlbear-knowledge, etc.). The v2 architecture
decision states "Everything is owlbear" and "Bearclaw name dropped." However,
the voice-addon-architecture doc and task #52 use `owlbear-voice`.

| Option | Consistency | Notes |
|--------|------------|-------|
| `owlbear-voice` (.80) | High — matches all other workspace members | Follows v2 naming convention |
| `owlbear-voice` (.50) | Low — contradicts "Bearclaw name dropped" | Legacy name from v1 |

**Recommendation (.80):** Rename to `owlbear-voice` for consistency. Import
path: `owlbear_voice`. Entry point: `owlbear-voice`.

### 3.4 Proposed pyproject.toml

Based on monorepo-tooling patterns (uv_build backend, src layout):

```toml
[project]
name = "owlbear-voice"
version = "0.1.0"
requires-python = ">=3.12"
description = "Voice addon for OwlBear — STT + TTS as a standalone process"
dependencies = [
    "moonshine-voice>=0.0.49,<0.1.0",
    "numpy>=1.26",
    "pyttsx3>=2.90",
    "sounddevice>=0.4",
]

[project.optional-dependencies]
kokoro = ["kokoro>=0.9.4", "soundfile"]

[project.scripts]
owlbear-voice = "owlbear_voice.main:main"

[build-system]
requires = ["uv_build>=0.11.1,<0.12"]
build-backend = "uv_build"
```

### 3.5 Entry Point Design

The voice addon is designed as a standalone process communicating via
line-delimited JSON on stdio (per voice-addon-architecture.md). The entry point
script (`owlbear_voice/main.py`) should:

1. Parse CLI args (model arch, language, TTS backend)
2. Initialize STT and TTS lazily
3. Read speak commands from stdin, write transcripts to stdout
4. Exit cleanly on EOF/SIGTERM

v1 patterns to port: lazy model loading (STTEngine, TTSEngine), asyncio thread
offloading for blocking TTS, sounddevice mic capture.

### 3.6 Blocker: Workspace Not Yet Scaffolded

Task #7 (Create monorepo skeleton) is in `ideation`. The workspace root
`pyproject.toml` with `[tool.uv.workspace]` must exist before any member package
can be added. Task #52 must list #7 as a dependency.

## 4. Recommendation (.85 confidence)

1. **Rename to `owlbear-voice`** for v2 naming consistency
2. **Use the pyproject.toml structure from §3.4** — base deps are STT+pyttsx3,
   kokoro is an optional extra
3. **Add `depends_on: [7]`** to task #52 — cannot scaffold without workspace
4. **Set `requires-python = ">=3.12"`** — kokoro's `<3.13` is handled at
   dep-resolution time, not workspace level
5. **Port v1 patterns:** lazy loading, async wrappers, sounddevice capture

**Risks:**
- kokoro's `<3.13` cap may persist, blocking quality TTS on newer Python
- moonshine-voice ships platform-specific wheels; CI needs per-platform testing
- espeak-ng system dependency required for kokoro on Windows

## 5. Follow-up Tasks

```
kanban\kanban-md.exe edit 52 --depends-on 7
kanban\kanban-md.exe create "Align voice package naming to owlbear-voice across tasks and docs" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nAlign voice package naming with v2 convention (owlbear-{name}).\n\n## Acceptance Criteria\n- [ ] Tasks #49-52 updated to owlbear-voice naming\n- [ ] voice-addon-architecture.md updated\n- [ ] Import path: owlbear_voice\n\n## Context\nSee docs/research/bearclaw-voice-workspace-package.md section 3.3"
```
