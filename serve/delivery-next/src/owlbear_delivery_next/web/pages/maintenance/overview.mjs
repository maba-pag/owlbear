import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { overview } from "/assets/page/overview/overview.mjs";

const TAGS = { failed: "error", running: "info" };
const BY = { curation: "memory curator", owner: "your memory action" };

// An action's last run in words: who ran it when two can (D-01M63CF1XKCCF6TP60734BTMWD), then what and when.
export function lastSaid(last) {
  const at = last.ended_at || last.started_at;
  const when = at ? `, ${new Date(at).toLocaleString()}` : "";
  return [BY[last.by] ? ` (${BY[last.by]})` : "", `${last.action ?? last.state}${when}`];
}

// A project's maintenance at a glance: the last run of each action that keeps a record, and any that failed or runs.
function said(actions) {
  const recorded = actions.filter((a) => a.built && a.recorded);
  const tags = recorded.filter((a) => TAGS[a.last?.state]).map((a) => html`<p-tag compact="true"
    variant=${TAGS[a.last.state]}>${a.name} ${a.last.state}</p-tag>`);
  if (!recorded.length) return [nothing, html`<p-text size="sm" class="runs">No action keeps a run record.</p-text>`];
  const run = (a) => {
    if (!a.last) return `${a.name}: never run`;
    const [by, what] = lastSaid(a.last);
    // A qualification of what it shows stays; a tagged run's reason waits on the project's own page.
    const note = a.last.reason && !TAGS[a.last.state] ? ` — ${a.last.reason}` : "";
    return `${a.name}${by}: ${what}${note}`;
  };
  return [tags.length ? tags : nothing, html`<ul class="runs">${recorded.map((a) => html`<li>${run(a)}</li>`)}</ul>`];
}

// One summary per project, each opening its maintenance (D-01M63C6PMT4FX370W6B2VS9HAM); *live()* says it shows.
export function maintained(show, live) {
  return overview({ path: "/maintenance", said, show, live });
}
