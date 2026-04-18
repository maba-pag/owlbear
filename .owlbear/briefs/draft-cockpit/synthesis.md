# Synthesis — Cockpit v1

**Synthesised by:** Pragmatist
**Sources:** context.md, decisions.md, research-notes.md, voices/{architect, data, enduser, security}.md
**Date:** 2026-04-17

---

## 1. Convergences

### Stack and Infrastructure (all four panelists)

- **FastAPI + React 19 + Vite** as the delivery stack. Architect recommends it at 95% confidence; Data, End User, and Security all work within this assumption without contest.
- **Backend at `serve/cockpit/`** importing `owlbear_kanban` directly, mirroring the MCP adapter pattern with HTTP routes. Architect maps the package structure; Data and Security design within it.
- **Porsche Design System (React wrapper) as primary**, with **Radix UI + Tailwind** as fallback if PDS card customization proves too rigid. Architect and End User converge; Security is neutral (CSP-compatible either way).
- **TanStack Query** for data fetching, polling, and optimistic mutation management (Architect, End User implicitly via optimistic-UI patterns).

### Security Posture (Security + Architect + Data)

- **Localhost-only bind (`127.0.0.1`)**, no auth for v1. Security provides the trust-model rationale; Architect and Data do not contest.
- **XSS sanitization is the load-bearing security control.** Security elevates this to P0; all panelists treat sanitized markdown rendering as a given. `rehypeSanitize` + CSP + no `dangerouslySetInnerHTML` — three non-negotiable layers.
- **Agent-only verbs hidden at the HTTP layer** (structural enforcement). No endpoint exists for `claim_task`, `start_work`, `end_work`, `pick_dispatchable`. Security and Architect converge on this as the D4 enforcement mechanism.
- **CSRF defense:** custom header `X-Cockpit-Request` + strict CORS + Origin/Host validation. Security specifies; Architect's HTTP surface is compatible.
- **`--allow-remote` gate** required before any non-localhost bind, with mandatory auth when enabled. Security specifies; no dissent.

### Polling and Cross-Process Detection (Architect + Data — explicit convergence)

- **The per-instance `revision` counter cannot detect cross-process changes.** Data calls this out as Risk #1 ("factually wrong" to rely on it). Architect independently selects **mtime-scan** (`os.scandir()` → `{filename: mtime_ns}` dict) as the cache-invalidation mechanism. These converge on the same solution.
- **3-second poll interval** with a **500ms skip window** after local mutations to prevent echo-clobber. Both Architect and Data specify this independently.
- **`config.yml` mtime watch** for column/priority/timeout changes; catch parse errors and hold previous config on failure (Data). Architect's mtime-scan infrastructure supports this.

### Layout and Interaction Model (End User + Architect + reference projects)

- **Nav | Workspace | Sidecar | Status** layout pattern. End User provides the concrete spec (56px icon rail, ~360px sidecar, top status bar). Architect provides the CSS Grid areas (five zones with reserved `contextual` and `sidecar`). Both align with Linear / Vibe Kanban / Mission Control prior art.
- **Sidecar detail pane over modals** for task editing. All four Part C reference projects converge here. End User and Architect agree.
- **Card density: ~48–56px tall**, priority-coded left border, block badge, running indicator. End User specifies; Architect flags PDS card rigidity as a risk but not as a disagreement.
- **Drag-to-move + context menu** for status transitions. Valid targets highlight on drag; invalid dim. End User specifies with Linear/GitHub Projects as precedent.
- **Animated card transitions (~300ms)** as the demo-readiness hero moment. End User specifies; no dissent.
- **Running-state derivation computed server-side** (`free` / `running` / `stuck` / `anomalous`). Data defines the logic; Architect places it in the API response as `claim_status`. End User consumes it in the activity panel.

### Audit and Actor Identity (Security + Data)

- **`actor: "cockpit"`** on all GUI-initiated mutations. Security and Data agree. Limitation accepted: XSS-driven mutations also log as `"cockpit"` (reinforces XSS prevention as primary control).

---

## 2. Disagreements

### 2.1 — O6 "No Silent Data Loss" vs. Rejected Conflict Detection

**Data vs. Context (D6/O6 tension)**

- **Data** identifies an unresolvable requirements tension: the engine does whole-record read-modify-write; concurrent same-task writes silently clobber all fields. O6 says "errors surface inline without silent data loss." The user rejected per-task conflict detection. These three constraints are mutually exclusive.
- **Data** offers two options: **(a)** Narrow O6 scope — "no silent data loss" means engine errors only, not concurrent-write races; accept and document the race risk. **(b)** Lightweight pre-write timestamp check — compare `updated` field at save time vs. editor-open time; warn (not block) on mismatch. This is a single-field comparison, not full conflict detection.
- **Architect** does not address this tension directly. The mtime-scan cache detects changed files but does not feed into the editor save path.
- **Security** notes that stale-view → clobbered edits is "Medium" severity with "Medium" residual risk.

**Resolution required from user.**

### 2.2 — Activity Surface Placement: Sidecar Tab vs. Bottom Panel

**End User (sidecar tab) vs. original sketch implications**

- **End User** moved the activity surface from the bottom panel into the **right sidecar as a second tab** alongside the Detail tab. Rationale: full sidecar height gives activity proper real estate; avoids bottom-panel invention.
- **Trade-off acknowledged by End User (Warning #3):** You cannot view the activity list AND edit a task simultaneously. The compact status-bar summary ("3 running · 1 stuck · 2 free") is the relief valve.
- **Architect** shows `sidecar` as a reserved grid area but does not specify activity placement. No conflict, but no reinforcement of the tab-sharing approach either.
- No other panelist contests the move.

**Resolution required from user** — is simultaneous activity + task editing a v1 need?

### 2.3 — Backend Enforcement of D4 Stuck-Only Release

**Security vs. Architect (additive, not conflicting)**

- **Security** recommends the backend adapter check claim expiry before calling `release_task()`. If the claim is active (not expired), require an explicit `force: true` parameter. Rationale: D4 says "humans release **stuck** work"; XSS can bypass UI-only confirms, so backend enforcement is needed.
- **Data** independently recommends a **pre-release re-read** — re-read the task before release to check if the claim is now fresh (different agent or refreshed `claimed_at`). Acknowledges the TOCTOU race (narrowed to milliseconds, not eliminated).
- **Architect** does not include either check in the HTTP surface spec. The `POST /release` endpoint calls `release_task()` unconditionally.

These are complementary, not conflicting — but they add backend complexity. **User must decide** how strictly D4 is enforced at the HTTP layer.

---

## 3. Decisions to Surface in M4

| # | Decision | Raised By | Options |
|---|----------|-----------|---------|
| **Q1** | How strictly do we honor O6 "no silent data loss" for concurrent writes? | Data | **(a)** Narrow scope: O6 covers engine errors only; accept race risk. **(b)** Lightweight `updated`-timestamp warning on save. |
| **Q2** | Sidecar tab or dedicated panel for activity? | End User | **(a)** Sidecar tab (current). **(b)** Bottom panel (simultaneous view + edit). **(c)** Sidecar tab + accept the trade-off; status-bar summary is sufficient. |
| **Q3** | Benchmark `list_tasks()` at 200 tasks before locking architecture? | Architect | **(a)** Yes — write benchmark script first sprint, target <150ms p99. **(b)** Proceed and add filesystem watcher if needed. |
| **Q4** | Backend enforce D4 stuck-only release, or UI-only confirm? | Security, Data | **(a)** Backend stuck-check + `force` param (structural D4). **(b)** UI confirm only (simpler, but XSS-bypassable). **(c)** Both (belt + suspenders). |
| **Q5** | Sidecar overlay vs. resize at narrow viewports? | End User | **(a)** Sidecar shrinks board (current). **(b)** Sidecar overlays board (drawer). Validate with static mockup before committing. |

---

## 4. Recommendation

### Recommended Path

1. **Accept Q1 option (b)** — lightweight `updated`-timestamp warning. It's a single-field comparison, not full conflict detection, and closes the O6 gap without violating the user's rejection of per-task conflict resolution. **Confidence: 0.75** — Data rates this as viable but notes it's a warning, not a block; some silent loss remains possible if the user dismisses.

2. **Accept Q2 option (a) — sidecar tab** with the status-bar summary as relief valve. The trade-off (no simultaneous activity + edit) is real but narrow; the status bar covers the most common "is anything stuck?" query. Revisit if user feedback shows constant tab-switching. **Confidence: 0.80** — End User's own position at 0.82, with the caveat explicitly flagged.

3. **Do Q3 — benchmark first.** The cost is one script and one measurement. The risk it validates (Architect's #1 concern) would force rework if discovered late. **Confidence: 0.95** — all panelists benefit; no downside.

4. **Accept Q4 option (c) — both backend stuck-check and UI confirm.** The backend check is ~10 lines of code and provides structural D4 enforcement that survives XSS. The UI confirm provides UX clarity. Belt + suspenders justified because D4 is a named invariant. **Confidence: 0.85** — Security and Data both want backend enforcement; Architect's surface is easily extended.

5. **Validate Q5 with a static HTML mockup** before committing to sidecar-resize vs. overlay. End User already specifies this validation step. If the mockup fails at 1440×900, switch to overlay/drawer. **Confidence: 0.90** — concrete, testable, no code risk.

### Open Tensions in the Recommendation

- **Q1 confidence is lowest (0.75)** because Data explicitly notes the timestamp check does not fully prevent silent loss — it only catches same-task concurrent edits where `updated` changed, not edits to fields that don't update the timestamp. The user must decide if this partial mitigation is sufficient for O6.
- **Q2 is the most subjective** — "can I live without simultaneous activity + edit?" is a workflow question only the user can answer from experience.

---

## 5. Open Questions

| # | Question | Source | Why It Blocks |
|---|----------|--------|--------------|
| Q1 | Scope of O6 "no silent data loss" — engine errors only, or concurrent-write races too? | Data §3 | Determines whether the editor save path needs a pre-write check or not. |
| Q2 | Is simultaneous activity view + task editing a v1 requirement? | End User Warning #3 | Determines sidecar-tab vs. dedicated-panel layout decision. |
| Q4 | Backend enforce D4 stuck-only release? | Security §3, Data §2 | Determines HTTP adapter complexity and whether D4 is structural or policy-in-prose. |
| Q5 | Sidecar behavior at 1440×900 — resize or overlay? | End User §7 | Determines whether board readability is preserved with sidecar open. Testable with mockup. |

Q3 (benchmark) is recommended unconditionally — not a user decision, just a scheduling question.

---

## Combined Confidence: 0.83

Strong convergence on stack, security posture, polling mechanism, layout pattern, and interaction model. The 0.17 uncertainty is concentrated in: (a) the O6 concurrent-write tension (Data, 0.78 confidence), (b) sidecar width viability at reference viewport (End User, 0.82 confidence), and (c) PDS card customization fit (Architect, 0.85 confidence — validate with prototype). No panelist contradicts another's core position; disagreements are additive constraints, not incompatible stances.
