import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { here } from "/assets/ui.mjs";
import { overview } from "/assets/page/overview/overview.mjs";
import { show, wide } from "./state.mjs";

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

// What a scope's list says at a glance: what is in force and drafted, and what waits on the owner.
function said(got) {
  const count = (test) => got.decisions.filter(test).length;
  const waiting = got.queue?.length ?? 0, conflicts = count((d) => d.conflict);
  const problems = count((d) => d.findings && !d.conflict);
  const tags = html`${waiting ? html`<p-tag compact="true" variant="info">${plural(waiting, "read-back")} waiting
    </p-tag>` : nothing}
    ${conflicts ? html`<p-tag compact="true" variant="error">${plural(conflicts, "conflict")}</p-tag>` : nothing}
    ${problems ? html`<p-tag compact="true" variant="warning">${plural(problems, "problem")}</p-tag>` : nothing}`;
  const text = `${count((d) => d.state === "in_force")} in force · ${plural(count((d) => d.state === "draft"),
    "draft")}`;
  return [tags, html`<p-text size="sm" class="counts">${text}</p-text>`];
}

export const scopes = overview({
  fixed: [
    { key: "global", name: "Global", href: here({ view: "global" }), path: "/owlbear/decisions?where=global" },
    { key: "owlbear", name: "OwlBear", href: here({ view: "owlbear" }), path: "/owlbear/decisions?where=project" },
  ],
  path: "/decisions?where=project", said, unread: (got) => (got.available ? "" : got.reason || "it is unavailable"),
  show: () => show(), live: () => wide === "",
});

export function scopesView() {
  return scopes.view({ id: "scopes", heading: "Decisions by scope",
    intro: "Global and OwlBear's own decisions, then each project's. Open one to read and act on its decisions." });
}
