import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { project } from "/assets/ui.mjs";
import { state } from "./state.mjs";

// The clone whose Maintenance page holds an origin's Suppression review: the page's project when it is a clone of
// that origin, else the first loaded clone of it that the machine host knows by id.
function cloneOf(origin) {
  const clones = state.loaded.clones.filter((c) => c.id && c.name === origin);
  return clones.find((c) => c.id === project) ?? clones[0];
}

function maintenance(origin) {
  const c = origin ? cloneOf(origin) : undefined, named = origin || "no project";
  if (!c) {
    return html`<p-text size="sm">Suppression review of ${named}: open the
      <a href="/maintenance">Maintenance page</a> and choose a project there.</p-text>`;
  }
  const to = `/maintenance?project=${encodeURIComponent(c.id)}#audit-suppressions`;
  return html`<p-text size="sm"><a href=${to}>Suppression review of ${named}</a> on the Maintenance page
    </p-text>`;
}

// The untriaged entries the Suppression review filed, folded below Open: first a way to each origin's Suppression
// review, then the entries as the Inbox lists them. Nothing when none passes the filters.
export function reviews(entries, listed) {
  if (!entries.length) return nothing;
  const origins = [...new Set(entries.map((e) => e.origin))];
  return html`<details id="suppression-reviews" class="later">
    <summary id="reviews-title">Suppression reviews (${entries.length})</summary>
    <div class="maintenance">${origins.map(maintenance)}</div>
    ${listed}
  </details>`;
}
