# First-Principles Stance — Cockpit Decisions Tab

## Irreducible Claims

After stripping the framing, the actual load-bearing claims are:

1. **The cockpit needs more than one view.** At least three tabs are planned (kanban, decisions, memory). This is the real driver — not "decisions are hard to find."
2. **Pending DRs need a resolution flow.** This already exists (sidecar + modal). The question is whether the existing surface is insufficient.
3. **Resolved DRs should be visible somewhere.** Currently invisible. This is the only genuinely new capability.

Everything else in the outcomes derives from these three or is inherited structure.

## Assumptions Challenged

### A1 — "Cockpit feels incomplete" is not a problem statement

The framing says the trigger is "the cockpit feels incomplete." That's a desire for a different product shape, not a user pain. No one is failing to resolve DRs. No one reported that the sidecar is inadequate. The honest claim is: **"we want the cockpit to become a multi-view dashboard, and decisions is the first non-kanban view."**

This matters because it changes the success criterion. "Feels complete" is unfalsifiable. "Has a working multi-tab architecture with N tabs" is testable.

**Challenge:** Reframe the problem as "establish multi-tab cockpit architecture" and treat decisions content as the proving payload — not the motivation.

### A2 — Bundling infrastructure + content is a choice, not a necessity

The brief bundles two independent deliverables:
- Tab/route infrastructure (general, reusable)
- Decisions list/detail view (specific content)

These are coupled only by scheduling convenience. The tab system could ship with a placeholder second tab. The decisions view could ship as an improved sidecar without tabs. Bundling them means the tab system is shaped by decisions-specific needs (split layout, deep links) before seeing what Memory or Notebook need. That risks over-fitting the "pluggable" pattern to a single consumer.

**Challenge:** Is the tab system better designed after two tabs exist, not one? Would shipping tab infrastructure with a minimal stub (even an empty "Decisions" label that opens the existing sidecar content in a full-page layout) yield a more honest general pattern?

### A3 — Split list+detail assumes volume that may not exist

The two-panel layout (list + detail) is a standard dashboard pattern. But how many DRs exist at any point? If a typical project has 1–5 pending DRs and a handful of resolved ones, the list panel is a short list that barely justifies its own column. The layout was inherited from "this is what dashboards look like," not from measured cardinality.

**Challenge:** What is the actual DR volume? If it's low, a simpler layout (single list with expandable rows, or click-to-detail navigation) may be more appropriate than a permanent two-column split.

### A4 — Deep-link receiver without sender is speculative infrastructure

The outcomes include "deep-link receiver" but scope out the sender (kanban cross-nav). A receiver that nobody calls is dead code. The justification is "optional for V1" — but that means V1 ships code that does nothing until a future task wires the sender.

**Challenge:** Either include the sender or drop the receiver. A route parameter that React Router already handles for free (`/decisions/:id`) doesn't need to be called out as an outcome — it's an implementation detail, not a feature.

### A5 — "Resolved DRs should be browsable" is unvalidated

The only new capability is viewing resolved DRs. But who browses resolved decisions and when? If the answer is "during audits or retrospectives," that's a low-frequency need that might not justify a full tab — a simple "show resolved" toggle on the existing popover could suffice.

**Challenge:** Name the actor and trigger for browsing resolved DRs. If it's speculative, downgrade it from outcome to nice-to-have.

## What Actually Needs to Be True

After reduction:

1. The cockpit must support multiple top-level views with URL-based routing. (Real — three tabs are planned.)
2. Adding a new view must require only a route definition and a nav entry. (Real — but can only be validated when the second and third tabs arrive.)
3. Decisions need a view that shows both pending and resolved items with resolution capability. (Partially real — resolution exists; resolved-DR browsing is unvalidated.)

## Confidence

**0.82** — The tab infrastructure need is genuine and well-motivated by planned tabs. The decisions content is reasonable as a proving payload but carries smuggled assumptions about layout and deep-linking that should be tested against actual usage patterns before hardening.
