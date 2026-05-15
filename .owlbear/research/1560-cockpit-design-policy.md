<!-- markdownlint-disable MD013 MD060 -->

# Cockpit Design Policy

> **Owning task:** #1560 - P2-01: Decide Cockpit PDS policy and redesign constraints  
> **Related DR:** #1534 - `.owlbear/kanban/decisions/resolved/1534-decision.md`  
> **Date:** 2026-05-14 **Status:** Approved policy package

## 1. Context And Question

Cockpit's Board Visual Design pass improved cards and columns but did not produce a polished dashboard. The consolidated audit found that the remaining failures are systemic: shell chrome, sidecar, filters, overlays, dialogs, responsive behavior, and visual gates were not designed as one product surface.

Question: what design policy should govern the next Cockpit remediation cycle so child tasks do not false-green with isolated local polish?

## 2. Sources Studied

| Source | What It Establishes | Confidence |
|---|---|---:|
| `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` | Current visual failures, PDS capability gap, asset-mode finding, and remediation lanes | 0.95 |
| `serve/cockpit/README.md` | Cockpit product boundary, frontend stack, PDS local runtime packaging, decision lifecycle | 0.90 |
| `share/skills/h-frontend-conventions/SKILL.md` | Cockpit should use PDS components/tokens and prove PDS behavior with proper jsdom or Playwright evidence | 0.88 |
| `share/skills/h-frontend-design/SKILL.md` | Cockpit defaults to a dense developer-operations work surface, not marketing composition | 0.86 |
| PDS v4 docs listed in `.owlbear/sources/overview.md` | PDS provides component, overlay, token, spacing, select, popover, and theme guidance | 0.84 |

Audit section mapping required by #1560 AC-4/AC-5 evidence:

- Section 4: component-level findings that drive the PDS visible-control policy in Section 5.
- Section 7: visual target and composition findings that drive Sections 4 and 6.
- Section 8: remediation lane structure that informs Section 8 follow-up task mapping.
- Section 9: implementation and verification gates that inform Section 7 required visual gates.

## 3. Decision

Approve a full coordinated Cockpit dashboard redesign cycle.

This is not a CDN or token-only problem. PDS custom elements already hydrate from local pinned assets. The visual failure is composition: Cockpit mixes PDS, native controls, raw lists, raw dialogs, scattered inline styles, and underdesigned sidecar/chrome surfaces.

## 4. Visual Target

Cockpit is a developer-operations cockpit: quiet, dense, predictable, and optimized for repeated scanning and action.

Required qualities:

- Visible product identity without landing-page or hero treatment.
- Compact dashboard chrome with clear status, navigation, task inspection, and decision-resolution roles.
- Information density high enough for operations work, with hierarchy and whitespace used to organize rather than decorate.
- Typography hierarchy based on PDS text/heading patterns where practical; no oversized display type inside dashboard panels.
- Surface/elevation rules that distinguish app chrome, board columns, task cards, inspector sections, overlays, and blocking dialogs.
- Empty states that are intentionally quiet and useful, not raw placeholder strings.
- Icons/actions that use PDS/lucide-equivalent semantics when available; custom symbols require an explicit exception.

## 5. PDS Visible-Control Policy

PDS-first applies to every visible production control. Exceptions are allowed only when the policy or task notes name the reason and test strategy.

| Cockpit Need | Required Default | Accepted Exception Pattern |
|---|---|---|
| Icon or compact action | `PButtonPure` or appropriate PDS button | Native button only when PDS cannot expose required a11y/test behavior; document proof path |
| Primary/secondary command | `PButton` | Native button only for browser-required semantics that PDS cannot satisfy |
| Compact disclosure | `PPopover` | None for status/header disclosures unless PDS runtime blocks the use case |
| Blocking confirmation/decision | `PModal` | Native dialog only with explicit accessibility proof and follow-up to replace |
| Dense side workflow | `PSheet` | In-layout inspector section when the workflow is persistent, not temporary |
| Search | `PInputSearch` | Native input only with documented jsdom limitation and Playwright coverage |
| Binary filter/setting | `PSwitch` or `PCheckbox` | Native checkbox only when preserving native form behavior is intentionally required |
| Select/dropdown | `PSelect` plus `PSelectOption` | Native options are not accepted inside PDS selects unless a task documents why |
| Metadata/status chip | `PTag` or `PTagDismissible` | Raw spans only for non-interactive text where chip semantics are wrong |
| Activity filters | `PSegmentedControl` | Button group only if PDS segmented control cannot support the filter contract |
| Structured activity/history | `PTable`, `PTextList`, or structured rows with PDS typography | Raw `ul/li` only for true prose lists |
| Separators | `PDivider` or tokenized borders | Custom borders only when tied to an existing layout surface rule |

## 6. Surface Policies

### Shell And Status Bar

The shell must communicate Cockpit identity and workflow roles at a glance. Status controls must not look like unrelated buttons, and opening status details must never reflow the header or board.

### Sidecar Inspector

The sidecar is an inspector, not debug output. It needs a clear selected-task header, metadata rows, tags/dependencies, body, actions, activity, and empty states. Pending decision requests may remain there only if they are composed as a subordinate queue. If they dominate the inspector, move them to a `PSheet` or dedicated route.

### Overlays

Use `PPopover` for compact status disclosure, `PModal` for blocking confirmation/decision, and `PSheet` for dense workflows. Health, DR, Cleanup, ConfirmDialog, ResolveModal, ArchivalModal, RepairPanel, and the task context menu are all overlay surfaces and need consistent behavior and tests.

### Filters And Forms

Filters need a designed toolbar/panel, not a raw inline block. Use PDS search/select/switch/checkbox controls, active filter chips/count, clear action placement, and compact field grouping. Opening filters must not create accidental layout jumps.

### Cards And Columns

Cards must support scanning beyond title-only content: task ID, title, priority/status tag, first tags with overflow behavior, blocked/claimed indicator, compact age or update-recency signal, and non-color signal text or icon. Columns must use polished labels, count badges, focusable scroll regions, and intentional empty states.

### Responsive Contract

320px no-overflow remains a hard gate. Preferred mobile contract is board-first with sidecar/detail in a sheet. If full mobile support proves too expensive, use a controlled narrow-view state instead of a broken compressed desktop layout.

### Asset Mode

Keep local pinned PDS runtime assets. Live CDN mode is not a visual-remediation tool and must not be introduced unless the product explicitly changes CSP, offline-after-build, and consumer packaging constraints.

## 7. Required Visual Gates

Every Cockpit visual remediation wave must include screenshot or real-browser visual evidence for:

- Desktop home board.
- Desktop selected-task sidecar.
- Filter panel open with active filters.
- Task context menu open.
- Health and DR disclosures.
- Cleanup/resolve/archival modal or sheet state.
- Dark mode.
- Tablet viewport.
- 320px viewport.

Structural gates must also reject:

- Document-level horizontal overflow at supported widths.
- In-flow popovers/dialogs that expand the status bar or board.
- Raw native controls in core visible flows without documented exception.
- Scrollable regions without keyboard focusability.
- Core visible controls removed from normal tab order without a documented focus-management exception.
- Color-only task state signaling.

## 8. Follow-Up Task Mapping

| Policy Area | Owning Tasks |
|---|---|
| Shell, sidecar, status, nav, activity | #1562, #1568 |
| Overlay system and context menu | #1563, #1569 |
| Filters and form controls | #1564, #1570 |
| Task card information density | #1565, #1571 |
| Responsive contract | #1566, #1572 |
| Theme bootstrap and PDS asset bug lane | #1561, #1567 |
| Column polish and empty states | #1574, #1575 |
| Final consolidation and screenshot gates | #1573 |

## 9. Recommendation

Proceed with the task graph under #1559 using this policy as the shared target. Do not advance design-dependent implementation tasks unless their RED criteria carry the relevant PDS component contracts, responsive contract, and screenshot/structural gates from this document.

Challenge: proceed - confidence in recommendation 0.90. The main risk is scope size; the existing task graph mitigates it by splitting work into RED/GREEN pairs and keeping #1573 as the final consolidation gate.