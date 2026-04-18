# Cockpit Layout Validation — 1440×900 + Sidecar + 700 Tasks

> **Owning task:** #922 — P0-02: Static layout mockup 1440x900 + sidecar + 700 tasks (D13)
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

D13 gates all Phase 1/2 work: can 7 kanban columns remain readable at 1440×900 with a ~360px sidecar open and 700 task cards? If columns fall below 100px, the sidecar must switch to an overlay/drawer pattern.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | OwlBear board config | `.owlbear/kanban/config.yml` | 7 status columns: research→done (0.95) |
| S2 | OwlBear Brief D13/D14 | `.owlbear/briefs/draft-cockpit/decisions.md` | Layout spec: 56px rail, 360px sidecar (0.95) |
| S3 | Porsche DS Grid docs | designsystem.porsche.com/v3/styles/grid | Grid primitives, spacing tokens, fluid columns (0.70) |
| S4 | Brief research-notes §B.7 | `.owlbear/briefs/draft-cockpit/research-notes.md` | Prior art layouts: Linear, Airflow, Prefect, Temporal (0.80) |
| S5 | Pragmatic Drag-and-Drop | github.com/atlassian/pragmatic-drag-and-drop | Atlassian kanban patterns (Trello/Jira) (0.60) |

## 3. Analysis

### 3.1 Horizontal Pixel Budget

| Region | Width | Source |
|--------|-------|--------|
| Viewport | 1440 px | D13 |
| Left icon rail | 56 px | D14 |
| Right sidecar | 360 px | D14 |
| **Kanban workspace** | **1024 px** | Remainder |
| Workspace padding (L+R) | 32 px | 16px each side |
| Column gaps (6 × 8px) | 48 px | Standard 8px gap |
| **Available for columns** | **944 px** | 1024 − 32 − 48 |
| **Per column (÷7)** | **≈ 135 px** | 944 / 7 |

Conservative scenario (12px gaps): 1024 − 32 − 72 = 920px → **131 px/col**.
Generous scenario (6px gaps): 1024 − 32 − 36 = 956px → **137 px/col**.

**Range: 131–137 px per column. All scenarios exceed the 100px threshold.**

### 3.2 Card Readability at ~135px

| Element | Budget | Notes |
|---------|--------|-------|
| Priority border (left) | 4 px | Color-coded per priority |
| Card padding (L+R) | 16 px | 8px each side |
| Available text width | ~115 px | For title + indicators |
| Title characters visible | ~16–18 | System font at ~6.5–7px avg char width |
| Block badge | 16 px icon | Shield icon, no text |
| Running indicator | 8 px dot | Top-right pulse dot |

Title truncation at ~16 chars is aggressive but workable with tooltip-on-hover. Industry comparison:

| Tool | Column width | Cards visible |
|------|-------------|---------------|
| Trello | ~272 px | 30+ chars |
| Jira | ~220–280 px | 25–35 chars |
| Linear | ~200–280 px | 25–35 chars |
| GitHub Projects | ~280 px | 30+ chars |
| **OwlBear cockpit** | **~135 px** | **~16 chars** |

OwlBear columns are narrower than all major tools, but our cards are simpler (title + 3 indicators, no avatars/labels/due dates), which offsets the width constraint.

### 3.3 Vertical Density

| Metric | Value |
|--------|-------|
| Viewport height | 900 px |
| Status bar (top) | 48 px |
| Column header | 32 px |
| Available column height | ~820 px |
| Card height (with gap) | ~56 px (48–56 card + 4–8 gap) |
| Cards visible per column | ~14–15 |
| Cards per column (700/7 avg) | ~100 |
| Scroll ratio | ~7:1 (14 visible of 100) |

Standard kanban behavior — `overflow-y: auto` on each column. Non-uniform distribution (research/backlog heavy, review/docs light) means active columns are shorter and more readable.

### 3.4 Trade-Off Matrix

| Option | Column width | Pros | Cons | Confidence |
|--------|-------------|------|------|------------|
| A. Always-visible sidecar (360px) | ~135 px | Persistent detail view, no dismiss/reopen friction, matches Linear/Airflow | Narrower columns than industry standard, aggressive truncation | **0.82** |
| B. Overlay/drawer sidecar | ~195 px (full workspace) | Wider columns (~195px), more title chars (~25) | Extra click to open/close, lost context on dismiss | 0.65 |
| C. Narrower sidecar (300px) | ~144 px | Slightly wider columns, still always-visible | Still narrower than industry, gains only ~9px | 0.55 |
| D. Collapsible columns (hide research/done) | ~188 px (5 cols) | Much wider active columns | Hides workflow start/end, non-standard | 0.45 |

## 4. Recommendation

**Option A — Always-visible sidecar at 360px.** Confidence: **0.82**.

Columns at ~135px exceed the 100px minimum by 35%. Title truncation is the main trade-off, mitigated by:
1. Tooltip on card hover showing full title
2. Card-click opens full detail in sidecar
3. Card design is indicator-dense (border + badge + dot), not text-dense

Challenge: N/A — this is a data-driven layout calculation, not an architectural choice. The pixel math is deterministic; the mockup will confirm visual readability empirically.

## 5. Follow-up Tasks

The mockup implementation task (#922 itself) proceeds with Option A parameters. The mockup will provide empirical visual confirmation.

No additional follow-up tasks needed beyond the existing #922 AC, which requires user visual confirmation.
