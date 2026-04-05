# README Trim Assessment

> **Owning task:** #93 — Rewrite README.md for v2 architecture
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #93 requests a full README rewrite for v2. However, task #28 (archived) already completed a v2 rewrite — the current README is 108 lines with v2 content. The question is: **what work remains for #93, and how should the AC be scoped?**

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| OwlBear README.md (current) | Local: `README.md` | 1.0 | 108-line v2 README, product of #28 |
| Research: readme-v2-rewrite | Local: `docs/research/readme-v2-rewrite.md` | 1.0 | Original structure recommendation (~61 lines) |
| Task #28 (archived) | Local: kanban task | 1.0 | Full rewrite history, builder/reviewer/audit trail |
| Claude Code README | `github.com/anthropics/claude-code` | .85 | Minimal: title, get-started, plugins, bugs, data policy |
| Aider README | `github.com/Aider-AI/aider` | .75 | Features + getting-started + docs links; setup details external |

## 3. Analysis

### 3.1 AC Satisfaction (current README vs #93 AC)

| AC Item | Status | Evidence |
|---------|--------|----------|
| Title: "On-demand AI development system built on GitHub Copilot" | MET | Line 3 |
| Overview: 2-3 sentences, no v1 refs | MET | Lines 5-8 |
| Prerequisites: Python 3.12+, uv, VS Code + Copilot, Copilot CLI | MET | Lines 12-16 |
| Quick Start: git clone, uv sync, kanban setup, open VS Code | MET | Lines 20-30 |
| Directory layout table matching copilot-instructions.md | MET | Lines 65-82, all 13 entries match |
| How It Works: agents, skills, MCP servers, orchestrator | MET | Lines 84-94 |
| Development: uv sync, pytest, ruff | MET | Lines 96-102 |
| No v1 references (daemon, bearclaw, etc.) | MET | Only `v1/` dir listing (describes real directory) |
| Total length under 80 lines | NOT MET | 108 lines (28 over) |
| License preserved | MET | Line 104 |

**9 of 10 items already satisfied.** The only gap is the 80-line target.

### 3.2 Line Budget Analysis

| Section | Lines | In recommended structure? |
|---------|-------|--------------------------|
| Title + tagline | 3 | Yes |
| Overview | 6 | Yes |
| Prerequisites | 7 | Yes |
| Quick Start | 13 | Yes |
| **New Project Setup** | **27** | **No** |
| Directory Layout | 21 | Yes |
| How It Works | 11 | Yes |
| Development | 7 | Yes |
| License | 5 | Yes |
| **Total** | **108** | — |
| **Without New Project Setup** | **~81** | — |

### 3.3 "New Project Setup" Disposition

The section documents `scripts/setup.py` (real, functional script). Both Claude Code and Aider keep secondary setup workflows out of the README — they link to external docs.

| Option | Lines saved | Trade-off |
|--------|-------------|-----------|
| Remove entirely | 27 | Loses discoverability of setup.py |
| Replace with one-line link | 25 | Preserves discoverability, minimal footprint |
| Keep, raise line target to 120 | 0 | Matches #28's original target |

## 4. Recommendation (.90 confidence)

**Reframe #93 as a trim task, not a rewrite.** The rewrite was completed by #28. Remaining work:

1. Replace the "New Project Setup" section with a one-line pointer to `scripts/setup.py` (saves ~25 lines)
2. Tighten Quick Start from 13 to ~10 lines (minor prose compression)
3. Target: ≤80 lines

This is a 15-minute docs edit, not a rewrite. The architect should refine '#93's AC accordingly.

**Risk:** The `v1/` directory entry in the layout table is technically a v1 reference, but it describes a real directory. Removing it would make the layout table incomplete. Recommend keeping it — the AC item lists specific v1 terms (daemon, bearclaw, PydanticAI, Slack, approval gates, browser automation, Qdrant) and `v1/` is none of those.

## 5. Follow-up Tasks

No new tasks needed — #93 itself covers the remaining work. The AC should be refined by the architect to reflect the narrower scope (trim, not rewrite).
