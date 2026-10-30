import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { overview } from "/assets/page/overview/overview.mjs";

const TAGS = { failed: "error", running: "info" };

// A project's maintenance at a glance: the last run of each action that keeps a record, and any that failed or runs.
function said(actions) {
  const recorded = actions.filter((a) => a.built && a.recorded);
  const tags = recorded.filter((a) => TAGS[a.last?.state]).map((a) => html`<p-tag compact="true"
    variant=${TAGS[a.last.state]}>${a.name} ${a.last.state}</p-tag>`);
  if (!recorded.length) return [nothing, html`<p-text size="sm" class="runs">No action keeps a run record.</p-text>`];
  const run = (a) => {
    if (!a.last) return `${a.name}: never run`;
    const at = a.last.ended_at || a.last.started_at;
    return `${a.name}: ${a.last.state}${at ? `, ${new Date(at).toLocaleString()}` : ""}`;
  };
  return [tags.length ? tags : nothing, html`<ul class="runs">${recorded.map((a) => html`<li>${run(a)}</li>`)}</ul>`];
}

// One summary per project, each opening its maintenance (D-01M63C6PMT4FX370W6B2VS9HAM); *live()* says it shows.
export function maintained(show, live) {
  return overview({ path: "/maintenance", said, show, live });
}
