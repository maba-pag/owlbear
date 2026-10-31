import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { here } from "/assets/ui.mjs";

const HEADS = ["Agent", "Project", "Sessions", "Compacted", "Compactions", "How early (median)", "Earliest",
  "Context setting"];
const LAYERS = { project: "project layer", machine: "This machine", global: "Global" };

const percent = (share) => `${Math.round(share * 100)}%`;

function sessions(r) {
  const more = [r.missing ? `${r.missing.toLocaleString()} without a log` : "",
    r.unreadable ? `${r.unreadable.toLocaleString()} unreadable` : ""].filter(Boolean);
  return [r.sessions.toLocaleString(), ...more].join(" · ");
}

// A link to where the role's context is set, on the project and layer whose value applies, or why there is none.
function setting(role, e) {
  if (e.why) return html`<span>${e.name}: ${e.why}</span>`;
  const text = `${e.project ? `${e.name}: ` : ""}${LAYERS[e.layer]}${e.unset ? " (unset)" : ""}`;
  const back = `${location.pathname}${location.search}#compaction`;
  return html`<a href=${here({ project: e.clone, layer: e.layer, back }, `/config#set-agents-${role}`)}
    aria-label=${`${text}, ${role}'s context setting`}>${text}</a>`;
}

function row(r) {
  const agent = r.subagent ? `${r.subagent} (subagent of ${r.agent})` : r.agent;
  const where = r.project === null ? "All projects" : r.project === "" ? "This machine" : r.name || r.project;
  const links = r.subagent ? "–" : html`${r.settings.map((e, i) => html`${i ? html`<br>` : nothing}${setting(r.agent,
    e)}`)}`;
  return html`<p-table-row><p-table-cell>${agent}</p-table-cell><p-table-cell>${where}</p-table-cell>
    <p-table-cell class="num">${sessions(r)}</p-table-cell>
    <p-table-cell class="num">${r.logs ? `${r.compacted} of ${r.logs} (${percent(r.compacted / r.logs)})` : "–"}
    </p-table-cell>
    <p-table-cell class="num">${r.compactions.toLocaleString()}</p-table-cell>
    <p-table-cell class="num">${r.median == null ? "–" : `${percent(r.median)} of its model calls`}</p-table-cell>
    <p-table-cell class="num">${r.earliest == null ? "–" : percent(r.earliest)}</p-table-cell>
    <p-table-cell>${links}</p-table-cell></p-table-row>`;
}

/** Per agent, how often its sessions compacted their context and how early, with links to its context setting. */
export function compaction(c) {
  const read = c.rows.some((r) => r.logs);
  return html`<section id="compaction" aria-labelledby="compaction-title">
    <p-heading size="lg"><h2 id="compaction-title" tabindex="-1">Context compaction</h2></p-heading>
    <p-text size="sm">A session compacts its context when its conversation nears the model's context window: the
      runtime replaces earlier turns with a summary. How early is the share of the agent's model calls made before
      its first compaction, over the sessions that compacted; only sessions whose runtime log is readable count.
      </p-text>
    ${c.rows.length ? html`<p-table id="compaction-table" caption="Compaction per agent"><p-table-head>
      <p-table-head-row>${HEADS.map((h) => html`<p-table-head-cell>${h}</p-table-head-cell>`)}</p-table-head-row>
      </p-table-head><p-table-body>${c.rows.map(row)}</p-table-body></p-table>` : nothing}
    ${read ? nothing : html`<p-text id="compaction-none" size="sm">No session of these filters has a readable log.
      </p-text>`}
    ${c.errors.length || c.settings_errors?.length ? html`<ul id="compaction-errors" class="notes">
      ${c.errors.map((e) => html`<li class="error">Could not read the log of session ${e.session}
        (${e.project || "this machine"}): ${e.error}</li>`)}
      ${(c.settings_errors ?? []).map((e) => html`<li class="error">Could not read the settings of ${e.project}
        (${e.file}): ${e.error}</li>`)}</ul>` : nothing}
  </section>`;
}

let arrived = false;

// Arriving at #compaction, from a context setting's way back: the section scrolls into view with its heading focused.
export function arrive() {
  const title = document.getElementById("compaction-title");
  if (arrived || location.hash !== "#compaction" || !title) return;
  arrived = true;
  title.scrollIntoView({ block: "start" });
  title.focus({ preventScroll: true });
}
